import asyncio
import aiohttp
import aiofiles
import logging
import os
import time
import hashlib
from urllib.parse import urlparse, urljoin, quote
from pathlib import Path
from typing import Optional, Dict, Any, List
import mimetypes
from fake_useragent import UserAgent
from src.config import Config
from src.models import WebResource, ContentType, ArchiveStatus

logger = logging.getLogger(__name__)

class WebDownloader:
    def __init__(self):
        self.session = None
        self.ua = UserAgent()
        self.downloaded_urls = set()
        self.domain_stats = {}
    
    async def __aenter__(self):
        connector = aiohttp.TCPConnector(limit=Config.CONCURRENT_DOWNLOADS)
        timeout = aiohttp.ClientTimeout(total=Config.DOWNLOAD_TIMEOUT)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={'User-Agent': self.ua.random}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def download_resource(self, resource: WebResource) -> WebResource:
        """Télécharge une ressource web"""
        if resource.url in self.downloaded_urls:
            resource.status = ArchiveStatus.SKIPPED
            resource.error_message = "Already downloaded"
            return resource
        
        try:
            # Vérifier robots.txt si activé
            if Config.RESPECT_ROBOTS_TXT:
                if not await self._can_fetch(resource.url):
                    resource.status = ArchiveStatus.SKIPPED
                    resource.error_message = "Blocked by robots.txt"
                    return resource
            
            # Limiter le taux de requêtes
            await self._rate_limit(resource.url)
            
            # Télécharger le contenu
            async with self.session.get(resource.url) as response:
                if response.status >= 400:
                    resource.status = ArchiveStatus.FAILED
                    resource.error_message = f"HTTP {response.status}"
                    return resource
                
                content = await response.read()
                content_type = response.headers.get('content-type', '').lower()
                
                # Déterminer le type de contenu
                resource.content_type = self._determine_content_type(content_type, resource.url)
                resource.content_length = len(content)
                
                # Générer le chemin de fichier
                file_path = self._generate_file_path(resource)
                
                # Sauvegarder le fichier
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                async with aiofiles.open(file_path, 'wb') as f:
                    await f.write(content)
                
                resource.file_path = file_path
                resource.status = ArchiveStatus.DOWNLOADED
                self.downloaded_urls.add(resource.url)
                
                # Mettre à jour les statistiques du domaine
                domain = urlparse(resource.url).netloc
                if domain not in self.domain_stats:
                    self.domain_stats[domain] = {'count': 0, 'size': 0}
                self.domain_stats[domain]['count'] += 1
                self.domain_stats[domain]['size'] += len(content)
                
                logger.info(f"Téléchargé: {resource.url} -> {file_path}")
                
        except asyncio.TimeoutError:
            resource.status = ArchiveStatus.FAILED
            resource.error_message = "Timeout during download"
        except Exception as e:
            resource.status = ArchiveStatus.FAILED
            resource.error_message = str(e)
            logger.error(f"Erreur téléchargement {resource.url}: {e}")
        
        return resource
    
    async def extract_links(self, resource: WebResource) -> List[str]:
        """Extrait les liens d'une page web téléchargée"""
        if not resource.file_path or resource.content_type != ContentType.WEB_PAGE:
            return []
        
        try:
            async with aiofiles.open(resource.file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            
            links = []
            base_url = resource.url
            
            # Extraire les liens des balises <a>
            for link in soup.find_all('a', href=True):
                href = link['href']
                absolute_url = urljoin(base_url, href)
                if self._is_valid_url(absolute_url):
                    links.append(absolute_url)
            
            # Extraire les ressources (images, CSS, JS)
            for tag in soup.find_all(['img', 'link', 'script']):
                src = tag.get('src') or tag.get('href')
                if src:
                    absolute_url = urljoin(base_url, src)
                    if self._is_valid_url(absolute_url):
                        links.append(absolute_url)
            
            return list(set(links))  # Supprimer les doublons
            
        except Exception as e:
            logger.error(f"Erreur extraction liens {resource.file_path}: {e}")
            return []
    
    def _determine_content_type(self, content_type: str, url: str) -> ContentType:
        """Détermine le type de contenu"""
        content_type = content_type.lower()
        
        if 'text/html' in content_type:
            return ContentType.WEB_PAGE
        elif 'image/' in content_type:
            return ContentType.IMAGE
        elif 'video/' in content_type:
            return ContentType.VIDEO
        elif 'audio/' in content_type:
            return ContentType.AUDIO
        elif any(doc_type in content_type for doc_type in ['pdf', 'document', 'msword', 'officedocument']):
            return ContentType.DOCUMENT
        elif 'application/' in content_type:
            return ContentType.APPLICATION
        else:
            # Deviner par l'extension du fichier
            ext = Path(urlparse(url).path).suffix.lower()
            if ext in ['.html', '.htm', '.php', '.asp', '.jsp']:
                return ContentType.WEB_PAGE
            elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp']:
                return ContentType.IMAGE
            elif ext in ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm']:
                return ContentType.VIDEO
            elif ext in ['.mp3', '.wav', '.ogg', '.m4a', '.flac']:
                return ContentType.AUDIO
            elif ext in ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt']:
                return ContentType.DOCUMENT
            else:
                return ContentType.UNKNOWN
    
    def _generate_file_path(self, resource: WebResource) -> str:
        """Génère un chemin de fichier pour la ressource"""
        parsed_url = urlparse(resource.url)
        domain = parsed_url.netloc
        path = parsed_url.path
        
        # Nettoyer le domaine
        domain = domain.replace('www.', '')
        domain = ''.join(c for c in domain if c.isalnum() or c in '.-_')
        
        # Générer un nom de fichier
        if path and path != '/':
            filename = os.path.basename(path)
            if not filename:
                filename = 'index.html'
        else:
            filename = 'index.html'
        
        # Ajouter une extension si nécessaire
        if not os.path.splitext(filename)[1]:
            if resource.content_type == ContentType.WEB_PAGE:
                filename += '.html'
            elif resource.content_type == ContentType.DOCUMENT:
                filename += '.txt'
        
        # Créer un hash pour éviter les conflits
        url_hash = hashlib.md5(resource.url.encode()).hexdigest()[:8]
        
        # Assembler le chemin final
        safe_filename = ''.join(c for c in filename if c.isalnum() or c in '.-_')[:100]
        final_filename = f"{url_hash}_{safe_filename}"
        
        return os.path.join(Config.ARCHIVE_PATH, domain, final_filename)
    
    async def _can_fetch(self, url: str) -> bool:
        """Vérifie si l'URL peut être récupérée selon robots.txt"""
        # Implementation simplifiée - dans un cas réel, utiliser urllib.robotparser
        return True
    
    async def _rate_limit(self, url: str):
        """Applique la limitation de taux"""
        domain = urlparse(url).netloc
        if hasattr(self, '_last_request_time'):
            if domain in self._last_request_time:
                elapsed = time.time() - self._last_request_time[domain]
                if elapsed < Config.DELAY_BETWEEN_REQUESTS:
                    await asyncio.sleep(Config.DELAY_BETWEEN_REQUESTS - elapsed)
        else:
            self._last_request_time = {}
        
        self._last_request_time[domain] = time.time()
    
    def _is_valid_url(self, url: str) -> bool:
        """Vérifie si une URL est valide pour le téléchargement"""
        try:
            parsed = urlparse(url)
            if not parsed.scheme in ['http', 'https']:
                return False
            if not parsed.netloc:
                return False
            
            # Filtrer les extensions non désirées
            path = parsed.path.lower()
            excluded_extensions = ['.ico', '.css', '.js', '.woff', '.woff2', '.ttf']
            if any(path.endswith(ext) for ext in excluded_extensions):
                return False
            
            return True
        except:
            return False
