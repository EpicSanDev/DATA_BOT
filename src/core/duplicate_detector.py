"""
Module de détection de doublons pour DATA_BOT v2
Utilise différentes techniques pour détecter les contenus dupliqués
"""

import hashlib
import logging
import os
import re
from typing import List, Dict, Set, Tuple, Optional
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from datetime import datetime

from src.core.models import WebResource, ArchiveStatus
from src.database.database import DatabaseManager
from src.core.config import Config

logger = logging.getLogger(__name__)

class DuplicateDetector:
    """Détecteur de doublons pour l'archive"""
    
    def __init__(self):
        self.url_hashes: Dict[str, str] = {}
        self.content_hashes: Dict[str, List[str]] = {}
        self.title_hashes: Dict[str, List[str]] = {}
        
    async def detect_duplicates(self) -> Dict[str, List[WebResource]]:
        """
        Détecte tous les doublons dans l'archive
        
        Returns:
            Dictionnaire avec les types de doublons et les ressources concernées
        """
        logger.info("🔍 Début de la détection de doublons")
        
        async with DatabaseManager() as db:
            resources = await db.get_all_resources(limit=100000)
        
        duplicates = {
            'url_duplicates': [],
            'content_duplicates': [],
            'title_duplicates': [],
            'similar_urls': []
        }
        
        # Détection des doublons d'URL
        duplicates['url_duplicates'] = await self._detect_url_duplicates(resources)
        
        # Détection des doublons de contenu
        duplicates['content_duplicates'] = await self._detect_content_duplicates(resources)
        
        # Détection des doublons de titre
        duplicates['title_duplicates'] = await self._detect_title_duplicates(resources)
        
        # Détection des URLs similaires
        duplicates['similar_urls'] = await self._detect_similar_urls(resources)
        
        total_duplicates = sum(len(group) for groups in duplicates.values() for group in groups)
        logger.info(f"✅ Détection terminée: {total_duplicates} groupes de doublons trouvés")
        
        return duplicates
    
    async def _detect_url_duplicates(self, resources: List[WebResource]) -> List[List[WebResource]]:
        """Détecte les doublons basés sur l'URL normalisée"""
        url_groups: Dict[str, List[WebResource]] = {}
        
        for resource in resources:
            normalized_url = self._normalize_url(resource.url)
            if normalized_url not in url_groups:
                url_groups[normalized_url] = []
            url_groups[normalized_url].append(resource)
        
        # Retourner seulement les groupes avec plus d'une ressource
        duplicates = [group for group in url_groups.values() if len(group) > 1]
        
        logger.info(f"URLs dupliquées: {len(duplicates)} groupes trouvés")
        return duplicates
    
    async def _detect_content_duplicates(self, resources: List[WebResource]) -> List[List[WebResource]]:
        """Détecte les doublons basés sur le hash du contenu"""
        content_groups: Dict[str, List[WebResource]] = {}
        
        for resource in resources:
            if resource.status in [ArchiveStatus.DOWNLOADED, ArchiveStatus.SCREENSHOT]:
                content_hash = await self._get_content_hash(resource)
                if content_hash:
                    if content_hash not in content_groups:
                        content_groups[content_hash] = []
                    content_groups[content_hash].append(resource)
        
        duplicates = [group for group in content_groups.values() if len(group) > 1]
        
        logger.info(f"Contenus dupliqués: {len(duplicates)} groupes trouvés")
        return duplicates
    
    async def _detect_title_duplicates(self, resources: List[WebResource]) -> List[List[WebResource]]:
        """Détecte les doublons basés sur le titre normalisé"""
        title_groups: Dict[str, List[WebResource]] = {}
        
        for resource in resources:
            if resource.title:
                normalized_title = self._normalize_title(resource.title)
                if len(normalized_title) > 10:  # Ignorer les titres trop courts
                    if normalized_title not in title_groups:
                        title_groups[normalized_title] = []
                    title_groups[normalized_title].append(resource)
        
        duplicates = [group for group in title_groups.values() if len(group) > 1]
        
        logger.info(f"Titres dupliqués: {len(duplicates)} groupes trouvés")
        return duplicates
    
    async def _detect_similar_urls(self, resources: List[WebResource]) -> List[List[WebResource]]:
        """Détecte les URLs similaires (même domaine + chemin similaire)"""
        domain_groups: Dict[str, List[WebResource]] = {}
        
        # Grouper par domaine
        for resource in resources:
            domain = self._extract_domain(resource.url)
            if domain not in domain_groups:
                domain_groups[domain] = []
            domain_groups[domain].append(resource)
        
        similar_groups = []
        
        # Pour chaque domaine, chercher les chemins similaires
        for domain, domain_resources in domain_groups.items():
            if len(domain_resources) > 1:
                path_groups = self._group_by_similar_paths(domain_resources)
                similar_groups.extend([group for group in path_groups if len(group) > 1])
        
        logger.info(f"URLs similaires: {len(similar_groups)} groupes trouvés")
        return similar_groups
    
    def _normalize_url(self, url: str) -> str:
        """Normalise une URL pour la comparaison"""
        parsed = urlparse(url.lower())
        
        # Supprimer www.
        netloc = parsed.netloc
        if netloc.startswith('www.'):
            netloc = netloc[4:]
        
        # Supprimer les paramètres de tracking courants
        query_params = parse_qs(parsed.query)
        tracking_params = {
            'utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term',
            'fbclid', 'gclid', '_ga', '_gid', 'ref', 'source'
        }
        
        clean_params = {k: v for k, v in query_params.items() 
                       if k.lower() not in tracking_params}
        
        # Reconstruire la query string
        query_string = '&'.join(f"{k}={'&'.join(v)}" for k, v in clean_params.items())
        
        # Supprimer le fragment
        clean_url = f"{parsed.scheme}://{netloc}{parsed.path}"
        if query_string:
            clean_url += f"?{query_string}"
        
        # Supprimer le slash final si pas de query string
        if clean_url.endswith('/') and '?' not in clean_url:
            clean_url = clean_url[:-1]
        
        return clean_url
    
    def _normalize_title(self, title: str) -> str:
        """Normalise un titre pour la comparaison"""
        # Supprimer les espaces en trop et normaliser
        normalized = re.sub(r'\s+', ' ', title.strip().lower())
        
        # Supprimer les suffixes courants
        suffixes = [
            ' - youtube', ' | youtube', ' - google', ' | google',
            ' - wikipedia', ' | wikipedia', ' - reddit', ' | reddit',
            ' - twitter', ' | twitter', ' - facebook', ' | facebook'
        ]
        
        for suffix in suffixes:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)]
        
        # Supprimer la ponctuation en fin
        normalized = re.sub(r'[.!?]+$', '', normalized)
        
        return normalized
    
    def _extract_domain(self, url: str) -> str:
        """Extrait le domaine d'une URL"""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    
    def _group_by_similar_paths(self, resources: List[WebResource]) -> List[List[WebResource]]:
        """Groupe les ressources par chemins similaires"""
        path_groups: Dict[str, List[WebResource]] = {}
        
        for resource in resources:
            parsed = urlparse(resource.url)
            path_key = self._get_path_similarity_key(parsed.path)
            
            if path_key not in path_groups:
                path_groups[path_key] = []
            path_groups[path_key].append(resource)
        
        return list(path_groups.values())
    
    def _get_path_similarity_key(self, path: str) -> str:
        """Génère une clé de similarité pour un chemin"""
        # Supprimer les extensions
        path_without_ext = re.sub(r'\.[^/]+$', '', path)
        
        # Supprimer les IDs numériques
        path_clean = re.sub(r'/\d+/', '/{id}/', path_without_ext)
        path_clean = re.sub(r'/\d+$', '/{id}', path_clean)
        
        # Supprimer les GUIDs/UUIDs
        path_clean = re.sub(r'/[a-f0-9-]{8,}/', '/{guid}/', path_clean)
        path_clean = re.sub(r'/[a-f0-9-]{8,}$', '/{guid}', path_clean)
        
        return path_clean
    
    async def _get_content_hash(self, resource: WebResource) -> Optional[str]:
        """Calcule le hash du contenu d'une ressource"""
        try:
            if resource.file_path and os.path.exists(resource.file_path):
                return await self._hash_file(resource.file_path)
            elif resource.screenshot_path and os.path.exists(resource.screenshot_path):
                return await self._hash_file(resource.screenshot_path)
            else:
                # Hash basé sur l'URL et le titre si pas de fichier
                content = f"{resource.url}|{resource.title or ''}"
                return hashlib.md5(content.encode('utf-8')).hexdigest()
        except Exception as e:
            logger.warning(f"Erreur calcul hash pour {resource.url}: {e}")
            return None
    
    async def _hash_file(self, file_path: str) -> str:
        """Calcule le hash MD5 d'un fichier"""
        hash_md5 = hashlib.md5()
        
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.warning(f"Erreur lecture fichier {file_path}: {e}")
            return ""
    
    async def remove_duplicates(self, duplicates: Dict[str, List[List[WebResource]]], 
                              strategy: str = "keep_first") -> int:
        """
        Supprime les doublons selon la stratégie choisie
        
        Args:
            duplicates: Dictionnaire des doublons détectés
            strategy: "keep_first", "keep_best", "keep_latest"
        
        Returns:
            Nombre de ressources supprimées
        """
        logger.info(f"🗑️ Suppression des doublons avec la stratégie: {strategy}")
        
        removed_count = 0
        
        async with DatabaseManager() as db:
            for duplicate_type, groups in duplicates.items():
                for group in groups:
                    if len(group) <= 1:
                        continue
                    
                    # Déterminer quelle ressource garder
                    to_keep = self._select_resource_to_keep(group, strategy)
                    to_remove = [r for r in group if r.url != to_keep.url]
                    
                    for resource in to_remove:
                        try:
                            # Supprimer les fichiers associés
                            if resource.file_path and os.path.exists(resource.file_path):
                                os.remove(resource.file_path)
                            if resource.screenshot_path and os.path.exists(resource.screenshot_path):
                                os.remove(resource.screenshot_path)
                            
                            # Supprimer de la base de données
                            await db.delete_resource_by_url(resource.url)
                            removed_count += 1
                            
                            logger.info(f"Doublón supprimé: {resource.url}")
                            
                        except Exception as e:
                            logger.error(f"Erreur suppression {resource.url}: {e}")
        
        logger.info(f"✅ Suppression terminée: {removed_count} doublons supprimés")
        return removed_count
    
    def _select_resource_to_keep(self, group: List[WebResource], strategy: str) -> WebResource:
        """Sélectionne la ressource à conserver dans un groupe de doublons"""
        if strategy == "keep_first":
            return min(group, key=lambda x: x.discovered_at or datetime.min)
        
        elif strategy == "keep_latest":
            return max(group, key=lambda x: x.discovered_at or datetime.min)
        
        elif strategy == "keep_best":
            # Prioriser: downloaded > screenshot > failed
            # Puis par taille de contenu
            def score(resource):
                status_score = {
                    ArchiveStatus.DOWNLOADED: 3,
                    ArchiveStatus.SCREENSHOT: 2,
                    ArchiveStatus.PENDING: 1,
                    ArchiveStatus.FAILED: 0
                }.get(resource.status, 0)
                
                size_score = resource.content_length or 0
                return (status_score, size_score)
            
            return max(group, key=score)
        
        else:
            return group[0]
    
    async def get_duplicate_stats(self) -> Dict[str, int]:
        """Retourne des statistiques sur les doublons"""
        duplicates = await self.detect_duplicates()
        
        stats = {
            'total_duplicate_groups': 0,
            'total_duplicate_resources': 0,
            'url_duplicates': 0,
            'content_duplicates': 0,
            'title_duplicates': 0,
            'similar_urls': 0
        }
        
        for duplicate_type, groups in duplicates.items():
            group_count = len(groups)
            resource_count = sum(len(group) for group in groups)
            
            stats['total_duplicate_groups'] += group_count
            stats['total_duplicate_resources'] += resource_count
            stats[duplicate_type] = group_count
        
        return stats
    
    async def mark_duplicates_in_database(self):
        """Marque les doublons dans la base de données avec des métadonnées"""
        duplicates = await self.detect_duplicates()
        
        async with DatabaseManager() as db:
            for duplicate_type, groups in duplicates.items():
                for i, group in enumerate(groups):
                    group_id = f"{duplicate_type}_{i}"
                    
                    for resource in group:
                        # Mettre à jour les métadonnées
                        if not resource.metadata:
                            resource.metadata = {}
                        
                        resource.metadata['duplicate_group'] = group_id
                        resource.metadata['duplicate_type'] = duplicate_type
                        resource.metadata['duplicate_count'] = len(group)
                        
                        await db.save_resource(resource)
        
        logger.info("✅ Doublons marqués dans la base de données")


class ContentHasher:
    """Utilitaires pour le hashage de contenu"""
    
    @staticmethod
    def hash_text_content(text: str) -> str:
        """Hash un contenu textuel"""
        # Normaliser le texte
        normalized = re.sub(r'\s+', ' ', text.strip().lower())
        # Supprimer la ponctuation
        normalized = re.sub(r'[^\w\s]', '', normalized)
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()
    
    @staticmethod
    def hash_image_content(image_path: str) -> Optional[str]:
        """Hash le contenu d'une image (pour les screenshots)"""
        try:
            with open(image_path, 'rb') as f:
                content = f.read()
            return hashlib.md5(content).hexdigest()
        except Exception:
            return None
    
    @staticmethod
    def fuzzy_text_similarity(text1: str, text2: str) -> float:
        """Calcule la similarité entre deux textes (méthode simple)"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)