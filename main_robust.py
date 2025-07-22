import asyncio
import logging
import signal
import sys
from datetime import datetime
from typing import List, Optional
from src.config import Config
from src.models import WebResource, ArchiveStatus
from src.ollama_client import OllamaClient
from src.explorer import WebExplorer
from src.downloader import WebDownloader
from src.screenshot_robust import ScreenshotCapture
from src.database import DatabaseManager

logger = logging.getLogger(__name__)

class ArchiveBot:
    def __init__(self):
        self.running = False
        self.stats = {
            'start_time': None,
            'processed': 0,
            'downloaded': 0,
            'screenshots': 0,
            'failed': 0
        }
    
    async def start(self, mode: str = "explore", seed_urls: List[str] = None):
        """Démarre le bot d'archivage"""
        logger.info("🤖 Démarrage du Bot d'Archivage Internet")
        
        # Configuration
        Config.setup_directories()
        Config.setup_logging()
        
        self.running = True
        self.stats['start_time'] = datetime.now()
        
        # Gestionnaire d'interruption
        def signal_handler(signum, frame):
            logger.info("Signal d'arrêt reçu, arrêt en cours...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            # Vérifier la disponibilité d'Ollama
            await self._check_ollama()
            
            if mode == "explore":
                await self._run_exploration_mode(seed_urls)
            elif mode == "process":
                await self._run_processing_mode()
            elif mode == "continuous":
                await self._run_continuous_mode(seed_urls)
            else:
                logger.error(f"Mode inconnu: {mode}")
                
        except Exception as e:
            logger.error(f"Erreur fatale: {e}")
        finally:
            await self._cleanup()
    
    async def _check_ollama(self):
        """Vérifie la disponibilité d'Ollama"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{Config.OLLAMA_HOST}/api/tags", timeout=5) as response:
                    if response.status == 200:
                        logger.info("✅ Ollama accessible")
                        return True
        except Exception as e:
            logger.warning(f"⚠️ Ollama non accessible: {e}")
            logger.warning("Le bot fonctionnera sans intelligence IA")
            return False
    
    async def _run_exploration_mode(self, seed_urls: List[str] = None):
        """Mode exploration : découvre de nouvelles URLs"""
        logger.info("🔍 Mode Exploration")
        
        async with DatabaseManager() as db:
            try:
                async with OllamaClient() as ollama:
                    explorer = WebExplorer()
                    
                    if seed_urls:
                        # Exploration à partir d'URLs de départ
                        resources = await explorer.explore_from_seed_urls(seed_urls, ollama, db)
                    else:
                        # Exploration autonome avec requêtes générées
                        resources = await explorer.explore_from_queries(ollama, db)
                    
                    logger.info(f"✅ Exploration terminée: {len(resources)} nouvelles ressources découvertes")
            except Exception as e:
                logger.error(f"Erreur exploration: {e}")
                # Mode fallback sans Ollama
                explorer = WebExplorer()
                if seed_urls:
                    # Ajouter manuellement les URLs de départ
                    for url in seed_urls:
                        await db.mark_url_as_discovered(url)
                    logger.info(f"✅ {len(seed_urls)} URLs ajoutées pour traitement")
    
    async def _run_processing_mode(self):
        """Mode traitement : traite les URLs en attente"""
        logger.info("⚙️ Mode Traitement")
        
        async with DatabaseManager() as db:
            async with WebDownloader() as downloader:
                async with ScreenshotCapture() as screenshot:
                    
                    # Récupérer les ressources en attente
                    pending_resources = await db.get_pending_resources(limit=500)
                    logger.info(f"📋 {len(pending_resources)} ressources à traiter")
                    
                    if not pending_resources:
                        logger.info("Aucune ressource en attente. Utilisez le mode 'explore' d'abord.")
                        return
                    
                    # Traiter les ressources par lots
                    batch_size = Config.CONCURRENT_DOWNLOADS
                    for i in range(0, len(pending_resources), batch_size):
                        if not self.running:
                            break
                        
                        batch = pending_resources[i:i + batch_size]
                        await self._process_batch(batch, downloader, screenshot, None, db)
                        
                        # Pause entre les lots
                        await asyncio.sleep(1)
                    
                    logger.info("✅ Traitement terminé")
    
    async def _run_continuous_mode(self, seed_urls: List[str] = None):
        """Mode continu : explore et traite en continu"""
        logger.info("🔄 Mode Continu")
        
        async with DatabaseManager() as db:
            async with WebDownloader() as downloader:
                async with ScreenshotCapture() as screenshot:
                    explorer = WebExplorer()
                    
                    # Essayer d'initialiser Ollama
                    ollama_client = None
                    try:
                        ollama_client = OllamaClient()
                        await ollama_client.__aenter__()
                        logger.info("✅ Ollama connecté")
                    except Exception as e:
                        logger.warning(f"⚠️ Ollama indisponible, mode sans IA: {e}")
                    
                    # Ajouter les URLs de départ si fournies
                    if seed_urls:
                        for url in seed_urls:
                            await db.mark_url_as_discovered(url)
                        logger.info(f"✅ {len(seed_urls)} URLs de départ ajoutées")
                    
                    cycle = 0
                    try:
                        while self.running:
                            cycle += 1
                            logger.info(f"🔄 Cycle {cycle}")
                            
                            # Phase 1: Exploration (si Ollama disponible)
                            if ollama_client and cycle % 3 == 1:
                                try:
                                    if seed_urls and cycle == 1:
                                        await explorer.explore_from_seed_urls(seed_urls, ollama_client, db)
                                    else:
                                        await explorer.explore_from_queries(ollama_client, db)
                                except Exception as e:
                                    logger.error(f"Erreur exploration cycle {cycle}: {e}")
                            
                            # Phase 2: Traitement
                            pending = await db.get_pending_resources(limit=50)
                            if pending:
                                logger.info(f"⚙️ Traitement de {len(pending)} ressources")
                                
                                batch_size = min(Config.CONCURRENT_DOWNLOADS, len(pending))
                                for i in range(0, len(pending), batch_size):
                                    if not self.running:
                                        break
                                    
                                    batch = pending[i:i + batch_size]
                                    await self._process_batch(batch, downloader, screenshot, ollama_client, db)
                            else:
                                logger.info("Aucune ressource en attente")
                            
                            # Phase 3: Statistiques
                            stats = await db.get_archive_stats()
                            self._log_stats(stats)
                            
                            # Pause entre les cycles
                            if self.running:
                                logger.info("💤 Pause avant le prochain cycle...")
                                await asyncio.sleep(60)  # 1 minute
                    
                    finally:
                        if ollama_client:
                            await ollama_client.__aexit__(None, None, None)
                        
                    logger.info("🛑 Mode continu arrêté")
    
    async def _process_batch(self, batch: List[WebResource], downloader: WebDownloader, 
                           screenshot: ScreenshotCapture, ollama: Optional[OllamaClient], db: DatabaseManager):
        """Traite un lot de ressources"""
        tasks = []
        
        for resource in batch:
            if not self.running:
                break
            
            task = self._process_single_resource(resource, downloader, screenshot, ollama, db)
            tasks.append(task)
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Compter les résultats
            for result in results:
                if isinstance(result, Exception):
                    self.stats['failed'] += 1
                    logger.error(f"Erreur traitement: {result}")
                else:
                    self.stats['processed'] += 1
                    if result and result.status == ArchiveStatus.DOWNLOADED:
                        self.stats['downloaded'] += 1
                    elif result and result.status == ArchiveStatus.SCREENSHOT:
                        self.stats['screenshots'] += 1
                    else:
                        self.stats['failed'] += 1
    
    async def _process_single_resource(self, resource: WebResource, downloader: WebDownloader,
                                     screenshot: ScreenshotCapture, ollama: Optional[OllamaClient], 
                                     db: DatabaseManager) -> Optional[WebResource]:
        """Traite une seule ressource"""
        try:
            logger.info(f"🔄 Traitement: {resource.url}")
            
            # Essayer de télécharger d'abord
            resource = await downloader.download_resource(resource)
            
            if resource.status == ArchiveStatus.DOWNLOADED:
                # Si téléchargement réussi, extraire les métadonnées
                if resource.file_path and ollama:
                    # Lire un aperçu du contenu pour la catégorisation
                    try:
                        with open(resource.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content_preview = f.read(2000)
                        
                        # Catégoriser avec Ollama si disponible
                        category_info = await ollama.categorize_content(
                            resource.url, 
                            resource.title or "", 
                            content_preview
                        )
                        resource.metadata.update(category_info)
                        
                    except Exception as e:
                        logger.warning(f"Erreur lecture contenu {resource.file_path}: {e}")
                
                # Extraire les liens pour futures explorations
                try:
                    links = await downloader.extract_links(resource)
                    for link in links[:10]:  # Limiter le nombre de liens
                        await db.mark_url_as_discovered(link, resource.url, resource.depth + 1)
                except Exception as e:
                    logger.warning(f"Erreur extraction liens {resource.url}: {e}")
            
            else:
                # Si téléchargement échoué, essayer un screenshot
                logger.info(f"📸 Screenshot de secours: {resource.url}")
                resource = await screenshot.capture_screenshot(resource)
                
                if resource.status == ArchiveStatus.SCREENSHOT and ollama:
                    # Catégoriser avec le texte extrait du screenshot
                    content_preview = resource.metadata.get('page_text_preview', '')
                    if content_preview:
                        try:
                            category_info = await ollama.categorize_content(
                                resource.url,
                                resource.title or "",
                                content_preview
                            )
                            resource.metadata.update(category_info)
                        except Exception as e:
                            logger.warning(f"Erreur catégorisation Ollama: {e}")
                    
                    # Extraire les liens visibles
                    try:
                        links = await screenshot.extract_links_from_screenshot(resource)
                        for link in links[:5]:  # Moins de liens pour les screenshots
                            await db.mark_url_as_discovered(link, resource.url, resource.depth + 1)
                    except Exception as e:
                        logger.warning(f"Erreur extraction liens screenshot {resource.url}: {e}")
            
            # Sauvegarder les mises à jour
            await db.save_resource(resource)
            
            logger.info(f"✅ Traité: {resource.url} -> {resource.status.value}")
            return resource
            
        except Exception as e:
            logger.error(f"❌ Erreur traitement {resource.url}: {e}")
            resource.status = ArchiveStatus.FAILED
            resource.error_message = str(e)
            await db.save_resource(resource)
            return resource
    
    def _log_stats(self, db_stats):
        """Affiche les statistiques"""
        runtime = datetime.now() - self.stats['start_time']
        
        logger.info("📊 STATISTIQUES")
        logger.info(f"⏱️  Temps d'exécution: {runtime}")
        logger.info(f"🔍 Total découvert: {db_stats.total_discovered}")
        logger.info(f"💾 Total téléchargé: {db_stats.total_downloaded}")
        logger.info(f"📸 Total screenshots: {db_stats.total_screenshots}")
        logger.info(f"❌ Total échecs: {db_stats.total_failed}")
        logger.info(f"💽 Taille totale: {db_stats.total_size_mb:.2f} MB")
        logger.info(f"🌐 Domaines explorés: {db_stats.domains_discovered}")
        logger.info("━" * 50)
    
    async def _cleanup(self):
        """Nettoyage avant arrêt"""
        logger.info("🧹 Nettoyage en cours...")
        # Ici on pourrait ajouter du nettoyage spécifique
        logger.info("✅ Nettoyage terminé")


async def main():
    """Point d'entrée principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Bot d'Archivage Internet Automatique")
    parser.add_argument("--mode", choices=["explore", "process", "continuous"], 
                       default="continuous", help="Mode d'exécution")
    parser.add_argument("--urls", nargs="*", help="URLs de départ pour l'exploration")
    parser.add_argument("--log-level", default="INFO", help="Niveau de log")
    
    args = parser.parse_args()
    
    # Configuration du logging
    Config.setup_logging(args.log_level)
    
    # Démarrer le bot
    bot = ArchiveBot()
    await bot.start(mode=args.mode, seed_urls=args.urls)

if __name__ == "__main__":
    asyncio.run(main())
