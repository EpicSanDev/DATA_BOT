"""
ML Categorizer pour DATA_BOT v4
Catégorisation automatique du contenu utilisant l'apprentissage automatique
"""

import asyncio
import logging
import json
import pickle
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
import os

try:
    import numpy as np
    import pandas as pd
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.naive_bayes import MultinomialNB
    from sklearn.multiclass import OneVsRestClassifier
    from sklearn.preprocessing import MultiLabelBinarizer
    from sklearn.metrics import classification_report
    from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
    import joblib
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

from src.core.models import WebResource, ContentType
from src.database.database import DatabaseManager

logger = logging.getLogger(__name__)

class MLCategorizer:
    """Catégoriseur ML pour la classification automatique du contenu"""
    
    def __init__(self, model_dir: str = "data/ml_models"):
        """
        Initialise le catégoriseur ML
        
        Args:
            model_dir: Répertoire pour stocker les modèles
        """
        if not ML_AVAILABLE:
            raise ImportError("Les dépendances ML ne sont pas installées")
        
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(exist_ok=True, parents=True)
        
        # Modèles et transformateurs
        self.tfidf_vectorizer = None
        self.nb_classifier = None
        self.label_binarizer = None
        self.transformer_pipeline = None
        
        # Configuration
        self.config = {
            'max_features': 10000,
            'ngram_range': (1, 2),
            'min_df': 2,
            'max_df': 0.95,
            'transformer_model': 'distilbert-base-uncased',
            'confidence_threshold': 0.3,
            'max_categories_per_resource': 5
        }
        
        # Catégories prédéfinies
        self.predefined_categories = [
            'Technology', 'Science', 'Business', 'Politics', 'Entertainment',
            'Sports', 'Health', 'Education', 'Travel', 'Food', 'Fashion',
            'Art', 'Music', 'Movies', 'Books', 'Gaming', 'Programming',
            'AI/ML', 'Cybersecurity', 'Finance', 'Marketing', 'Social Media',
            'Environment', 'Climate', 'History', 'Philosophy', 'Psychology',
            'Medicine', 'Research', 'Innovation', 'Startups', 'Industry',
            'News', 'Opinion', 'Tutorial', 'Review', 'Guide', 'Documentation'
        ]
        
        self.initialized = False
    
    async def initialize(self):
        """Initialise le catégoriseur ML"""
        try:
            logger.info("Initialisation du ML Categorizer...")
            
            # Charger les modèles existants ou les créer
            await self._load_or_create_models()
            
            # Initialiser le pipeline Transformer
            await self._initialize_transformer_pipeline()
            
            self.initialized = True
            logger.info("ML Categorizer initialisé avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du ML Categorizer: {e}")
            raise
    
    async def _load_or_create_models(self):
        """Charge les modèles existants ou les crée"""
        vectorizer_path = self.model_dir / "tfidf_vectorizer.pkl"
        classifier_path = self.model_dir / "nb_classifier.pkl"
        binarizer_path = self.model_dir / "label_binarizer.pkl"
        
        if (vectorizer_path.exists() and 
            classifier_path.exists() and 
            binarizer_path.exists()):
            
            logger.info("Chargement des modèles existants...")
            
            self.tfidf_vectorizer = joblib.load(vectorizer_path)
            self.nb_classifier = joblib.load(classifier_path)
            self.label_binarizer = joblib.load(binarizer_path)
            
            logger.info("Modèles chargés avec succès")
        else:
            logger.info("Création de nouveaux modèles...")
            await self._create_default_models()
    
    async def _create_default_models(self):
        """Crée des modèles par défaut"""
        # Créer le vectoriseur TF-IDF
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=self.config['max_features'],
            ngram_range=self.config['ngram_range'],
            min_df=self.config['min_df'],
            max_df=self.config['max_df'],
            stop_words='english'
        )
        
        # Créer le classificateur
        self.nb_classifier = OneVsRestClassifier(MultinomialNB())
        
        # Créer le binariseur de labels
        self.label_binarizer = MultiLabelBinarizer()
        
        # Ajuster avec les catégories prédéfinies
        self.label_binarizer.fit([self.predefined_categories])
        
        logger.info("Modèles par défaut créés")
    
    async def _initialize_transformer_pipeline(self):
        """Initialise le pipeline Transformer pour classification"""
        try:
            self.transformer_pipeline = pipeline(
                "zero-shot-classification",
                model=self.config['transformer_model'],
                device=-1  # CPU
            )
            logger.info("Pipeline Transformer initialisé")
            
        except Exception as e:
            logger.warning(f"Impossible d'initialiser le pipeline Transformer: {e}")
            self.transformer_pipeline = None
    
    async def categorize_resource(self, resource: WebResource) -> List[str]:
        """
        Catégorise une ressource
        
        Args:
            resource: Ressource à catégoriser
            
        Returns:
            Liste des catégories prédites
        """
        if not self.initialized:
            await self.initialize()
        
        try:
            # Préparer le texte pour classification
            text = await self._prepare_text(resource)
            
            if not text.strip():
                return []
            
            # Classification avec différentes méthodes
            categories = []
            
            # 1. Classification avec TF-IDF + Naive Bayes (si modèle entraîné)
            if hasattr(self.nb_classifier, 'classes_'):
                nb_categories = await self._classify_with_naive_bayes(text)
                categories.extend(nb_categories)
            
            # 2. Classification avec Transformer (zero-shot)
            if self.transformer_pipeline:
                transformer_categories = await self._classify_with_transformer(text)
                categories.extend(transformer_categories)
            
            # 3. Classification basée sur des règles
            rule_categories = await self._classify_with_rules(resource)
            categories.extend(rule_categories)
            
            # Fusionner et nettoyer les catégories
            final_categories = await self._merge_and_rank_categories(categories)
            
            logger.debug(f"Catégories prédites pour {resource.url}: {final_categories}")
            
            return final_categories[:self.config['max_categories_per_resource']]
            
        except Exception as e:
            logger.error(f"Erreur lors de la catégorisation de {resource.url}: {e}")
            return []
    
    async def _prepare_text(self, resource: WebResource) -> str:
        """Prépare le texte pour classification"""
        texts = []
        
        # Titre (pondéré plus)
        if resource.title:
            texts.extend([resource.title] * 3)
        
        # Contenu
        if resource.content:
            # Prendre les premiers 1000 caractères pour éviter la surcharge
            content = resource.content[:1000]
            texts.append(content)
        
        # URL (pour les indices)
        if resource.url:
            texts.append(resource.url.replace('/', ' ').replace('-', ' ').replace('_', ' '))
        
        return ' '.join(texts)
    
    async def _classify_with_naive_bayes(self, text: str) -> List[Tuple[str, float]]:
        """Classification avec Naive Bayes"""
        try:
            # Vectoriser le texte
            text_vector = self.tfidf_vectorizer.transform([text])
            
            # Prédire les probabilités
            probabilities = self.nb_classifier.predict_proba(text_vector)[0]
            
            # Récupérer les catégories avec leurs scores
            categories_with_scores = []
            for i, prob in enumerate(probabilities):
                if prob > self.config['confidence_threshold']:
                    category = self.label_binarizer.classes_[i]
                    categories_with_scores.append((category, prob))
            
            return categories_with_scores
            
        except Exception as e:
            logger.error(f"Erreur Naive Bayes: {e}")
            return []
    
    async def _classify_with_transformer(self, text: str) -> List[Tuple[str, float]]:
        """Classification avec Transformer (zero-shot)"""
        try:
            if not self.transformer_pipeline:
                return []
            
            # Classification zero-shot
            result = self.transformer_pipeline(text, self.predefined_categories)
            
            # Extraire les résultats avec scores
            categories_with_scores = []
            for label, score in zip(result['labels'], result['scores']):
                if score > self.config['confidence_threshold']:
                    categories_with_scores.append((label, score))
            
            return categories_with_scores
            
        except Exception as e:
            logger.error(f"Erreur Transformer: {e}")
            return []
    
    async def _classify_with_rules(self, resource: WebResource) -> List[Tuple[str, float]]:
        """Classification basée sur des règles"""
        categories_with_scores = []
        
        # Règles basées sur l'URL
        url_lower = resource.url.lower()
        
        # Domaines spécialisés
        domain_rules = {
            'github.com': ('Programming', 0.9),
            'stackoverflow.com': ('Programming', 0.8),
            'arxiv.org': ('Research', 0.9),
            'wikipedia.org': ('Education', 0.7),
            'youtube.com': ('Entertainment', 0.6),
            'netflix.com': ('Movies', 0.8),
            'spotify.com': ('Music', 0.8),
            'amazon.com': ('Business', 0.6),
            'linkedin.com': ('Business', 0.7),
            'twitter.com': ('Social Media', 0.7),
            'facebook.com': ('Social Media', 0.7),
            'instagram.com': ('Social Media', 0.7),
            'reddit.com': ('Social Media', 0.6)
        }
        
        for domain, (category, score) in domain_rules.items():
            if domain in url_lower:
                categories_with_scores.append((category, score))
        
        # Règles basées sur les mots-clés dans l'URL
        keyword_rules = {
            'api': ('Programming', 0.6),
            'doc': ('Documentation', 0.7),
            'tutorial': ('Tutorial', 0.8),
            'guide': ('Guide', 0.8),
            'review': ('Review', 0.7),
            'news': ('News', 0.7),
            'blog': ('Opinion', 0.6),
            'tech': ('Technology', 0.7),
            'ai': ('AI/ML', 0.8),
            'ml': ('AI/ML', 0.8),
            'security': ('Cybersecurity', 0.7),
            'crypto': ('Finance', 0.7),
            'health': ('Health', 0.7),
            'sport': ('Sports', 0.7),
            'game': ('Gaming', 0.7),
            'music': ('Music', 0.7),
            'movie': ('Movies', 0.7),
            'book': ('Books', 0.7)
        }
        
        for keyword, (category, score) in keyword_rules.items():
            if keyword in url_lower:
                categories_with_scores.append((category, score))
        
        # Règles basées sur le type de contenu
        if resource.content_type:
            content_type_rules = {
                ContentType.PDF: ('Documentation', 0.6),
                ContentType.IMAGE: ('Art', 0.5),
                ContentType.VIDEO: ('Entertainment', 0.6),
                ContentType.AUDIO: ('Music', 0.7)
            }
            
            if resource.content_type in content_type_rules:
                category, score = content_type_rules[resource.content_type]
                categories_with_scores.append((category, score))
        
        return categories_with_scores
    
    async def _merge_and_rank_categories(self, 
                                       categories_list: List[List[Tuple[str, float]]]) -> List[str]:
        """Fusionne et classe les catégories par score"""
        # Fusionner toutes les catégories avec leurs scores
        category_scores = {}
        
        for categories in categories_list:
            for category, score in categories:
                if category in category_scores:
                    # Moyenne pondérée des scores
                    category_scores[category] = (category_scores[category] + score) / 2
                else:
                    category_scores[category] = score
        
        # Trier par score décroissant
        sorted_categories = sorted(
            category_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Retourner seulement les noms des catégories
        return [category for category, score in sorted_categories 
                if score > self.config['confidence_threshold']]
    
    async def train_model(self, training_data: List[Dict[str, Any]]):
        """
        Entraîne le modèle avec des données d'entraînement
        
        Args:
            training_data: Liste de dictionnaires avec 'text' et 'categories'
        """
        if not self.initialized:
            await self.initialize()
        
        logger.info(f"Entraînement du modèle avec {len(training_data)} exemples...")
        
        try:
            # Préparer les données
            texts = [item['text'] for item in training_data]
            categories_lists = [item['categories'] for item in training_data]
            
            # Vectoriser les textes
            X = self.tfidf_vectorizer.fit_transform(texts)
            
            # Binariser les labels
            y = self.label_binarizer.fit_transform(categories_lists)
            
            # Entraîner le classificateur
            self.nb_classifier.fit(X, y)
            
            # Sauvegarder les modèles
            await self._save_models()
            
            logger.info("Modèle entraîné et sauvegardé avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'entraînement: {e}")
            raise
    
    async def _save_models(self):
        """Sauvegarde les modèles entraînés"""
        try:
            joblib.dump(self.tfidf_vectorizer, self.model_dir / "tfidf_vectorizer.pkl")
            joblib.dump(self.nb_classifier, self.model_dir / "nb_classifier.pkl")
            joblib.dump(self.label_binarizer, self.model_dir / "label_binarizer.pkl")
            
            logger.info("Modèles sauvegardés")
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde: {e}")
            raise
    
    async def evaluate_model(self, test_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Évalue les performances du modèle
        
        Args:
            test_data: Données de test
            
        Returns:
            Métriques de performance
        """
        if not hasattr(self.nb_classifier, 'classes_'):
            logger.error("Modèle non entraîné")
            return {}
        
        try:
            # Préparer les données de test
            texts = [item['text'] for item in test_data]
            true_categories = [item['categories'] for item in test_data]
            
            # Prédictions
            X_test = self.tfidf_vectorizer.transform(texts)
            y_true = self.label_binarizer.transform(true_categories)
            y_pred = self.nb_classifier.predict(X_test)
            
            # Générer le rapport de classification
            report = classification_report(
                y_true, y_pred,
                target_names=self.label_binarizer.classes_,
                output_dict=True,
                zero_division=0
            )
            
            return report
            
        except Exception as e:
            logger.error(f"Erreur lors de l'évaluation: {e}")
            return {}
    
    async def get_category_statistics(self, database_manager: DatabaseManager) -> Dict[str, Any]:
        """Retourne les statistiques des catégories"""
        try:
            # Récupérer toutes les ressources avec catégories
            resources = await database_manager.get_all_resources()
            
            # Compter les catégories
            category_counts = {}
            total_resources = 0
            categorized_resources = 0
            
            for resource in resources:
                total_resources += 1
                if resource.categories:
                    categorized_resources += 1
                    for category in resource.categories:
                        category_counts[category] = category_counts.get(category, 0) + 1
            
            # Statistiques
            stats = {
                'total_resources': total_resources,
                'categorized_resources': categorized_resources,
                'categorization_rate': categorized_resources / total_resources if total_resources > 0 else 0,
                'total_categories': len(category_counts),
                'category_distribution': dict(sorted(
                    category_counts.items(),
                    key=lambda x: x[1],
                    reverse=True
                )),
                'top_categories': list(sorted(
                    category_counts.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:10])
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Erreur lors du calcul des statistiques: {e}")
            return {}
    
    async def auto_categorize_uncategorized(self, database_manager: DatabaseManager,
                                          batch_size: int = 100) -> Dict[str, int]:
        """
        Catégorise automatiquement toutes les ressources non catégorisées
        
        Args:
            database_manager: Gestionnaire de base de données
            batch_size: Taille des lots pour le traitement
            
        Returns:
            Statistiques de catégorisation
        """
        logger.info("Début de la catégorisation automatique...")
        
        stats = {'processed': 0, 'categorized': 0, 'errors': 0}
        
        try:
            # Récupérer les ressources non catégorisées
            uncategorized = await database_manager.get_uncategorized_resources()
            total = len(uncategorized)
            
            logger.info(f"{total} ressources à catégoriser")
            
            # Traiter par lots
            for i in range(0, total, batch_size):
                batch = uncategorized[i:i + batch_size]
                
                for resource in batch:
                    try:
                        categories = await self.categorize_resource(resource)
                        
                        if categories:
                            await database_manager.update_resource_categories(
                                resource.id, categories
                            )
                            stats['categorized'] += 1
                        
                        stats['processed'] += 1
                        
                    except Exception as e:
                        logger.error(f"Erreur pour {resource.url}: {e}")
                        stats['errors'] += 1
                
                # Log du progrès
                progress = (i + len(batch)) / total * 100
                logger.info(f"Progression: {progress:.1f}% ({stats['processed']}/{total})")
            
            logger.info(f"Catégorisation terminée: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Erreur lors de la catégorisation automatique: {e}")
            return stats