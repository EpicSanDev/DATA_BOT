import asyncio
import aiohttp
import logging
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin, urlparse
import json
from src.core.config import Config

logger = logging.getLogger(__name__)

class OllamaClient:
    def __init__(self, host: str = None, model: str = None):
        self.host = host or Config.OLLAMA_HOST
        self.model = model or Config.OLLAMA_MODEL
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def generate_search_queries(self, context: str = "", num_queries: int = 5) -> List[str]:
        """Génère des requêtes de recherche intelligentes avec Ollama"""
        prompt = f"""
        Tu es un assistant spécialisé dans la génération de requêtes de recherche pour archiver automatiquement des contenus web intéressants.
        
        Contexte: {context if context else "Exploration générale d'Internet"}
        
        Génère {num_queries} requêtes de recherche diverses et intéressantes qui permettront de découvrir du contenu web varié à archiver.
        Les requêtes doivent couvrir différents domaines comme:
        - Actualités et événements récents
        - Ressources éducatives et scientifiques
        - Culture et arts
        - Technologie et innovation
        - Histoire et patrimoine
        - Ressources pratiques et utiles
        
        Retourne UNIQUEMENT une liste JSON de requêtes, par exemple:
        ["intelligence artificielle 2024", "musées virtuels", "documentation technique opensource", "actualités science", "tutoriels programmation"]
        """
        
        try:
            response = await self._make_request(prompt)
            # Nettoyer et parser la réponse
            content = response.strip()
            if content.startswith('```'):
                content = content.split('\n', 1)[1]
            if content.endswith('```'):
                content = content.rsplit('\n', 1)[0]
            
            queries = json.loads(content)
            return queries[:num_queries]
        except Exception as e:
            logger.error(f"Erreur génération requêtes Ollama: {e}")
            # Fallback avec des requêtes par défaut
            return [
                "actualités technologie 2024",
                "ressources éducatives gratuites",
                "documentation développement",
                "culture numérique",
                "science nouvelles découvertes"
            ][:num_queries]
    
    async def categorize_content(self, url: str, title: str, content_preview: str) -> Dict[str, Any]:
        """Catégorise automatiquement le contenu web"""
        prompt = f"""
        Analyse ce contenu web et catégorise-le:
        
        URL: {url}
        Titre: {title}
        Aperçu du contenu: {content_preview[:500]}...
        
        Retourne un JSON avec:
        - category: une catégorie principale (tech, education, news, culture, science, business, entertainment, other)
        - subcategory: sous-catégorie plus spécifique
        - tags: liste de 3-5 tags pertinents
        - priority: nombre de 1 à 10 (importance pour archivage)
        - language: langue détectée (fr, en, es, etc.)
        - content_type: type de contenu (article, tutorial, documentation, news, blog, reference, other)
        
        Exemple de réponse:
        {{"category": "tech", "subcategory": "ai", "tags": ["intelligence artificielle", "machine learning", "tutorial"], "priority": 8, "language": "fr", "content_type": "tutorial"}}
        """
        
        try:
            response = await self._make_request(prompt)
            content = response.strip()
            if content.startswith('```'):
                content = content.split('\n', 1)[1]
            if content.endswith('```'):
                content = content.rsplit('\n', 1)[0]
            
            return json.loads(content)
        except Exception as e:
            logger.error(f"Erreur catégorisation Ollama: {e}")
            return {
                "category": "other",
                "subcategory": "unknown",
                "tags": [],
                "priority": 5,
                "language": "unknown",
                "content_type": "other"
            }
    
    async def should_archive_url(self, url: str, title: str = "", domain_stats: Dict = None) -> Dict[str, Any]:
        """Détermine si une URL vaut la peine d'être archivée"""
        prompt = f"""
        Détermine si cette URL vaut la peine d'être archivée automatiquement:
        
        URL: {url}
        Titre: {title}
        Statistiques du domaine: {domain_stats}
        
        Analyse selon ces critères:
        - Qualité et utilité du contenu
        - Unicité et rareté de l'information
        - Valeur historique ou de référence
        - Éviter le spam et contenu de faible qualité
        - Éviter les pages purement commerciales
        
        Retourne un JSON avec:
        - should_archive: true/false
        - confidence: score de 0 à 100
        - reasons: liste des raisons pour/contre
        - suggested_priority: 1-10
        
        Exemple:
        {{"should_archive": true, "confidence": 85, "reasons": ["contenu éducatif unique", "ressource de référence"], "suggested_priority": 7}}
        """
        
        try:
            response = await self._make_request(prompt)
            content = response.strip()
            if content.startswith('```'):
                content = content.split('\n', 1)[1]
            if content.endswith('```'):
                content = content.rsplit('\n', 1)[0]
            
            return json.loads(content)
        except Exception as e:
            logger.error(f"Erreur évaluation URL Ollama: {e}")
            return {
                "should_archive": True,
                "confidence": 50,
                "reasons": ["evaluation failed, defaulting to archive"],
                "suggested_priority": 5
            }
    
    async def _make_request(self, prompt: str) -> str:
        """Fait une requête à Ollama"""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "max_tokens": 1000
            }
        }
        
        async with self.session.post(
            f"{self.host}/api/generate",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            if response.status != 200:
                raise Exception(f"Ollama request failed: {response.status}")
            
            result = await response.json()
            return result.get("response", "")
