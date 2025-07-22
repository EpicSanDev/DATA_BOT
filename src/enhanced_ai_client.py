"""
Client IA étendu pour DATA_BOT v2
Support de multiples modèles d'IA
"""

import asyncio
import logging
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    # Simuler httpx pour les tests
    class MockAsyncClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def get(self, url): 
            class MockResponse:
                status_code = 200
                def json(self): return {"ip": "127.0.0.1"}
                def raise_for_status(self): pass
            return MockResponse()
        async def post(self, url, **kwargs):
            class MockResponse:
                status_code = 200
                def json(self): return {"response": "Mock AI response"}
                def raise_for_status(self): pass
            return MockResponse()
    
    class MockHTTPX:
        AsyncClient = MockAsyncClient
    
    httpx = MockHTTPX()

from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod

from src.config import Config

logger = logging.getLogger(__name__)

class AIProvider(ABC):
    """Interface abstraite pour les fournisseurs d'IA"""
    
    @abstractmethod
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """Génère une réponse à partir d'un prompt"""
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """Vérifie si le fournisseur est disponible"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Retourne le nom du fournisseur"""
        pass

class OllamaProvider(AIProvider):
    """Fournisseur Ollama (original)"""
    
    def __init__(self, host: str = None, model: str = None):
        self.host = host or Config.OLLAMA_HOST
        self.model = model or Config.OLLAMA_MODEL
        self.client = None
    
    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
    
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """Génère une réponse via Ollama"""
        try:
            data = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": kwargs.get("temperature", 0.7),
                    "top_k": kwargs.get("top_k", 40),
                    "top_p": kwargs.get("top_p", 0.9)
                }
            }
            
            response = await self.client.post(
                f"{self.host}/api/generate",
                json=data
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "")
            
        except Exception as e:
            logger.error(f"Erreur Ollama: {e}")
            raise
    
    async def is_available(self) -> bool:
        """Vérifie la disponibilité d'Ollama"""
        try:
            response = await self.client.get(f"{self.host}/api/version")
            return response.status_code == 200
        except:
            return False
    
    def get_name(self) -> str:
        return f"Ollama ({self.model})"

class OpenAIProvider(AIProvider):
    """Fournisseur OpenAI (simulation - nécessiterait une vraie clé API)"""
    
    def __init__(self, api_key: str = None, model: str = "gpt-3.5-turbo"):
        self.api_key = api_key or "sk-fake-key-for-demo"
        self.model = model
        self.client = None
    
    async def __aenter__(self):
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
    
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """Simule une réponse OpenAI (pour démo)"""
        # En réalité, ceci ferait un appel à l'API OpenAI
        # Pour la démo, on retourne une réponse simulée
        await asyncio.sleep(0.1)  # Simuler la latence réseau
        
        if "search query" in prompt.lower():
            return "artificial intelligence news, machine learning trends, tech innovations"
        elif "evaluate url" in prompt.lower():
            return "This URL appears to contain valuable technical content worth archiving."
        elif "categorize" in prompt.lower():
            return json.dumps({
                "category": "Technology",
                "subcategory": "Artificial Intelligence",
                "tags": ["AI", "machine learning", "technology"],
                "priority": 8,
                "summary": "Content about AI and technology trends"
            })
        else:
            return "This is a simulated OpenAI response for demonstration purposes."
    
    async def is_available(self) -> bool:
        """Simule la vérification de disponibilité"""
        return self.api_key != "sk-fake-key-for-demo"  # Retourne False pour la démo
    
    def get_name(self) -> str:
        return f"OpenAI ({self.model})"

