"""
GraphQL Server pour DATA_BOT v4
API GraphQL complète pour l'accès aux données et fonctionnalités
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
import os

try:
    import strawberry
    from strawberry.fastapi import GraphQLRouter
    from strawberry.types import Info
    from fastapi import FastAPI
    import uvicorn
    GRAPHQL_AVAILABLE = True
except ImportError:
    GRAPHQL_AVAILABLE = False

from src.core.models import WebResource, ArchiveStatus, ContentType
from src.database.database import DatabaseManager

logger = logging.getLogger(__name__)

# Types GraphQL
@strawberry.type
class WebResourceType:
    id: int
    url: str
    title: Optional[str] = None
    content: Optional[str] = None
    content_type: Optional[str] = None
    categories: List[str] = strawberry.field(default_factory=list)
    tags: List[str] = strawberry.field(default_factory=list)
    language: Optional[str] = None
    file_size: Optional[int] = None
    status: Optional[str] = None
    priority: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@strawberry.type
class ClusterType:
    id: int
    name: str
    description: str
    size: int
    keywords: List[str] = strawberry.field(default_factory=list)
    coherence_score: float = 0.0
    created_at: Optional[datetime] = None

@strawberry.type
class SearchResultType:
    resources: List[WebResourceType]
    total: int
    clusters: Optional[List[ClusterType]] = None
    query: str
    execution_time: float

@strawberry.type
class StatisticsType:
    total_resources: int
    total_categories: int
    total_clusters: int
    storage_size: int
    last_update: Optional[datetime] = None

@strawberry.input
class ResourceFilterInput:
    categories: Optional[List[str]] = None
    content_type: Optional[str] = None
    status: Optional[str] = None
    language: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None

@strawberry.input
class CreateResourceInput:
    url: str
    title: Optional[str] = None
    content: Optional[str] = None
    categories: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    priority: Optional[int] = None

@strawberry.input
class UpdateResourceInput:
    title: Optional[str] = None
    content: Optional[str] = None
    categories: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    priority: Optional[int] = None
    status: Optional[str] = None

class GraphQLContext:
    """Contexte GraphQL contenant les gestionnaires"""
    def __init__(self, database_manager: DatabaseManager,
                 opensearch_manager=None,
                 ml_categorizer=None,
                 result_clusterer=None):
        self.database_manager = database_manager
        self.opensearch_manager = opensearch_manager
        self.ml_categorizer = ml_categorizer
        self.result_clusterer = result_clusterer

# Queries
@strawberry.type
class Query:
    @strawberry.field
    async def resources(self, 
                       info: Info,
                       limit: int = 20,
                       offset: int = 0,
                       filters: Optional[ResourceFilterInput] = None) -> List[WebResourceType]:
        """Récupère les ressources avec filtres optionnels"""
        context: GraphQLContext = info.context
        
        try:
            # Convertir les filtres
            filter_dict = {}
            if filters:
                if filters.categories:
                    filter_dict['categories'] = filters.categories
                if filters.content_type:
                    filter_dict['content_type'] = filters.content_type
                if filters.status:
                    filter_dict['status'] = filters.status
                if filters.language:
                    filter_dict['language'] = filters.language
                if filters.date_from:
                    filter_dict['date_from'] = filters.date_from
                if filters.date_to:
                    filter_dict['date_to'] = filters.date_to
            
            resources = await context.database_manager.get_resources_with_filters(
                filters=filter_dict,
                limit=limit,
                offset=offset
            )
            
            return [_convert_resource_to_graphql(resource) for resource in resources]
            
        except Exception as e:
            logger.error(f"Erreur GraphQL resources: {e}")
            return []
    
    @strawberry.field
    async def resource(self, info: Info, id: int) -> Optional[WebResourceType]:
        """Récupère une ressource par ID"""
        context: GraphQLContext = info.context
        
        try:
            resource = await context.database_manager.get_resource_by_id(id)
            if resource:
                return _convert_resource_to_graphql(resource)
            return None
            
        except Exception as e:
            logger.error(f"Erreur GraphQL resource: {e}")
            return None
    
    @strawberry.field
    async def search(self, 
                    info: Info,
                    query: str,
                    limit: int = 20,
                    enable_clustering: bool = False) -> SearchResultType:
        """Recherche avec clustering optionnel"""
        context: GraphQLContext = info.context
        start_time = datetime.now()
        
        try:
            # Recherche dans OpenSearch si disponible
            if context.opensearch_manager:
                search_result = await context.opensearch_manager.search(
                    query, size=limit
                )
                resources = []
                for hit in search_result.get('hits', []):
                    # Convertir les hits OpenSearch en WebResource
                    resource = WebResource(
                        id=int(hit.url.split('/')[-1]) if hit.url.split('/')[-1].isdigit() else 0,
                        url=hit.url,
                        title=hit.title,
                        content=hit.content,
                        categories=hit.categories,
                        created_at=hit.created_at
                    )
                    resources.append(resource)
                total = search_result.get('total', 0)
            else:
                # Recherche basique dans la base de données
                resources = await context.database_manager.search_resources(query, limit)
                total = len(resources)
            
            # Clustering si demandé
            clusters = None
            if enable_clustering and context.result_clusterer and len(resources) >= 3:
                clustering_result = await context.result_clusterer.cluster_search_results(
                    resources, query
                )
                clusters = [_convert_cluster_to_graphql(cluster) 
                           for cluster in clustering_result.clusters]
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return SearchResultType(
                resources=[_convert_resource_to_graphql(r) for r in resources],
                total=total,
                clusters=clusters,
                query=query,
                execution_time=execution_time
            )
            
        except Exception as e:
            logger.error(f"Erreur GraphQL search: {e}")
            return SearchResultType(
                resources=[],
                total=0,
                query=query,
                execution_time=0
            )
    
    @strawberry.field
    async def categories(self, info: Info) -> List[str]:
        """Récupère toutes les catégories"""
        context: GraphQLContext = info.context
        
        try:
            categories = await context.database_manager.get_all_categories()
            return categories
            
        except Exception as e:
            logger.error(f"Erreur GraphQL categories: {e}")
            return []
    
    @strawberry.field
    async def clusters(self, info: Info, limit: int = 10) -> List[ClusterType]:
        """Récupère les clusters"""
        context: GraphQLContext = info.context
        
        try:
            clusters = await context.database_manager.get_clusters(limit=limit)
            return [_convert_cluster_to_graphql(cluster) for cluster in clusters]
            
        except Exception as e:
            logger.error(f"Erreur GraphQL clusters: {e}")
            return []
    
    @strawberry.field
    async def statistics(self, info: Info) -> StatisticsType:
        """Récupère les statistiques générales"""
        context: GraphQLContext = info.context
        
        try:
            stats = await context.database_manager.get_statistics()
            
            return StatisticsType(
                total_resources=stats.get('total_resources', 0),
                total_categories=stats.get('total_categories', 0),
                total_clusters=stats.get('total_clusters', 0),
                storage_size=stats.get('storage_size', 0),
                last_update=stats.get('last_update')
            )
            
        except Exception as e:
            logger.error(f"Erreur GraphQL statistics: {e}")
            return StatisticsType(
                total_resources=0,
                total_categories=0,
                total_clusters=0,
                storage_size=0
            )

# Mutations
@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_resource(self, 
                            info: Info,
                            input: CreateResourceInput) -> Optional[WebResourceType]:
        """Crée une nouvelle ressource"""
        context: GraphQLContext = info.context
        
        try:
            # Créer l'objet WebResource
            resource = WebResource(
                url=input.url,
                title=input.title,
                content=input.content,
                categories=input.categories or [],
                tags=input.tags or [],
                priority=input.priority or 0,
                status=ArchiveStatus.PENDING,
                created_at=datetime.now()
            )
            
            # Sauvegarder dans la base de données
            resource_id = await context.database_manager.save_resource(resource)
            resource.id = resource_id
            
            # Catégorisation automatique si ML disponible
            if context.ml_categorizer and not input.categories:
                categories = await context.ml_categorizer.categorize_resource(resource)
                if categories:
                    await context.database_manager.update_resource_categories(
                        resource_id, categories
                    )
                    resource.categories = categories
            
            return _convert_resource_to_graphql(resource)
            
        except Exception as e:
            logger.error(f"Erreur GraphQL create_resource: {e}")
            return None
    
    @strawberry.mutation
    async def update_resource(self, 
                            info: Info,
                            id: int,
                            input: UpdateResourceInput) -> Optional[WebResourceType]:
        """Met à jour une ressource"""
        context: GraphQLContext = info.context
        
        try:
            # Récupérer la ressource existante
            resource = await context.database_manager.get_resource_by_id(id)
            if not resource:
                return None
            
            # Mettre à jour les champs
            if input.title is not None:
                resource.title = input.title
            if input.content is not None:
                resource.content = input.content
            if input.categories is not None:
                resource.categories = input.categories
            if input.tags is not None:
                resource.tags = input.tags
            if input.priority is not None:
                resource.priority = input.priority
            if input.status is not None:
                resource.status = ArchiveStatus(input.status)
            
            resource.updated_at = datetime.now()
            
            # Sauvegarder
            await context.database_manager.update_resource(resource)
            
            return _convert_resource_to_graphql(resource)
            
        except Exception as e:
            logger.error(f"Erreur GraphQL update_resource: {e}")
            return None
    
    @strawberry.mutation
    async def delete_resource(self, info: Info, id: int) -> bool:
        """Supprime une ressource"""
        context: GraphQLContext = info.context
        
        try:
            success = await context.database_manager.delete_resource(id)
            
            # Supprimer de OpenSearch si disponible
            if success and context.opensearch_manager:
                await context.opensearch_manager.delete_resource(id)
            
            return success
            
        except Exception as e:
            logger.error(f"Erreur GraphQL delete_resource: {e}")
            return False
    
    @strawberry.mutation
    async def categorize_resource(self, info: Info, id: int) -> Optional[WebResourceType]:
        """Catégorise automatiquement une ressource"""
        context: GraphQLContext = info.context
        
        if not context.ml_categorizer:
            return None
        
        try:
            resource = await context.database_manager.get_resource_by_id(id)
            if not resource:
                return None
            
            categories = await context.ml_categorizer.categorize_resource(resource)
            
            if categories:
                await context.database_manager.update_resource_categories(id, categories)
                resource.categories = categories
            
            return _convert_resource_to_graphql(resource)
            
        except Exception as e:
            logger.error(f"Erreur GraphQL categorize_resource: {e}")
            return None
    
    @strawberry.mutation
    async def cluster_resources(self, 
                              info: Info,
                              algorithm: str = "hdbscan") -> List[ClusterType]:
        """Effectue un clustering des ressources"""
        context: GraphQLContext = info.context
        
        if not context.result_clusterer:
            return []
        
        try:
            # Récupérer toutes les ressources
            resources = await context.database_manager.get_all_resources()
            
            # Effectuer le clustering
            clustering_result = await context.result_clusterer.cluster_resources(
                resources, algorithm
            )
            
            # Sauvegarder les clusters
            await context.database_manager.save_clusters(clustering_result.clusters)
            
            return [_convert_cluster_to_graphql(cluster) 
                   for cluster in clustering_result.clusters]
            
        except Exception as e:
            logger.error(f"Erreur GraphQL cluster_resources: {e}")
            return []

# Subscriptions (pour les mises à jour en temps réel)
@strawberry.type
class Subscription:
    @strawberry.subscription
    async def resource_updates(self, info: Info) -> WebResourceType:
        """Souscription aux mises à jour de ressources"""
        # Implémentation basique pour demonstration
        while True:
            await asyncio.sleep(30)
            # Ici on pourrait écouter les changements de la base de données
            # et émettre des événements
            yield WebResourceType(
                id=0,
                url="",
                title="Update notification"
            )

# Fonctions utilitaires
def _convert_resource_to_graphql(resource: WebResource) -> WebResourceType:
    """Convertit WebResource en WebResourceType GraphQL"""
    return WebResourceType(
        id=resource.id,
        url=resource.url,
        title=resource.title,
        content=resource.content,
        content_type=resource.content_type.value if resource.content_type else None,
        categories=resource.categories or [],
        tags=resource.tags or [],
        language=resource.language,
        file_size=resource.file_size,
        status=resource.status.value if resource.status else None,
        priority=resource.priority,
        created_at=resource.created_at,
        updated_at=resource.updated_at
    )

def _convert_cluster_to_graphql(cluster) -> ClusterType:
    """Convertit Cluster en ClusterType GraphQL"""
    return ClusterType(
        id=cluster.id,
        name=cluster.name,
        description=cluster.description,
        size=cluster.size,
        keywords=cluster.keywords or [],
        coherence_score=cluster.coherence_score,
        created_at=cluster.created_at
    )

# Schema GraphQL principal
schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    subscription=Subscription
)

class GraphQLServer:
    """Serveur GraphQL pour DATA_BOT v4"""
    
    def __init__(self, database_manager: DatabaseManager,
                 opensearch_manager=None,
                 ml_categorizer=None,
                 result_clusterer=None,
                 port: int = 8083):
        """
        Initialise le serveur GraphQL
        
        Args:
            database_manager: Gestionnaire de base de données
            opensearch_manager: Gestionnaire OpenSearch (optionnel)
            ml_categorizer: Catégoriseur ML (optionnel)
            result_clusterer: Clusterer de résultats (optionnel)
            port: Port du serveur
        """
        if not GRAPHQL_AVAILABLE:
            raise ImportError("Les dépendances GraphQL ne sont pas installées")
        
        self.database_manager = database_manager
        self.opensearch_manager = opensearch_manager
        self.ml_categorizer = ml_categorizer
        self.result_clusterer = result_clusterer
        self.port = port
        
        # Créer l'application FastAPI
        self.app = FastAPI(title="DATA_BOT v4 GraphQL API")
        
        # Contexte GraphQL
        self.context = GraphQLContext(
            database_manager=database_manager,
            opensearch_manager=opensearch_manager,
            ml_categorizer=ml_categorizer,
            result_clusterer=result_clusterer
        )
        
        # Router GraphQL
        self.graphql_router = GraphQLRouter(
            schema,
            context_getter=lambda: self.context
        )
        
        # Ajouter le router à l'app
        self.app.include_router(self.graphql_router, prefix="/graphql")
        
        # Endpoint de santé
        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy", "service": "DATA_BOT v4 GraphQL"}
        
        # Endpoint d'information sur le schéma
        @self.app.get("/schema")
        async def get_schema():
            return {"schema": str(schema)}
    
    async def start(self):
        """Démarre le serveur GraphQL"""
        config = uvicorn.Config(
            self.app,
            host="0.0.0.0",
            port=self.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        
        logger.info(f"Démarrage du serveur GraphQL sur le port {self.port}")
        logger.info(f"GraphQL Playground disponible sur http://localhost:{self.port}/graphql")
        
        await server.serve()
    
    async def stop(self):
        """Arrête le serveur GraphQL"""
        logger.info("Arrêt du serveur GraphQL")

# Point d'entrée pour tests
if __name__ == "__main__":
    import asyncio
    
    async def main():
        # Configuration basique pour tests
        from src.database.database import DatabaseManager
        
        db_manager = DatabaseManager("sqlite:///test.db")
        await db_manager.initialize()
        
        server = GraphQLServer(db_manager)
        await server.start()
    
    asyncio.run(main())