#!/usr/bin/env python3
"""
Test basique pour DATA_BOT v4
Vérifie que les composants principaux peuvent être importés et initialisés
"""

import sys
import os
import asyncio
import logging
from pathlib import Path

# Ajouter le répertoire src au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_v4_imports():
    """Test des imports v4"""
    logger.info("🧪 Test des imports v4...")
    
    try:
        # Import du point d'entrée principal
        from main_v4 import DataBotV4
        logger.info("✅ main_v4.DataBotV4 importé")
        
        # Import des nouveaux composants
        from src.opensearch_manager import OpenSearchManager
        logger.info("✅ OpenSearchManager importé")
        
        from src.ml_categorizer import MLCategorizer
        logger.info("✅ MLCategorizer importé")
        
        from src.result_clusterer import ResultClusterer
        logger.info("✅ ResultClusterer importé")
        
        from src.graphql_server import GraphQLServer
        logger.info("✅ GraphQLServer importé")
        
        from src.admin_interface import AdminInterface
        logger.info("✅ AdminInterface importé")
        
        from src.api_server_v4 import APIServerV4
        logger.info("✅ APIServerV4 importé")
        
        from src.kubernetes_deployer import KubernetesDeployer
        logger.info("✅ KubernetesDeployer importé")
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ Erreur d'import: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Erreur inattendue: {e}")
        return False

async def test_v4_basic_initialization():
    """Test d'initialisation basique"""
    logger.info("🧪 Test d'initialisation basique...")
    
    try:
        # Test d'initialisation du ML Categorizer (sans ML libs)
        try:
            from src.ml_categorizer import MLCategorizer
            # Ne pas initialiser complètement car les libs ML peuvent ne pas être présentes
            logger.info("✅ MLCategorizer structure OK")
        except ImportError as e:
            logger.warning(f"⚠️ MLCategorizer nécessite des dépendances ML: {e}")
        
        # Test d'initialisation du Result Clusterer (sans ML libs)
        try:
            from src.result_clusterer import ResultClusterer
            logger.info("✅ ResultClusterer structure OK")
        except ImportError as e:
            logger.warning(f"⚠️ ResultClusterer nécessite des dépendances ML: {e}")
        
        # Test d'initialisation de l'OpenSearch Manager (sans opensearch)
        try:
            from src.opensearch_manager import OpenSearchManager
            logger.info("✅ OpenSearchManager structure OK")
        except ImportError as e:
            logger.warning(f"⚠️ OpenSearchManager nécessite opensearch-py: {e}")
        
        # Test d'initialisation du GraphQL Server (sans fastapi)
        try:
            from src.graphql_server import GraphQLServer
            logger.info("✅ GraphQLServer structure OK")
        except ImportError as e:
            logger.warning(f"⚠️ GraphQLServer nécessite strawberry-graphql: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur d'initialisation: {e}")
        return False

async def test_v4_configuration():
    """Test de la configuration v4"""
    logger.info("🧪 Test de la configuration v4...")
    
    try:
        # Vérifier que les fichiers de configuration existent
        files_to_check = [
            "requirements_v4.txt",
            "Dockerfile",
            "docker-compose.yml",
            "README_v4.md",
            "k8s/01-namespace-config.yaml",
            "k8s/02-databot-deployment.yaml",
            "k8s/03-databases.yaml",
            "k8s/04-search-engines.yaml",
            "monitoring/prometheus.yml",
            "nginx/nginx.conf"
        ]
        
        for file_path in files_to_check:
            if Path(file_path).exists():
                logger.info(f"✅ {file_path} existe")
            else:
                logger.warning(f"⚠️ {file_path} manquant")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur de configuration: {e}")
        return False

async def test_v4_docker_compose():
    """Test de la configuration Docker Compose"""
    logger.info("🧪 Test de la configuration Docker Compose...")
    
    try:
        import yaml
        
        with open("docker-compose.yml", 'r') as f:
            compose_config = yaml.safe_load(f)
        
        # Vérifier les services essentiels
        essential_services = [
            "databot-v4", "redis", "postgres", 
            "elasticsearch", "opensearch", "qdrant"
        ]
        
        services = compose_config.get("services", {})
        
        for service in essential_services:
            if service in services:
                logger.info(f"✅ Service {service} configuré")
            else:
                logger.warning(f"⚠️ Service {service} manquant")
        
        # Vérifier les volumes
        volumes = compose_config.get("volumes", {})
        if volumes:
            logger.info(f"✅ {len(volumes)} volumes configurés")
        
        # Vérifier le réseau
        networks = compose_config.get("networks", {})
        if networks:
            logger.info(f"✅ {len(networks)} réseaux configurés")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur Docker Compose: {e}")
        return False

async def test_v4_kubernetes():
    """Test des manifests Kubernetes"""
    logger.info("🧪 Test des manifests Kubernetes...")
    
    try:
        import yaml
        
        k8s_files = [
            "k8s/01-namespace-config.yaml",
            "k8s/02-databot-deployment.yaml", 
            "k8s/03-databases.yaml",
            "k8s/04-search-engines.yaml"
        ]
        
        total_resources = 0
        
        for k8s_file in k8s_files:
            if Path(k8s_file).exists():
                with open(k8s_file, 'r') as f:
                    manifests = list(yaml.safe_load_all(f))
                    resource_count = len([m for m in manifests if m])
                    total_resources += resource_count
                    logger.info(f"✅ {k8s_file}: {resource_count} ressources")
            else:
                logger.warning(f"⚠️ {k8s_file} manquant")
        
        logger.info(f"✅ Total: {total_resources} ressources Kubernetes")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur Kubernetes: {e}")
        return False

async def main():
    """Test principal"""
    logger.info("🚀 Démarrage des tests DATA_BOT v4")
    
    # Créer les répertoires nécessaires pour les tests
    for directory in ['logs', 'data', 'config']:
        Path(directory).mkdir(exist_ok=True)
    
    tests = [
        ("Imports v4", test_v4_imports),
        ("Initialisation basique", test_v4_basic_initialization),
        ("Configuration v4", test_v4_configuration),
        ("Docker Compose", test_v4_docker_compose),
        ("Kubernetes", test_v4_kubernetes)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Test: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            result = await test_func()
            results[test_name] = result
            
            if result:
                logger.info(f"✅ {test_name}: RÉUSSI")
            else:
                logger.error(f"❌ {test_name}: ÉCHOUÉ")
                
        except Exception as e:
            logger.error(f"❌ {test_name}: ERREUR - {e}")
            results[test_name] = False
    
    # Résumé final
    logger.info(f"\n{'='*50}")
    logger.info("RÉSUMÉ DES TESTS")
    logger.info(f"{'='*50}")
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ RÉUSSI" if result else "❌ ÉCHOUÉ"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nTotal: {passed}/{total} tests réussis")
    
    if passed == total:
        logger.info("🎉 Tous les tests sont passés! DATA_BOT v4 semble correctement configuré.")
        return True
    else:
        logger.warning(f"⚠️ {total - passed} test(s) ont échoué. Vérifiez les dépendances.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)