class LocalLLMProvider(AIProvider):
    """Fournisseur pour modèles LLM locaux (HuggingFace Transformers, etc.)"""
    
    def __init__(self, model_name: str = "gpt2"):
        self.model_name = model_name
        self.model = None
        self.tokenizer = None
    
    async def __aenter__(self):
        # Simule le chargement d'un modèle local
        # En réalité, on chargerait ici transformers, torch, etc.
        logger.info(f"Chargement simulé du modèle local: {self.model_name}")
        await asyncio.sleep(1)  # Simuler le temps de chargement
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Libérer les ressources du modèle
        self.model = None
        self.tokenizer = None
    
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """Simule la génération avec un modèle local"""
        await asyncio.sleep(0.5)  # Simuler le temps de traitement
        
        # Réponses simulées basées sur le prompt
        if "search" in prompt.lower():
            return "technology news, programming tutorials, open source projects"
        elif "evaluate" in prompt.lower():
            return "This content appears to be relevant and worth archiving."
        else:
            return f"Local LLM response for: {prompt[:50]}..."
    
    async def is_available(self) -> bool:
        """Vérifie si les dépendances locales sont disponibles"""
        try:
            # En réalité, on vérifierait l'import de transformers, torch, etc.
            return False  # Désactivé pour la démo
        except ImportError:
            return False
    
    def get_name(self) -> str:
        return f"Local LLM ({self.model_name})"

class FallbackProvider(AIProvider):
    """Fournisseur de secours avec réponses prédéfinies"""
    
    def __init__(self):
        self.responses = {
            "search_queries": [
                "technology news",
                "programming tutorials", 
                "open source projects",
                "artificial intelligence",
                "web development",
                "data science"
            ],
            "url_evaluation": "This URL contains potentially valuable content for archiving.",
            "categorization": {
                "category": "General",
                "subcategory": "Web Content", 
                "tags": ["web", "content"],
                "priority": 5,
                "summary": "General web content"
            }
        }
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
    
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """Génère des réponses prédéfinies"""
        prompt_lower = prompt.lower()
        
        if "search query" in prompt_lower or "generate queries" in prompt_lower:
            import random
            queries = random.sample(self.responses["search_queries"], 3)
            return ", ".join(queries)
        
        elif "evaluate url" in prompt_lower:
            return self.responses["url_evaluation"]
        
        elif "categorize" in prompt_lower:
            return json.dumps(self.responses["categorization"])
        
        else:
            return "This is a fallback response when AI providers are unavailable."
    
    async def is_available(self) -> bool:
        """Le fournisseur de secours est toujours disponible"""
        return True
    
    def get_name(self) -> str:
        return "Fallback Provider"

