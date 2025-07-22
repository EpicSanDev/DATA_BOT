import sqlite3
import asyncio
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from src.models import WebResource, ArchiveStatus, ContentType, ArchiveStats
from src.config import Config

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DATABASE_PATH
        self.connection = None
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            self.connection.close()
    
    async def connect(self):
        """Établit la connexion à la base de données"""
        # Créer le répertoire si nécessaire
        import os
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row  # Pour accéder aux colonnes par nom
        await self.create_tables()
    
    async def create_tables(self):
        """Crée les tables de la base de données"""
        cursor = self.connection.cursor()
        
        # Table des ressources web
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS web_resources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                title TEXT,
                content_type TEXT,
                file_path TEXT,
                screenshot_path TEXT,
                content_length INTEGER,
                status TEXT,
                discovered_at TIMESTAMP,
                archived_at TIMESTAMP,
                parent_url TEXT,
                depth INTEGER DEFAULT 0,
                tags TEXT,  -- JSON array
                metadata TEXT,  -- JSON object
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table des requêtes de recherche
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS search_queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                category TEXT,
                priority INTEGER DEFAULT 1,
                generated_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                executed_at TIMESTAMP,
                results_count INTEGER DEFAULT 0
            )
        ''')
        
        # Table des domaines découverts
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS domains (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT UNIQUE NOT NULL,
                first_discovered TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_visited TIMESTAMP,
                total_pages INTEGER DEFAULT 0,
                total_size_bytes INTEGER DEFAULT 0,
                success_rate REAL DEFAULT 0.0,
                robots_txt TEXT,
                is_blocked BOOLEAN DEFAULT FALSE
            )
        ''')
        
        # Table des statistiques
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS archive_stats (
                id INTEGER PRIMARY KEY,
                total_discovered INTEGER DEFAULT 0,
                total_downloaded INTEGER DEFAULT 0,
                total_screenshots INTEGER DEFAULT 0,
                total_failed INTEGER DEFAULT 0,
                total_size_mb REAL DEFAULT 0.0,
                domains_discovered INTEGER DEFAULT 0,
                start_time TIMESTAMP,
                last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Index pour les recherches
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_url ON web_resources(url)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON web_resources(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_domain ON web_resources(url)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_content_type ON web_resources(content_type)')
        
        self.connection.commit()
        logger.info("Tables de base de données créées/vérifiées")
    
    async def save_resource(self, resource: WebResource) -> int:
        """Sauvegarde ou met à jour une ressource web"""
        cursor = self.connection.cursor()
        
        import json
        tags_json = json.dumps(resource.tags) if resource.tags else '[]'
        metadata_json = json.dumps(resource.metadata) if resource.metadata else '{}'
        
        try:
            # Essayer d'insérer
            cursor.execute('''
                INSERT INTO web_resources 
                (url, title, content_type, file_path, screenshot_path, content_length, 
                 status, discovered_at, archived_at, parent_url, depth, tags, metadata, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                resource.url,
                resource.title,
                resource.content_type.value if resource.content_type else None,
                resource.file_path,
                resource.screenshot_path,
                resource.content_length,
                resource.status.value if resource.status else None,
                resource.discovered_at,
                resource.archived_at,
                resource.parent_url,
                resource.depth,
                tags_json,
                metadata_json,
                resource.error_message
            ))
            resource_id = cursor.lastrowid
            
        except sqlite3.IntegrityError:
            # URL existe déjà, mettre à jour
            cursor.execute('''
                UPDATE web_resources SET
                    title = ?, content_type = ?, file_path = ?, screenshot_path = ?,
                    content_length = ?, status = ?, archived_at = ?, tags = ?,
                    metadata = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP
                WHERE url = ?
            ''', (
                resource.title,
                resource.content_type.value if resource.content_type else None,
                resource.file_path,
                resource.screenshot_path,
                resource.content_length,
                resource.status.value if resource.status else None,
                resource.archived_at,
                tags_json,
                metadata_json,
                resource.error_message,
                resource.url
            ))
            
            # Récupérer l'ID existant
            cursor.execute('SELECT id FROM web_resources WHERE url = ?', (resource.url,))
            resource_id = cursor.fetchone()[0]
        
        self.connection.commit()
        return resource_id
    
    async def get_resource_by_url(self, url: str) -> Optional[WebResource]:
        """Récupère une ressource par son URL"""
        cursor = self.connection.cursor()
        cursor.execute('SELECT * FROM web_resources WHERE url = ?', (url,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        return self._row_to_resource(row)
    
    async def get_pending_resources(self, limit: int = 100) -> List[WebResource]:
        """Récupère les ressources en attente de traitement"""
        cursor = self.connection.cursor()
        cursor.execute('''
            SELECT * FROM web_resources 
            WHERE status = ? 
            ORDER BY discovered_at ASC
            LIMIT ?
        ''', (ArchiveStatus.PENDING.value, limit))
        
        return [self._row_to_resource(row) for row in cursor.fetchall()]
    
    async def get_resources_by_status(self, status: ArchiveStatus, limit: int = 100, offset: int = 0) -> List[WebResource]:
        """Récupère les ressources par statut"""
        cursor = self.connection.cursor()
        cursor.execute('''
            SELECT * FROM web_resources 
            WHERE status = ? 
            ORDER BY discovered_at DESC
            LIMIT ? OFFSET ?
        ''', (status.value, limit, offset))
        
        return [self._row_to_resource(row) for row in cursor.fetchall()]
    
    async def get_all_resources(self, limit: int = 1000, offset: int = 0) -> List[WebResource]:
        """Récupère toutes les ressources avec pagination"""
        cursor = self.connection.cursor()
        cursor.execute('''
            SELECT * FROM web_resources 
            ORDER BY discovered_at DESC
            LIMIT ? OFFSET ?
        ''', (limit, offset))
        
        return [self._row_to_resource(row) for row in cursor.fetchall()]
    
    async def get_resource_by_id(self, resource_id: int) -> Optional[WebResource]:
        """Récupère une ressource par son ID"""
        cursor = self.connection.cursor()
        cursor.execute('SELECT * FROM web_resources WHERE id = ?', (resource_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        return self._row_to_resource(row)
    
    async def delete_resource(self, resource_id: int) -> bool:
        """Supprime une ressource par ID"""
        cursor = self.connection.cursor()
        cursor.execute('DELETE FROM web_resources WHERE id = ?', (resource_id,))
        self.connection.commit()
        return cursor.rowcount > 0
    
    async def delete_resource_by_url(self, url: str) -> bool:
        """Supprime une ressource par URL"""
        cursor = self.connection.cursor()
        cursor.execute('DELETE FROM web_resources WHERE url = ?', (url,))
        self.connection.commit()
        return cursor.rowcount > 0
    
    async def search_resources(self, query: str, limit: int = 100) -> List[WebResource]:
        """Recherche dans les ressources"""
        cursor = self.connection.cursor()
        search_pattern = f"%{query}%"
        cursor.execute('''
            SELECT * FROM web_resources 
            WHERE title LIKE ? OR url LIKE ? OR metadata LIKE ?
            ORDER BY discovered_at DESC
            LIMIT ?
        ''', (search_pattern, search_pattern, search_pattern, limit))
        
        return [self._row_to_resource(row) for row in cursor.fetchall()]
    
    async def get_downloaded_resources(self, limit: int = 1000) -> List[WebResource]:
        """Récupère les ressources téléchargées"""
        return await self.get_resources_by_status(ArchiveStatus.DOWNLOADED, limit)
    
    async def mark_url_as_discovered(self, url: str, parent_url: str = None, depth: int = 0):
        """Marque une URL comme découverte"""
        resource = WebResource(
            url=url,
            parent_url=parent_url,
            depth=depth,
            status=ArchiveStatus.PENDING
        )
        await self.save_resource(resource)
    
    def _row_to_resource(self, row) -> WebResource:
        """Convertit une ligne de base de données en WebResource"""
        import json
        from datetime import datetime
        
        # Parse les champs JSON
        tags = json.loads(row['tags']) if row['tags'] else []
        metadata = json.loads(row['metadata']) if row['metadata'] else {}
        
        # Parse les dates
        discovered_at = datetime.fromisoformat(row['discovered_at']) if row['discovered_at'] else None
        archived_at = datetime.fromisoformat(row['archived_at']) if row['archived_at'] else None
        
        # Parse les enums
        content_type = ContentType(row['content_type']) if row['content_type'] else ContentType.UNKNOWN
        status = ArchiveStatus(row['status']) if row['status'] else ArchiveStatus.PENDING
        
        return WebResource(
            url=row['url'],
            title=row['title'],
            content_type=content_type,
            file_path=row['file_path'],
            screenshot_path=row['screenshot_path'],
            content_length=row['content_length'],
            status=status,
            discovered_at=discovered_at,
            archived_at=archived_at,
            parent_url=row['parent_url'],
            depth=row['depth'] or 0,
            tags=tags,
            metadata=metadata,
            error_message=row['error_message']
        )
    
    async def search_resources_old(self, query: str, content_type: ContentType = None) -> List[WebResource]:
        """Recherche des ressources par contenu"""
        cursor = self.connection.cursor()
        
        sql = '''
            SELECT * FROM web_resources 
            WHERE (title LIKE ? OR url LIKE ? OR metadata LIKE ?)
        '''
        params = [f'%{query}%', f'%{query}%', f'%{query}%']
        
        if content_type:
            sql += ' AND content_type = ?'
            params.append(content_type.value)
        
        sql += ' ORDER BY discovered_at DESC LIMIT 100'
        
        cursor.execute(sql, params)
        return [self._row_to_resource(row) for row in cursor.fetchall()]
    
    async def get_domain_stats(self, domain: str) -> Dict[str, Any]:
        """Récupère les statistiques d'un domaine"""
        cursor = self.connection.cursor()
        cursor.execute('''
            SELECT 
                COUNT(*) as total_pages,
                SUM(content_length) as total_size,
                COUNT(CASE WHEN status = 'downloaded' THEN 1 END) as downloaded,
                COUNT(CASE WHEN status = 'screenshot' THEN 1 END) as screenshots,
                COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed
            FROM web_resources 
            WHERE url LIKE ?
        ''', (f'%{domain}%',))
        
        row = cursor.fetchone()
        return {
            'total_pages': row[0],
            'total_size': row[1] or 0,
            'downloaded': row[2],
            'screenshots': row[3],
            'failed': row[4],
            'success_rate': (row[2] + row[3]) / max(row[0], 1) * 100
        }
    
    async def get_archive_stats(self) -> ArchiveStats:
        """Récupère les statistiques globales de l'archive"""
        cursor = self.connection.cursor()
        
        # Statistiques des ressources
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN status = 'downloaded' THEN 1 END) as downloaded,
                COUNT(CASE WHEN status = 'screenshot' THEN 1 END) as screenshots,
                COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
                SUM(content_length) as total_size,
                COUNT(DISTINCT SUBSTR(url, INSTR(url, '://') + 3, 
                      CASE WHEN INSTR(SUBSTR(url, INSTR(url, '://') + 3), '/') > 0 
                           THEN INSTR(SUBSTR(url, INSTR(url, '://') + 3), '/') - 1 
                           ELSE LENGTH(SUBSTR(url, INSTR(url, '://') + 3)) END)) as domains
            FROM web_resources
        ''')
        
        row = cursor.fetchone()
        
        stats = ArchiveStats(
            total_discovered=row[0] or 0,
            total_downloaded=row[1] or 0,
            total_screenshots=row[2] or 0,
            total_failed=row[3] or 0,
            total_size_mb=(row[4] or 0) / (1024 * 1024),
            domains_discovered=row[5] or 0
        )
        
        return stats
    
    async def save_search_query(self, query: str, category: str, generated_by: str = "ollama") -> int:
        """Sauvegarde une requête de recherche"""
        cursor = self.connection.cursor()
        cursor.execute('''
            INSERT INTO search_queries (query, category, generated_by)
            VALUES (?, ?, ?)
        ''', (query, category, generated_by))
        
        self.connection.commit()
        return cursor.lastrowid
    
    async def mark_url_as_discovered(self, url: str, parent_url: str = None, depth: int = 0) -> int:
        """Marque une URL comme découverte"""
        resource = WebResource(
            url=url,
            parent_url=parent_url,
            depth=depth,
            status=ArchiveStatus.PENDING
        )
        return await self.save_resource(resource)
    
    def _row_to_resource(self, row) -> WebResource:
        """Convertit une ligne de DB en WebResource"""
        import json
        
        tags = json.loads(row['tags']) if row['tags'] else []
        metadata = json.loads(row['metadata']) if row['metadata'] else {}
        
        return WebResource(
            url=row['url'],
            title=row['title'],
            content_type=ContentType(row['content_type']) if row['content_type'] else ContentType.UNKNOWN,
            file_path=row['file_path'],
            screenshot_path=row['screenshot_path'],
            content_length=row['content_length'],
            status=ArchiveStatus(row['status']) if row['status'] else ArchiveStatus.PENDING,
            discovered_at=datetime.fromisoformat(row['discovered_at']) if row['discovered_at'] else None,
            archived_at=datetime.fromisoformat(row['archived_at']) if row['archived_at'] else None,
            parent_url=row['parent_url'],
            depth=row['depth'],
            tags=tags,
            metadata=metadata,
            error_message=row['error_message']
        )
