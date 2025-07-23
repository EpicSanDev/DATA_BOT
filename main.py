"""
DATA_BOT v4 - Enterprise-grade archiving platform
- Complete admin interface
- OpenSearch support as ES alternative
- Automatic result clustering
- GraphQL API
- Machine learning categorization
- Kubernetes deployment support
- 100% Docker containerization
"""

import asyncio
import logging
import argparse
import signal
import sys
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

# Ajouter le répertoire src au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.config import Config
from src.core.models import WebResource, ArchiveStatus
from src.core.enhanced_ai_client import EnhancedAIClient
from src.database.database.database import DatabaseManager
from src.api.api_server import APIServerV4
from src.api.admin_interface import AdminInterface
from src.database.database.opensearch_manager import OpenSearchManager
from src.ml.ml_categorizer import MLCategorizer
from src.core.result_clusterer import ResultClusterer
from src.api.graphql_server import GraphQLServer

logger = logging.getLogger(__name__)

class DataBotV4(DataBotV3):
    """Classe principale pour DATA_BOT v4 avec fonctionnalités enterprise"""
    
    def __init__(self):
        super().__init__()
        
        # Nouveaux composants v4
        self.components.update({
            'opensearch_manager': None,
            'admin_interface': None,
            'ml_categorizer': None,
            'result_clusterer': None,
            'graphql_server': None,
            'api_server_v4': None
        })
        
        # Configuration v4 - Initialize as a dictionary if it doesn't exist
        if not hasattr(self, 'config'):
            self.config = {}
            
        self.config.update({
            'admin_port': int(os.getenv('ADMIN_PORT', 8082)),
            'graphql_port': int(os.getenv('GRAPHQL_PORT', 8083)),
            'use_opensearch': os.getenv('USE_OPENSEARCH', 'false').lower() == 'true',
            'enable_ml_categorization': os.getenv('ENABLE_ML_CATEGORIZATION', 'true').lower() == 'true',
            'enable_result_clustering': os.getenv('ENABLE_RESULT_CLUSTERING', 'true').lower() == 'true',
            'kubernetes_namespace': os.getenv('KUBERNETES_NAMESPACE', 'databot'),
        })
    
    async def _initialize_components(self, args):
        """Initialise tous les composants v4"""
        try:
            # Initialiser d'abord les composants v3
            await super()._initialize_components(args)
            
            # OpenSearch Manager (alternative à Elasticsearch)
            if self.config.get('use_opensearch', False) or args.enable_opensearch:
                logger.info("Initialisation d'OpenSearch...")
                from src.database.opensearch_manager import OpenSearchManager
                self.components['opensearch_manager'] = OpenSearchManager(
                    host=os.getenv('OPENSEARCH_HOST', 'localhost'),
                    port=int(os.getenv('OPENSEARCH_PORT', 9201))
                )
                await self.components['opensearch_manager'].initialize()
            
            # ML Categorizer
            if self.config.get('enable_ml_categorization', True):
                logger.info("Initialisation du catégoriseur ML...")
                from src.ml.ml_categorizer import MLCategorizer
                self.components['ml_categorizer'] = MLCategorizer()
                await self.components['ml_categorizer'].initialize()
            
            # Result Clusterer
            if self.config.get('enable_result_clustering', True):
                logger.info("Initialisation du clusterer de résultats...")
                from src.core.result_clusterer import ResultClusterer
                self.components['result_clusterer'] = ResultClusterer()
                await self.components['result_clusterer'].initialize()
            
            # GraphQL Server
            if args.enable_graphql:
                logger.info("Initialisation du serveur GraphQL...")
                from src.api.graphql_server import GraphQLServer
                self.components['graphql_server'] = GraphQLServer(
                    database_manager=self.components['database_manager'],
                    port=self.config['graphql_port']
                )
            
            # Admin Interface
            if args.enable_admin or args.mode == 'admin':
                logger.info("Initialisation de l'interface d'administration...")
                from src.api.admin_interface import AdminInterface
                self.components['admin_interface'] = AdminInterface(
                    database_manager=self.components['database_manager'],
                    port=self.config['admin_port']
                )
            
            # API Server v4 (étend v3)
            if args.mode == 'server' or args.enable_api:
                logger.info("Initialisation du serveur API v4...")
                from src.api.api_server import APIServerV4
                self.components['api_server_v4'] = APIServerV4(
                    database_manager=self.components['database_manager'],
                    opensearch_manager=self.components.get('opensearch_manager'),
                    ml_categorizer=self.components.get('ml_categorizer'),
                    result_clusterer=self.components.get('result_clusterer'),
                    port=self.config['port']
                )
            
            logger.info("Tous les composants v4 ont été initialisés avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation des composants v4: {e}")
            raise
    
    async def start_services(self, args):
        """Démarre tous les services v4"""
        tasks = []
        
        # Démarrer les services v3
        v3_tasks = await super().start_services(args)
        if v3_tasks:
            tasks.extend(v3_tasks)
        
        # GraphQL Server
        if self.components.get('graphql_server'):
            tasks.append(
                asyncio.create_task(
                    self.components['graphql_server'].start(),
                    name="graphql_server"
                )
            )
        
        # Admin Interface
        if self.components.get('admin_interface'):
            tasks.append(
                asyncio.create_task(
                    self.components['admin_interface'].start(),
                    name="admin_interface"
                )
            )
        
        # API Server v4
        if self.components.get('api_server_v4'):
            tasks.append(
                asyncio.create_task(
                    self.components['api_server_v4'].start(),
                    name="api_server_v4"
                )
            )
        
        return tasks
    
    async def run_ml_categorization(self, args):
        """Exécute la catégorisation ML sur le contenu existant"""
        if not self.components.get('ml_categorizer'):
            logger.error("ML Categorizer non initialisé")
            return
        
        logger.info("Début de la catégorisation ML...")
        
        # Récupérer toutes les ressources non catégorisées
        resources = await self.components['database_manager'].get_uncategorized_resources()
        
        total = len(resources)
        logger.info(f"Catégorisation de {total} ressources...")
        
        for i, resource in enumerate(resources, 1):
            try:
                categories = await self.components['ml_categorizer'].categorize_resource(resource)
                await self.components['database_manager'].update_resource_categories(
                    resource.id, categories
                )
                
                if i % 100 == 0:
                    logger.info(f"Progression: {i}/{total} ({i/total*100:.1f}%)")
                    
            except Exception as e:
                logger.error(f"Erreur lors de la catégorisation de {resource.url}: {e}")
        
        logger.info("Catégorisation ML terminée")
    
    async def shutdown(self):
        """Arrête proprement tous les composants v4"""
        logger = logging.getLogger(__name__)
        logger.info("🔄 Arrêt de DATA_BOT v4...")
        
        try:
            # Arrêter les composants v4 spécifiques
            if hasattr(self, 'components') and self.components:
                if self.components.get('kubernetes_deployer'):
                    logger.info("Arrêt du déployeur Kubernetes...")
                    # Note: Kubernetes deployer n'a généralement pas besoin d'arrêt explicite
                
                if self.components.get('api_server_v4'):
                    logger.info("Arrêt du serveur API v4...")
                    try:
                        await self.components['api_server_v4'].stop()
                    except Exception as e:
                        logger.warning(f"Erreur lors de l'arrêt du serveur API v4: {e}")
                
                if self.components.get('graphql_server'):
                    logger.info("Arrêt du serveur GraphQL...")
                    try:
                        await self.components['graphql_server'].stop()
                    except Exception as e:
                        logger.warning(f"Erreur lors de l'arrêt du serveur GraphQL: {e}")
                
                if self.components.get('admin_interface'):
                    logger.info("Arrêt de l'interface d'administration...")
                    try:
                        await self.components['admin_interface'].stop()
                    except Exception as e:
                        logger.warning(f"Erreur lors de l'arrêt de l'interface admin: {e}")
            
            # Appeler le nettoyage des classes parentes
            await super()._cleanup()
            logger.info("✅ DATA_BOT v4 arrêté proprement")
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'arrêt: {e}")
            raise
    
    async def run_result_clustering(self, args):
        """Exécute le clustering automatique des résultats"""
        if not self.components.get('result_clusterer'):
            logger.error("Result Clusterer non initialisé")
            return
        
        logger.info("Début du clustering des résultats...")
        
        # Récupérer toutes les ressources
        resources = await self.components['database_manager'].get_all_resources()
        
        # Effectuer le clustering
        clusters = await self.components['result_clusterer'].cluster_resources(resources)
        
        # Sauvegarder les clusters
        await self.components['database_manager'].save_clusters(clusters)
        
        logger.info(f"Clustering terminé: {len(clusters)} clusters créés")
    
    async def deploy_to_kubernetes(self, args):
        """Déploie l'application sur Kubernetes"""
        logger.info("Déploiement sur Kubernetes...")
        
        from src.utils.kubernetes_deployer import KubernetesDeployer
        deployer = KubernetesDeployer(
            namespace=self.config['kubernetes_namespace']
        )
        
        await deployer.deploy(
            environment=args.k8s_environment or 'development',
            replicas=args.k8s_replicas or 1
        )
        
        logger.info("Déploiement Kubernetes terminé")