class EnhancedAIClient:
    """Client IA étendu avec support de multiples fournisseurs"""
    
    def __init__(self):
        self.providers: List[AIProvider] = []
        self.current_provider: Optional[AIProvider] = None
        self.fallback_provider = FallbackProvider()
        self.provider_preferences = ["ollama", "openai", "local", "fallback"]
    
    async def __aenter__(self):
        await self._initialize_providers()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        for provider in self.providers:
            try:
                await provider.__aexit__(exc_type, exc_val, exc_tb)
            except:
                pass
    
    async def _initialize_providers(self):
        """Initialize tous les fournisseurs disponibles"""
        # Ollama (original)
        ollama = OllamaProvider()
        try:
            await ollama.__aenter__()
            if await ollama.is_available():
                self.providers.append(ollama)
                logger.info("✅ Fournisseur Ollama disponible")
            else:
                logger.warning("⚠️ Fournisseur Ollama non disponible")
                await ollama.__aexit__(None, None, None)
        except Exception as e:
            logger.warning(f"⚠️ Erreur initialisation Ollama: {e}")
        
        # OpenAI (simulé)
        openai = OpenAIProvider()
        try:
            await openai.__aenter__()
            if await openai.is_available():
                self.providers.append(openai)
                logger.info("✅ Fournisseur OpenAI disponible")
            else:
                logger.info("ℹ️ Fournisseur OpenAI non configuré (clé API manquante)")
                await openai.__aexit__(None, None, None)
        except Exception as e:
            logger.warning(f"⚠️ Erreur initialisation OpenAI: {e}")
        
        # Modèle local (simulé)
        local_llm = LocalLLMProvider()
        try:
            await local_llm.__aenter__()
            if await local_llm.is_available():
                self.providers.append(local_llm)
                logger.info("✅ Fournisseur LLM local disponible")
            else:
                logger.info("ℹ️ Fournisseur LLM local non disponible (dépendances manquantes)")
                await local_llm.__aexit__(None, None, None)
        except Exception as e:
            logger.warning(f"⚠️ Erreur initialisation LLM local: {e}")
        
        # Fallback toujours disponible
        await self.fallback_provider.__aenter__()
        self.providers.append(self.fallback_provider)
        logger.info("✅ Fournisseur de secours activé")
        
        # Sélectionner le fournisseur préféré
        self.current_provider = self._select_best_provider()
        logger.info(f"🤖 Fournisseur actif: {self.current_provider.get_name()}")
    
    def _select_best_provider(self) -> AIProvider:
        """Sélectionne le meilleur fournisseur disponible"""
        for pref in self.provider_preferences:
            for provider in self.providers:
                provider_name = provider.get_name().lower()
                if pref in provider_name:
                    return provider
        
        # Par défaut, retourner le premier disponible
        return self.providers[0] if self.providers else self.fallback_provider
    
    async def generate_search_queries(self, context: str = "", count: int = 5) -> List[str]:
        """Génère des requêtes de recherche intelligentes"""
        prompt = f"""Generate {count} diverse and interesting search queries for web archiving.
        Context: {context}
        Focus on: technology, programming, science, culture, news
        Return queries separated by commas."""
        
        try:
            response = await self.current_provider.generate_response(prompt)
            queries = [q.strip() for q in response.split(',') if q.strip()]
            return queries[:count]
        except Exception as e:
            logger.error(f"Erreur génération requêtes: {e}")
            return await self._fallback_search_queries(count)
    
    async def _fallback_search_queries(self, count: int) -> List[str]:
        """Requêtes de secours si l'IA échoue"""
        fallback_queries = [
            "artificial intelligence news",
            "open source programming",
            "machine learning tutorials",
            "web development trends",
            "cybersecurity updates",
            "data science resources",
            "technology innovations",
            "software engineering best practices"
        ]
        import random
        return random.sample(fallback_queries, min(count, len(fallback_queries)))
    
    async def evaluate_url(self, url: str, title: str = "", content_preview: str = "") -> Dict[str, Any]:
        """Évalue si une URL vaut la peine d'être archivée"""
        prompt = f"""Evaluate if this URL is worth archiving:
        URL: {url}
        Title: {title}
        Preview: {content_preview[:200]}...
        
        Consider: relevance, uniqueness, information value, quality
        Return a JSON with: should_archive (boolean), score (1-10), reason (string)"""
        
        try:
            response = await self.current_provider.generate_response(prompt)
            
            # Tenter de parser la réponse JSON
            try:
                result = json.loads(response)
                return {
                    'should_archive': result.get('should_archive', True),
                    'score': result.get('score', 6),
                    'reason': result.get('reason', 'Content evaluation')
                }
            except json.JSONDecodeError:
                # Si pas JSON, analyser la réponse texte
                should_archive = 'worth' in response.lower() or 'valuable' in response.lower()
                return {
                    'should_archive': should_archive,
                    'score': 7 if should_archive else 4,
                    'reason': response[:100]
                }
                
        except Exception as e:
            logger.error(f"Erreur évaluation URL: {e}")
            return {
                'should_archive': True,
                'score': 5,
                'reason': 'Default evaluation due to AI error'
            }
    
    async def categorize_content(self, url: str, title: str, content: str) -> Dict[str, Any]:
        """Catégorise et analyse le contenu"""
        prompt = f"""Categorize this web content:
        URL: {url}
        Title: {title}
        Content: {content[:500]}...
        
        Return JSON with:
        - category: main category
        - subcategory: specific subcategory  
        - tags: array of relevant tags
        - priority: importance score 1-10
        - summary: brief description
        - language: detected language"""
        
        try:
            response = await self.current_provider.generate_response(prompt)
            
            try:
                result = json.loads(response)
                return {
                    'category': result.get('category', 'General'),
                    'subcategory': result.get('subcategory', 'Web Content'),
                    'tags': result.get('tags', []),
                    'priority': result.get('priority', 5),
                    'summary': result.get('summary', ''),
                    'language': result.get('language', 'unknown')
                }
            except json.JSONDecodeError:
                # Analyse de secours basée sur le contenu
                return self._analyze_content_fallback(url, title, content)
                
        except Exception as e:
            logger.error(f"Erreur catégorisation: {e}")
            return self._analyze_content_fallback(url, title, content)
    
    def _analyze_content_fallback(self, url: str, title: str, content: str) -> Dict[str, Any]:
        """Analyse de secours sans IA"""
        # Analyse basique par mots-clés
        tech_keywords = ['programming', 'code', 'software', 'technology', 'api', 'github']
        science_keywords = ['research', 'study', 'paper', 'science', 'analysis']
        news_keywords = ['news', 'article', 'report', 'update', 'announcement']
        
        text = f"{title} {content}".lower()
        
        if any(keyword in text for keyword in tech_keywords):
            category = 'Technology'
            subcategory = 'Programming'
            tags = ['tech', 'programming']
        elif any(keyword in text for keyword in science_keywords):
            category = 'Science'
            subcategory = 'Research'
            tags = ['science', 'research']
        elif any(keyword in text for keyword in news_keywords):
            category = 'News'
            subcategory = 'Current Events'
            tags = ['news', 'current events']
        else:
            category = 'General'
            subcategory = 'Web Content'
            tags = ['web', 'content']
        
        return {
            'category': category,
            'subcategory': subcategory,
            'tags': tags,
            'priority': 5,
            'summary': title[:100] if title else 'Web content',
            'language': 'unknown'
        }
    
    async def switch_provider(self, provider_name: str) -> bool:
        """Change le fournisseur d'IA actuel"""
        for provider in self.providers:
            if provider_name.lower() in provider.get_name().lower():
                self.current_provider = provider
                logger.info(f"🔄 Fournisseur changé pour: {provider.get_name()}")
                return True
        
        logger.warning(f"Fournisseur non trouvé: {provider_name}")
        return False
    
    async def get_provider_status(self) -> Dict[str, Any]:
        """Retourne le statut de tous les fournisseurs"""
        status = {
            'current_provider': self.current_provider.get_name() if self.current_provider else None,
            'available_providers': [],
            'total_providers': len(self.providers)
        }
        
        for provider in self.providers:
            try:
                is_available = await provider.is_available()
                status['available_providers'].append({
                    'name': provider.get_name(),
                    'available': is_available,
                    'type': provider.__class__.__name__
                })
            except Exception as e:
                status['available_providers'].append({
                    'name': provider.get_name(),
                    'available': False,
                    'error': str(e),
                    'type': provider.__class__.__name__
                })
        
        return status
    
    async def test_all_providers(self) -> Dict[str, Any]:
        """Teste tous les fournisseurs avec un prompt simple"""
        test_prompt = "Generate a simple test response."
        results = {}
        
        for provider in self.providers:
            try:
                start_time = asyncio.get_event_loop().time()
                response = await provider.generate_response(test_prompt)
                end_time = asyncio.get_event_loop().time()
                
                results[provider.get_name()] = {
                    'success': True,
                    'response_time': end_time - start_time,
                    'response_length': len(response),
                    'response_preview': response[:100]
                }
            except Exception as e:
                results[provider.get_name()] = {
                    'success': False,
                    'error': str(e),
                    'response_time': None
                }
        
        return results