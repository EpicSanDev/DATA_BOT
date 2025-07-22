import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Set
from urllib.parse import urlparse, urljoin
import requests
from bs4 import BeautifulSoup
from src.config import Config
from src.models import WebResource, ArchiveStatus, SearchQuery
from src.ollama_client import OllamaClient
from src.downloader import WebDownloader
from src.screenshot import ScreenshotCapture
from src.database import DatabaseManager

logger = logging.getLogger(__name__)

class WebExplorer:
    def __init__(self):
        self.visited_urls: Set[str] = set()
        self.discovered_urls: Set[str] = set()
        self.domain_limits: Dict[str, int] = {}
        self.search_engines = [
            "https://www.google.com/search?q={}",
            "https://duckduckgo.com/?q={}",
            "https://www.bing.com/search?q={}",
        ]
    
    async def explore_from_queries(self, ollama_client: OllamaClient, db: DatabaseManager) -> List[WebResource]:
        """Explore Internet à partir de requêtes générées par Ollama"""
        logger.info("Démarrage de l'exploration automatique")
        
        # Générer des requêtes de recherche intelligentes
        search_queries = await ollama_client.generate_search_queries(
            context="Exploration automatique pour archivage",
            num_queries=10
        )
        
        all_resources = []
        
        for query in search_queries:
            logger.info(f"Exploration avec la requête: {query}")
            
            # Sauvegarder la requête en DB
            await db.save_search_query(query, "auto_exploration")
            
            # Rechercher des URLs avec cette requête
            urls = await self._search_urls(query)
            
            # Convertir en WebResource et analyser avec Ollama
            for url in urls[:10]:  # Limiter à 10 par requête
                if url not in self.discovered_urls:
                    resource = WebResource(url=url, parent_url="search", depth=0)
                    
                    # Demander à Ollama si cette URL vaut la peine d'être archivée
                    decision = await ollama_client.should_archive_url(url)
                    
                    if decision.get('should_archive', True):
                        resource.metadata.update(decision)
                        all_resources.append(resource)
                        self.discovered_urls.add(url)
                        
                        # Sauvegarder en DB
                        await db.save_resource(resource)
            
            # Petite pause entre les requêtes
            await asyncio.sleep(2)
        
        logger.info(f"Exploration terminée: {len(all_resources)} nouvelles ressources découvertes")
        return all_resources
    
    async def explore_from_seed_urls(self, seed_urls: List[str], ollama_client: OllamaClient, db: DatabaseManager) -> List[WebResource]:
        """Explore Internet à partir d'URLs de départ"""
        logger.info(f"Exploration à partir de {len(seed_urls)} URLs de départ")
        
        to_explore = [(url, 0) for url in seed_urls]
        all_resources = []
        
        while to_explore and len(all_resources) < 1000:  # Limite globale
            url, depth = to_explore.pop(0)
            
            if url in self.visited_urls or depth > Config.MAX_DEPTH:
                continue
            
            # Vérifier les limites par domaine
            domain = urlparse(url).netloc
            if domain in self.domain_limits:
                if self.domain_limits[domain] >= Config.MAX_PAGES_PER_DOMAIN:
                    continue
            else:
                self.domain_limits[domain] = 0
            
            try:
                # Créer la ressource
                resource = WebResource(url=url, depth=depth)
                
                # Demander à Ollama s'il faut archiver
                decision = await ollama_client.should_archive_url(url)
                
                if not decision.get('should_archive', True):
                    logger.info(f"Ollama recommande de ne pas archiver: {url}")
                    continue
                
                resource.metadata.update(decision)
                
                # Découvrir des liens depuis cette page
                new_urls = await self._discover_links_from_url(url)
                
                # Ajouter les nouveaux liens à explorer
                for new_url in new_urls:
                    if new_url not in self.discovered_urls:
                        to_explore.append((new_url, depth + 1))
                        self.discovered_urls.add(new_url)
                
                # Ajouter la ressource à traiter
                all_resources.append(resource)
                self.visited_urls.add(url)
                self.domain_limits[domain] += 1
                
                # Sauvegarder en DB
                await db.save_resource(resource)
                
                logger.info(f"Découvert: {url} (profondeur {depth}, {len(new_urls)} nouveaux liens)")
                
                # Pause pour respecter les serveurs
                await asyncio.sleep(random.uniform(1, 3))
                
            except Exception as e:
                logger.error(f"Erreur exploration {url}: {e}")
                continue
        
        logger.info(f"Exploration terminée: {len(all_resources)} ressources découvertes")
        return all_resources
    
    async def _search_urls(self, query: str) -> List[str]:
        """Recherche des URLs via les moteurs de recherche"""
        urls = []
        
        for search_engine in self.search_engines:
            try:
                search_url = search_engine.format(query.replace(' ', '+'))
                
                # Faire la recherche avec une session simple
                headers = {'User-Agent': Config.USER_AGENT}
                response = requests.get(search_url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Extraire les liens selon le moteur
                    if 'google.com' in search_url:
                        links = soup.find_all('a', href=True)
                        for link in links:
                            href = link['href']
                            if href.startswith('/url?q='):
                                # Nettoyer les URLs Google
                                url = href.split('/url?q=')[1].split('&')[0]
                                if self._is_valid_search_result(url):
                                    urls.append(url)
                    
                    elif 'duckduckgo.com' in search_url:
                        links = soup.find_all('a', {'data-testid': 'result-title-a'})
                        for link in links:
                            href = link.get('href')
                            if href and self._is_valid_search_result(href):
                                urls.append(href)
                    
                    elif 'bing.com' in search_url:
                        links = soup.find_all('a', href=True)
                        for link in links:
                            href = link['href']
                            if href.startswith('http') and self._is_valid_search_result(href):
                                urls.append(href)
                
                # Limite par moteur de recherche
                if len(urls) >= 20:
                    break
                    
                # Pause entre les moteurs
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Erreur recherche {search_engine}: {e}")
                continue
        
        # Supprimer les doublons et limiter
        return list(set(urls))[:30]
    
    async def _discover_links_from_url(self, url: str) -> List[str]:
        """Découvre des liens depuis une URL"""
        try:
            headers = {'User-Agent': Config.USER_AGENT}
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            links = []
            
            # Extraire tous les liens
            for link in soup.find_all('a', href=True):
                href = link['href']
                absolute_url = urljoin(url, href)
                
                if self._is_valid_discovery_url(absolute_url):
                    links.append(absolute_url)
            
            return list(set(links))[:50]  # Limiter et supprimer doublons
            
        except Exception as e:
            logger.error(f"Erreur découverte liens {url}: {e}")
            return []
    
    def _is_valid_search_result(self, url: str) -> bool:
        """Vérifie si une URL de résultat de recherche est valide"""
        if not url or not url.startswith('http'):
            return False
        
        # Exclure les URLs de moteurs de recherche eux-mêmes
        excluded_domains = [
            'google.com', 'bing.com', 'duckduckgo.com', 'yahoo.com',
            'facebook.com', 'twitter.com', 'linkedin.com', 'instagram.com',
            'youtube.com', 'tiktok.com'
        ]
        
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        for excluded in excluded_domains:
            if excluded in domain:
                return False
        
        return True
    
    def _is_valid_discovery_url(self, url: str) -> bool:
        """Vérifie si une URL découverte est valide pour l'exploration"""
        if not url or not url.startswith('http'):
            return False
        
        parsed = urlparse(url)
        
        # Exclure certaines extensions
        path = parsed.path.lower()
        excluded_extensions = [
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.ico',
            '.css', '.js', '.woff', '.woff2', '.ttf', '.eot',
            '.mp3', '.mp4', '.avi', '.mov', '.wmv', '.zip', '.rar'
        ]
        
        if any(path.endswith(ext) for ext in excluded_extensions):
            return False
        
        # Exclure certains patterns d'URL
        excluded_patterns = [
            '/api/', '/ajax/', '/json/', '/xml/',
            'login', 'register', 'cart', 'checkout',
            'admin', 'wp-admin', 'dashboard'
        ]
        
        if any(pattern in url.lower() for pattern in excluded_patterns):
            return False
        
        return True
    
    async def get_exploration_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques d'exploration"""
        return {
            'visited_urls': len(self.visited_urls),
            'discovered_urls': len(self.discovered_urls),
            'domains_explored': len(self.domain_limits),
            'domain_limits': dict(self.domain_limits)
        }
