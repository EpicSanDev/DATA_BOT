"""
Gestionnaire Elasticsearch pour DATA_BOT v3
Recherche full-text avancée et analytics
"""

import asyncio
import logging
import json
import hashlib
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass
from pathlib import Path

try:
    from elasticsearch import AsyncElasticsearch
    from elasticsearch.helpers import async_bulk
    ELASTICSEARCH_AVAILABLE = True
except ImportError:
    ELASTICSEARCH_AVAILABLE = False

from src.core.models import WebResource, ContentType
from src.database.database import DatabaseManager

logger = logging.getLogger(__name__)

@dataclass
class ElasticsearchHit:
    """Résultat de recherche Elasticsearch"""
    url: str
    title: Optional[str]
    content: Optional[str]
    score: float
    highlights: Dict[str, List[str]]
    metadata: Dict[str, Any]
    snippet: Optional[str] = None

@dataclass
class ElasticsearchResults:
    """Résultats de recherche Elasticsearch"""
    hits: List[ElasticsearchHit]
    total: int
    max_score: float
    took: int  # Temps en ms
    aggregations: Optional[Dict[str, Any]] = None

@dataclass
class ElasticsearchStats:
    """Statistiques Elasticsearch"""
    total_documents: int
    index_size_mb: float
    last_updated: datetime
    cluster_health: str
    node_count: int

