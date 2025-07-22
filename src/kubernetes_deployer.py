"""
Kubernetes Deployer pour DATA_BOT v4
Utilitaire pour déployer et gérer l'application sur Kubernetes
"""

import asyncio
import logging
import yaml
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

try:
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException
    KUBERNETES_AVAILABLE = True
except ImportError:
    KUBERNETES_AVAILABLE = False

logger = logging.getLogger(__name__)

class KubernetesDeployer:
    """Déployeur Kubernetes pour DATA_BOT v4"""
    
    def __init__(self, namespace: str = "databot-v4", kubeconfig_path: Optional[str] = None):
        """
        Initialise le déployeur Kubernetes
        
        Args:
            namespace: Namespace Kubernetes
            kubeconfig_path: Chemin vers le fichier kubeconfig
        """
        if not KUBERNETES_AVAILABLE:
            raise ImportError("kubernetes-client n'est pas installé")
        
        self.namespace = namespace
        self.kubeconfig_path = kubeconfig_path
        
        # Clients Kubernetes
        self.core_v1 = None
        self.apps_v1 = None
        self.networking_v1 = None
        
        # Chemins des manifests
        self.manifests_dir = Path(__file__).parent.parent / "k8s"
        
        # Configuration de déploiement
        self.deployment_config = {
            "development": {
                "replicas": 1,
                "resources": {
                    "requests": {"memory": "512Mi", "cpu": "250m"},
                    "limits": {"memory": "2Gi", "cpu": "1000m"}
                }
            },
            "staging": {
                "replicas": 2,
                "resources": {
                    "requests": {"memory": "1Gi", "cpu": "500m"},
                    "limits": {"memory": "4Gi", "cpu": "2000m"}
                }
            },
            "production": {
                "replicas": 3,
                "resources": {
                    "requests": {"memory": "2Gi", "cpu": "1000m"},
                    "limits": {"memory": "8Gi", "cpu": "4000m"}
                }
            }
        }
    
    async def initialize(self):
        """Initialise la connexion Kubernetes"""
        try:
            # Charger la configuration Kubernetes
            if self.kubeconfig_path:
                config.load_kube_config(config_file=self.kubeconfig_path)
            else:
                try:
                    # Essayer la config in-cluster (si on est dans un pod)
                    config.load_incluster_config()
                except:
                    # Sinon charger la config locale
                    config.load_kube_config()
            
            # Initialiser les clients
            self.core_v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()
            self.networking_v1 = client.NetworkingV1Api()
            
            logger.info("Connexion Kubernetes initialisée")
            
        except Exception as e:
            logger.error(f"Erreur initialisation Kubernetes: {e}")
            raise
    
    async def deploy(self, environment: str = "development", 
                    replicas: Optional[int] = None,
                    image_tag: str = "latest") -> Dict[str, Any]:
        """
        Déploie l'application sur Kubernetes
        
        Args:
            environment: Environnement (development, staging, production)
            replicas: Nombre de répliques (optionnel)
            image_tag: Tag de l'image Docker
            
        Returns:
            Résultat du déploiement
        """
        if not self.core_v1:
            await self.initialize()
        
        logger.info(f"Déploiement DATA_BOT v4 - Environnement: {environment}")
        
        deployment_result = {
            "namespace": self.namespace,
            "environment": environment,
            "image_tag": image_tag,
            "timestamp": datetime.now().isoformat(),
            "status": "starting",
            "components": {}
        }
        
        try:
            # 1. Créer le namespace et la configuration
            await self._deploy_namespace_and_config()
            deployment_result["components"]["namespace"] = "success"
            
            # 2. Déployer les bases de données
            await self._deploy_databases()
            deployment_result["components"]["databases"] = "success"
            
            # 3. Déployer les moteurs de recherche
            await self._deploy_search_engines()
            deployment_result["components"]["search_engines"] = "success"
            
            # 4. Déployer l'application principale
            await self._deploy_main_application(environment, replicas, image_tag)
            deployment_result["components"]["main_application"] = "success"
            
            # 5. Vérifier le déploiement
            health_status = await self._check_deployment_health()
            deployment_result["health_check"] = health_status
            
            if health_status["overall_status"] == "healthy":
                deployment_result["status"] = "success"
                logger.info("Déploiement réussi ✅")
            else:
                deployment_result["status"] = "partial"
                logger.warning("Déploiement partiellement réussi ⚠️")
            
            return deployment_result
            
        except Exception as e:
            logger.error(f"Erreur lors du déploiement: {e}")
            deployment_result["status"] = "failed"
            deployment_result["error"] = str(e)
            return deployment_result
    
    async def _deploy_namespace_and_config(self):
        """Déploie le namespace et la configuration"""
        manifest_path = self.manifests_dir / "01-namespace-config.yaml"
        await self._apply_manifest(manifest_path)
    
    async def _deploy_databases(self):
        """Déploie les bases de données"""
        manifest_path = self.manifests_dir / "03-databases.yaml"
        await self._apply_manifest(manifest_path)
        
        # Attendre que les bases de données soient prêtes
        await self._wait_for_deployment_ready("postgres")
        await self._wait_for_deployment_ready("redis")
    
    async def _deploy_search_engines(self):
        """Déploie les moteurs de recherche"""
        manifest_path = self.manifests_dir / "04-search-engines.yaml"
        await self._apply_manifest(manifest_path)
        
        # Attendre que les moteurs de recherche soient prêts
        await self._wait_for_deployment_ready("elasticsearch")
        await self._wait_for_deployment_ready("opensearch")
        await self._wait_for_deployment_ready("qdrant")
    
    async def _deploy_main_application(self, environment: str, 
                                     replicas: Optional[int], 
                                     image_tag: str):
        """Déploie l'application principale"""
        # Charger le manifest
        manifest_path = self.manifests_dir / "02-databot-deployment.yaml"
        
        with open(manifest_path, 'r') as f:
            manifests = list(yaml.safe_load_all(f))
        
        # Modifier la configuration selon l'environnement
        env_config = self.deployment_config.get(environment, self.deployment_config["development"])
        
        for manifest in manifests:
            if manifest["kind"] == "Deployment" and manifest["metadata"]["name"] == "databot-v4":
                # Mettre à jour les répliques
                if replicas:
                    manifest["spec"]["replicas"] = replicas
                else:
                    manifest["spec"]["replicas"] = env_config["replicas"]
                
                # Mettre à jour l'image
                container = manifest["spec"]["template"]["spec"]["containers"][0]
                container["image"] = f"databot:v4-{image_tag}"
                
                # Mettre à jour les ressources
                container["resources"] = env_config["resources"]
        
        # Appliquer les manifests modifiés
        await self._apply_manifests(manifests)
        
        # Attendre que l'application soit prête
        await self._wait_for_deployment_ready("databot-v4")
    
    async def _apply_manifest(self, manifest_path: Path):
        """Applique un fichier manifest"""
        logger.info(f"Application du manifest: {manifest_path}")
        
        with open(manifest_path, 'r') as f:
            manifests = list(yaml.safe_load_all(f))
        
        await self._apply_manifests(manifests)
    
    async def _apply_manifests(self, manifests: List[Dict[str, Any]]):
        """Applique une liste de manifests"""
        for manifest in manifests:
            if not manifest:
                continue
            
            kind = manifest["kind"]
            name = manifest["metadata"]["name"]
            
            try:
                if kind == "Namespace":
                    await self._apply_namespace(manifest)
                elif kind == "ConfigMap":
                    await self._apply_configmap(manifest)
                elif kind == "Secret":
                    await self._apply_secret(manifest)
                elif kind == "PersistentVolumeClaim":
                    await self._apply_pvc(manifest)
                elif kind == "Deployment":
                    await self._apply_deployment(manifest)
                elif kind == "Service":
                    await self._apply_service(manifest)
                elif kind == "Ingress":
                    await self._apply_ingress(manifest)
                else:
                    logger.warning(f"Type de ressource non supporté: {kind}")
                
                logger.debug(f"✅ {kind}/{name} appliqué")
                
            except ApiException as e:
                if e.status == 409:  # Already exists
                    logger.debug(f"⚠️ {kind}/{name} existe déjà")
                else:
                    logger.error(f"❌ Erreur pour {kind}/{name}: {e}")
                    raise
    
    async def _apply_namespace(self, manifest: Dict[str, Any]):
        """Applique un namespace"""
        try:
            self.core_v1.create_namespace(body=manifest)
        except ApiException as e:
            if e.status != 409:  # Not "already exists"
                raise
    
    async def _apply_configmap(self, manifest: Dict[str, Any]):
        """Applique un ConfigMap"""
        try:
            self.core_v1.create_namespaced_config_map(
                namespace=self.namespace,
                body=manifest
            )
        except ApiException as e:
            if e.status == 409:
                # Mettre à jour si existe
                self.core_v1.patch_namespaced_config_map(
                    name=manifest["metadata"]["name"],
                    namespace=self.namespace,
                    body=manifest
                )
            else:
                raise
    
    async def _apply_secret(self, manifest: Dict[str, Any]):
        """Applique un Secret"""
        try:
            self.core_v1.create_namespaced_secret(
                namespace=self.namespace,
                body=manifest
            )
        except ApiException as e:
            if e.status == 409:
                # Mettre à jour si existe
                self.core_v1.patch_namespaced_secret(
                    name=manifest["metadata"]["name"],
                    namespace=self.namespace,
                    body=manifest
                )
            else:
                raise
    
    async def _apply_pvc(self, manifest: Dict[str, Any]):
        """Applique un PersistentVolumeClaim"""
        try:
            self.core_v1.create_namespaced_persistent_volume_claim(
                namespace=self.namespace,
                body=manifest
            )
        except ApiException as e:
            if e.status != 409:  # PVC can't be updated
                raise
    
    async def _apply_deployment(self, manifest: Dict[str, Any]):
        """Applique un Deployment"""
        try:
            self.apps_v1.create_namespaced_deployment(
                namespace=self.namespace,
                body=manifest
            )
        except ApiException as e:
            if e.status == 409:
                # Mettre à jour si existe
                self.apps_v1.patch_namespaced_deployment(
                    name=manifest["metadata"]["name"],
                    namespace=self.namespace,
                    body=manifest
                )
            else:
                raise
    
    async def _apply_service(self, manifest: Dict[str, Any]):
        """Applique un Service"""
        try:
            self.core_v1.create_namespaced_service(
                namespace=self.namespace,
                body=manifest
            )
        except ApiException as e:
            if e.status == 409:
                # Mettre à jour si existe
                self.core_v1.patch_namespaced_service(
                    name=manifest["metadata"]["name"],
                    namespace=self.namespace,
                    body=manifest
                )
            else:
                raise
    
    async def _apply_ingress(self, manifest: Dict[str, Any]):
        """Applique un Ingress"""
        try:
            self.networking_v1.create_namespaced_ingress(
                namespace=self.namespace,
                body=manifest
            )
        except ApiException as e:
            if e.status == 409:
                # Mettre à jour si existe
                self.networking_v1.patch_namespaced_ingress(
                    name=manifest["metadata"]["name"],
                    namespace=self.namespace,
                    body=manifest
                )
            else:
                raise
    
    async def _wait_for_deployment_ready(self, deployment_name: str, timeout: int = 300):
        """Attend qu'un déploiement soit prêt"""
        logger.info(f"Attente que le déploiement {deployment_name} soit prêt...")
        
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                deployment = self.apps_v1.read_namespaced_deployment(
                    name=deployment_name,
                    namespace=self.namespace
                )
                
                status = deployment.status
                if (status.ready_replicas and 
                    status.ready_replicas == status.replicas):
                    logger.info(f"✅ {deployment_name} est prêt")
                    return
                
                await asyncio.sleep(10)
                
            except ApiException as e:
                if e.status == 404:
                    logger.warning(f"Déploiement {deployment_name} non trouvé")
                    await asyncio.sleep(5)
                else:
                    raise
        
        raise TimeoutError(f"Timeout en attendant que {deployment_name} soit prêt")
    
    async def _check_deployment_health(self) -> Dict[str, Any]:
        """Vérifie la santé du déploiement"""
        health_status = {
            "overall_status": "healthy",
            "components": {},
            "timestamp": datetime.now().isoformat()
        }
        
        # Vérifier chaque composant
        components = [
            "databot-v4", "postgres", "redis", 
            "elasticsearch", "opensearch", "qdrant"
        ]
        
        for component in components:
            try:
                deployment = self.apps_v1.read_namespaced_deployment(
                    name=component,
                    namespace=self.namespace
                )
                
                status = deployment.status
                if (status.ready_replicas and 
                    status.ready_replicas == status.replicas):
                    health_status["components"][component] = "healthy"
                else:
                    health_status["components"][component] = "unhealthy"
                    health_status["overall_status"] = "degraded"
                
            except ApiException as e:
                health_status["components"][component] = "not_found"
                if component == "databot-v4":  # Composant critique
                    health_status["overall_status"] = "unhealthy"
        
        return health_status
    
    async def get_deployment_status(self) -> Dict[str, Any]:
        """Récupère le statut du déploiement"""
        if not self.core_v1:
            await self.initialize()
        
        return await self._check_deployment_health()
    
    async def scale_deployment(self, deployment_name: str, replicas: int) -> bool:
        """Scale un déploiement"""
        if not self.apps_v1:
            await self.initialize()
        
        try:
            # Récupérer le déploiement actuel
            deployment = self.apps_v1.read_namespaced_deployment(
                name=deployment_name,
                namespace=self.namespace
            )
            
            # Modifier le nombre de répliques
            deployment.spec.replicas = replicas
            
            # Appliquer le changement
            self.apps_v1.patch_namespaced_deployment(
                name=deployment_name,
                namespace=self.namespace,
                body=deployment
            )
            
            logger.info(f"Déploiement {deployment_name} scalé à {replicas} répliques")
            return True
            
        except ApiException as e:
            logger.error(f"Erreur lors du scaling de {deployment_name}: {e}")
            return False
    
    async def delete_deployment(self) -> bool:
        """Supprime le déploiement complet"""
        if not self.core_v1:
            await self.initialize()
        
        try:
            # Supprimer le namespace (cela supprime tout)
            self.core_v1.delete_namespace(name=self.namespace)
            logger.info(f"Namespace {self.namespace} supprimé")
            return True
            
        except ApiException as e:
            logger.error(f"Erreur lors de la suppression: {e}")
            return False

