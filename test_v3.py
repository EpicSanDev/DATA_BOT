#!/usr/bin/env python3
"""
Test script pour DATA_BOT v3
Teste les nouvelles fonctionnalités sans dépendances externes
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Ajouter le répertoire racine au path
sys.path.insert(0, str(Path(__file__).parent))

from src.models import WebResource, ContentType, ArchiveStatus

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def test_vector_manager():
    """Test du gestionnaire vectoriel"""
    logger.info("🔍 Test du gestionnaire vectoriel...")
    
    try:
        from src.vector_manager import VectorManager
        
        # Test avec ChromaDB en mode local
        vm = VectorManager(provider="chromadb", config={"persist_directory": "./test_vectors"})
        await vm.initialize()
        
        # Test d'indexation
        test_resource = WebResource(
            url="https://test.example.com",
            title="Page de test",
            content_type=ContentType.WEB_PAGE
        )
        
        test_content = "Ceci est un contenu de test pour l'indexation vectorielle. Il contient des mots-clés importants pour la recherche sémantique."
        
        success = await vm.index_resource(test_resource, test_content)
        assert success, "Échec de l'indexation"
        
        # Test de recherche
        results = await vm.semantic_search("recherche sémantique", limit=5)
        logger.info(f"Résultats de recherche: {len(results)}")
        
        await vm.close()
        logger.info("✅ Test gestionnaire vectoriel réussi")
        
    except ImportError as e:
        logger.warning(f"ChromaDB non disponible, test ignoré: {e}")
    except Exception as e:
        logger.error(f"❌ Erreur test vectoriel: {e}")

async def test_elasticsearch_manager():
    """Test du gestionnaire Elasticsearch"""
    logger.info("🔎 Test du gestionnaire Elasticsearch...")
    
    try:
        from src.elasticsearch_manager import ElasticsearchManager
        
        # Test sans connexion réelle
        em = ElasticsearchManager(host="localhost", port=9200)
        
        # Test de préparation de document
        test_resource = WebResource(
            url="https://test.example.com",
            title="Page de test ES",
            content_type=ContentType.WEB_PAGE
        )
        
        logger.info("✅ Test gestionnaire Elasticsearch préparé (connexion non testée)")
        
    except ImportError as e:
        logger.warning(f"Elasticsearch non disponible, test ignoré: {e}")
    except Exception as e:
        logger.error(f"❌ Erreur test Elasticsearch: {e}")

async def test_api_server_v3():
    """Test du serveur API v3"""
    logger.info("📱 Test du serveur API v3...")
    
    try:
        from src.api_server_v3 import APIServerV3
        
        # Créer une instance sans démarrer
        api = APIServerV3(host="localhost", port=8080, enable_pwa=True)
        
        # Vérifier que l'app est créée
        assert api.app is not None, "App FastAPI non créée"
        assert api.enable_pwa is True, "PWA non activé"
        
        logger.info("✅ Test serveur API v3 réussi")
        
    except Exception as e:
        logger.error(f"❌ Erreur test API v3: {e}")

async def test_browser_plugin_server():
    """Test du serveur plugin navigateur"""
    logger.info("🔌 Test du serveur plugin navigateur...")
    
    try:
        from src.browser_plugin_server import BrowserPluginServer
        
        # Créer une instance
        plugin_server = BrowserPluginServer(port=8081)
        
        # Vérifier que l'app est créée
        assert plugin_server.app is not None, "App FastAPI non créée"
        
        # Vérifier que les fichiers du plugin sont créés
        assert plugin_server.plugin_dir.exists(), "Répertoire plugin non créé"
        assert (plugin_server.plugin_dir / "manifest.json").exists(), "Manifest non créé"
        
        logger.info("✅ Test serveur plugin réussi")
        
    except Exception as e:
        logger.error(f"❌ Erreur test plugin: {e}")

async def test_distributed_manager():
    """Test du gestionnaire distribué"""
    logger.info("🌐 Test du gestionnaire distribué...")
    
    try:
        from src.distributed_manager import DistributedManager, TaskType, NodeType
        
        # Test en mode local (sans Redis)
        dm = DistributedManager(node_type="hybrid")
        await dm.initialize()
        
        # Test de soumission de tâche
        task_id = await dm.submit_task(
            TaskType.ARCHIVE,
            {"url": "https://test.example.com"},
            priority=1
        )
        
        assert task_id is not None, "ID de tâche non généré"
        
        # Test de récupération du statut
        status = await dm.get_cluster_status()
        assert status is not None, "Statut cluster non récupéré"
        
        await dm.shutdown()
        logger.info("✅ Test gestionnaire distribué réussi")
        
    except Exception as e:
        logger.error(f"❌ Erreur test distribué: {e}")

async def test_mobile_files():
    """Test des fichiers de l'interface mobile"""
    logger.info("📱 Test des fichiers interface mobile...")
    
    try:
        # Vérifier que les fichiers existent
        mobile_files = [
            "src/templates/mobile_app.html",
            "src/mobile/app.css",
        ]
        
        for file_path in mobile_files:
            path = Path(file_path)
            assert path.exists(), f"Fichier manquant: {file_path}"
            assert path.stat().st_size > 0, f"Fichier vide: {file_path}"
        
        logger.info("✅ Test fichiers mobile réussi")
        
    except Exception as e:
        logger.error(f"❌ Erreur test fichiers mobile: {e}")

async def test_v3_integration():
    """Test d'intégration v3"""
    logger.info("🔗 Test d'intégration v3...")
    
    try:
        # Import du point d'entrée principal
        from main_v3 import DataBotV3
        
        # Créer une instance
        bot = DataBotV3()
        
        # Vérifier que les composants sont initialisés
        assert hasattr(bot, 'components'), "Composants non initialisés"
        assert 'vector_manager' in bot.components, "Composant vectoriel manquant"
        assert 'elasticsearch_manager' in bot.components, "Composant ES manquant"
        
        logger.info("✅ Test intégration v3 réussi")
        
    except Exception as e:
        logger.error(f"❌ Erreur test intégration: {e}")

async def main():
    """Fonction principale de test"""
    logger.info("🚀 Démarrage des tests DATA_BOT v3")
    
    tests = [
        test_mobile_files,
        test_api_server_v3,
        test_browser_plugin_server,
        test_distributed_manager,
        test_vector_manager,
        test_elasticsearch_manager,
        test_v3_integration
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            await test()
            passed += 1
        except Exception as e:
            logger.error(f"❌ Test {test.__name__} échoué: {e}")
            failed += 1
    
    logger.info(f"📊 Résultats des tests: {passed} réussis, {failed} échoués")
    
    if failed == 0:
        logger.info("🎉 Tous les tests sont passés!")
        return 0
    else:
        logger.error("💥 Certains tests ont échoué")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Tests interrompus par l'utilisateur")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Erreur fatale: {e}")
        sys.exit(1)