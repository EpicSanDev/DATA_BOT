"""
Module de support proxy pour DATA_BOT v2
"""

import asyncio
import logging
import random
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    # Mock pour les tests
    class MockAsyncClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def get(self, url):
            class MockResponse:
                status_code = 200
            return MockResponse()
    
    class MockHTTPX:
        AsyncClient = MockAsyncClient
    
    httpx = MockHTTPX()

from typing import List, Dict, Optional, Union
from urllib.parse import urlparse

from src.core.config import Config

logger = logging.getLogger(__name__)

class ProxyManager:
    """Gestionnaire de proxies pour les requêtes web"""
    
    def __init__(self):
        self.proxies: List[Dict] = []
        self.current_proxy_index = 0
        self.failed_proxies: set = set()
        self.rotation_strategy = "round_robin"  # round_robin, random, failover
        
        # Charger les proxies depuis la configuration
        self._load_proxies()
    
    def _load_proxies(self):
        """Charge la liste des proxies depuis la configuration"""
        # Configuration via variables d'environnement
        import os
        
        proxy_list = os.getenv("PROXY_LIST", "")
        if proxy_list:
            for proxy_string in proxy_list.split(','):
                proxy_string = proxy_string.strip()
                if proxy_string:
                    proxy_info = self._parse_proxy_string(proxy_string)
                    if proxy_info:
                        self.proxies.append(proxy_info)
        
        # Ajouter des proxies publics de test (pour démonstration)
        if not self.proxies:
            self._add_demo_proxies()
        
        logger.info(f"📡 {len(self.proxies)} proxies configurés")
    
    def _parse_proxy_string(self, proxy_string: str) -> Optional[Dict]:
        """Parse une chaîne de proxy en dictionnaire"""
        try:
            # Format: protocol://username:password@host:port
            # ou: protocol://host:port
            # ou: host:port (assume http)
            
            if '://' not in proxy_string and ':' in proxy_string:
                proxy_string = f"http://{proxy_string}"
            
            parsed = urlparse(proxy_string)
            
            proxy_info = {
                'protocol': parsed.scheme or 'http',
                'host': parsed.hostname,
                'port': parsed.port,
                'username': parsed.username,
                'password': parsed.password,
                'url': proxy_string,
                'working': True,
                'last_tested': None,
                'response_time': None
            }
            
            return proxy_info
            
        except Exception as e:
            logger.warning(f"Impossible de parser le proxy {proxy_string}: {e}")
            return None
    
    def _add_demo_proxies(self):
        """Ajoute des proxies de démonstration (fictifs)"""
        demo_proxies = [
            "http://proxy1.example.com:8080",
            "http://proxy2.example.com:3128", 
            "http://user:pass@proxy3.example.com:8080",
            "socks5://proxy4.example.com:1080"
        ]
        
        for proxy_string in demo_proxies:
            proxy_info = self._parse_proxy_string(proxy_string)
            if proxy_info:
                proxy_info['demo'] = True  # Marquer comme démo
                self.proxies.append(proxy_info)
    
    def get_next_proxy(self) -> Optional[Dict]:
        """Obtient le prochain proxy selon la stratégie"""
        if not self.proxies:
            return None
        
        if self.rotation_strategy == "round_robin":
            return self._get_round_robin_proxy()
        elif self.rotation_strategy == "random":
            return self._get_random_proxy()
        elif self.rotation_strategy == "failover":
            return self._get_failover_proxy()
        else:
            return self.proxies[0]
    
    def _get_round_robin_proxy(self) -> Optional[Dict]:
        """Proxy en rotation circulaire"""
        if not self.proxies:
            return None
        
        # Filtrer les proxies défaillants
        working_proxies = [p for p in self.proxies if p['url'] not in self.failed_proxies]
        
        if not working_proxies:
            # Réinitialiser si tous les proxies ont échoué
            self.failed_proxies.clear()
            working_proxies = self.proxies
        
        proxy = working_proxies[self.current_proxy_index % len(working_proxies)]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(working_proxies)
        
        return proxy
    
    def _get_random_proxy(self) -> Optional[Dict]:
        """Proxy aléatoire"""
        working_proxies = [p for p in self.proxies if p['url'] not in self.failed_proxies]
        
        if not working_proxies:
            self.failed_proxies.clear()
            working_proxies = self.proxies
        
        return random.choice(working_proxies) if working_proxies else None
    
    def _get_failover_proxy(self) -> Optional[Dict]:
        """Proxy de basculement (toujours le premier qui fonctionne)"""
        for proxy in self.proxies:
            if proxy['url'] not in self.failed_proxies:
                return proxy
        
        # Réinitialiser si tous ont échoué
        self.failed_proxies.clear()
        return self.proxies[0] if self.proxies else None
    
    def mark_proxy_failed(self, proxy: Dict):
        """Marque un proxy comme défaillant"""
        self.failed_proxies.add(proxy['url'])
        proxy['working'] = False
        logger.warning(f"❌ Proxy marqué comme défaillant: {proxy['url']}")
    
    def mark_proxy_working(self, proxy: Dict, response_time: float = None):
        """Marque un proxy comme fonctionnel"""
        if proxy['url'] in self.failed_proxies:
            self.failed_proxies.remove(proxy['url'])
        
        proxy['working'] = True
        proxy['response_time'] = response_time
        from datetime import datetime
        proxy['last_tested'] = datetime.now()
        
        logger.debug(f"✅ Proxy fonctionne: {proxy['url']} ({response_time:.2f}s)")
    
    async def test_proxy(self, proxy: Dict, test_url: str = "http://httpbin.org/ip") -> bool:
        """Teste un proxy spécifique"""
        try:
            proxy_url = self._format_proxy_url(proxy)
            
            async with httpx.AsyncClient(
                proxies={"http://": proxy_url, "https://": proxy_url},
                timeout=10.0
            ) as client:
                start_time = asyncio.get_event_loop().time()
                response = await client.get(test_url)
                end_time = asyncio.get_event_loop().time()
                
                if response.status_code == 200:
                    response_time = end_time - start_time
                    self.mark_proxy_working(proxy, response_time)
                    return True
                else:
                    self.mark_proxy_failed(proxy)
                    return False
                    
        except Exception as e:
            logger.debug(f"Test proxy échoué {proxy['url']}: {e}")
            self.mark_proxy_failed(proxy)
            return False
    
    async def test_all_proxies(self) -> Dict[str, any]:
        """Teste tous les proxies"""
        logger.info("🧪 Test de tous les proxies...")
        
        results = {
            'total': len(self.proxies),
            'working': 0,
            'failed': 0,
            'details': []
        }
        
        for proxy in self.proxies:
            # Skip les proxies de démo
            if proxy.get('demo'):
                results['details'].append({
                    'url': proxy['url'],
                    'status': 'demo',
                    'response_time': None
                })
                continue
            
            is_working = await self.test_proxy(proxy)
            
            if is_working:
                results['working'] += 1
                status = 'working'
            else:
                results['failed'] += 1
                status = 'failed'
            
            results['details'].append({
                'url': proxy['url'],
                'status': status,
                'response_time': proxy.get('response_time')
            })
        
        logger.info(f"✅ Test proxies terminé: {results['working']}/{results['total']} fonctionnels")
        return results
    
    def _format_proxy_url(self, proxy: Dict) -> str:
        """Formate l'URL du proxy pour httpx"""
        if proxy.get('username') and proxy.get('password'):
            return f"{proxy['protocol']}://{proxy['username']}:{proxy['password']}@{proxy['host']}:{proxy['port']}"
        else:
            return f"{proxy['protocol']}://{proxy['host']}:{proxy['port']}"
    
    def get_proxy_config_for_httpx(self, proxy: Dict = None) -> Optional[Dict]:
        """Retourne la configuration proxy pour httpx"""
        if not proxy:
            proxy = self.get_next_proxy()
        
        if not proxy or proxy.get('demo'):
            return None
        
        proxy_url = self._format_proxy_url(proxy)
        return {
            "http://": proxy_url,
            "https://": proxy_url
        }
    
    def get_stats(self) -> Dict[str, any]:
        """Retourne les statistiques des proxies"""
        working = sum(1 for p in self.proxies if p.get('working', True) and p['url'] not in self.failed_proxies)
        failed = len(self.failed_proxies)
        
        return {
            'total_proxies': len(self.proxies),
            'working_proxies': working,
            'failed_proxies': failed,
            'rotation_strategy': self.rotation_strategy,
            'current_index': self.current_proxy_index
        }
    
    def set_rotation_strategy(self, strategy: str):
        """Change la stratégie de rotation"""
        if strategy in ["round_robin", "random", "failover"]:
            self.rotation_strategy = strategy
            logger.info(f"🔄 Stratégie de rotation changée: {strategy}")
        else:
            logger.warning(f"Stratégie inconnue: {strategy}")
    
    def add_proxy(self, proxy_string: str) -> bool:
        """Ajoute un nouveau proxy"""
        proxy_info = self._parse_proxy_string(proxy_string)
        if proxy_info:
            self.proxies.append(proxy_info)
            logger.info(f"➕ Proxy ajouté: {proxy_string}")
            return True
        return False
    
    def remove_proxy(self, proxy_url: str) -> bool:
        """Supprime un proxy"""
        for i, proxy in enumerate(self.proxies):
            if proxy['url'] == proxy_url:
                del self.proxies[i]
                self.failed_proxies.discard(proxy_url)
                logger.info(f"➖ Proxy supprimé: {proxy_url}")
                return True
        return False
    
    def clear_failed_proxies(self):
        """Efface la liste des proxies défaillants"""
        self.failed_proxies.clear()
        logger.info("🧹 Liste des proxies défaillants effacée")
    
    def get_best_proxies(self, limit: int = 5) -> List[Dict]:
        """Retourne les meilleurs proxies (par temps de réponse)"""
        working_proxies = [p for p in self.proxies 
                          if p.get('working', True) and p['url'] not in self.failed_proxies
                          and p.get('response_time') is not None]
        
        # Trier par temps de réponse
        working_proxies.sort(key=lambda x: x.get('response_time', float('inf')))
        
        return working_proxies[:limit]