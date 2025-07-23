"""
Result Clusterer pour DATA_BOT v4
Clustering automatique des résultats de recherche et du contenu
"""

import asyncio
import logging
import json
import numpy as np
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
import os

try:
    import numpy as np
    import pandas as pd
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
    from sklearn.metrics import silhouette_score, calinski_harabasz_score
    from sklearn.decomposition import PCA
    from sklearn.manifold import TSNE
    from sentence_transformers import SentenceTransformer
    import umap
    import hdbscan
    CLUSTERING_AVAILABLE = True
except ImportError:
    CLUSTERING_AVAILABLE = False

from src.core.models import WebResource, ContentType
from src.database.database import DatabaseManager

logger = logging.getLogger(__name__)

@dataclass
class Cluster:
    """Représente un cluster de ressources"""
    id: int
    name: str
    description: str
    resources: List[WebResource]
    centroid: Optional[np.ndarray] = None
    keywords: List[str] = None
    size: int = 0
    coherence_score: float = 0.0
    created_at: datetime = None

@dataclass
class ClusteringResult:
    """Résultat d'un clustering"""
    clusters: List[Cluster]
    algorithm: str
    parameters: Dict[str, Any]
    silhouette_score: float
    calinski_harabasz_score: float
    n_clusters: int
    n_noise: int
    execution_time: float

