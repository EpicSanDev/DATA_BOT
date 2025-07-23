"""
Module de compression intelligente pour DATA_BOT v2
Compression adaptative selon le type de contenu
"""

import os
import gzip
import zipfile
import logging
import mimetypes
from typing import Optional, Dict, List, Tuple
from pathlib import Path
from datetime import datetime

from src.core.models import WebResource, ContentType
from src.database.database import DatabaseManager
from src.core.config import Config

logger = logging.getLogger(__name__)

class CompressionManager:
    """Gestionnaire de compression intelligente"""
    
    def __init__(self):
        self.compression_stats = {
            'files_compressed': 0,
            'original_size': 0,
            'compressed_size': 0,
            'space_saved': 0
        }
        
        # Configuration de compression par type de fichier
        self.compression_config = {
            'text': {
                'algorithms': ['gzip', 'zip'],
                'min_size': 1024,  # 1KB minimum
                'compression_ratio_threshold': 0.8  # Compresser si on gagne au moins 20%
            },
            'html': {
                'algorithms': ['gzip'],
                'min_size': 2048,  # 2KB minimum
                'compression_ratio_threshold': 0.7
            },
            'json': {
                'algorithms': ['gzip'],
                'min_size': 1024,
                'compression_ratio_threshold': 0.6
            },
            'image': {
                'algorithms': [],  # Pas de compression pour les images déjà compressées
                'min_size': 0,
                'compression_ratio_threshold': 1.0
            }
        }
    
    async def compress_archive(self, force_recompress: bool = False) -> Dict[str, int]:
        """
        Compresse tous les fichiers de l'archive
        
        Args:
            force_recompress: Recompresser même les fichiers déjà compressés
        
        Returns:
            Statistiques de compression
        """
        logger.info("🗜️ Début de la compression intelligente de l'archive")
        
        async with DatabaseManager() as db:
            resources = await db.get_downloaded_resources()
        
        for resource in resources:
            if resource.file_path and os.path.exists(resource.file_path):
                await self._compress_resource_file(resource, force_recompress)
                await db.save_resource(resource)
        
        logger.info(f"✅ Compression terminée: {self.compression_stats}")
        return self.compression_stats
    
    async def _compress_resource_file(self, resource: WebResource, force: bool = False):
        """Compresse le fichier d'une ressource si bénéfique"""
        file_path = Path(resource.file_path)
        
        # Vérifier si déjà compressé
        if file_path.suffix in ['.gz', '.zip', '.bz2'] and not force:
            logger.debug(f"Fichier déjà compressé: {file_path}")
            return
        
        # Obtenir la taille originale
        original_size = file_path.stat().st_size
        self.compression_stats['original_size'] += original_size
        
        # Déterminer le type de contenu
        content_type = self._detect_content_type(file_path)
        config = self.compression_config.get(content_type, self.compression_config['text'])
        
        # Vérifier si la compression est pertinente
        if original_size < config['min_size']:
            logger.debug(f"Fichier trop petit pour compression: {file_path}")
            return
        
        # Tester différents algorithmes
        best_algorithm = None
        best_size = original_size
        best_path = None
        
        for algorithm in config['algorithms']:
            try:
                compressed_path = await self._compress_with_algorithm(
                    file_path, algorithm, test_only=True
                )
                
                if compressed_path and compressed_path.exists():
                    compressed_size = compressed_path.stat().st_size
                    compression_ratio = compressed_size / original_size
                    
                    if (compression_ratio < config['compression_ratio_threshold'] and 
                        compressed_size < best_size):
                        best_algorithm = algorithm
                        best_size = compressed_size
                        if best_path and best_path.exists():
                            best_path.unlink()  # Supprimer le précédent test
                        best_path = compressed_path
                    else:
                        compressed_path.unlink()  # Supprimer le fichier de test
                        
            except Exception as e:
                logger.warning(f"Erreur test compression {algorithm} pour {file_path}: {e}")
        
        # Appliquer la meilleure compression
        if best_algorithm and best_path:
            try:
                # Remplacer l'original par la version compressée
                backup_path = file_path.with_suffix(file_path.suffix + '.backup')
                file_path.rename(backup_path)
                
                final_compressed_path = await self._compress_with_algorithm(
                    backup_path, best_algorithm, test_only=False
                )
                
                if final_compressed_path and final_compressed_path.exists():
                    # Mettre à jour la ressource
                    resource.file_path = str(final_compressed_path)
                    resource.content_length = best_size
                    
                    if not resource.metadata:
                        resource.metadata = {}
                    resource.metadata['compressed'] = True
                    resource.metadata['compression_algorithm'] = best_algorithm
                    resource.metadata['original_size'] = original_size
                    resource.metadata['compressed_size'] = best_size
                    resource.metadata['compression_ratio'] = best_size / original_size
                    
                    # Supprimer le backup
                    backup_path.unlink()
                    
                    # Mettre à jour les stats
                    self.compression_stats['files_compressed'] += 1
                    self.compression_stats['compressed_size'] += best_size
                    self.compression_stats['space_saved'] += (original_size - best_size)
                    
                    logger.info(f"Compressé {file_path.name}: "
                              f"{original_size} → {best_size} bytes "
                              f"({(1-best_size/original_size)*100:.1f}% économie)")
                else:
                    # Restaurer l'original en cas d'échec
                    backup_path.rename(file_path)
                    
            except Exception as e:
                logger.error(f"Erreur compression finale {file_path}: {e}")
                # Restaurer l'original
                if backup_path.exists():
                    backup_path.rename(file_path)
        
        # Nettoyer les fichiers de test restants
        if best_path and best_path.exists():
            best_path.unlink()
    
    async def _compress_with_algorithm(self, file_path: Path, 
                                     algorithm: str, test_only: bool = False) -> Optional[Path]:
        """Compresse un fichier avec l'algorithme spécifié"""
        if algorithm == 'gzip':
            return await self._compress_gzip(file_path, test_only)
        elif algorithm == 'zip':
            return await self._compress_zip(file_path, test_only)
        else:
            raise ValueError(f"Algorithme de compression non supporté: {algorithm}")
    
    async def _compress_gzip(self, file_path: Path, test_only: bool = False) -> Optional[Path]:
        """Compression GZIP"""
        suffix = '.test.gz' if test_only else '.gz'
        compressed_path = file_path.with_suffix(file_path.suffix + suffix)
        
        try:
            with open(file_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb', compresslevel=9) as f_out:
                    f_out.write(f_in.read())
            
            return compressed_path
            
        except Exception as e:
            logger.error(f"Erreur compression GZIP {file_path}: {e}")
            if compressed_path.exists():
                compressed_path.unlink()
            return None
    
    async def _compress_zip(self, file_path: Path, test_only: bool = False) -> Optional[Path]:
        """Compression ZIP"""
        suffix = '.test.zip' if test_only else '.zip'
        compressed_path = file_path.with_suffix(file_path.suffix + suffix)
        
        try:
            with zipfile.ZipFile(compressed_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
                zipf.write(file_path, file_path.name)
            
            return compressed_path
            
        except Exception as e:
            logger.error(f"Erreur compression ZIP {file_path}: {e}")
            if compressed_path.exists():
                compressed_path.unlink()
            return None
    
    def _detect_content_type(self, file_path: Path) -> str:
        """Détecte le type de contenu d'un fichier"""
        # Basé sur l'extension
        suffix = file_path.suffix.lower()
        
        if suffix in ['.html', '.htm', '.xhtml']:
            return 'html'
        elif suffix in ['.json', '.jsonl']:
            return 'json'
        elif suffix in ['.txt', '.md', '.csv', '.xml', '.css', '.js']:
            return 'text'
        elif suffix in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
            return 'image'
        else:
            # Utiliser mimetypes pour deviner
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if mime_type:
                if mime_type.startswith('text/'):
                    return 'text'
                elif mime_type.startswith('image/'):
                    return 'image'
                elif mime_type == 'application/json':
                    return 'json'
        
        return 'text'  # Par défaut
    
    async def decompress_resource(self, resource: WebResource) -> bool:
        """Décompresse un fichier de ressource"""
        if not resource.file_path or not os.path.exists(resource.file_path):
            return False
        
        file_path = Path(resource.file_path)
        
        try:
            if file_path.suffix == '.gz':
                return await self._decompress_gzip(resource, file_path)
            elif file_path.suffix == '.zip':
                return await self._decompress_zip(resource, file_path)
            else:
                logger.warning(f"Format de compression non supporté: {file_path.suffix}")
                return False
                
        except Exception as e:
            logger.error(f"Erreur décompression {file_path}: {e}")
            return False
    
    async def _decompress_gzip(self, resource: WebResource, file_path: Path) -> bool:
        """Décompression GZIP"""
        original_path = file_path.with_suffix('')  # Supprimer .gz
        
        try:
            with gzip.open(file_path, 'rb') as f_in:
                with open(original_path, 'wb') as f_out:
                    f_out.write(f_in.read())
            
            # Mettre à jour la ressource
            resource.file_path = str(original_path)
            resource.content_length = original_path.stat().st_size
            
            if resource.metadata:
                resource.metadata.pop('compressed', None)
                resource.metadata.pop('compression_algorithm', None)
            
            # Supprimer le fichier compressé
            file_path.unlink()
            
            logger.info(f"Décompressé: {file_path} → {original_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur décompression GZIP {file_path}: {e}")
            if original_path.exists():
                original_path.unlink()
            return False
    
    async def _decompress_zip(self, resource: WebResource, file_path: Path) -> bool:
        """Décompression ZIP"""
        try:
            with zipfile.ZipFile(file_path, 'r') as zipf:
                # Supposer qu'il n'y a qu'un fichier dans l'archive
                names = zipf.namelist()
                if len(names) != 1:
                    logger.error(f"Archive ZIP contient {len(names)} fichiers, attendu 1")
                    return False
                
                original_name = names[0]
                original_path = file_path.parent / original_name
                
                zipf.extract(original_name, file_path.parent)
                
                # Mettre à jour la ressource
                resource.file_path = str(original_path)
                resource.content_length = original_path.stat().st_size
                
                if resource.metadata:
                    resource.metadata.pop('compressed', None)
                    resource.metadata.pop('compression_algorithm', None)
                
                # Supprimer le fichier compressé
                file_path.unlink()
                
                logger.info(f"Décompressé: {file_path} → {original_path}")
                return True
                
        except Exception as e:
            logger.error(f"Erreur décompression ZIP {file_path}: {e}")
            return False
    
    async def get_compression_stats(self) -> Dict[str, any]:
        """Retourne les statistiques de compression"""
        async with DatabaseManager() as db:
            resources = await db.get_all_resources()
        
        stats = {
            'total_files': 0,
            'compressed_files': 0,
            'total_original_size': 0,
            'total_compressed_size': 0,
            'total_space_saved': 0,
            'compression_ratio': 0.0,
            'algorithms_used': {}
        }
        
        for resource in resources:
            if resource.file_path and os.path.exists(resource.file_path):
                stats['total_files'] += 1
                
                if resource.metadata and resource.metadata.get('compressed'):
                    stats['compressed_files'] += 1
                    
                    original_size = resource.metadata.get('original_size', 0)
                    compressed_size = resource.content_length or 0
                    algorithm = resource.metadata.get('compression_algorithm', 'unknown')
                    
                    stats['total_original_size'] += original_size
                    stats['total_compressed_size'] += compressed_size
                    stats['total_space_saved'] += (original_size - compressed_size)
                    
                    if algorithm not in stats['algorithms_used']:
                        stats['algorithms_used'][algorithm] = 0
                    stats['algorithms_used'][algorithm] += 1
                else:
                    file_size = resource.content_length or 0
                    stats['total_original_size'] += file_size
                    stats['total_compressed_size'] += file_size
        
        if stats['total_original_size'] > 0:
            stats['compression_ratio'] = stats['total_compressed_size'] / stats['total_original_size']
        
        return stats
    
    async def auto_compress_new_files(self):
        """Compresse automatiquement les nouveaux fichiers"""
        logger.info("🔄 Compression automatique des nouveaux fichiers")
        
        async with DatabaseManager() as db:
            # Récupérer les ressources téléchargées récemment et non compressées
            resources = await db.get_resources_by_status('downloaded', limit=100)
            
            new_files = []
            for resource in resources:
                if (resource.file_path and os.path.exists(resource.file_path) and
                    not (resource.metadata and resource.metadata.get('compressed'))):
                    new_files.append(resource)
        
        if new_files:
            logger.info(f"Compression de {len(new_files)} nouveaux fichiers")
            
            for resource in new_files:
                await self._compress_resource_file(resource)
                await db.save_resource(resource)
        
        return len(new_files)
    
    async def cleanup_compression_artifacts(self):
        """Nettoie les artefacts de compression (fichiers .test.*, .backup, etc.)"""
        logger.info("🧹 Nettoyage des artefacts de compression")
        
        archive_path = Path(Config.ARCHIVE_PATH)
        artifacts_removed = 0
        
        for pattern in ['*.test.gz', '*.test.zip', '*.backup']:
            for artifact in archive_path.rglob(pattern):
                try:
                    artifact.unlink()
                    artifacts_removed += 1
                    logger.debug(f"Artefact supprimé: {artifact}")
                except Exception as e:
                    logger.warning(f"Impossible de supprimer {artifact}: {e}")
        
        logger.info(f"✅ {artifacts_removed} artefacts supprimés")
        return artifacts_removed
    
    def get_compression_recommendations(self, resources: List[WebResource]) -> List[Dict]:
        """Génère des recommandations de compression"""
        recommendations = []
        
        for resource in resources:
            if not resource.file_path or not os.path.exists(resource.file_path):
                continue
            
            file_path = Path(resource.file_path)
            file_size = file_path.stat().st_size
            
            # Ignorer si déjà compressé
            if resource.metadata and resource.metadata.get('compressed'):
                continue
            
            content_type = self._detect_content_type(file_path)
            config = self.compression_config.get(content_type, self.compression_config['text'])
            
            if file_size >= config['min_size'] and config['algorithms']:
                potential_savings = file_size * (1 - config['compression_ratio_threshold'])
                
                recommendations.append({
                    'url': resource.url,
                    'file_path': str(file_path),
                    'current_size': file_size,
                    'content_type': content_type,
                    'potential_savings': potential_savings,
                    'recommended_algorithms': config['algorithms']
                })
        
        # Trier par économie potentielle
        recommendations.sort(key=lambda x: x['potential_savings'], reverse=True)
        
        return recommendations