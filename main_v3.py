"""
DATA_BOT v3 - Point d'entrée principal avec fonctionnalités avancées
- Interface mobile native (PWA)
- Support bases vectorielles (Qdrant/ChromaDB)
- Intégration Elasticsearch
- Plugin navigateur
- Mode distribué multi-machines
"""

import asyncio
import logging
import argparse
import signal
import sys
import os
from datetime import datetime
from typing import List, Optional

# Ajouter le répertoire src au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config import Config
from src.models import WebResource, ArchiveStatus
from src.enhanced_ai_client import EnhancedAIClient
from src.database import DatabaseManager
from src.api_server_v3 import APIServerV3
from src.vector_manager import VectorManager
from src.elasticsearch_manager import ElasticsearchManager
from src.browser_plugin_server import BrowserPluginServer
from src.distributed_manager import DistributedManager
from main_v2 import DataBotV2

logger = logging.getLogger(__name__)

class DataBotV3(DataBotV2):
    """Classe principale pour DATA_BOT v3 avec fonctionnalités avancées"""
    
    def __init__(self):
        super().__init__()
        
        # Nouveaux composants v3
        self.components.update({
            'vector_manager': None,
            'elasticsearch_manager': None,
            'browser_plugin_server': None,
            'distributed_manager': None,
            'api_server_v3': None
        })
    
    async def _initialize_components(self, args):
        """Initialise tous les composants v2 + v3"""
        # Initialiser les composants v2 d'abord
        await super()._initialize_components(args)
        
        logger.info("🔧 Initialisation des composants v3...")
        
        # Gestionnaire de bases vectorielles
        if args.enable_vector_search:
            self.components['vector_manager'] = VectorManager(
                provider=args.vector_provider,
                config=args.vector_config
            )
            await self.components['vector_manager'].initialize()
            logger.info("✅ Gestionnaire de bases vectorielles initialisé")
        
        # Gestionnaire Elasticsearch
        if args.enable_elasticsearch:
            self.components['elasticsearch_manager'] = ElasticsearchManager(
                host=args.elasticsearch_host,
                port=args.elasticsearch_port
            )
            await self.components['elasticsearch_manager'].initialize()
            logger.info("✅ Gestionnaire Elasticsearch initialisé")
        
        # Serveur pour plugin navigateur
        if args.enable_browser_plugin:
            self.components['browser_plugin_server'] = BrowserPluginServer(
                port=args.plugin_port
            )
            await self.components['browser_plugin_server'].start()
            logger.info("✅ Serveur plugin navigateur initialisé")
        
        # Gestionnaire distribué
        if args.enable_distributed:
            self.components['distributed_manager'] = DistributedManager(
                node_type=args.node_type,
                coordinator_host=args.coordinator_host,
                coordinator_port=args.coordinator_port
            )
            await self.components['distributed_manager'].initialize()
            logger.info("✅ Gestionnaire distribué initialisé")
        
        # Serveur API v3 (remplace le v2)
        if args.enable_mobile_interface:
            self.components['api_server_v3'] = APIServerV3(
                host=args.api_host,
                port=args.api_port,
                enable_pwa=True,
                vector_manager=self.components.get('vector_manager'),
                elasticsearch_manager=self.components.get('elasticsearch_manager'),
                distributed_manager=self.components.get('distributed_manager')
            )
            # Remplacer le serveur API v2 par v3
            self.components['api_server'] = self.components['api_server_v3']
            logger.info("✅ Serveur API v3 avec interface mobile initialisé")
    
    async def _run_vector_mode(self, args):
        """Mode gestion des bases vectorielles"""
        logger.info("🔍 Mode bases vectorielles")
        
        if args.vector_action == "index":
            # Indexer tout le contenu archivé
            stats = await self.components['vector_manager'].index_all_content()
            logger.info(f"✅ Indexation terminée: {stats}")
        
        elif args.vector_action == "search":
            # Recherche sémantique
            results = await self.components['vector_manager'].semantic_search(
                query=args.search_query,
                limit=args.search_limit
            )
            logger.info(f"📋 {len(results)} résultats trouvés:")
            for result in results:
                logger.info(f"  - {result.url} (score: {result.score:.3f})")
        
        elif args.vector_action == "reindex":
            # Réindexer avec nouveaux paramètres
            await self.components['vector_manager'].clear_index()
            stats = await self.components['vector_manager'].index_all_content()
            logger.info(f"✅ Réindexation terminée: {stats}")
    
    async def _run_elasticsearch_mode(self, args):
        """Mode gestion Elasticsearch"""
        logger.info("🔎 Mode Elasticsearch")
        
        if args.es_action == "index":
            # Indexer tout le contenu
            stats = await self.components['elasticsearch_manager'].index_all_content()
            logger.info(f"✅ Indexation ES terminée: {stats}")
        
        elif args.es_action == "search":
            # Recherche avancée
            results = await self.components['elasticsearch_manager'].advanced_search(
                query=args.search_query,
                filters=args.search_filters,
                sort=args.search_sort
            )
            logger.info(f"📋 {len(results.hits)} résultats trouvés (total: {results.total}):")
            for hit in results.hits[:10]:  # Afficher les 10 premiers
                logger.info(f"  - {hit.url} (score: {hit.score:.3f})")
        
        elif args.es_action == "reindex":
            # Réindexer avec nouveau mapping
            await self.components['elasticsearch_manager'].reset_index()
            stats = await self.components['elasticsearch_manager'].index_all_content()
            logger.info(f"✅ Réindexation ES terminée: {stats}")
    
    async def _run_distributed_mode(self, args):
        """Mode gestion distribuée"""
        logger.info("🌐 Mode distribué")
        
        if args.distributed_action == "coordinator":
            # Mode coordinateur
            logger.info("👑 Démarrage en mode coordinateur")
            await self.components['distributed_manager'].run_coordinator()
        
        elif args.distributed_action == "worker":
            # Mode worker
            logger.info("👷 Démarrage en mode worker")
            await self.components['distributed_manager'].run_worker()
        
        elif args.distributed_action == "status":
            # Statut du cluster
            status = await self.components['distributed_manager'].get_cluster_status()
            logger.info(f"📊 Statut du cluster:")
            logger.info(f"  Coordinateur: {status.coordinator}")
            logger.info(f"  Workers actifs: {len(status.workers)}")
            logger.info(f"  Tâches en cours: {status.active_tasks}")
            logger.info(f"  Tâches en attente: {status.pending_tasks}")
    
    async def start(self, args):
        """Démarre DATA_BOT v3 avec tous ses composants"""
        logger.info("🚀 Démarrage de DATA_BOT v3")
        
        # Configuration
        Config.setup_directories()
        Config.setup_logging(args.log_level)
        
        self.running = True
        
        # Gestionnaire d'interruption
        def signal_handler(signum, frame):
            logger.info("Signal d'arrêt reçu, arrêt en cours...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            # Initialiser les composants
            await self._initialize_components(args)
            
            # Démarrer les services
            await self._start_services(args)
            
            # Mode d'exécution v3
            if args.mode == "mobile":
                await self._run_mobile_mode(args)
            elif args.mode == "vector":
                await self._run_vector_mode(args)
            elif args.mode == "elasticsearch":
                await self._run_elasticsearch_mode(args)
            elif args.mode == "distributed":
                await self._run_distributed_mode(args)
            else:
                # Modes v2 via la classe parent
                await super().start(args)
                
        except Exception as e:
            logger.error(f"Erreur fatale v3: {e}")
        finally:
            await self._cleanup_v3()
    
    async def _run_mobile_mode(self, args):
        """Mode interface mobile (PWA)"""
        logger.info("📱 Mode interface mobile (PWA)")
        logger.info(f"📱 Interface mobile PWA: http://{args.api_host}:{args.api_port}/mobile")
        logger.info(f"🌐 API REST: http://{args.api_host}:{args.api_port}/api/v3")
        
        # Comme le mode serveur mais avec interface mobile activée
        await self._run_server_mode(args)
    
    async def _cleanup_v3(self):
        """Nettoyage spécifique v3"""
        logger.info("🧹 Nettoyage v3 en cours...")
        
        # Nettoyage composants v3
        if self.components['vector_manager']:
            await self.components['vector_manager'].close()
        
        if self.components['elasticsearch_manager']:
            await self.components['elasticsearch_manager'].close()
        
        if self.components['browser_plugin_server']:
            await self.components['browser_plugin_server'].stop()
        
        if self.components['distributed_manager']:
            await self.components['distributed_manager'].shutdown()
        
        # Nettoyage v2
        await super()._cleanup()


async def main():
    """Point d'entrée principal de DATA_BOT v3"""
    parser = argparse.ArgumentParser(description="DATA_BOT v3 - Bot d'Archivage Internet Avancé")
    
    # Modes d'exécution v3
    parser.add_argument("--mode", 
                       choices=["explore", "process", "continuous", "server", "mobile", 
                               "export", "cleanup", "compress", "duplicates", "schedule",
                               "vector", "elasticsearch", "distributed"], 
                       default="mobile", 
                       help="Mode d'exécution")
    
    # Options générales (héritées de v2)
    parser.add_argument("--urls", nargs="*", help="URLs de départ pour l'exploration")
    parser.add_argument("--log-level", default="INFO", help="Niveau de log")
    
    # Options API/Serveur
    parser.add_argument("--enable-api", action="store_true", default=True, help="Activer l'API REST")
    parser.add_argument("--api-host", default="localhost", help="Host du serveur API")
    parser.add_argument("--api-port", type=int, default=8080, help="Port du serveur API")
    
    # Options interface mobile
    parser.add_argument("--enable-mobile-interface", action="store_true", default=True, 
                       help="Activer l'interface mobile PWA")
    
    # Options bases vectorielles
    parser.add_argument("--enable-vector-search", action="store_true", default=True,
                       help="Activer la recherche vectorielle")
    parser.add_argument("--vector-provider", choices=["chromadb", "qdrant"], default="chromadb",
                       help="Fournisseur de base vectorielle")
    parser.add_argument("--vector-config", help="Configuration du fournisseur vectoriel")
    parser.add_argument("--vector-action", choices=["index", "search", "reindex"], 
                       help="Action pour le mode vector")
    
    # Options Elasticsearch
    parser.add_argument("--enable-elasticsearch", action="store_true", default=True,
                       help="Activer Elasticsearch")
    parser.add_argument("--elasticsearch-host", default="localhost", help="Host Elasticsearch")
    parser.add_argument("--elasticsearch-port", type=int, default=9200, help="Port Elasticsearch")
    parser.add_argument("--es-action", choices=["index", "search", "reindex"],
                       help="Action pour le mode elasticsearch")
    
    # Options plugin navigateur
    parser.add_argument("--enable-browser-plugin", action="store_true", default=True,
                       help="Activer le serveur pour plugin navigateur")
    parser.add_argument("--plugin-port", type=int, default=8081, help="Port du serveur plugin")
    
    # Options mode distribué
    parser.add_argument("--enable-distributed", action="store_true", default=False,
                       help="Activer le mode distribué")
    parser.add_argument("--node-type", choices=["coordinator", "worker", "hybrid"], default="hybrid",
                       help="Type de nœud distribué")
    parser.add_argument("--coordinator-host", default="localhost", help="Host du coordinateur")
    parser.add_argument("--coordinator-port", type=int, default=8082, help="Port du coordinateur")
    parser.add_argument("--distributed-action", choices=["coordinator", "worker", "status"],
                       help="Action pour le mode distribué")
    
    # Options de recherche
    parser.add_argument("--search-query", help="Requête de recherche")
    parser.add_argument("--search-limit", type=int, default=10, help="Limite de résultats")
    parser.add_argument("--search-filters", help="Filtres de recherche (JSON)")
    parser.add_argument("--search-sort", help="Tri des résultats")
    
    # Options planificateur (héritées de v2)
    parser.add_argument("--enable-scheduler", action="store_true", default=True, help="Activer le planificateur")
    
    args = parser.parse_args()
    
    # Configuration du logging
    Config.setup_logging(args.log_level)
    
    # Démarrer DATA_BOT v3
    bot_v3 = DataBotV3()
    await bot_v3.start(args)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Arrêt de DATA_BOT v3")
    except Exception as e:
        print(f"❌ Erreur fatale v3: {e}")
        sys.exit(1)