def create_argument_parser():
    """Créé le parser d'arguments pour v4"""
    parser = argparse.ArgumentParser(description='DATA_BOT v4 - Enterprise Archiving Platform')
    
    # Modes principaux
    parser.add_argument('--mode', choices=[
        'server', 'admin', 'worker', 'ml-categorize', 'cluster', 'k8s-deploy'
    ], default='server', help='Mode de fonctionnement')
    
    # Arguments de base (hérités des versions précédentes)
    parser.add_argument("--urls", nargs="*", help="URLs de départ pour l'exploration")
    parser.add_argument("--log-level", default="INFO", help="Niveau de log")
    
    # Configuration API
    parser.add_argument("--enable-api", action="store_true", default=True, help="Activer l'API REST")
    parser.add_argument("--api-host", default="localhost", help="Host du serveur API")
    parser.add_argument("--api-port", type=int, default=8080, help="Port du serveur API")
    
    # Composants optionnels v4
    parser.add_argument('--enable-opensearch', action='store_true',
                       help='Utiliser OpenSearch au lieu d\'Elasticsearch')
    parser.add_argument('--enable-graphql', action='store_true',
                       help='Activer le serveur GraphQL')
    parser.add_argument('--enable-admin', action='store_true',
                       help='Activer l\'interface d\'administration')
    
    # Configuration planificateur
    parser.add_argument("--enable-scheduler", action="store_true", default=True, help="Activer le planificateur")
    
    # Configuration mobile (hérité de v3)
    parser.add_argument("--enable-mobile-interface", action="store_true", default=True, 
                       help="Activer l'interface mobile")
    
    # Configuration vectorielle (hérité de v3)
    parser.add_argument("--enable-vector-search", action="store_true", default=True,
                       help="Activer la recherche vectorielle")
    parser.add_argument("--vector-provider", choices=["chromadb", "qdrant"], default="chromadb",
                       help="Fournisseur de base vectorielle")
    parser.add_argument("--vector-config", help="Configuration du fournisseur vectoriel")
    parser.add_argument("--vector-action", choices=["index", "search", "reindex"], 
                       default="index", help="Action vectorielle")
    
    # Configuration Elasticsearch (hérité de v3)
    parser.add_argument("--enable-elasticsearch", action="store_true", default=True,
                       help="Activer Elasticsearch")
    parser.add_argument("--elasticsearch-host", default="localhost", help="Host Elasticsearch")
    parser.add_argument("--elasticsearch-port", type=int, default=9200, help="Port Elasticsearch")
    parser.add_argument("--es-action", choices=["index", "search", "reindex"],
                       default="index", help="Action Elasticsearch")
    
    # Configuration plugin navigateur (hérité de v3)
    parser.add_argument("--enable-browser-plugin", action="store_true", default=True,
                       help="Activer le plugin navigateur")
    parser.add_argument("--plugin-port", type=int, default=8081, help="Port du serveur plugin")
    
    # Configuration distribuée (hérité de v3)
    parser.add_argument("--enable-distributed", action="store_true", default=False,
                       help="Activer le mode distribué")
    parser.add_argument("--node-type", choices=["coordinator", "worker", "hybrid"], default="hybrid",
                       help="Type de nœud")
    parser.add_argument("--coordinator-host", default="localhost", help="Host du coordinateur")
    parser.add_argument("--coordinator-port", type=int, default=8082, help="Port du coordinateur")
    
    # Configuration export
    parser.add_argument("--export-format", choices=["json", "csv", "html", "xml", "zip"], 
                       default="json", help="Format d'export")
    parser.add_argument("--include-files", action="store_true", help="Inclure les fichiers dans l'export")
    parser.add_argument("--filter-status", help="Filtrer par statut pour l'export")
    parser.add_argument("--max-exports", type=int, default=10, help="Nombre max d'exports à conserver")
    
    # Configuration compression
    parser.add_argument("--force-recompress", action="store_true", help="Forcer la recompression")
    parser.add_argument("--auto-compress", action="store_true", default=True, help="Compression automatique")
    
    # Configuration doublons
    parser.add_argument("--check-duplicates", action="store_true", default=True, help="Vérifier les doublons")
    parser.add_argument("--remove-duplicates", action="store_true", help="Supprimer les doublons")
    parser.add_argument("--duplicate-strategy", choices=["keep_first", "keep_best", "keep_latest"], 
                       default="keep_latest", help="Stratégie de gestion des doublons")
    
    # Configuration planification
    parser.add_argument("--schedule-action", choices=["list", "add", "remove"], help="Action de planification")
    parser.add_argument("--task-name", help="Nom de la tâche à ajouter")
    parser.add_argument("--task-type", choices=["archive", "export", "cleanup", "compression", "duplicate_check"], 
                       help="Type de tâche")
    parser.add_argument("--task-frequency", choices=["once", "hourly", "daily", "weekly", "monthly"], 
                       default="daily", help="Fréquence de la tâche")
    parser.add_argument("--task-id", help="ID de la tâche pour suppression")
    
    # Configuration ML
    parser.add_argument('--ml-model', default='distilbert-base-uncased',
                       help='Modèle ML pour la catégorisation')
    parser.add_argument('--clustering-algorithm', choices=['kmeans', 'hdbscan', 'agglomerative'],
                       default='hdbscan', help='Algorithme de clustering')
    
    # Configuration Kubernetes
    parser.add_argument('--k8s-environment', choices=['development', 'staging', 'production'],
                       help='Environnement Kubernetes')
    parser.add_argument('--k8s-replicas', type=int, default=1,
                       help='Nombre de répliques Kubernetes')
    parser.add_argument('--k8s-namespace', default='databot',
                       help='Namespace Kubernetes')
    
    # Configuration Docker
    parser.add_argument('--docker-registry', help='Registre Docker pour les images')
    parser.add_argument('--docker-tag', default='latest', help='Tag Docker')
    
    return parser