# Utilitaire CLI pour déploiement
async def main():
    """Point d'entrée CLI pour le déployeur"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Déployeur Kubernetes DATA_BOT v4")
    parser.add_argument("action", choices=["deploy", "status", "scale", "delete"])
    parser.add_argument("--environment", choices=["development", "staging", "production"], 
                       default="development")
    parser.add_argument("--namespace", default="databot-v4")
    parser.add_argument("--replicas", type=int)
    parser.add_argument("--image-tag", default="latest")
    parser.add_argument("--deployment", help="Nom du déploiement pour le scaling")
    
    args = parser.parse_args()
    
    deployer = KubernetesDeployer(namespace=args.namespace)
    
    if args.action == "deploy":
        result = await deployer.deploy(
            environment=args.environment,
            replicas=args.replicas,
            image_tag=args.image_tag
        )
        print(f"Résultat du déploiement: {result}")
        
    elif args.action == "status":
        status = await deployer.get_deployment_status()
        print(f"Statut du déploiement: {status}")
        
    elif args.action == "scale":
        if not args.deployment or not args.replicas:
            print("--deployment et --replicas sont requis pour le scaling")
            return
        
        success = await deployer.scale_deployment(args.deployment, args.replicas)
        print(f"Scaling: {'Réussi' if success else 'Échoué'}")
        
    elif args.action == "delete":
        success = await deployer.delete_deployment()
        print(f"Suppression: {'Réussie' if success else 'Échouée'}")

if __name__ == "__main__":
    asyncio.run(main())