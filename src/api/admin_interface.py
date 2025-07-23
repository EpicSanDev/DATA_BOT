"""
Interface d'administration complète pour DATA_BOT v4
Dashboard et outils de gestion avancés
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path
import os

try:
    import streamlit as st
    import plotly.express as px
    import plotly.graph_objects as go
    import pandas as pd
    from streamlit_autorefresh import st_autorefresh
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False

from src.core.models import WebResource, ArchiveStatus, ContentType
from src.database.database import DatabaseManager

logger = logging.getLogger(__name__)

class AdminInterface:
    """Interface d'administration complète pour DATA_BOT v4"""
    
    def __init__(self, database_manager: DatabaseManager,
                 opensearch_manager=None,
                 ml_categorizer=None,
                 result_clusterer=None,
                 port: int = 8082):
        """
        Initialise l'interface d'administration
        
        Args:
            database_manager: Gestionnaire de base de données
            opensearch_manager: Gestionnaire OpenSearch (optionnel)
            ml_categorizer: Catégoriseur ML (optionnel)  
            result_clusterer: Clusterer de résultats (optionnel)
            port: Port du serveur
        """
        if not STREAMLIT_AVAILABLE:
            raise ImportError("Streamlit n'est pas installé")
        
        self.database_manager = database_manager
        self.opensearch_manager = opensearch_manager
        self.ml_categorizer = ml_categorizer
        self.result_clusterer = result_clusterer
        self.port = port
        
        # Configuration Streamlit
        st.set_page_config(
            page_title="DATA_BOT v4 Admin",
            page_icon="🤖",
            layout="wide",
            initial_sidebar_state="expanded"
        )
    
    async def start(self):
        """Démarre l'interface d'administration"""
        logger.info(f"Démarrage de l'interface d'administration sur le port {self.port}")
        
        # Configuration de la session
        if 'initialized' not in st.session_state:
            st.session_state.initialized = True
            st.session_state.database_manager = self.database_manager
            st.session_state.opensearch_manager = self.opensearch_manager
            st.session_state.ml_categorizer = self.ml_categorizer
            st.session_state.result_clusterer = self.result_clusterer
        
        await self._render_admin_interface()
    
    async def _render_admin_interface(self):
        """Rend l'interface d'administration"""
        # Titre principal
        st.title("🤖 DATA_BOT v4 - Administration")
        st.markdown("---")
        
        # Auto-refresh pour les données en temps réel
        count = st_autorefresh(interval=30000, limit=None, key="admin_refresh")
        
        # Sidebar pour navigation
        st.sidebar.title("Navigation")
        page = st.sidebar.selectbox(
            "Choisir une page",
            [
                "📊 Dashboard",
                "🔍 Recherche & Exploration",
                "📚 Gestion des Ressources", 
                "🏷️ Catégories & Tags",
                "🧬 Clustering",
                "🤖 Machine Learning",
                "⚙️ Configuration",
                "📈 Monitoring",
                "🔧 Outils",
                "📊 Rapports"
            ]
        )
        
        # Afficher la page sélectionnée
        if page == "📊 Dashboard":
            await self._render_dashboard()
        elif page == "🔍 Recherche & Exploration":
            await self._render_search_page()
        elif page == "📚 Gestion des Ressources":
            await self._render_resources_management()
        elif page == "🏷️ Catégories & Tags":
            await self._render_categories_management()
        elif page == "🧬 Clustering":
            await self._render_clustering_page()
        elif page == "🤖 Machine Learning":
            await self._render_ml_page()
        elif page == "⚙️ Configuration":
            await self._render_configuration()
        elif page == "📈 Monitoring":
            await self._render_monitoring()
        elif page == "🔧 Outils":
            await self._render_tools()
        elif page == "📊 Rapports":
            await self._render_reports()
    
    async def _render_dashboard(self):
        """Dashboard principal avec métriques et visualisations"""
        st.header("📊 Dashboard Principal")
        
        # Métriques principales
        col1, col2, col3, col4 = st.columns(4)
        
        # Récupérer les statistiques
        stats = await self._get_system_statistics()
        
        with col1:
            st.metric(
                "Ressources Totales", 
                stats.get('total_resources', 0),
                delta=stats.get('resources_delta', 0)
            )
        
        with col2:
            st.metric(
                "Catégories", 
                stats.get('total_categories', 0),
                delta=stats.get('categories_delta', 0)
            )
        
        with col3:
            st.metric(
                "Clusters", 
                stats.get('total_clusters', 0),
                delta=stats.get('clusters_delta', 0)
            )
        
        with col4:
            st.metric(
                "Taille Stockage", 
                f"{stats.get('storage_size_mb', 0):.1f} MB",
                delta=f"{stats.get('storage_delta_mb', 0):.1f} MB"
            )
        
        st.markdown("---")
        
        # Graphiques
        col1, col2 = st.columns(2)
        
        with col1:
            # Evolution des ressources dans le temps
            st.subheader("📈 Evolution des Ressources")
            timeline_data = await self._get_timeline_data()
            if timeline_data:
                fig = px.line(
                    timeline_data, 
                    x='date', 
                    y='count',
                    title="Ressources ajoutées par jour"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Distribution des types de contenu
            st.subheader("📊 Types de Contenu")
            content_types = await self._get_content_type_distribution()
            if content_types:
                fig = px.pie(
                    values=list(content_types.values()),
                    names=list(content_types.keys()),
                    title="Distribution des types de contenu"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Status du système
        st.subheader("🔧 Status du Système")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            db_status = await self._check_database_status()
            st.success("✅ Base de données") if db_status else st.error("❌ Base de données")
        
        with col2:
            opensearch_status = await self._check_opensearch_status()
            st.success("✅ OpenSearch") if opensearch_status else st.warning("⚠️ OpenSearch")
        
        with col3:
            ml_status = await self._check_ml_status()
            st.success("✅ ML Categorizer") if ml_status else st.warning("⚠️ ML Categorizer")
    
    async def _render_search_page(self):
        """Page de recherche et exploration"""
        st.header("🔍 Recherche & Exploration")
        
        # Interface de recherche
        col1, col2 = st.columns([3, 1])
        
        with col1:
            query = st.text_input("🔍 Rechercher:", placeholder="Entrez votre requête...")
        
        with col2:
            search_type = st.selectbox("Type", ["Général", "Titre", "Contenu", "Catégories"])
        
        # Options avancées
        with st.expander("Options avancées"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                enable_clustering = st.checkbox("Activer le clustering", value=True)
                limit = st.slider("Nombre de résultats", 10, 100, 20)
            
            with col2:
                content_type_filter = st.multiselect(
                    "Types de contenu", 
                    ["web_page", "pdf", "image", "video", "audio"]
                )
                category_filter = st.multiselect(
                    "Catégories", 
                    await self._get_all_categories()
                )
            
            with col3:
                date_range = st.date_input(
                    "Période",
                    value=[datetime.now() - timedelta(days=30), datetime.now()],
                    max_value=datetime.now()
                )
        
        if query and st.button("🔍 Rechercher"):
            with st.spinner("Recherche en cours..."):
                results = await self._perform_search(
                    query, search_type, limit, enable_clustering,
                    content_type_filter, category_filter, date_range
                )
                
                if results:
                    st.success(f"✅ {len(results['resources'])} résultats trouvés")
                    
                    # Afficher les clusters si disponibles
                    if enable_clustering and results.get('clusters'):
                        st.subheader("🧬 Clusters détectés")
                        for cluster in results['clusters']:
                            with st.expander(f"📁 {cluster['name']} ({cluster['size']} ressources)"):
                                st.write(cluster['description'])
                                st.write(f"**Mots-clés:** {', '.join(cluster['keywords'])}")
                    
                    # Afficher les résultats
                    st.subheader("📄 Résultats")
                    for resource in results['resources']:
                        with st.expander(f"🔗 {resource['title'] or resource['url']}"):
                            col1, col2 = st.columns([3, 1])
                            
                            with col1:
                                st.write(f"**URL:** {resource['url']}")
                                if resource['content']:
                                    st.write(f"**Contenu:** {resource['content'][:200]}...")
                                if resource['categories']:
                                    st.write(f"**Catégories:** {', '.join(resource['categories'])}")
                            
                            with col2:
                                st.write(f"**Type:** {resource['content_type']}")
                                st.write(f"**Statut:** {resource['status']}")
                                st.write(f"**Créé:** {resource['created_at']}")
                else:
                    st.warning("Aucun résultat trouvé")
    
    async def _render_resources_management(self):
        """Page de gestion des ressources"""
        st.header("📚 Gestion des Ressources")
        
        # Actions principales
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("➕ Ajouter une ressource"):
                await self._show_add_resource_form()
        
        with col2:
            if st.button("🔄 Actualiser l'index"):
                await self._refresh_search_index()
        
        with col3:
            if st.button("🧹 Nettoyer les doublons"):
                await self._clean_duplicates()
        
        st.markdown("---")
        
        # Filtres
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status_filter = st.selectbox(
                "Statut", 
                ["Tous", "En attente", "Traité", "Échec", "Ignoré"]
            )
        
        with col2:
            category_filter = st.selectbox(
                "Catégorie", 
                ["Toutes"] + await self._get_all_categories()
            )
        
        with col3:
            sort_by = st.selectbox(
                "Trier par", 
                ["Date de création", "Date de modification", "Titre", "Taille"]
            )
        
        # Liste des ressources
        st.subheader("📋 Liste des Ressources")
        
        resources = await self._get_filtered_resources(
            status_filter, category_filter, sort_by
        )
        
        if resources:
            # Tableau interactif
            df = pd.DataFrame([
                {
                    'ID': r['id'],
                    'Titre': r['title'] or r['url'][:50] + '...',
                    'URL': r['url'],
                    'Catégories': ', '.join(r['categories']) if r['categories'] else '',
                    'Statut': r['status'],
                    'Taille': f"{r['file_size'] or 0} bytes",
                    'Créé': r['created_at']
                }
                for r in resources
            ])
            
            # Sélection de ressources
            selected_rows = st.multiselect(
                "Sélectionner des ressources pour actions groupées:",
                df.index,
                format_func=lambda x: f"{df.iloc[x]['Titre']}"
            )
            
            if selected_rows:
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("🏷️ Catégoriser"):
                        await self._categorize_selected_resources(selected_rows, df)
                
                with col2:
                    if st.button("🗑️ Supprimer"):
                        await self._delete_selected_resources(selected_rows, df)
                
                with col3:
                    if st.button("📊 Analyser"):
                        await self._analyze_selected_resources(selected_rows, df)
            
            # Afficher le tableau
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Aucune ressource trouvée avec ces filtres")
    
    async def _render_categories_management(self):
        """Page de gestion des catégories et tags"""
        st.header("🏷️ Gestion des Catégories & Tags")
        
        # Statistiques des catégories
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Statistiques des Catégories")
            categories_stats = await self._get_categories_statistics()
            
            if categories_stats:
                fig = px.bar(
                    x=list(categories_stats.keys()),
                    y=list(categories_stats.values()),
                    title="Nombre de ressources par catégorie"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("🔧 Actions")
            
            # Ajouter une catégorie
            new_category = st.text_input("Nouvelle catégorie:")
            if st.button("➕ Ajouter") and new_category:
                await self._add_category(new_category)
                st.success(f"Catégorie '{new_category}' ajoutée")
            
            # Fusionner des catégories
            st.markdown("**Fusionner des catégories:**")
            categories = await self._get_all_categories()
            source_cat = st.selectbox("Catégorie source:", categories)
            target_cat = st.selectbox("Catégorie cible:", categories)
            
            if st.button("🔀 Fusionner") and source_cat != target_cat:
                await self._merge_categories(source_cat, target_cat)
                st.success(f"Catégories fusionnées: {source_cat} → {target_cat}")
        
        st.markdown("---")
        
        # Gestion des tags
        st.subheader("🏷️ Gestion des Tags")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Tags les plus utilisés
            tags_stats = await self._get_tags_statistics()
            if tags_stats:
                st.write("**Tags les plus utilisés:**")
                for tag, count in tags_stats.items():
                    st.write(f"• {tag}: {count} ressources")
        
        with col2:
            # Actions sur les tags
            st.write("**Actions sur les tags:**")
            
            # Nettoyer les tags
            if st.button("🧹 Nettoyer les tags"):
                await self._clean_tags()
                st.success("Tags nettoyés")
            
            # Suggérer des tags
            if st.button("💡 Suggérer des tags"):
                suggestions = await self._suggest_tags()
                if suggestions:
                    st.write("**Suggestions de tags:**")
                    for suggestion in suggestions:
                        st.write(f"• {suggestion}")
    
    async def _render_clustering_page(self):
        """Page de clustering"""
        st.header("🧬 Clustering des Résultats")
        
        if not self.result_clusterer:
            st.warning("⚠️ Le module de clustering n'est pas disponible")
            return
        
        # Configuration du clustering
        col1, col2 = st.columns(2)
        
        with col1:
            algorithm = st.selectbox(
                "Algorithme", 
                ["hdbscan", "kmeans", "agglomerative", "dbscan"]
            )
            
            if algorithm in ["kmeans", "agglomerative"]:
                n_clusters = st.slider("Nombre de clusters", 2, 20, 5)
            else:
                n_clusters = None
        
        with col2:
            min_cluster_size = st.slider("Taille minimale des clusters", 2, 10, 3)
            max_clusters = st.slider("Nombre maximum de clusters", 5, 50, 20)
        
        # Lancer le clustering
        if st.button("🚀 Lancer le clustering"):
            with st.spinner("Clustering en cours..."):
                result = await self._perform_clustering(
                    algorithm, n_clusters, min_cluster_size, max_clusters
                )
                
                if result:
                    st.success(f"✅ Clustering terminé: {result['n_clusters']} clusters créés")
                    
                    # Métriques de qualité
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric(
                            "Score Silhouette", 
                            f"{result['silhouette_score']:.3f}"
                        )
                    
                    with col2:
                        st.metric(
                            "Score Calinski-Harabasz", 
                            f"{result['calinski_harabasz_score']:.1f}"
                        )
                    
                    with col3:
                        st.metric(
                            "Temps d'exécution", 
                            f"{result['execution_time']:.2f}s"
                        )
                    
                    # Visualisation des clusters
                    st.subheader("📊 Visualisation des Clusters")
                    await self._visualize_clusters(result['clusters'])
        
        # Clusters existants
        st.markdown("---")
        st.subheader("📁 Clusters Existants")
        
        existing_clusters = await self._get_existing_clusters()
        if existing_clusters:
            for cluster in existing_clusters:
                with st.expander(f"📁 {cluster['name']} ({cluster['size']} ressources)"):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.write(cluster['description'])
                        st.write(f"**Mots-clés:** {', '.join(cluster['keywords'])}")
                        st.write(f"**Score de cohérence:** {cluster['coherence_score']:.3f}")
                    
                    with col2:
                        if st.button(f"🔍 Explorer", key=f"explore_{cluster['id']}"):
                            await self._explore_cluster(cluster['id'])
                        
                        if st.button(f"🗑️ Supprimer", key=f"delete_{cluster['id']}"):
                            await self._delete_cluster(cluster['id'])
        else:
            st.info("Aucun cluster existant. Lancez un clustering pour en créer.")
    
    async def _render_ml_page(self):
        """Page Machine Learning"""
        st.header("🤖 Machine Learning")
        
        if not self.ml_categorizer:
            st.warning("⚠️ Le module ML n'est pas disponible")
            return
        
        # Statistiques ML
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Statistiques de Catégorisation")
            ml_stats = await self._get_ml_statistics()
            
            if ml_stats:
                st.metric("Ressources catégorisées", ml_stats['categorized_resources'])
                st.metric("Taux de catégorisation", f"{ml_stats['categorization_rate']:.1%}")
                st.metric("Nombre de catégories", ml_stats['total_categories'])
        
        with col2:
            st.subheader("🔧 Actions ML")
            
            # Catégorisation automatique
            if st.button("🏷️ Catégoriser toutes les ressources"):
                with st.spinner("Catégorisation en cours..."):
                    result = await self._auto_categorize_all()
                    st.success(f"✅ {result['categorized']} ressources catégorisées")
            
            # Entraînement du modèle
            if st.button("🎯 Entraîner le modèle"):
                with st.spinner("Entraînement en cours..."):
                    result = await self._train_ml_model()
                    if result:
                        st.success("✅ Modèle entraîné avec succès")
            
            # Évaluation du modèle
            if st.button("📊 Évaluer le modèle"):
                with st.spinner("Évaluation en cours..."):
                    metrics = await self._evaluate_ml_model()
                    if metrics:
                        st.success("✅ Évaluation terminée")
                        st.json(metrics)
        
        # Configuration du modèle
        st.markdown("---")
        st.subheader("⚙️ Configuration du Modèle")
        
        col1, col2 = st.columns(2)
        
        with col1:
            model_type = st.selectbox(
                "Type de modèle", 
                ["Naive Bayes", "Transformer", "Hybride"]
            )
            
            confidence_threshold = st.slider(
                "Seuil de confiance", 
                0.1, 0.9, 0.3, 0.1
            )
        
        with col2:
            max_categories = st.slider(
                "Nombre max de catégories par ressource", 
                1, 10, 5
            )
            
            batch_size = st.slider(
                "Taille des lots", 
                10, 1000, 100, 10
            )
        
        if st.button("💾 Sauvegarder la configuration"):
            await self._save_ml_config(
                model_type, confidence_threshold, max_categories, batch_size
            )
            st.success("✅ Configuration sauvegardée")
    
    async def _render_monitoring(self):
        """Page de monitoring système"""
        st.header("📈 Monitoring Système")
        
        # Métriques en temps réel
        col1, col2, col3, col4 = st.columns(4)
        
        system_metrics = await self._get_system_metrics()
        
        with col1:
            st.metric("CPU Usage", f"{system_metrics.get('cpu_percent', 0):.1f}%")
        
        with col2:
            st.metric("Memory Usage", f"{system_metrics.get('memory_percent', 0):.1f}%")
        
        with col3:
            st.metric("Disk Usage", f"{system_metrics.get('disk_percent', 0):.1f}%")
        
        with col4:
            st.metric("Active Connections", system_metrics.get('connections', 0))
        
        # Graphiques de monitoring
        st.subheader("📊 Métriques dans le Temps")
        
        # Graphique CPU/Memory
        monitoring_data = await self._get_monitoring_history()
        if monitoring_data:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=monitoring_data['timestamps'],
                y=monitoring_data['cpu'],
                mode='lines',
                name='CPU %'
            ))
            fig.add_trace(go.Scatter(
                x=monitoring_data['timestamps'],
                y=monitoring_data['memory'],
                mode='lines',
                name='Memory %'
            ))
            st.plotly_chart(fig, use_container_width=True)
        
        # Logs système
        st.subheader("📝 Logs Récents")
        
        log_level = st.selectbox("Niveau de log", ["INFO", "WARNING", "ERROR"])
        recent_logs = await self._get_recent_logs(log_level)
        
        if recent_logs:
            for log in recent_logs:
                if log['level'] == 'ERROR':
                    st.error(f"[{log['timestamp']}] {log['message']}")
                elif log['level'] == 'WARNING':
                    st.warning(f"[{log['timestamp']}] {log['message']}")
                else:
                    st.info(f"[{log['timestamp']}] {log['message']}")
        else:
            st.info("Aucun log récent")
    
    # Méthodes utilitaires (stubs - implémentation complète nécessaire)
    
    async def _get_system_statistics(self) -> Dict[str, Any]:
        """Récupère les statistiques système"""
        # Implémentation stub
        return {
            'total_resources': 1250,
            'resources_delta': 45,
            'total_categories': 28,
            'categories_delta': 2,
            'total_clusters': 12,
            'clusters_delta': 1,
            'storage_size_mb': 2450.8,
            'storage_delta_mb': 125.3
        }
    
    async def _get_timeline_data(self) -> List[Dict[str, Any]]:
        """Récupère les données de timeline"""
        # Implémentation stub
        dates = pd.date_range(start='2024-01-01', end='2024-01-31', freq='D')
        return [
            {'date': date, 'count': np.random.randint(5, 50)}
            for date in dates
        ]
    
    async def _get_content_type_distribution(self) -> Dict[str, int]:
        """Récupère la distribution des types de contenu"""
        # Implémentation stub
        return {
            'Web Pages': 850,
            'PDFs': 200,
            'Images': 150,
            'Videos': 30,
            'Audio': 20
        }
    
    async def _check_database_status(self) -> bool:
        """Vérifie le statut de la base de données"""
        try:
            # Test simple de connexion
            await self.database_manager.get_statistics()
            return True
        except:
            return False
    
    async def _check_opensearch_status(self) -> bool:
        """Vérifie le statut d'OpenSearch"""
        if not self.opensearch_manager:
            return False
        try:
            stats = await self.opensearch_manager.get_index_stats()
            return bool(stats)
        except:
            return False
    
    async def _check_ml_status(self) -> bool:
        """Vérifie le statut du ML"""
        return self.ml_categorizer is not None and self.ml_categorizer.initialized
    
    async def _get_all_categories(self) -> List[str]:
        """Récupère toutes les catégories"""
        try:
            return await self.database_manager.get_all_categories()
        except:
            return []
    
    async def _perform_search(self, query: str, search_type: str, limit: int,
                            enable_clustering: bool, content_type_filter: List[str],
                            category_filter: List[str], date_range) -> Dict[str, Any]:
        """Effectue une recherche avec les paramètres donnés"""
        # Implémentation stub
        return {
            'resources': [],
            'clusters': [] if enable_clustering else None,
            'total': 0
        }

# Point d'entrée pour tests
if __name__ == "__main__":
    import asyncio
    
    async def main():
        from src.database.database import DatabaseManager
        
        db_manager = DatabaseManager("sqlite:///test.db")
        await db_manager.initialize()
        
        admin = AdminInterface(db_manager)
        await admin.start()
    
    asyncio.run(main())