async def main():
    """Point d'entrée principal pour DATA_BOT v4"""
    # Configuration du logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('logs/databot_v4.log', mode='a')
        ]
    )
    
    # Parser les arguments
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Créer l'instance DATA_BOT v4
    bot = DataBotV4()
    
    # Gestion des signaux
    def signal_handler(signum, frame):
        logger.info(f"Signal {signum} reçu, arrêt en cours...")
        asyncio.create_task(bot.shutdown())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Initialiser les composants
        await bot._initialize_components(args)
        
        # Exécuter selon le mode
        if args.mode == 'server':
            logger.info("Démarrage en mode serveur complet...")
            tasks = await bot.start_services(args)
            await asyncio.gather(*tasks)
            
        elif args.mode == 'admin':
            logger.info("Démarrage en mode administration...")
            if bot.components.get('admin_interface'):
                await bot.components['admin_interface'].start()
            else:
                logger.error("Interface d'administration non disponible")
                
        elif args.mode == 'worker':
            logger.info("Démarrage en mode worker...")
            await bot.run_continuous_processing()
            
        elif args.mode == 'ml-categorize':
            logger.info("Démarrage de la catégorisation ML...")
            await bot.run_ml_categorization(args)
            
        elif args.mode == 'cluster':
            logger.info("Démarrage du clustering...")
            await bot.run_result_clustering(args)
            
        elif args.mode == 'k8s-deploy':
            logger.info("Démarrage du déploiement Kubernetes...")
            await bot.deploy_to_kubernetes(args)
        
    except KeyboardInterrupt:
        logger.info("Arrêt demandé par l'utilisateur")
    except Exception as e:
        logger.error(f"Erreur fatale: {e}")
        raise
    finally:
        await bot.shutdown()

if __name__ == "__main__":
    # Créer les répertoires nécessaires
    for directory in ['logs', 'data', 'archive', 'screenshots', 'config']:
        Path(directory).mkdir(exist_ok=True)
    
    # Exécuter l'application
    asyncio.run(main())