class ResultClusterer:
    """Clusterer pour regrouper automatiquement les résultats"""
    
    def __init__(self, model_dir: str = "data/clustering_models"):
        """
        Initialise le clusterer
        
        Args:
            model_dir: Répertoire pour stocker les modèles
        """
        if not CLUSTERING_AVAILABLE:
            raise ImportError("Les dépendances de clustering ne sont pas installées")
        
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(exist_ok=True, parents=True)
        
        # Modèles et transformateurs
        self.tfidf_vectorizer = None
        self.sentence_transformer = None
        self.clustering_model = None
        self.embeddings_cache = {}
        
        # Configuration
        self.config = {
            'sentence_model': 'all-MiniLM-L6-v2',
            'max_features': 5000,
            'ngram_range': (1, 2),
            'min_df': 2,
            'max_df': 0.95,
            'clustering_algorithm': 'hdbscan',
            'min_cluster_size': 3,
            'max_clusters': 50,
            'similarity_threshold': 0.7,
            'keyword_extraction_top_k': 10
        }
        
        self.initialized = False
    
    async def initialize(self):
        """Initialise le clusterer"""
        try:
            logger.info("Initialisation du Result Clusterer...")
            
            # Initialiser le vectoriseur TF-IDF
            self.tfidf_vectorizer = TfidfVectorizer(
                max_features=self.config['max_features'],
                ngram_range=self.config['ngram_range'],
                min_df=self.config['min_df'],
                max_df=self.config['max_df'],
                stop_words='english'
            )
            
            # Initialiser le modèle de sentence transformers
            self.sentence_transformer = SentenceTransformer(
                self.config['sentence_model']
            )
            
            self.initialized = True
            logger.info("Result Clusterer initialisé avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du Result Clusterer: {e}")
            raise
    
    async def cluster_resources(self, resources: List[WebResource],
                              algorithm: str = None,
                              n_clusters: int = None) -> ClusteringResult:
        """
        Clustering des ressources
        
        Args:
            resources: Liste des ressources à clusterer
            algorithm: Algorithme de clustering ('kmeans', 'hdbscan', 'agglomerative', 'dbscan')
            n_clusters: Nombre de clusters (pour kmeans et agglomerative)
            
        Returns:
            Résultat du clustering
        """
        if not self.initialized:
            await self.initialize()
        
        if not resources:
            return ClusteringResult(
                clusters=[], algorithm='none', parameters={},
                silhouette_score=0, calinski_harabasz_score=0,
                n_clusters=0, n_noise=0, execution_time=0
            )
        
        start_time = datetime.now()
        algorithm = algorithm or self.config['clustering_algorithm']
        
        logger.info(f"Clustering de {len(resources)} ressources avec {algorithm}")
        
        try:
            # Préparer les embeddings
            embeddings = await self._get_embeddings(resources)
            
            # Effectuer le clustering
            labels, clustering_params = await self._perform_clustering(
                embeddings, algorithm, n_clusters
            )
            
            # Créer les clusters
            clusters = await self._create_clusters(resources, labels, embeddings)
            
            # Calculer les métriques
            metrics = await self._calculate_metrics(embeddings, labels)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            result = ClusteringResult(
                clusters=clusters,
                algorithm=algorithm,
                parameters=clustering_params,
                silhouette_score=metrics.get('silhouette_score', 0),
                calinski_harabasz_score=metrics.get('calinski_harabasz_score', 0),
                n_clusters=len(clusters),
                n_noise=sum(1 for label in labels if label == -1),
                execution_time=execution_time
            )
            
            logger.info(f"Clustering terminé: {len(clusters)} clusters en {execution_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors du clustering: {e}")
            raise
    
    async def _get_embeddings(self, resources: List[WebResource]) -> np.ndarray:
        """Génère les embeddings pour les ressources"""
        texts = []
        
        for resource in resources:
            # Créer un texte représentatif de la ressource
            text_parts = []
            
            if resource.title:
                text_parts.append(resource.title)
            
            if resource.content:
                # Prendre les premiers 500 caractères du contenu
                content_snippet = resource.content[:500].replace('\n', ' ').strip()
                text_parts.append(content_snippet)
            
            if resource.categories:
                text_parts.append(' '.join(resource.categories))
            
            if resource.tags:
                text_parts.append(' '.join(resource.tags))
            
            combined_text = ' '.join(text_parts) if text_parts else resource.url
            texts.append(combined_text)
        
        # Générer les embeddings avec sentence transformer
        embeddings = self.sentence_transformer.encode(
            texts,
            show_progress_bar=True,
            batch_size=32
        )
        
        return embeddings
    
    async def _perform_clustering(self, embeddings: np.ndarray,
                                algorithm: str,
                                n_clusters: int = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Effectue le clustering avec l'algorithme spécifié"""
        params = {}
        
        if algorithm == 'kmeans':
            if n_clusters is None:
                n_clusters = await self._estimate_optimal_clusters(embeddings)
            
            model = KMeans(
                n_clusters=n_clusters,
                random_state=42,
                n_init=10
            )
            labels = model.fit_predict(embeddings)
            params = {'n_clusters': n_clusters, 'algorithm': 'kmeans'}
            
        elif algorithm == 'hdbscan':
            model = hdbscan.HDBSCAN(
                min_cluster_size=self.config['min_cluster_size'],
                min_samples=None,
                metric='euclidean'
            )
            labels = model.fit_predict(embeddings)
            params = {
                'min_cluster_size': self.config['min_cluster_size'],
                'algorithm': 'hdbscan'
            }
            
        elif algorithm == 'agglomerative':
            if n_clusters is None:
                n_clusters = await self._estimate_optimal_clusters(embeddings)
            
            model = AgglomerativeClustering(
                n_clusters=n_clusters,
                linkage='ward'
            )
            labels = model.fit_predict(embeddings)
            params = {'n_clusters': n_clusters, 'algorithm': 'agglomerative'}
            
        elif algorithm == 'dbscan':
            # Estimer eps automatiquement
            eps = await self._estimate_eps(embeddings)
            
            model = DBSCAN(
                eps=eps,
                min_samples=self.config['min_cluster_size']
            )
            labels = model.fit_predict(embeddings)
            params = {'eps': eps, 'min_samples': self.config['min_cluster_size'], 'algorithm': 'dbscan'}
            
        else:
            raise ValueError(f"Algorithme de clustering non supporté: {algorithm}")
        
        self.clustering_model = model
        return labels, params
    
    async def _estimate_optimal_clusters(self, embeddings: np.ndarray) -> int:
        """Estime le nombre optimal de clusters avec la méthode du coude"""
        n_samples = len(embeddings)
        
        # Limites raisonnables
        min_clusters = 2
        max_clusters = min(self.config['max_clusters'], n_samples // 2)
        
        if max_clusters <= min_clusters:
            return min_clusters
        
        # Tester différents nombres de clusters
        inertias = []
        cluster_range = range(min_clusters, max_clusters + 1)
        
        for k in cluster_range:
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            kmeans.fit(embeddings)
            inertias.append(kmeans.inertia_)
        
        # Méthode du coude simplifiée
        # Chercher le point où le taux de diminution de l'inertie ralentit
        diffs = np.diff(inertias)
        diffs2 = np.diff(diffs)
        
        if len(diffs2) > 0:
            optimal_k = np.argmax(diffs2) + min_clusters + 1
        else:
            optimal_k = min_clusters + len(inertias) // 2
        
        return min(optimal_k, max_clusters)
    
    async def _estimate_eps(self, embeddings: np.ndarray) -> float:
        """Estime le paramètre eps pour DBSCAN"""
        from sklearn.neighbors import NearestNeighbors
        
        # Calculer les distances au k-ème plus proche voisin
        k = self.config['min_cluster_size']
        nbrs = NearestNeighbors(n_neighbors=k).fit(embeddings)
        distances, indices = nbrs.kneighbors(embeddings)
        
        # Prendre la distance moyenne au k-ème voisin
        k_distances = distances[:, k-1]
        k_distances = np.sort(k_distances)
        
        # Utiliser le 90ème percentile comme eps
        eps = np.percentile(k_distances, 90)
        
        return eps
    
    async def _create_clusters(self, resources: List[WebResource],
                             labels: np.ndarray,
                             embeddings: np.ndarray) -> List[Cluster]:
        """Crée les objets Cluster à partir des labels"""
        clusters = []
        unique_labels = np.unique(labels)
        
        for label in unique_labels:
            if label == -1:  # Bruit/outliers
                continue
            
            # Ressources du cluster
            cluster_indices = np.where(labels == label)[0]
            cluster_resources = [resources[i] for i in cluster_indices]
            
            # Centroïde
            cluster_embeddings = embeddings[cluster_indices]
            centroid = np.mean(cluster_embeddings, axis=0)
            
            # Mots-clés et nom du cluster
            keywords = await self._extract_cluster_keywords(cluster_resources)
            cluster_name = await self._generate_cluster_name(keywords, cluster_resources)
            description = await self._generate_cluster_description(cluster_resources, keywords)
            
            # Score de cohérence
            coherence_score = await self._calculate_cluster_coherence(cluster_embeddings)
            
            cluster = Cluster(
                id=int(label),
                name=cluster_name,
                description=description,
                resources=cluster_resources,
                centroid=centroid,
                keywords=keywords,
                size=len(cluster_resources),
                coherence_score=coherence_score,
                created_at=datetime.now()
            )
            
            clusters.append(cluster)
        
        # Trier les clusters par taille (descendant)
        clusters.sort(key=lambda c: c.size, reverse=True)
        
        return clusters
    
    async def _extract_cluster_keywords(self, resources: List[WebResource]) -> List[str]:
        """Extrait les mots-clés représentatifs d'un cluster"""
        # Combiner tous les textes du cluster
        texts = []
        for resource in resources:
            text_parts = []
            if resource.title:
                text_parts.append(resource.title)
            if resource.content:
                text_parts.append(resource.content[:200])  # Premiers 200 chars
            texts.append(' '.join(text_parts))
        
        combined_text = ' '.join(texts)
        
        if not combined_text.strip():
            return []
        
        # Vectoriser avec TF-IDF
        try:
            tfidf = TfidfVectorizer(
                max_features=self.config['keyword_extraction_top_k'] * 2,
                stop_words='english',
                ngram_range=(1, 2)
            )
            
            tfidf_matrix = tfidf.fit_transform([combined_text])
            feature_names = tfidf.get_feature_names_out()
            scores = tfidf_matrix.toarray()[0]
            
            # Prendre les top mots-clés
            top_indices = np.argsort(scores)[-self.config['keyword_extraction_top_k']:][::-1]
            keywords = [feature_names[i] for i in top_indices if scores[i] > 0]
            
            return keywords
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction de mots-clés: {e}")
            return []
    
    async def _generate_cluster_name(self, keywords: List[str], 
                                   resources: List[WebResource]) -> str:
        """Génère un nom pour le cluster"""
        if not keywords:
            # Utiliser les domaines les plus fréquents
            domains = []
            for resource in resources:
                try:
                    from urllib.parse import urlparse
                    domain = urlparse(resource.url).netloc
                    domains.append(domain)
                except:
                    pass
            
            if domains:
                most_common_domain = max(set(domains), key=domains.count)
                return f"Cluster {most_common_domain}"
            else:
                return f"Cluster {len(resources)} resources"
        
        # Utiliser les premiers mots-clés
        if len(keywords) >= 2:
            return f"{keywords[0]} & {keywords[1]}"
        else:
            return keywords[0]
    
    async def _generate_cluster_description(self, resources: List[WebResource],
                                          keywords: List[str]) -> str:
        """Génère une description pour le cluster"""
        description_parts = []
        
        # Taille du cluster
        description_parts.append(f"Cluster de {len(resources)} ressources")
        
        # Mots-clés principaux
        if keywords[:3]:
            description_parts.append(f"focalisé sur: {', '.join(keywords[:3])}")
        
        # Types de contenu
        content_types = {}
        for resource in resources:
            if resource.content_type:
                ct = resource.content_type.value
                content_types[ct] = content_types.get(ct, 0) + 1
        
        if content_types:
            main_type = max(content_types.items(), key=lambda x: x[1])
            if main_type[1] > len(resources) * 0.5:  # Plus de 50%
                description_parts.append(f"principalement du contenu {main_type[0]}")
        
        return '. '.join(description_parts) + '.'
    
    async def _calculate_cluster_coherence(self, embeddings: np.ndarray) -> float:
        """Calcule le score de cohérence d'un cluster"""
        if len(embeddings) < 2:
            return 1.0
        
        # Calculer la distance moyenne au centroïde
        centroid = np.mean(embeddings, axis=0)
        distances = np.linalg.norm(embeddings - centroid, axis=1)
        avg_distance = np.mean(distances)
        
        # Normaliser pour avoir un score entre 0 et 1
        # Plus la distance moyenne est faible, plus le score est élevé
        max_distance = np.sqrt(embeddings.shape[1])  # Distance max théorique
        coherence_score = 1 - (avg_distance / max_distance)
        
        return max(0, min(1, coherence_score))
    
    async def _calculate_metrics(self, embeddings: np.ndarray, 
                               labels: np.ndarray) -> Dict[str, float]:
        """Calcule les métriques de qualité du clustering"""
        metrics = {}
        
        try:
            # Exclure le bruit pour les métriques
            non_noise_mask = labels != -1
            if np.sum(non_noise_mask) > 1 and len(np.unique(labels[non_noise_mask])) > 1:
                
                # Silhouette score
                silhouette = silhouette_score(
                    embeddings[non_noise_mask], 
                    labels[non_noise_mask]
                )
                metrics['silhouette_score'] = silhouette
                
                # Calinski-Harabasz score
                calinski = calinski_harabasz_score(
                    embeddings[non_noise_mask], 
                    labels[non_noise_mask]
                )
                metrics['calinski_harabasz_score'] = calinski
                
        except Exception as e:
            logger.warning(f"Erreur lors du calcul des métriques: {e}")
            metrics['silhouette_score'] = 0
            metrics['calinski_harabasz_score'] = 0
        
        return metrics
    
    async def cluster_search_results(self, search_results: List[WebResource],
                                   query: str) -> ClusteringResult:
        """
        Clustering spécifique pour les résultats de recherche
        
        Args:
            search_results: Résultats de recherche
            query: Requête de recherche originale
            
        Returns:
            Résultat du clustering
        """
        logger.info(f"Clustering de {len(search_results)} résultats de recherche pour '{query}'")
        
        if len(search_results) < 3:
            # Pas assez de résultats pour clusterer
            return ClusteringResult(
                clusters=[], algorithm='none', parameters={},
                silhouette_score=0, calinski_harabasz_score=0,
                n_clusters=0, n_noise=0, execution_time=0
            )
        
        # Utiliser HDBSCAN pour les résultats de recherche (plus adapté)
        result = await self.cluster_resources(
            search_results, 
            algorithm='hdbscan'
        )
        
        # Réordonner les clusters par pertinence par rapport à la requête
        if result.clusters:
            result.clusters = await self._rank_clusters_by_relevance(
                result.clusters, query
            )
        
        return result
    
    async def _rank_clusters_by_relevance(self, clusters: List[Cluster], 
                                        query: str) -> List[Cluster]:
        """Classe les clusters par pertinence par rapport à une requête"""
        try:
            # Générer l'embedding de la requête
            query_embedding = self.sentence_transformer.encode([query])[0]
            
            # Calculer la similarité de chaque cluster avec la requête
            cluster_scores = []
            
            for cluster in clusters:
                if cluster.centroid is not None:
                    # Similarité cosinus avec le centroïde
                    similarity = np.dot(query_embedding, cluster.centroid) / (
                        np.linalg.norm(query_embedding) * np.linalg.norm(cluster.centroid)
                    )
                    cluster_scores.append((cluster, similarity))
                else:
                    cluster_scores.append((cluster, 0))
            
            # Trier par similarité décroissante
            cluster_scores.sort(key=lambda x: x[1], reverse=True)
            
            return [cluster for cluster, score in cluster_scores]
            
        except Exception as e:
            logger.error(f"Erreur lors du classement des clusters: {e}")
            return clusters
    
    async def get_cluster_recommendations(self, resource: WebResource,
                                        all_clusters: List[Cluster],
                                        top_k: int = 3) -> List[Tuple[Cluster, float]]:
        """
        Recommande des clusters similaires pour une ressource
        
        Args:
            resource: Ressource de référence
            all_clusters: Tous les clusters disponibles
            top_k: Nombre de recommandations
            
        Returns:
            Liste des clusters recommandés avec scores de similarité
        """
        if not all_clusters:
            return []
        
        try:
            # Générer l'embedding de la ressource
            resource_text = f"{resource.title or ''} {resource.content[:200] or ''}"
            resource_embedding = self.sentence_transformer.encode([resource_text])[0]
            
            # Calculer la similarité avec chaque cluster
            similarities = []
            
            for cluster in all_clusters:
                if cluster.centroid is not None:
                    similarity = np.dot(resource_embedding, cluster.centroid) / (
                        np.linalg.norm(resource_embedding) * np.linalg.norm(cluster.centroid)
                    )
                    similarities.append((cluster, similarity))
            
            # Trier par similarité décroissante
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            return similarities[:top_k]
            
        except Exception as e:
            logger.error(f"Erreur lors des recommandations de clusters: {e}")
            return []
    
    async def get_clustering_statistics(self, clusters: List[Cluster]) -> Dict[str, Any]:
        """Retourne les statistiques de clustering"""
        if not clusters:
            return {}
        
        sizes = [cluster.size for cluster in clusters]
        coherence_scores = [cluster.coherence_score for cluster in clusters]
        
        stats = {
            'total_clusters': len(clusters),
            'total_resources': sum(sizes),
            'avg_cluster_size': np.mean(sizes),
            'median_cluster_size': np.median(sizes),
            'min_cluster_size': min(sizes),
            'max_cluster_size': max(sizes),
            'avg_coherence_score': np.mean(coherence_scores),
            'cluster_size_distribution': {
                'small': sum(1 for s in sizes if s < 5),
                'medium': sum(1 for s in sizes if 5 <= s < 20),
                'large': sum(1 for s in sizes if s >= 20)
            },
            'top_clusters': [
                {
                    'name': cluster.name,
                    'size': cluster.size,
                    'coherence_score': cluster.coherence_score,
                    'keywords': cluster.keywords[:5]
                }
                for cluster in sorted(clusters, key=lambda c: c.size, reverse=True)[:5]
            ]
        }
        
        return stats