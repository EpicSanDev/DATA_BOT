"""
Gestionnaire OpenSearch pour DATA_BOT v4
Alternative open-source à Elasticsearch avec API compatible
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
    from opensearchpy import AsyncOpenSearch
    from opensearchpy.helpers import async_bulk
    OPENSEARCH_AVAILABLE = True
except ImportError:
    OPENSEARCH_AVAILABLE = False

from src.core.models import WebResource, ContentType
from src.database.database import DatabaseManager

logger = logging.getLogger(__name__)

@dataclass
class OpenSearchHit:
    """Résultat de recherche OpenSearch"""
    url: str
    title: str
    content: str
    score: float
    categories: List[str]
    content_type: str
    created_at: datetime
    highlights: Dict[str, List[str]] = None

class OpenSearchManager:
    """Gestionnaire OpenSearch pour recherche et analytics avancées"""
    
    def __init__(self, host: str = "localhost", port: int = 9201, 
                 index_name: str = "databot_v4", **kwargs):
        """
        Initialise le gestionnaire OpenSearch
        
        Args:
            host: Adresse du serveur OpenSearch
            port: Port du serveur OpenSearch
            index_name: Nom de l'index principal
            **kwargs: Arguments supplémentaires pour AsyncOpenSearch
        """
        if not OPENSEARCH_AVAILABLE:
            raise ImportError("opensearch-py n'est pas installé")
        
        self.host = host
        self.port = port
        self.index_name = index_name
        
        # Configuration par défaut
        self.config = {
            'hosts': [{'host': host, 'port': port}],
            'use_ssl': kwargs.get('use_ssl', False),
            'verify_certs': kwargs.get('verify_certs', False),
            'timeout': kwargs.get('timeout', 30),
            **kwargs
        }
        
        self.client = None
        self.initialized = False
        
    async def initialize(self):
        """Initialise la connexion OpenSearch"""
        try:
            self.client = AsyncOpenSearch(**self.config)
            
            # Tester la connexion
            info = await self.client.info()
            logger.info(f"Connexion OpenSearch établie: {info['version']['number']}")
            
            # Créer l'index s'il n'existe pas
            await self._create_index_if_not_exists()
            
            self.initialized = True
            logger.info("OpenSearch Manager initialisé avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation d'OpenSearch: {e}")
            raise
    
    async def _create_index_if_not_exists(self):
        """Crée l'index principal s'il n'existe pas"""
        try:
            if not await self.client.indices.exists(index=self.index_name):
                mapping = await self._get_index_mapping()
                settings = await self._get_index_settings()
                
                await self.client.indices.create(
                    index=self.index_name,
                    body={
                        'settings': settings,
                        'mappings': mapping
                    }
                )
                logger.info(f"Index '{self.index_name}' créé")
            else:
                logger.info(f"Index '{self.index_name}' existe déjà")
                
        except Exception as e:
            logger.error(f"Erreur lors de la création de l'index: {e}")
            raise
    
    async def _get_index_mapping(self) -> Dict[str, Any]:
        """Retourne le mapping pour l'index principal"""
        return {
            'properties': {
                'url': {
                    'type': 'keyword',
                    'index': True
                },
                'title': {
                    'type': 'text',
                    'analyzer': 'standard',
                    'fields': {
                        'keyword': {
                            'type': 'keyword'
                        }
                    }
                },
                'content': {
                    'type': 'text',
                    'analyzer': 'standard'
                },
                'content_type': {
                    'type': 'keyword'
                },
                'categories': {
                    'type': 'keyword'
                },
                'tags': {
                    'type': 'keyword'
                },
                'domain': {
                    'type': 'keyword'
                },
                'language': {
                    'type': 'keyword'
                },
                'created_at': {
                    'type': 'date'
                },
                'updated_at': {
                    'type': 'date'
                },
                'file_size': {
                    'type': 'long'
                },
                'word_count': {
                    'type': 'integer'
                },
                'priority': {
                    'type': 'integer'
                },
                'status': {
                    'type': 'keyword'
                },
                'content_hash': {
                    'type': 'keyword'
                },
                'embedding': {
                    'type': 'dense_vector',
                    'dims': 384
                }
            }
        }
    
    async def _get_index_settings(self) -> Dict[str, Any]:
        """Retourne les paramètres pour l'index principal"""
        return {
            'number_of_shards': 1,
            'number_of_replicas': 0,
            'refresh_interval': '1s',
            'analysis': {
                'analyzer': {
                    'custom_analyzer': {
                        'type': 'custom',
                        'tokenizer': 'standard',
                        'filter': ['lowercase', 'stop', 'stemmer']
                    }
                },
                'filter': {
                    'stemmer': {
                        'type': 'stemmer',
                        'language': 'french'
                    }
                }
            }
        }
    
    async def index_resource(self, resource: WebResource) -> bool:
        """
        Indexe une ressource dans OpenSearch
        
        Args:
            resource: Ressource à indexer
            
        Returns:
            bool: True si l'indexation a réussi
        """
        if not self.initialized:
            await self.initialize()
        
        try:
            # Préparer le document
            doc = await self._prepare_document(resource)
            
            # Indexer le document
            result = await self.client.index(
                index=self.index_name,
                id=str(resource.id),
                body=doc
            )
            
            logger.debug(f"Ressource indexée: {resource.url} -> {result['result']}")
            return result['result'] in ['created', 'updated']
            
        except Exception as e:
            logger.error(f"Erreur lors de l'indexation de {resource.url}: {e}")
            return False
    
    async def bulk_index_resources(self, resources: List[WebResource]) -> Dict[str, int]:
        """
        Indexe plusieurs ressources en lot
        
        Args:
            resources: Liste des ressources à indexer
            
        Returns:
            Dict avec statistiques d'indexation
        """
        if not self.initialized:
            await self.initialize()
        
        if not resources:
            return {'indexed': 0, 'errors': 0}
        
        try:
            # Préparer les documents
            actions = []
            for resource in resources:
                doc = await self._prepare_document(resource)
                actions.append({
                    '_index': self.index_name,
                    '_id': str(resource.id),
                    '_source': doc
                })
            
            # Indexation en lot
            success, failed = await async_bulk(
                self.client,
                actions,
                chunk_size=100,
                request_timeout=60
            )
            
            logger.info(f"Indexation en lot: {success} succès, {len(failed)} échecs")
            return {'indexed': success, 'errors': len(failed)}
            
        except Exception as e:
            logger.error(f"Erreur lors de l'indexation en lot: {e}")
            return {'indexed': 0, 'errors': len(resources)}
    
    async def search(self, query: str, 
                    filters: Optional[Dict[str, Any]] = None,
                    size: int = 20,
                    from_: int = 0,
                    sort: Optional[List[Dict[str, Any]]] = None,
                    highlight: bool = True) -> Dict[str, Any]:
        """
        Effectue une recherche dans OpenSearch
        
        Args:
            query: Requête de recherche
            filters: Filtres à appliquer
            size: Nombre de résultats
            from_: Offset pour la pagination
            sort: Critères de tri
            highlight: Activer le highlighting
            
        Returns:
            Dict avec résultats de recherche
        """
        if not self.initialized:
            await self.initialize()
        
        try:
            # Construire la requête
            search_body = await self._build_search_query(
                query, filters, sort, highlight
            )
            
            # Exécuter la recherche
            result = await self.client.search(
                index=self.index_name,
                body=search_body,
                size=size,
                from_=from_
            )
            
            # Traiter les résultats
            processed_results = await self._process_search_results(result)
            
            return processed_results
            
        except Exception as e:
            logger.error(f"Erreur lors de la recherche '{query}': {e}")
            return {'hits': [], 'total': 0, 'error': str(e)}
    
    async def suggest(self, text: str, field: str = 'title', size: int = 5) -> List[str]:
        """
        Suggestions de recherche
        
        Args:
            text: Texte pour suggestion
            field: Champ pour suggestion
            size: Nombre de suggestions
            
        Returns:
            Liste des suggestions
        """
        if not self.initialized:
            await self.initialize()
        
        try:
            suggestion_body = {
                'suggest': {
                    'suggestion': {
                        'text': text,
                        'term': {
                            'field': field,
                            'size': size
                        }
                    }
                }
            }
            
            result = await self.client.search(
                index=self.index_name,
                body=suggestion_body
            )
            
            suggestions = []
            for suggest in result.get('suggest', {}).get('suggestion', []):
                for option in suggest.get('options', []):
                    suggestions.append(option['text'])
            
            return suggestions[:size]
            
        except Exception as e:
            logger.error(f"Erreur lors de la suggestion pour '{text}': {e}")
            return []
    
    async def get_aggregations(self, agg_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Exécute des agrégations OpenSearch
        
        Args:
            agg_config: Configuration des agrégations
            
        Returns:
            Résultats des agrégations
        """
        if not self.initialized:
            await self.initialize()
        
        try:
            search_body = {
                'size': 0,
                'aggs': agg_config
            }
            
            result = await self.client.search(
                index=self.index_name,
                body=search_body
            )
            
            return result.get('aggregations', {})
            
        except Exception as e:
            logger.error(f"Erreur lors des agrégations: {e}")
            return {}
    
    async def _prepare_document(self, resource: WebResource) -> Dict[str, Any]:
        """Prépare un document pour l'indexation"""
        from urllib.parse import urlparse
        
        # Extraire le domaine
        domain = urlparse(resource.url).netloc
        
        # Calculer le hash du contenu
        content_hash = hashlib.md5(
            (resource.content or '').encode('utf-8')
        ).hexdigest()
        
        doc = {
            'url': resource.url,
            'title': resource.title or '',
            'content': resource.content or '',
            'content_type': resource.content_type.value if resource.content_type else 'unknown',
            'categories': resource.categories or [],
            'tags': resource.tags or [],
            'domain': domain,
            'language': resource.language or 'unknown',
            'created_at': resource.created_at.isoformat() if resource.created_at else None,
            'updated_at': resource.updated_at.isoformat() if resource.updated_at else None,
            'file_size': resource.file_size or 0,
            'word_count': len((resource.content or '').split()),
            'priority': resource.priority or 0,
            'status': resource.status.value if resource.status else 'unknown',
            'content_hash': content_hash
        }
        
        return doc
    
    async def _build_search_query(self, query: str, 
                                 filters: Optional[Dict[str, Any]] = None,
                                 sort: Optional[List[Dict[str, Any]]] = None,
                                 highlight: bool = True) -> Dict[str, Any]:
        """Construit une requête de recherche OpenSearch"""
        search_body = {}
        
        # Requête principale
        if query:
            search_body['query'] = {
                'multi_match': {
                    'query': query,
                    'fields': ['title^2', 'content', 'categories', 'tags'],
                    'fuzziness': 'AUTO'
                }
            }
        else:
            search_body['query'] = {'match_all': {}}
        
        # Filtres
        if filters:
            filter_clauses = []
            
            for field, value in filters.items():
                if isinstance(value, list):
                    filter_clauses.append({
                        'terms': {field: value}
                    })
                elif isinstance(value, dict) and 'range' in value:
                    filter_clauses.append({
                        'range': {field: value['range']}
                    })
                else:
                    filter_clauses.append({
                        'term': {field: value}
                    })
            
            if filter_clauses:
                search_body['query'] = {
                    'bool': {
                        'must': search_body['query'],
                        'filter': filter_clauses
                    }
                }
        
        # Tri
        if sort:
            search_body['sort'] = sort
        else:
            search_body['sort'] = [{'_score': {'order': 'desc'}}]
        
        # Highlighting
        if highlight:
            search_body['highlight'] = {
                'fields': {
                    'title': {},
                    'content': {
                        'fragment_size': 150,
                        'number_of_fragments': 3
                    }
                }
            }
        
        return search_body
    
    async def _process_search_results(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Traite les résultats de recherche OpenSearch"""
        hits = []
        
        for hit in result['hits']['hits']:
            source = hit['_source']
            highlights = hit.get('highlight', {})
            
            processed_hit = OpenSearchHit(
                url=source['url'],
                title=source['title'],
                content=source['content'],
                score=hit['_score'],
                categories=source.get('categories', []),
                content_type=source.get('content_type', 'unknown'),
                created_at=datetime.fromisoformat(source['created_at']) if source.get('created_at') else None,
                highlights=highlights
            )
            
            hits.append(processed_hit)
        
        return {
            'hits': hits,
            'total': result['hits']['total']['value'],
            'max_score': result['hits']['max_score'],
            'took': result['took']
        }
    
    async def delete_resource(self, resource_id: int) -> bool:
        """Supprime une ressource de l'index"""
        if not self.initialized:
            await self.initialize()
        
        try:
            result = await self.client.delete(
                index=self.index_name,
                id=str(resource_id)
            )
            return result['result'] == 'deleted'
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression de la ressource {resource_id}: {e}")
            return False
    
    async def get_index_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de l'index"""
        if not self.initialized:
            await self.initialize()
        
        try:
            stats = await self.client.indices.stats(index=self.index_name)
            return stats['indices'][self.index_name]
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des statistiques: {e}")
            return {}
    
    async def close(self):
        """Ferme la connexion OpenSearch"""
        if self.client:
            await self.client.close()
            logger.info("Connexion OpenSearch fermée")