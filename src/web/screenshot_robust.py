import asyncio
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from src.core.config import Config
from src.core.models import WebResource, ArchiveStatus

logger = logging.getLogger(__name__)

# Classe fallback sans Selenium
class FallbackScreenshot:
    def __init__(self):
        self.driver = None
        logger.warning("Module Screenshot en mode fallback (sans Selenium)")
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
    
    async def capture_screenshot(self, resource: WebResource) -> WebResource:
        """Mode fallback : marque comme échoué mais continue"""
        resource.status = ArchiveStatus.FAILED
        resource.error_message = "Screenshots non disponibles (Chrome non trouvé)"
        logger.warning(f"Screenshot non disponible pour: {resource.url}")
        return resource
    
    async def extract_links_from_screenshot(self, resource: WebResource) -> List[str]:
        return []

# Essayer d'importer Selenium, sinon utiliser le fallback
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    from PIL import Image
    import io
    import base64
    
    SELENIUM_AVAILABLE = True
    logger.info("Selenium disponible pour les screenshots")
    
except ImportError as e:
    SELENIUM_AVAILABLE = False
    logger.warning(f"Selenium non disponible: {e}")

if SELENIUM_AVAILABLE:
    class ScreenshotCapture:
        def __init__(self):
            self.driver = None
            self.driver_service = None
            self.chrome_available = False
        
        async def __aenter__(self):
            try:
                await self.setup_driver()
                return self
            except Exception as e:
                logger.error(f"Impossible d'initialiser les screenshots: {e}")
                # Retourner le fallback en cas d'erreur
                return FallbackScreenshot()
        
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            if self.driver:
                self.driver.quit()
        
        async def setup_driver(self):
            """Configure le driver Chrome pour les screenshots"""
            try:
                # Vérifier si Chrome est disponible
                chrome_paths = [
                    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                    '/Applications/Chromium.app/Contents/MacOS/Chromium',
                    '/usr/bin/google-chrome',
                    '/usr/bin/chromium-browser',
                    '/opt/google/chrome/chrome'
                ]
                
                chrome_binary = None
                for path in chrome_paths:
                    if os.path.exists(path):
                        chrome_binary = path
                        break
                
                if not chrome_binary:
                    raise Exception("Chrome/Chromium non trouvé. Installez Google Chrome ou Chromium.")
                
                # Configuration Chrome
                chrome_options = Options()
                chrome_options.binary_location = chrome_binary
                
                if Config.HEADLESS:
                    chrome_options.add_argument('--headless')
                
                chrome_options.add_argument(f'--window-size={Config.WINDOW_SIZE}')
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                chrome_options.add_argument('--disable-extensions')
                chrome_options.add_argument('--disable-plugins')
                chrome_options.add_argument('--disable-images')  # Pour accélérer
                chrome_options.add_argument(f'--user-agent={Config.USER_AGENT}')
                chrome_options.add_argument('--disable-gpu')
                chrome_options.add_argument('--remote-debugging-port=9222')
                
                # Installer automatiquement ChromeDriver
                try:
                    service = Service(ChromeDriverManager().install())
                except Exception as e:
                    logger.error(f"Erreur installation ChromeDriver: {e}")
                    raise Exception("Impossible d'installer ChromeDriver automatiquement")
                
                # Créer le driver dans un thread séparé pour éviter les blocages
                self.driver = await asyncio.get_event_loop().run_in_executor(
                    None, 
                    lambda: webdriver.Chrome(service=service, options=chrome_options)
                )
                
                # Configuration des timeouts
                self.driver.set_page_load_timeout(Config.SCREENSHOT_TIMEOUT)
                self.driver.implicitly_wait(10)
                
                self.chrome_available = True
                logger.info(f"Driver Chrome configuré avec binaire: {chrome_binary}")
                
            except Exception as e:
                logger.error(f"Erreur configuration driver Chrome: {e}")
                self.driver = None
                self.chrome_available = False
                raise
        
        async def capture_screenshot(self, resource: WebResource) -> WebResource:
            """Capture un screenshot d'une page web"""
            if not self.driver or not self.chrome_available:
                resource.status = ArchiveStatus.FAILED
                resource.error_message = "Driver Chrome non initialisé"
                return resource
            
            try:
                logger.info(f"Capture screenshot: {resource.url}")
                
                # Charger la page dans un thread séparé
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.driver.get,
                    resource.url
                )
                
                # Attendre que la page soit chargée
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                )
                
                # Petite pause pour s'assurer que tout est rendu
                await asyncio.sleep(2)
                
                # Capturer le titre de la page
                if not resource.title:
                    resource.title = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: self.driver.title
                    )
                
                # Prendre le screenshot de la page complète
                screenshot_data = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self._take_full_page_screenshot
                )
                
                # Générer le chemin de fichier pour le screenshot
                screenshot_path = self._generate_screenshot_path(resource)
                
                # Sauvegarder le screenshot
                os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
                
                # Convertir et sauvegarder l'image
                if isinstance(screenshot_data, str):
                    # Si c'est une string base64
                    image_data = base64.b64decode(screenshot_data)
                    with open(screenshot_path, 'wb') as f:
                        f.write(image_data)
                else:
                    # Si c'est déjà des données binaires
                    with open(screenshot_path, 'wb') as f:
                        f.write(screenshot_data)
                
                # Optimiser l'image
                await self._optimize_screenshot(screenshot_path)
                
                resource.screenshot_path = screenshot_path
                resource.status = ArchiveStatus.SCREENSHOT
                resource.archived_at = datetime.now()
                
                # Extraire du contenu textuel pour l'analyse
                page_text = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.driver.find_element(By.TAG_NAME, "body").text
                )
                
                resource.metadata['page_text_preview'] = page_text[:1000]
                resource.content_length = len(page_text)
                
                logger.info(f"Screenshot sauvegardé: {screenshot_path}")
                
            except asyncio.TimeoutError:
                resource.status = ArchiveStatus.FAILED
                resource.error_message = "Timeout lors de la capture"
                logger.error(f"Timeout screenshot: {resource.url}")
            except Exception as e:
                resource.status = ArchiveStatus.FAILED
                resource.error_message = str(e)
                logger.error(f"Erreur screenshot {resource.url}: {e}")
            
            return resource
        
        def _take_full_page_screenshot(self) -> bytes:
            """Prend un screenshot de la page complète"""
            # Obtenir les dimensions de la page
            total_width = self.driver.execute_script("return document.body.scrollWidth")
            total_height = self.driver.execute_script("return document.body.scrollHeight")
            
            # Ajuster la taille de la fenêtre
            self.driver.set_window_size(total_width, total_height)
            
            # Prendre le screenshot
            return self.driver.get_screenshot_as_png()
        
        def _generate_screenshot_path(self, resource: WebResource) -> str:
            """Génère un chemin pour le fichier screenshot"""
            from urllib.parse import urlparse
            import hashlib
            
            parsed_url = urlparse(resource.url)
            domain = parsed_url.netloc.replace('www.', '')
            domain = ''.join(c for c in domain if c.isalnum() or c in '.-_')
            
            # Générer un nom de fichier basé sur l'URL
            url_hash = hashlib.md5(resource.url.encode()).hexdigest()[:12]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            filename = f"{timestamp}_{url_hash}.png"
            
            return os.path.join(Config.SCREENSHOTS_PATH, domain, filename)
        
        async def _optimize_screenshot(self, image_path: str):
            """Optimise le screenshot pour réduire la taille du fichier"""
            try:
                def optimize():
                    with Image.open(image_path) as img:
                        # Convertir en RGB si nécessaire
                        if img.mode in ('RGBA', 'LA', 'P'):
                            img = img.convert('RGB')
                        
                        # Redimensionner si trop grand (garde le ratio)
                        max_width = 1920
                        max_height = 1080
                        img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                        
                        # Sauvegarder avec compression
                        img.save(image_path, 'PNG', optimize=True, compress_level=6)
                
                await asyncio.get_event_loop().run_in_executor(None, optimize)
                
            except Exception as e:
                logger.warning(f"Erreur optimisation screenshot {image_path}: {e}")
        
        async def extract_links_from_screenshot(self, resource: WebResource) -> List[str]:
            """Extrait les liens visibles sur la page via Selenium"""
            if not self.driver or not self.chrome_available:
                return []
            
            try:
                # Naviguer vers la page si pas déjà fait
                current_url = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.driver.current_url
                )
                
                if current_url != resource.url:
                    await asyncio.get_event_loop().run_in_executor(
                        None,
                        self.driver.get,
                        resource.url
                    )
                
                # Extraire tous les liens
                links = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: [
                        link.get_attribute('href') 
                        for link in self.driver.find_elements(By.TAG_NAME, 'a')
                        if link.get_attribute('href')
                    ]
                )
                
                # Filtrer et nettoyer les liens
                from urllib.parse import urljoin
                clean_links = []
                for link in links:
                    absolute_link = urljoin(resource.url, link)
                    if self._is_valid_link(absolute_link):
                        clean_links.append(absolute_link)
                
                return list(set(clean_links))  # Supprimer les doublons
                
            except Exception as e:
                logger.error(f"Erreur extraction liens screenshot {resource.url}: {e}")
                return []
        
        def _is_valid_link(self, url: str) -> bool:
            """Vérifie si un lien est valide pour l'archivage"""
            if not url or url.startswith(('javascript:', 'mailto:', 'tel:')):
                return False
            
            from urllib.parse import urlparse
            try:
                parsed = urlparse(url)
                return parsed.scheme in ['http', 'https'] and parsed.netloc
            except:
                return False

else:
    # Si Selenium n'est pas disponible, utiliser uniquement le fallback
    ScreenshotCapture = FallbackScreenshot
