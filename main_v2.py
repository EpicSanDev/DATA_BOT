"""
DATA_BOT v2 - Point d'entrée principal avec toutes les nouvelles fonctionnalités
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
from src.api_server import APIServer
from src.export_manager import ExportManager
from src.duplicate_detector import DuplicateDetector
from src.compression_manager import CompressionManager
from src.proxy_manager import ProxyManager
from src.task_scheduler import TaskScheduler, ScheduledTask, TaskFrequency
from main import ArchiveBot

logger = logging.getLogger(__name__)

class DataBotV2:
    """Classe principale pour DATA_BOT v2"""
    
    def __init__(self):
        self.running = False
        self.api_server = None
        self.scheduler = None
        self.proxy_manager = None
        
        self.components = {
            'api_server': None,
            'scheduler': None,
            'proxy_manager': None,
            'export_manager': None,
            'duplicate_detector': None,
            'compression_manager': None,
            'ai_client': None
        }
    
    async def start(self, args):
        """Démarre DATA_BOT v2 avec tous ses composants"""
        logger.info("🚀 Démarrage de DATA_BOT v2")
        
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
            
            # Mode d'exécution
            if args.mode == "server":
                await self._run_server_mode(args)
            elif args.mode == "export":
                await self._run_export_mode(args)
            elif args.mode == "cleanup":
                await self._run_cleanup_mode(args)
            elif args.mode == "compress":
                await self._run_compression_mode(args)
            elif args.mode == "duplicates":
                await self._run_duplicates_mode(args)
            elif args.mode == "schedule":
                await self._run_schedule_mode(args)
            else:
                # Mode archivage classique avec améliorations v2
                await self._run_enhanced_archive_mode(args)
                
        except Exception as e:
            logger.error(f"Erreur fatale: {e}")
        finally:
            await self._cleanup()
    
    async def _initialize_components(self, args):
        """Initialise tous les composants v2"""
        logger.info("🔧 Initialisation des composants v2...")
        
        # Gestionnaire de proxies
        self.components['proxy_manager'] = ProxyManager()
        logger.info("✅ Gestionnaire de proxies initialisé")
        
        # Client IA étendu
        self.components['ai_client'] = EnhancedAIClient()
        await self.components['ai_client'].__aenter__()
        logger.info("✅ Client IA étendu initialisé")
        
        # Gestionnaire d'export
        self.components['export_manager'] = ExportManager()
        logger.info("✅ Gestionnaire d'export initialisé")
        
        # Détecteur de doublons
        self.components['duplicate_detector'] = DuplicateDetector()
        logger.info("✅ Détecteur de doublons initialisé")
        
        # Gestionnaire de compression
        self.components['compression_manager'] = CompressionManager()
        logger.info("✅ Gestionnaire de compression initialisé")
        
        # Planificateur de tâches
        self.components['scheduler'] = TaskScheduler()
        logger.info("✅ Planificateur de tâches initialisé")
        
        # Serveur API
        self.components['api_server'] = APIServer(
            host=args.api_host, 
            port=args.api_port
        )
        logger.info("✅ Serveur API initialisé")
    
    async def _start_services(self, args):
        """Démarre les services en arrière-plan"""
        if args.enable_scheduler:
            await self.components['scheduler'].start()
            logger.info("⏰ Planificateur démarré")
        
        if args.enable_api:
            self.components['api_server'].start()
            logger.info(f"🌐 API disponible sur http://{args.api_host}:{args.api_port}")
    
    async def _run_server_mode(self, args):
        """Mode serveur - maintient les services actifs"""
        logger.info("🖥️ Mode serveur actif")
        logger.info(f"📱 Interface web: http://{args.api_host}:{args.api_port}")
        logger.info("Appuyez sur Ctrl+C pour arrêter")
        
        try:
            while self.running:
                await asyncio.sleep(1)
                
                # Auto-compression périodique
                if hasattr(self, '_last_auto_compress'):
                    if (datetime.now() - self._last_auto_compress).seconds > 3600:  # 1h
                        await self.components['compression_manager'].auto_compress_new_files()
                        self._last_auto_compress = datetime.now()
                else:
                    self._last_auto_compress = datetime.now()
                    
        except KeyboardInterrupt:
            logger.info("Arrêt demandé par l'utilisateur")
    
    async def _run_export_mode(self, args):
        """Mode export de données"""
        logger.info(f"📤 Export en format {args.export_format}")
        
        export_path = await self.components['export_manager'].export_archive(
            format_type=args.export_format,
            include_files=args.include_files,
            filter_status=args.filter_status
        )
        
        logger.info(f"✅ Export terminé: {export_path}")
    
    async def _run_cleanup_mode(self, args):
        """Mode nettoyage"""
        logger.info("🧹 Mode nettoyage")
        
        # Nettoyer les exports anciens
        await self.components['export_manager'].cleanup_old_exports(args.max_exports)
        
        # Nettoyer les artefacts de compression
        await self.components['compression_manager'].cleanup_compression_artifacts()
        
        logger.info("✅ Nettoyage terminé")
    
    async def _run_compression_mode(self, args):
        """Mode compression"""
        logger.info("🗜️ Mode compression")
        
        stats = await self.components['compression_manager'].compress_archive(
            force_recompress=args.force_recompress
        )
        
        logger.info(f"✅ Compression terminée: {stats}")
    
    async def _run_duplicates_mode(self, args):
        """Mode détection de doublons"""
        logger.info("🔍 Mode détection de doublons")
        
        duplicates = await self.components['duplicate_detector'].detect_duplicates()
        
        for duplicate_type, groups in duplicates.items():
            logger.info(f"{duplicate_type}: {len(groups)} groupes de doublons")
            for i, group in enumerate(groups[:3]):  # Afficher les 3 premiers
                logger.info(f"  Groupe {i+1}: {len(group)} ressources")
                for resource in group[:2]:  # Afficher les 2 premières
                    logger.info(f"    - {resource.url}")
        
        if args.remove_duplicates:
            removed = await self.components['duplicate_detector'].remove_duplicates(
                duplicates, args.duplicate_strategy
            )
            logger.info(f"✅ {removed} doublons supprimés")
    
    async def _run_schedule_mode(self, args):
        """Mode gestion des tâches programmées"""
        logger.info("📅 Mode planification")
        
        if args.schedule_action == "list":
            tasks = await self.components['scheduler'].list_tasks()
            logger.info(f"📋 {len(tasks)} tâches programmées:")
            for task in tasks:
                logger.info(f"  - {task.name} ({task.status.value}) - Prochaine: {task.next_run}")
        
        elif args.schedule_action == "add":
            task = ScheduledTask(
                id="",
                name=args.task_name,
                task_type=args.task_type,
                frequency=TaskFrequency(args.task_frequency),
                parameters={}
            )
            task_id = await self.components['scheduler'].add_task(task)
            logger.info(f"✅ Tâche ajoutée: {task_id}")
        
        elif args.schedule_action == "remove" and args.task_id:
            success = await self.components['scheduler'].remove_task(args.task_id)
            if success:
                logger.info("✅ Tâche supprimée")
            else:
                logger.error("❌ Tâche non trouvée")
    
    async def _run_enhanced_archive_mode(self, args):
        """Mode archivage avec améliorations v2"""
        logger.info("🔄 Mode archivage amélioré v2")
        
        # Utiliser le bot d'archivage original mais avec les améliorations v2
        bot = ArchiveBot()
        
        # Intégrer le support proxy si configuré
        if self.components['proxy_manager'].proxies:
            logger.info("🔗 Support proxy activé")
            # Le proxy manager sera utilisé dans les composants de téléchargement
        
        # Lancer l'archivage
        await bot.start(mode=args.mode, seed_urls=args.urls)
        
        # Post-traitement v2
        if args.auto_compress:
            logger.info("🗜️ Compression automatique...")
            await self.components['compression_manager'].auto_compress_new_files()
        
        if args.check_duplicates:
            logger.info("🔍 Vérification des doublons...")
            await self.components['duplicate_detector'].mark_duplicates_in_database()
    
    async def _cleanup(self):
        """Nettoyage avant arrêt"""
        logger.info("🧹 Nettoyage en cours...")
        
        # Arrêter les services
        if self.components['scheduler']:
            await self.components['scheduler'].stop()
        
        if self.components['api_server']:
            self.components['api_server'].stop()
        
        if self.components['ai_client']:
            await self.components['ai_client'].__aexit__(None, None, None)
        
        logger.info("✅ Nettoyage terminé")


async def main():
    """Point d'entrée principal de DATA_BOT v2"""
    parser = argparse.ArgumentParser(description="DATA_BOT v2 - Bot d'Archivage Internet Avancé")
    
    # Modes d'exécution
    parser.add_argument("--mode", 
                       choices=["explore", "process", "continuous", "server", "export", "cleanup", "compress", "duplicates", "schedule"], 
                       default="server", 
                       help="Mode d'exécution")
    
    # Options générales
    parser.add_argument("--urls", nargs="*", help="URLs de départ pour l'exploration")
    parser.add_argument("--log-level", default="INFO", help="Niveau de log")
    
    # Options API/Serveur
    parser.add_argument("--enable-api", action="store_true", default=True, help="Activer l'API REST")
    parser.add_argument("--api-host", default="localhost", help="Host du serveur API")
    parser.add_argument("--api-port", type=int, default=8080, help="Port du serveur API")
    
    # Options planificateur
    parser.add_argument("--enable-scheduler", action="store_true", default=True, help="Activer le planificateur")
    
    # Options export
    parser.add_argument("--export-format", choices=["json", "csv", "html", "xml", "zip"], 
                       default="json", help="Format d'export")
    parser.add_argument("--include-files", action="store_true", help="Inclure les fichiers dans l'export")
    parser.add_argument("--filter-status", help="Filtrer par statut pour l'export")
    
    # Options nettoyage
    parser.add_argument("--max-exports", type=int, default=10, help="Nombre max d'exports à conserver")
    
    # Options compression
    parser.add_argument("--force-recompress", action="store_true", help="Forcer la recompression")
    parser.add_argument("--auto-compress", action="store_true", default=True, help="Compression automatique")
    
    # Options doublons
    parser.add_argument("--check-duplicates", action="store_true", default=True, help="Vérifier les doublons")
    parser.add_argument("--remove-duplicates", action="store_true", help="Supprimer les doublons")
    parser.add_argument("--duplicate-strategy", choices=["keep_first", "keep_best", "keep_latest"], 
                       default="keep_best", help="Stratégie de suppression des doublons")
    
    # Options planification
    parser.add_argument("--schedule-action", choices=["list", "add", "remove"], help="Action de planification")
    parser.add_argument("--task-name", help="Nom de la tâche à ajouter")
    parser.add_argument("--task-type", choices=["archive", "export", "cleanup", "compression", "duplicate_check"], 
                       help="Type de tâche")
    parser.add_argument("--task-frequency", choices=["once", "hourly", "daily", "weekly", "monthly"], 
                       help="Fréquence de la tâche")
    parser.add_argument("--task-id", help="ID de la tâche pour suppression")
    
    args = parser.parse_args()
    
    # Configuration du logging
    Config.setup_logging(args.log_level)
    
    # Démarrer DATA_BOT v2
    bot_v2 = DataBotV2()
    await bot_v2.start(args)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Arrêt de DATA_BOT v2")
    except Exception as e:
        print(f"❌ Erreur fatale: {e}")
        sys.exit(1)