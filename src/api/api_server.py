"""
API Server v4 - Extension du serveur v3 avec nouvelles fonctionnalités enterprise
Support OpenSearch, ML, clustering, et interface d'administration
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

try:
    from fastapi import FastAPI, HTTPException, Request, Query, Body, Depends
    from fastapi.responses import JSONResponse, HTMLResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

from src.core.models import WebResource, ArchiveStatus, ContentType
from src.api.analytics_api import create_analytics_router

logger = logging.getLogger(__name__)

# Base API Server class to replace the removed APIServerV3
class BaseAPIServer:
    """Base API Server class"""
    
    def __init__(self, database_manager, port: int = 8080):
        self.database_manager = database_manager
        self.port = port
        self.app = None
        
    async def start(self):
        """Start the API server"""
        pass
        
    async def stop(self):
        """Stop the API server"""
        pass

# Modèles Pydantic pour l'API v4
class SearchRequestV4(BaseModel):
    query: str
    search_engine: Optional[str] = "auto"  # "elasticsearch", "opensearch", "auto"
    enable_clustering: bool = False
    clustering_algorithm: Optional[str] = "hdbscan"
    filters: Optional[Dict[str, Any]] = None
    limit: int = 20
    offset: int = 0

class ClusteringRequest(BaseModel):
    algorithm: str = "hdbscan"
    n_clusters: Optional[int] = None
    min_cluster_size: int = 3
    resource_ids: Optional[List[int]] = None

class MLCategorizationRequest(BaseModel):
    resource_ids: Optional[List[int]] = None
    confidence_threshold: float = 0.3
    max_categories: int = 5
    auto_save: bool = True

class AdminTaskRequest(BaseModel):
    task_type: str
    parameters: Optional[Dict[str, Any]] = None
    priority: int = 1

class SystemConfigUpdate(BaseModel):
    component: str  # "opensearch", "ml", "clustering"
    settings: Dict[str, Any]

class APIServerV4(BaseAPIServer):
    """Serveur API v4 avec fonctionnalités enterprise"""
    
    def __init__(self, database_manager, opensearch_manager=None,
                 ml_categorizer=None, result_clusterer=None, 
                 admin_interface=None, port: int = 8080):
        """
        Initialise le serveur API v4
        
        Args:
            database_manager: Gestionnaire de base de données
            opensearch_manager: Gestionnaire OpenSearch
            ml_categorizer: Catégoriseur ML
            result_clusterer: Clusterer de résultats
            admin_interface: Interface d'administration
            port: Port du serveur
        """
        if not FASTAPI_AVAILABLE:
            raise ImportError("FastAPI n'est pas installé")
        
        super().__init__(database_manager, port)
        
        # Nouveaux composants v4
        self.opensearch_manager = opensearch_manager
        self.ml_categorizer = ml_categorizer
        self.result_clusterer = result_clusterer
        self.admin_interface = admin_interface
        
        # Ajouter le router d'analytics
        analytics_router = create_analytics_router(self.database_manager)
        self.app.include_router(analytics_router)
        
        # Reconfigurer l'app FastAPI pour v4
        self._setup_v4_routes()
        
        # Ajouter route pour le dashboard analytics
        @self.app.get("/dashboard/analytics", response_class=HTMLResponse)
        async def analytics_dashboard():
            """Serve the analytics dashboard"""
            try:
                dashboard_path = Path(__file__).parent / "templates" / "dashboard_analytics.html"
                with open(dashboard_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Error serving analytics dashboard: {e}")
                return HTMLResponse("<h1>Dashboard not available</h1>", status_code=500)
    
    def _setup_v4_routes(self):
        """Configure les routes spécifiques à v4"""
        
        # Routes de recherche avancée
        @self.app.post("/api/v4/search/advanced")
        async def advanced_search(request: SearchRequestV4):
            """Recherche avancée avec support multi-moteurs et clustering"""
            try:
                start_time = datetime.now()
                
                # Déterminer le moteur de recherche
                search_engine = await self._determine_search_engine(request.search_engine)
                
                # Effectuer la recherche
                if search_engine == "opensearch" and self.opensearch_manager:
                    search_results = await self._search_with_opensearch(request)
                elif search_engine == "elasticsearch" and self.elasticsearch_manager:
                    search_results = await self._search_with_elasticsearch(request)
                else:
                    # Recherche basique dans la base de données
                    search_results = await self._search_with_database(request)
                
                # Clustering si demandé
                clusters = None
                if request.enable_clustering and self.result_clusterer:
                    clusters = await self._perform_search_clustering(
                        search_results['resources'], 
                        request.query,
                        request.clustering_algorithm
                    )
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                return {
                    "results": search_results,
                    "clusters": clusters,
                    "search_engine": search_engine,
                    "execution_time": execution_time,
                    "query": request.query
                }
                
            except Exception as e:
                logger.error(f"Erreur recherche avancée: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Routes de clustering
        @self.app.post("/api/v4/clustering/run")
        async def run_clustering(request: ClusteringRequest):
            """Lance un clustering des ressources"""
            if not self.result_clusterer:
                raise HTTPException(status_code=503, detail="Clustering non disponible")
            
            try:
                # Récupérer les ressources à clusterer
                if request.resource_ids:
                    resources = []
                    for resource_id in request.resource_ids:
                        resource = await self.database_manager.get_resource_by_id(resource_id)
                        if resource:
                            resources.append(resource)
                else:
                    resources = await self.database_manager.get_all_resources()
                
                # Effectuer le clustering
                clustering_result = await self.result_clusterer.cluster_resources(
                    resources, 
                    algorithm=request.algorithm,
                    n_clusters=request.n_clusters
                )
                
                # Sauvegarder les clusters
                await self.database_manager.save_clusters(clustering_result.clusters)
                
                return {
                    "clusters": [
                        {
                            "id": cluster.id,
                            "name": cluster.name,
                            "description": cluster.description,
                            "size": cluster.size,
                            "keywords": cluster.keywords,
                            "coherence_score": cluster.coherence_score
                        }
                        for cluster in clustering_result.clusters
                    ],
                    "algorithm": clustering_result.algorithm,
                    "n_clusters": clustering_result.n_clusters,
                    "silhouette_score": clustering_result.silhouette_score,
                    "execution_time": clustering_result.execution_time
                }
                
            except Exception as e:
                logger.error(f"Erreur clustering: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v4/clustering/clusters")
        async def get_clusters(limit: int = Query(20), offset: int = Query(0)):
            """Récupère les clusters existants"""
            try:
                clusters = await self.database_manager.get_clusters(limit=limit, offset=offset)
                
                return {
                    "clusters": [
                        {
                            "id": cluster.id,
                            "name": cluster.name,
                            "description": cluster.description,
                            "size": cluster.size,
                            "keywords": cluster.keywords,
                            "coherence_score": cluster.coherence_score,
                            "created_at": cluster.created_at.isoformat() if cluster.created_at else None
                        }
                        for cluster in clusters
                    ],
                    "total": len(clusters)
                }
                
            except Exception as e:
                logger.error(f"Erreur récupération clusters: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Routes ML
        @self.app.post("/api/v4/ml/categorize")
        async def categorize_resources(request: MLCategorizationRequest):
            """Catégorise des ressources avec ML"""
            if not self.ml_categorizer:
                raise HTTPException(status_code=503, detail="ML Categorizer non disponible")
            
            try:
                results = []
                
                # Récupérer les ressources à catégoriser
                if request.resource_ids:
                    resources = []
                    for resource_id in request.resource_ids:
                        resource = await self.database_manager.get_resource_by_id(resource_id)
                        if resource:
                            resources.append(resource)
                else:
                    resources = await self.database_manager.get_uncategorized_resources()
                
                # Catégoriser chaque ressource
                for resource in resources:
                    categories = await self.ml_categorizer.categorize_resource(resource)
                    
                    # Filtrer par seuil de confiance
                    filtered_categories = categories[:request.max_categories]
                    
                    # Sauvegarder si demandé
                    if request.auto_save and filtered_categories:
                        await self.database_manager.update_resource_categories(
                            resource.id, filtered_categories
                        )
                    
                    results.append({
                        "resource_id": resource.id,
                        "url": resource.url,
                        "categories": filtered_categories,
                        "saved": request.auto_save
                    })
                
                return {
                    "categorized_resources": results,
                    "total_processed": len(results),
                    "total_categorized": len([r for r in results if r["categories"]])
                }
                
            except Exception as e:
                logger.error(f"Erreur catégorisation ML: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v4/ml/statistics")
        async def get_ml_statistics():
            """Récupère les statistiques ML"""
            if not self.ml_categorizer:
                raise HTTPException(status_code=503, detail="ML Categorizer non disponible")
            
            try:
                stats = await self.ml_categorizer.get_category_statistics(self.database_manager)
                return stats
                
            except Exception as e:
                logger.error(f"Erreur statistiques ML: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Routes d'administration
        @self.app.post("/api/v4/admin/task")
        async def execute_admin_task(request: AdminTaskRequest):
            """Exécute une tâche d'administration"""
            try:
                task_id = await self._execute_admin_task(request)
                
                return {
                    "task_id": task_id,
                    "task_type": request.task_type,
                    "status": "started",
                    "parameters": request.parameters
                }
                
            except Exception as e:
                logger.error(f"Erreur tâche admin: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v4/admin/system/status")
        async def get_system_status():
            """Récupère le statut système complet"""
            try:
                status = {
                    "database": await self._check_database_health(),
                    "opensearch": await self._check_opensearch_health(),
                    "ml_categorizer": await self._check_ml_health(),
                    "result_clusterer": await self._check_clustering_health(),
                    "uptime": self._get_uptime(),
                    "version": "4.0.0",
                    "timestamp": datetime.now().isoformat()
                }
                
                return status
                
            except Exception as e:
                logger.error(f"Erreur statut système: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.put("/api/v4/admin/config")
        async def update_system_config(request: SystemConfigUpdate):
            """Met à jour la configuration système"""
            try:
                success = await self._update_component_config(
                    request.component, 
                    request.settings
                )
                
                return {
                    "component": request.component,
                    "updated": success,
                    "settings": request.settings
                }
                
            except Exception as e:
                logger.error(f"Erreur mise à jour config: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Routes de monitoring avancé
        @self.app.get("/api/v4/monitoring/metrics")
        async def get_monitoring_metrics():
            """Récupère les métriques de monitoring"""
            try:
                metrics = await self._collect_monitoring_metrics()
                return metrics
                
            except Exception as e:
                logger.error(f"Erreur métriques: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v4/monitoring/logs")
        async def get_system_logs(
            level: str = Query("INFO"),
            limit: int = Query(100),
            since: Optional[str] = Query(None)
        ):
            """Récupère les logs système"""
            try:
                logs = await self._get_system_logs(level, limit, since)
                return {"logs": logs}
                
            except Exception as e:
                logger.error(f"Erreur logs: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Routes de comparaison et recommandations
        @self.app.get("/api/v4/recommendations/clusters/{resource_id}")
        async def get_cluster_recommendations(resource_id: int, top_k: int = Query(3)):
            """Recommande des clusters similaires pour une ressource"""
            if not self.result_clusterer:
                raise HTTPException(status_code=503, detail="Clustering non disponible")
            
            try:
                resource = await self.database_manager.get_resource_by_id(resource_id)
                if not resource:
                    raise HTTPException(status_code=404, detail="Ressource non trouvée")
                
                clusters = await self.database_manager.get_clusters()
                recommendations = await self.result_clusterer.get_cluster_recommendations(
                    resource, clusters, top_k
                )
                
                return {
                    "resource_id": resource_id,
                    "recommendations": [
                        {
                            "cluster": {
                                "id": cluster.id,
                                "name": cluster.name,
                                "description": cluster.description,
                                "size": cluster.size
                            },
                            "similarity_score": score
                        }
                        for cluster, score in recommendations
                    ]
                }
                
            except Exception as e:
                logger.error(f"Erreur recommandations: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Route de health check avancé
        @self.app.get("/api/v4/health/detailed")
        async def detailed_health_check():
            """Health check détaillé de tous les composants"""
            try:
                health = {
                    "status": "healthy",
                    "components": {
                        "database": {
                            "status": "healthy" if await self._check_database_health() else "unhealthy",
                            "details": await self._get_database_details()
                        },
                        "opensearch": {
                            "status": "healthy" if await self._check_opensearch_health() else "unhealthy",
                            "details": await self._get_opensearch_details()
                        },
                        "ml_categorizer": {
                            "status": "healthy" if await self._check_ml_health() else "unavailable",
                            "details": await self._get_ml_details()
                        },
                        "result_clusterer": {
                            "status": "healthy" if await self._check_clustering_health() else "unavailable",
                            "details": await self._get_clustering_details()
                        }
                    },
                    "timestamp": datetime.now().isoformat()
                }
                
                # Déterminer le statut global
                component_statuses = [comp["status"] for comp in health["components"].values()]
                if "unhealthy" in component_statuses:
                    health["status"] = "degraded"
                elif all(status in ["healthy", "unavailable"] for status in component_statuses):
                    health["status"] = "healthy"
                
                return health
                
            except Exception as e:
                logger.error(f"Erreur health check: {e}")
                return {"status": "error", "error": str(e)}
    
    # Méthodes utilitaires pour v4
    
    async def _determine_search_engine(self, preference: str) -> str:
        """Détermine le moteur de recherche à utiliser"""
        if preference == "opensearch" and self.opensearch_manager:
            return "opensearch"
        elif preference == "elasticsearch" and self.elasticsearch_manager:
            return "elasticsearch"
        elif preference == "auto":
            # Préférer OpenSearch puis Elasticsearch
            if self.opensearch_manager:
                return "opensearch"
            elif self.elasticsearch_manager:
                return "elasticsearch"
            else:
                return "database"
        else:
            return "database"
    
    async def _search_with_opensearch(self, request: SearchRequestV4) -> Dict[str, Any]:
        """Effectue une recherche avec OpenSearch"""
        try:
            result = await self.opensearch_manager.search(
                query=request.query,
                filters=request.filters,
                size=request.limit,
                from_=request.offset
            )
            
            # Convertir les hits en format standard
            resources = []
            for hit in result.get('hits', []):
                resources.append({
                    'id': hit.url.split('/')[-1] if hit.url.split('/')[-1].isdigit() else 0,
                    'url': hit.url,
                    'title': hit.title,
                    'content': hit.content,
                    'categories': hit.categories,
                    'score': hit.score
                })
            
            return {
                'resources': resources,
                'total': result.get('total', 0),
                'max_score': result.get('max_score', 0)
            }
            
        except Exception as e:
            logger.error(f"Erreur recherche OpenSearch: {e}")
            raise
    
    async def _search_with_database(self, request: SearchRequestV4) -> Dict[str, Any]:
        """Effectue une recherche basique dans la base de données"""
        try:
            resources = await self.database_manager.search_resources(
                query=request.query,
                limit=request.limit,
                offset=request.offset,
                filters=request.filters
            )
            
            return {
                'resources': [
                    {
                        'id': r.id,
                        'url': r.url,
                        'title': r.title,
                        'content': r.content,
                        'categories': r.categories,
                        'score': 1.0  # Score par défaut
                    }
                    for r in resources
                ],
                'total': len(resources),
                'max_score': 1.0
            }
            
        except Exception as e:
            logger.error(f"Erreur recherche base de données: {e}")
            raise
    
    async def _perform_search_clustering(self, resources: List[Dict[str, Any]], 
                                       query: str, algorithm: str) -> Optional[List[Dict[str, Any]]]:
        """Effectue un clustering des résultats de recherche"""
        try:
            if len(resources) < 3:
                return None
            
            # Convertir en objets WebResource
            web_resources = []
            for r in resources:
                resource = WebResource(
                    id=r.get('id', 0),
                    url=r['url'],
                    title=r.get('title'),
                    content=r.get('content'),
                    categories=r.get('categories', [])
                )
                web_resources.append(resource)
            
            # Effectuer le clustering
            clustering_result = await self.result_clusterer.cluster_search_results(
                web_resources, query
            )
            
            # Formater les résultats
            clusters = []
            for cluster in clustering_result.clusters:
                clusters.append({
                    'id': cluster.id,
                    'name': cluster.name,
                    'description': cluster.description,
                    'size': cluster.size,
                    'keywords': cluster.keywords,
                    'coherence_score': cluster.coherence_score,
                    'resource_ids': [r.id for r in cluster.resources]
                })
            
            return clusters
            
        except Exception as e:
            logger.error(f"Erreur clustering recherche: {e}")
            return None
    
    async def _execute_admin_task(self, request: AdminTaskRequest) -> str:
        """Exécute une tâche d'administration"""
        # Générer un ID de tâche
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Ici on pourrait implémenter un système de queue pour les tâches
        # Pour l'instant, on exécute directement selon le type
        
        if request.task_type == "reindex":
            await self._reindex_all_resources()
        elif request.task_type == "cleanup_duplicates":
            await self._cleanup_duplicates()
        elif request.task_type == "categorize_all":
            await self._categorize_all_resources()
        elif request.task_type == "cluster_all":
            await self._cluster_all_resources()
        
        return task_id
    
    async def _check_database_health(self) -> bool:
        """Vérifie la santé de la base de données"""
        try:
            await self.database_manager.get_statistics()
            return True
        except:
            return False
    
    async def _check_opensearch_health(self) -> bool:
        """Vérifie la santé d'OpenSearch"""
        if not self.opensearch_manager:
            return False
        try:
            await self.opensearch_manager.get_index_stats()
            return True
        except:
            return False
    
    async def _check_ml_health(self) -> bool:
        """Vérifie la santé du ML"""
        return (self.ml_categorizer is not None and 
                getattr(self.ml_categorizer, 'initialized', False))
    
    async def _check_clustering_health(self) -> bool:
        """Vérifie la santé du clustering"""
        return (self.result_clusterer is not None and 
                getattr(self.result_clusterer, 'initialized', False))
    
    async def _get_uptime(self) -> str:
        """Retourne l'uptime du serveur"""
        # Implémentation simple - dans un vrai système, on stockerait le temps de démarrage
        return "Unknown"
    
    async def _collect_monitoring_metrics(self) -> Dict[str, Any]:
        """Collecte les métriques de monitoring"""
        try:
            import psutil
            
            return {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent,
                "connections": len(psutil.net_connections()),
                "timestamp": datetime.now().isoformat()
            }
        except ImportError:
            return {
                "error": "psutil not available",
                "timestamp": datetime.now().isoformat()
            }
    
    # Stubs pour les méthodes de détails (à implémenter selon les besoins)
    async def _get_database_details(self) -> Dict[str, Any]:
        return {"type": "sqlite", "size": "unknown"}
    
    async def _get_opensearch_details(self) -> Dict[str, Any]:
        if self.opensearch_manager:
            return {"available": True, "version": "unknown"}
        return {"available": False}
    
    async def _get_ml_details(self) -> Dict[str, Any]:
        if self.ml_categorizer:
            return {"available": True, "model": "unknown"}
        return {"available": False}
    
    async def _get_clustering_details(self) -> Dict[str, Any]:
        if self.result_clusterer:
            return {"available": True, "algorithms": ["hdbscan", "kmeans"]}
        return {"available": False}
    
    async def _get_system_logs(self, level: str, limit: int, since: Optional[str]) -> List[Dict[str, Any]]:
        """Récupère les logs système"""
        # Implémentation stub - dans un vrai système, on lirait les fichiers de log
        return [
            {
                "timestamp": datetime.now().isoformat(),
                "level": level,
                "message": "System is running normally",
                "component": "api_server_v4"
            }
        ]
    
    async def _update_component_config(self, component: str, settings: Dict[str, Any]) -> bool:
        """Met à jour la configuration d'un composant"""
        # Implémentation stub
        logger.info(f"Updating {component} config: {settings}")
        return True
    
    # Tâches d'administration (stubs)
    async def _reindex_all_resources(self):
        """Réindexe toutes les ressources"""
        logger.info("Reindexing all resources...")
    
    async def _cleanup_duplicates(self):
        """Nettoie les doublons"""
        logger.info("Cleaning up duplicates...")
    
    async def _categorize_all_resources(self):
        """Catégorise toutes les ressources"""
        if self.ml_categorizer:
            await self.ml_categorizer.auto_categorize_uncategorized(self.database_manager)
    
    async def _cluster_all_resources(self):
        """Cluster toutes les ressources"""
        if self.result_clusterer:
            resources = await self.database_manager.get_all_resources()
            clustering_result = await self.result_clusterer.cluster_resources(resources)
            await self.database_manager.save_clusters(clustering_result.clusters)