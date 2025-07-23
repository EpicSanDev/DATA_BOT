"""
Gestionnaire de bases vectorielles pour DATA_BOT v3
Support pour ChromaDB (local) et Qdrant
"""

import asyncio
import logging
import json
import hashlib
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from pathlib import Path
from dataclasses import dataclass

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

from src.core.models import WebResource, ContentType
from src.database.database import DatabaseManager

logger = logging.getLogger(__name__)

@dataclass
class VectorSearchResult:
    """Résultat de recherche vectorielle"""
    url: str
    title: Optional[str]
    content: Optional[str]
    score: float
    metadata: Dict[str, Any]
    snippet: Optional[str] = None

@dataclass
class VectorIndexStats:
    """Statistiques d'indexation vectorielle"""
    total_documents: int
    total_vectors: int
    index_size_mb: float
    last_updated: datetime
    provider: str

class VectorManager:
    """Gestionnaire de bases vectorielles"""
    
    def __init__(self, provider: str = "chromadb", config: Optional[Dict[str, Any]] = None):
        self.provider = provider.lower()
        self.config = config or {}
        self.client = None
        self.collection = None
        self.db_manager = DatabaseManager()
        
        # Configuration par défaut
        self.collection_name = "databot_archive"
        self.vector_dimension = 384  # Dimension des embeddings
        self.chunk_size = 512  # Taille des chunks de texte
        
        # Cache des embeddings
        self.embedding_cache = {}
        
    async def initialize(self):
        """Initialise le gestionnaire vectoriel"""
        logger.info(f"🔍 Initialisation du gestionnaire vectoriel: {self.provider}")
        
        if self.provider == "chromadb":
            await self._initialize_chromadb()
        elif self.provider == "qdrant":
            await self._initialize_qdrant()
        else:
            raise ValueError(f"Provider vectoriel non supporté: {self.provider}")
        
        logger.info("✅ Gestionnaire vectoriel initialisé")
    
    async def _initialize_chromadb(self):
        """Initialise ChromaDB"""
        if not CHROMADB_AVAILABLE:
            raise ImportError("ChromaDB n'est pas installé. pip install chromadb")
        
        # Configuration ChromaDB
        persist_directory = self.config.get("persist_directory", "./data/vectors/chromadb")
        Path(persist_directory).mkdir(parents=True, exist_ok=True)
        
        settings = Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=persist_directory,
            anonymized_telemetry=False
        )
        
        self.client = chromadb.Client(settings)
        
        # Créer ou récupérer la collection
        try:
            self.collection = self.client.get_collection(name=self.collection_name)
            logger.info(f"Collection ChromaDB récupérée: {self.collection_name}")
        except Exception:
            # Créer la collection si elle n'existe pas
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "DATA_BOT Archive Vectors"}
            )
            logger.info(f"Collection ChromaDB créée: {self.collection_name}")
    
    async def _initialize_qdrant(self):
        """Initialise Qdrant"""
        if not QDRANT_AVAILABLE:
            raise ImportError("Qdrant client n'est pas installé. pip install qdrant-client")
        
        # Configuration Qdrant
        host = self.config.get("host", "localhost")
        port = self.config.get("port", 6333)
        
        self.client = QdrantClient(host=host, port=port)
        
        # Créer la collection si elle n'existe pas
        try:
            collections = self.client.get_collections()
            if self.collection_name not in [c.name for c in collections.collections]:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=self.vector_dimension,
                        distance=models.Distance.COSINE
                    )
                )
                logger.info(f"Collection Qdrant créée: {self.collection_name}")
            else:
                logger.info(f"Collection Qdrant récupérée: {self.collection_name}")
        except Exception as e:
            logger.error(f"Erreur initialisation Qdrant: {e}")
            raise
    
    async def get_embedding(self, text: str) -> List[float]:
        """Génère un embedding pour un texte"""
        # Cache simple basé sur le hash du texte
        text_hash = hashlib.md5(text.encode()).hexdigest()
        
        if text_hash in self.embedding_cache:
            return self.embedding_cache[text_hash]
        
        # TODO: Intégrer avec un service d'embedding réel
        # Pour le moment, on utilise un embedding factice
        # En production, utiliser sentence-transformers ou OpenAI
        
        # Embedding factice basé sur le hash (pour demo)
        import random
        random.seed(hash(text))
        embedding = [random.uniform(-1, 1) for _ in range(self.vector_dimension)]
        
        # Cache l'embedding
        self.embedding_cache[text_hash] = embedding
        
        return embedding
    
    def _chunk_text(self, text: str) -> List[str]:
        """Découpe le texte en chunks"""
        if not text:
            return []
        
        # Découpage simple par mots
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), self.chunk_size):
            chunk = " ".join(words[i:i + self.chunk_size])
            chunks.append(chunk)
        
        return chunks
    
    async def index_resource(self, resource: WebResource, content: Optional[str] = None) -> bool:
        """Indexe une ressource dans la base vectorielle"""
        try:
            if not content:
                # Essayer de lire le contenu depuis le fichier
                if resource.file_path and Path(resource.file_path).exists():
                    content = Path(resource.file_path).read_text(encoding='utf-8')
                else:
                    logger.warning(f"Pas de contenu pour indexer: {resource.url}")
                    return False
            
            # Découper le contenu en chunks
            chunks = self._chunk_text(content)
            if not chunks:
                return False
            
            # Indexer chaque chunk
            for i, chunk in enumerate(chunks):
                chunk_id = f"{hashlib.md5(resource.url.encode()).hexdigest()}_{i}"
                
                # Générer l'embedding
                embedding = await self.get_embedding(chunk)
                
                # Métadonnées
                metadata = {
                    "url": resource.url,
                    "title": resource.title or "",
                    "content_type": resource.content_type.value,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "indexed_at": datetime.now().isoformat(),
                    "file_path": resource.file_path or "",
                    "tags": resource.tags or []
                }
                
                # Indexer selon le provider
                if self.provider == "chromadb":
                    await self._index_chromadb(chunk_id, embedding, chunk, metadata)
                elif self.provider == "qdrant":
                    await self._index_qdrant(chunk_id, embedding, chunk, metadata)
            
            logger.info(f"Ressource indexée: {resource.url} ({len(chunks)} chunks)")
            return True
            
        except Exception as e:
            logger.error(f"Erreur indexation vectorielle {resource.url}: {e}")
            return False
    
    async def _index_chromadb(self, doc_id: str, embedding: List[float], content: str, metadata: Dict[str, Any]):
        """Indexe dans ChromaDB"""
        self.collection.add(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[metadata]
        )
    
    async def _index_qdrant(self, doc_id: str, embedding: List[float], content: str, metadata: Dict[str, Any]):
        """Indexe dans Qdrant"""
        # Ajouter le contenu aux métadonnées pour Qdrant
        metadata["content"] = content
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                models.PointStruct(
                    id=doc_id,
                    vector=embedding,
                    payload=metadata
                )
            ]
        )
    
    async def semantic_search(self, query: str, limit: int = 10, filters: Optional[Dict[str, Any]] = None) -> List[VectorSearchResult]:
        """Recherche sémantique"""
        try:
            # Générer l'embedding de la requête
            query_embedding = await self.get_embedding(query)
            
            # Rechercher selon le provider
            if self.provider == "chromadb":
                results = await self._search_chromadb(query_embedding, limit, filters)
            elif self.provider == "qdrant":
                results = await self._search_qdrant(query_embedding, limit, filters)
            else:
                results = []
            
            return results
            
        except Exception as e:
            logger.error(f"Erreur recherche sémantique: {e}")
            return []
    
    async def _search_chromadb(self, query_embedding: List[float], limit: int, filters: Optional[Dict[str, Any]]) -> List[VectorSearchResult]:
        """Recherche dans ChromaDB"""
        # Construire les filtres ChromaDB
        where_clause = {}
        if filters:
            if "content_type" in filters:
                where_clause["content_type"] = filters["content_type"]
            if "url_contains" in filters:
                # ChromaDB ne supporte pas les recherches de sous-chaînes directement
                pass
        
        # Effectuer la recherche
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where=where_clause if where_clause else None
        )
        
        # Convertir les résultats
        search_results = []
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                metadata = results["metadatas"][0][i]
                distance = results["distances"][0][i]
                score = 1.0 - distance  # Convertir distance en score de similarité
                
                search_results.append(VectorSearchResult(
                    url=metadata["url"],
                    title=metadata.get("title"),
                    content=results["documents"][0][i],
                    score=score,
                    metadata=metadata,
                    snippet=results["documents"][0][i][:200] + "..." if len(results["documents"][0][i]) > 200 else results["documents"][0][i]
                ))
        
        return search_results
    
    async def _search_qdrant(self, query_embedding: List[float], limit: int, filters: Optional[Dict[str, Any]]) -> List[VectorSearchResult]:
        """Recherche dans Qdrant"""
        # Construire les filtres Qdrant
        filter_conditions = None
        if filters:
            conditions = []
            if "content_type" in filters:
                conditions.append(
                    models.FieldCondition(
                        key="content_type",
                        match=models.MatchValue(value=filters["content_type"])
                    )
                )
            if "url_contains" in filters:
                conditions.append(
                    models.FieldCondition(
                        key="url",
                        match=models.MatchText(text=filters["url_contains"])
                    )
                )
            
            if conditions:
                filter_conditions = models.Filter(must=conditions)
        
        # Effectuer la recherche
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=limit,
            query_filter=filter_conditions
        )
        
        # Convertir les résultats
        search_results = []
        for result in results:
            metadata = result.payload
            
            search_results.append(VectorSearchResult(
                url=metadata["url"],
                title=metadata.get("title"),
                content=metadata.get("content", ""),
                score=result.score,
                metadata=metadata,
                snippet=metadata.get("content", "")[:200] + "..." if len(metadata.get("content", "")) > 200 else metadata.get("content", "")
            ))
        
        return search_results
    
    async def index_all_content(self) -> VectorIndexStats:
        """Indexe tout le contenu de l'archive"""
        logger.info("🔄 Indexation de tout le contenu...")
        
        # Récupérer toutes les ressources de la base
        # TODO: Implémenter la récupération depuis DatabaseManager
        
        total_indexed = 0
        total_errors = 0
        
        # Pour le moment, simuler quelques ressources
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
            sample_content = f"Contenu de la page {resource.title}. Ceci est un exemple de contenu pour l'indexation vectorielle."
            
            success = await self.index_resource(resource, sample_content)
            if success:
                total_indexed += 1
            else:
                total_errors += 1
        
        stats = VectorIndexStats(
            total_documents=total_indexed,
            total_vectors=total_indexed * 2,  # Approximation avec chunks
            index_size_mb=total_indexed * 0.1,  # Estimation
            last_updated=datetime.now(),
            provider=self.provider
        )
        
        logger.info(f"✅ Indexation terminée: {total_indexed} documents, {total_errors} erreurs")
        return stats
    
    async def clear_index(self):
        """Vide l'index vectoriel"""
        logger.info("🗑️ Suppression de l'index vectoriel...")
        
        if self.provider == "chromadb":
            # ChromaDB: supprimer et recréer la collection
            try:
                self.client.delete_collection(name=self.collection_name)
            except Exception:
                pass
            
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "DATA_BOT Archive Vectors"}
            )
        
        elif self.provider == "qdrant":
            # Qdrant: supprimer et recréer la collection
            try:
                self.client.delete_collection(collection_name=self.collection_name)
            except Exception:
                pass
            
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=self.vector_dimension,
                    distance=models.Distance.COSINE
                )
            )
        
        # Vider le cache
        self.embedding_cache.clear()
        
        logger.info("✅ Index vectoriel vidé")
    
    async def get_stats(self) -> VectorIndexStats:
        """Récupère les statistiques de l'index"""
        if self.provider == "chromadb":
            count = self.collection.count()
        elif self.provider == "qdrant":
            info = self.client.get_collection(collection_name=self.collection_name)
            count = info.points_count or 0
        else:
            count = 0
        
        return VectorIndexStats(
            total_documents=count,
            total_vectors=count,
            index_size_mb=count * 0.1,  # Estimation
            last_updated=datetime.now(),
            provider=self.provider
        )
    
    async def close(self):
        """Ferme la connexion au gestionnaire vectoriel"""
        if self.provider == "chromadb" and self.client:
            # ChromaDB persiste automatiquement
            pass
        elif self.provider == "qdrant" and self.client:
            # Qdrant se ferme automatiquement
            pass
        
        logger.info("🔒 Gestionnaire vectoriel fermé")