class ElasticsearchManager:
    """Gestionnaire Elasticsearch pour recherche full-text"""
    
    def __init__(self, host: str = "localhost", port: int = 9200, 
                 index_name: str = "databot_archive"):
        self.host = host
        self.port = port
        self.index_name = index_name
        self.client = None
        self.db_manager = DatabaseManager()
        
        # Configuration de mapping Elasticsearch
        self.mapping = {
            "mappings": {
                "properties": {
                    "url": {
                        "type": "keyword",
                        "index": True
                    },
                    "title": {
                        "type": "text",
                        "analyzer": "standard",
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                                "ignore_above": 256
                            }
                        }
                    },
                    "content": {
                        "type": "text",
                        "analyzer": "standard"
                    },
                    "content_type": {
                        "type": "keyword"
                    },
                    "domain": {
                        "type": "keyword"
                    },
                    "tags": {
                        "type": "keyword"
                    },
                    "file_path": {
                        "type": "keyword",
                        "index": False
                    },
                    "created_at": {
                        "type": "date"
                    },
                    "updated_at": {
                        "type": "date"
                    },
                    "status": {
                        "type": "keyword"
                    },
                    "size_bytes": {
                        "type": "long"
                    },
                    "language": {
                        "type": "keyword"
                    },
                    "author": {
                        "type": "text",
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                                "ignore_above": 256
                            }
                        }
                    },
                    "description": {
                        "type": "text"
                    },
                    "metadata": {
                        "type": "object",
                        "dynamic": True
                    }
                }
            },
            "settings": {
                "index": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "refresh_interval": "1s"
                },
                "analysis": {
                    "analyzer": {
                        "custom_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "char_filter": ["html_strip"],
                            "filter": ["lowercase", "stop", "stemmer"]
                        }
                    },
                    "filter": {
                        "stemmer": {
                            "type": "stemmer",
                            "language": "french"
                        }
                    }
                }
            }
        }
    
    async def initialize(self):
        """Initialise la connexion Elasticsearch"""
        if not ELASTICSEARCH_AVAILABLE:
            raise ImportError("Elasticsearch n'est pas installé. pip install elasticsearch")
        
        logger.info(f"🔎 Initialisation d'Elasticsearch: {self.host}:{self.port}")
        
        # Créer le client
        self.client = AsyncElasticsearch(
            hosts=[{"host": self.host, "port": self.port}],
            timeout=30,
            max_retries=3,
            retry_on_timeout=True
        )
        
        try:
            # Tester la connexion
            info = await self.client.info()
            logger.info(f"Connecté à Elasticsearch {info['version']['number']}")
            
            # Créer l'index s'il n'existe pas
            exists = await self.client.indices.exists(index=self.index_name)
            if not exists:
                await self.client.indices.create(
                    index=self.index_name,
                    body=self.mapping
                )
                logger.info(f"Index créé: {self.index_name}")
            else:
                logger.info(f"Index existant: {self.index_name}")
                
        except Exception as e:
            logger.error(f"Erreur connexion Elasticsearch: {e}")
            raise
        
        logger.info("✅ Elasticsearch initialisé")
    
    def _extract_domain(self, url: str) -> str:
        """Extrait le domaine d'une URL"""
        try:
            from urllib.parse import urlparse
            return urlparse(url).netloc
        except Exception:
            return ""
    
    def _detect_language(self, content: str) -> str:
        """Détecte la langue du contenu (simple heuristique)"""
        if not content:
            return "unknown"
        
        # Mots français courants
        french_words = ["le", "de", "et", "à", "un", "il", "être", "et", "en", "avoir", "que", "pour"]
        # Mots anglais courants  
        english_words = ["the", "of", "and", "to", "a", "in", "is", "it", "you", "that", "he", "was"]
        
        words = content.lower().split()[:100]  # Analyser les 100 premiers mots
        
        french_count = sum(1 for word in words if word in french_words)
        english_count = sum(1 for word in words if word in english_words)
        
        if french_count > english_count:
            return "fr"
        elif english_count > french_count:
            return "en"
        else:
            return "unknown"
    
    async def index_resource(self, resource: WebResource, content: Optional[str] = None) -> bool:
        """Indexe une ressource dans Elasticsearch"""
        try:
            if not content:
                # Essayer de lire le contenu depuis le fichier
                if resource.file_path and Path(resource.file_path).exists():
                    try:
                        content = Path(resource.file_path).read_text(encoding='utf-8')
                    except Exception as e:
                        logger.warning(f"Impossible de lire {resource.file_path}: {e}")
                        content = ""
                else:
                    content = ""
            
            # Préparer le document
            doc = {
                "url": resource.url,
                "title": resource.title or "",
                "content": content,
                "content_type": resource.content_type.value,
                "domain": self._extract_domain(resource.url),
                "tags": resource.tags or [],
                "file_path": resource.file_path or "",
                "created_at": resource.discovered_at.isoformat() if resource.discovered_at else datetime.now().isoformat(),
                "updated_at": resource.archived_at.isoformat() if resource.archived_at else None,
                "status": resource.status.value,
                "size_bytes": resource.content_length or 0,
                "language": self._detect_language(content),
                "description": content[:500] if content else "",  # Extrait court
                "metadata": resource.metadata or {}
            }
            
            # Indexer le document
            doc_id = hashlib.md5(resource.url.encode()).hexdigest()
            
            response = await self.client.index(
                index=self.index_name,
                id=doc_id,
                body=doc
            )
            
            logger.debug(f"Ressource indexée: {resource.url} (ID: {doc_id})")
            return True
            
        except Exception as e:
            logger.error(f"Erreur indexation Elasticsearch {resource.url}: {e}")
            return False
    
    async def advanced_search(self, query: str, 
                            filters: Optional[Dict[str, Any]] = None,
                            sort: Optional[str] = None,
                            limit: int = 10,
                            offset: int = 0,
                            highlight: bool = True) -> ElasticsearchResults:
        """Recherche avancée dans Elasticsearch"""
        try:
            # Construire la requête
            es_query = {
                "query": {
                    "bool": {
                        "should": [
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["title^3", "content^1", "description^2"],
                                    "type": "best_fields",
                                    "fuzziness": "AUTO"
                                }
                            },
                            {
                                "wildcard": {
                                    "url": f"*{query.lower()}*"
                                }
                            }
                        ],
                        "minimum_should_match": 1
                    }
                }
            }
            
            # Ajouter les filtres
            if filters:
                filter_clauses = []
                
                if "content_type" in filters:
                    filter_clauses.append({
                        "term": {"content_type": filters["content_type"]}
                    })
                
                if "domain" in filters:
                    filter_clauses.append({
                        "term": {"domain": filters["domain"]}
                    })
                
                if "tags" in filters:
                    filter_clauses.append({
                        "terms": {"tags": filters["tags"] if isinstance(filters["tags"], list) else [filters["tags"]]}
                    })
                
                if "date_from" in filters:
                    filter_clauses.append({
                        "range": {
                            "created_at": {
                                "gte": filters["date_from"]
                            }
                        }
                    })
                
                if "date_to" in filters:
                    filter_clauses.append({
                        "range": {
                            "created_at": {
                                "lte": filters["date_to"]
                            }
                        }
                    })
                
                if "language" in filters:
                    filter_clauses.append({
                        "term": {"language": filters["language"]}
                    })
                
                if filter_clauses:
                    es_query["query"]["bool"]["filter"] = filter_clauses
            
            # Tri
            sort_clause = []
            if sort:
                if sort == "relevance":
                    sort_clause = [{"_score": {"order": "desc"}}]
                elif sort == "date":
                    sort_clause = [{"created_at": {"order": "desc"}}]
                elif sort == "title":
                    sort_clause = [{"title.keyword": {"order": "asc"}}]
                elif sort == "domain":
                    sort_clause = [{"domain": {"order": "asc"}}]
            else:
                sort_clause = [{"_score": {"order": "desc"}}]
            
            # Highlighting
            highlight_config = {}
            if highlight:
                highlight_config = {
                    "fields": {
                        "title": {
                            "fragment_size": 150,
                            "number_of_fragments": 3
                        },
                        "content": {
                            "fragment_size": 150,
                            "number_of_fragments": 3
                        },
                        "description": {
                            "fragment_size": 150,
                            "number_of_fragments": 2
                        }
                    },
                    "pre_tags": ["<mark>"],
                    "post_tags": ["</mark>"]
                }
            
            # Agrégations pour les facettes
            aggregations = {
                "content_types": {
                    "terms": {"field": "content_type", "size": 10}
                },
                "domains": {
                    "terms": {"field": "domain", "size": 20}
                },
                "tags": {
                    "terms": {"field": "tags", "size": 30}
                },
                "languages": {
                    "terms": {"field": "language", "size": 10}
                }
            }
            
            # Construire la requête complète
            search_body = {
                "query": es_query["query"],
                "from": offset,
                "size": limit,
                "sort": sort_clause,
                "aggs": aggregations
            }
            
            if highlight_config:
                search_body["highlight"] = highlight_config
            
            # Exécuter la recherche
            response = await self.client.search(
                index=self.index_name,
                body=search_body
            )
            
            # Convertir les résultats
            hits = []
            for hit in response["hits"]["hits"]:
                source = hit["_source"]
                highlights = hit.get("highlight", {})
                
                # Créer le snippet
                snippet = ""
                if "content" in highlights:
                    snippet = " ".join(highlights["content"][:2])
                elif "description" in highlights:
                    snippet = highlights["description"][0]
                elif source.get("description"):
                    snippet = source["description"][:200] + "..."
                
                hits.append(ElasticsearchHit(
                    url=source["url"],
                    title=source.get("title"),
                    content=source.get("content", ""),
                    score=hit["_score"],
                    highlights=highlights,
                    metadata=source.get("metadata", {}),
                    snippet=snippet
                ))
            
            return ElasticsearchResults(
                hits=hits,
                total=response["hits"]["total"]["value"],
                max_score=response["hits"]["max_score"] or 0.0,
                took=response["took"],
                aggregations=response.get("aggregations", {})
            )
            
        except Exception as e:
            logger.error(f"Erreur recherche Elasticsearch: {e}")
            return ElasticsearchResults(hits=[], total=0, max_score=0.0, took=0)
    
    async def suggest(self, query: str, limit: int = 5) -> List[str]:
        """Suggestions de recherche"""
        try:
            # Recherche de suggestions basée sur les titres
            search_body = {
                "suggest": {
                    "title_suggest": {
                        "prefix": query,
                        "completion": {
                            "field": "title.suggest",
                            "size": limit
                        }
                    }
                }
            }
            
            response = await self.client.search(
                index=self.index_name,
                body=search_body
            )
            
            suggestions = []
            for suggestion in response["suggest"]["title_suggest"][0]["options"]:
                suggestions.append(suggestion["text"])
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Erreur suggestions Elasticsearch: {e}")
            return []
    
    async def get_analytics(self) -> Dict[str, Any]:
        """Récupère les analytics de l'archive"""
        try:
            # Agrégations pour les analytics
            search_body = {
                "size": 0,
                "aggs": {
                    "content_types_distribution": {
                        "terms": {"field": "content_type", "size": 10}
                    },
                    "top_domains": {
                        "terms": {"field": "domain", "size": 20}
                    },
                    "creation_timeline": {
                        "date_histogram": {
                            "field": "created_at",
                            "calendar_interval": "day",
                            "min_doc_count": 1
                        }
                    },
                    "language_distribution": {
                        "terms": {"field": "language", "size": 10}
                    },
                    "size_stats": {
                        "stats": {"field": "size_bytes"}
                    },
                    "popular_tags": {
                        "terms": {"field": "tags", "size": 30}
                    }
                }
            }
            
            response = await self.client.search(
                index=self.index_name,
                body=search_body
            )
            
            return {
                "total_documents": response["hits"]["total"]["value"],
                "aggregations": response["aggregations"]
            }
            
        except Exception as e:
            logger.error(f"Erreur analytics Elasticsearch: {e}")
            return {}
    
    async def index_all_content(self) -> ElasticsearchStats:
        """Indexe tout le contenu de l'archive"""
        logger.info("🔄 Indexation de tout le contenu dans Elasticsearch...")
        
        # TODO: Récupérer toutes les ressources de la base
        # Pour le moment, simuler quelques ressources
        
        total_indexed = 0
        total_errors = 0
        
        sample_resources = [
            WebResource(
                url="https://example.com/page1",
                title="Example Page 1",
                content_type=ContentType.WEB_PAGE,
                file_path=None
            ),
            WebResource(
                url="https://example.com/page2",
                title="Example Page 2", 
                content_type=ContentType.WEB_PAGE,
                file_path=None
            )
        ]
        
        for resource in sample_resources:
            # Contenu factice pour la démo
            sample_content = f"Contenu de la page {resource.title}. Ceci est un exemple de contenu pour l'indexation Elasticsearch avec recherche full-text."
            
            success = await self.index_resource(resource, sample_content)
            if success:
                total_indexed += 1
            else:
                total_errors += 1
        
        # Forcer le refresh de l'index
        await self.client.indices.refresh(index=self.index_name)
        
        # Récupérer les statistiques
        stats = await self.get_stats()
        
        logger.info(f"✅ Indexation Elasticsearch terminée: {total_indexed} documents, {total_errors} erreurs")
        return stats
    
    async def reset_index(self):
        """Recrée l'index Elasticsearch"""
        logger.info("🗑️ Recréation de l'index Elasticsearch...")
        
        try:
            # Supprimer l'index existant
            exists = await self.client.indices.exists(index=self.index_name)
            if exists:
                await self.client.indices.delete(index=self.index_name)
            
            # Recréer l'index
            await self.client.indices.create(
                index=self.index_name,
                body=self.mapping
            )
            
            logger.info("✅ Index Elasticsearch recréé")
            
        except Exception as e:
            logger.error(f"Erreur recréation index: {e}")
            raise
    
    async def get_stats(self) -> ElasticsearchStats:
        """Récupère les statistiques Elasticsearch"""
        try:
            # Statistiques de l'index
            stats_response = await self.client.indices.stats(index=self.index_name)
            index_stats = stats_response["indices"][self.index_name]
            
            # Santé du cluster
            health_response = await self.client.cluster.health()
            
            # Informations du cluster
            nodes_response = await self.client.cat.nodes(format="json")
            
            return ElasticsearchStats(
                total_documents=index_stats["total"]["docs"]["count"],
                index_size_mb=index_stats["total"]["store"]["size_in_bytes"] / (1024 * 1024),
                last_updated=datetime.now(),
                cluster_health=health_response["status"],
                node_count=len(nodes_response)
            )
            
        except Exception as e:
            logger.error(f"Erreur récupération stats Elasticsearch: {e}")
            return ElasticsearchStats(
                total_documents=0,
                index_size_mb=0.0,
                last_updated=datetime.now(),
                cluster_health="unknown",
                node_count=0
            )
    
    async def close(self):
        """Ferme la connexion Elasticsearch"""
        if self.client:
            await self.client.close()
        logger.info("🔒 Connexion Elasticsearch fermée")