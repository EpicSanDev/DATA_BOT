"""
Module d'export pour DATA_BOT v2
Fonctionnalités d'export en différents formats
"""

import json
import csv
import io
import zipfile
import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from src.core.models import WebResource, ArchiveStats
from src.database.database import DatabaseManager
from src.core.config import Config

logger = logging.getLogger(__name__)

class ExportManager:
    """Gestionnaire des exports de données"""
    
    def __init__(self):
        self.export_dir = Path(Config.ARCHIVE_PATH) / "exports"
        self.export_dir.mkdir(exist_ok=True)
    
    async def export_archive(self, format_type: str = "json", 
                           include_files: bool = False,
                           filter_status: Optional[str] = None) -> str:
        """
        Exporte l'archive complète dans le format spécifié
        
        Args:
            format_type: json, csv, html, xml, zip
            include_files: Inclure les fichiers téléchargés dans l'export
            filter_status: Filtrer par status (downloaded, screenshot, failed, etc.)
        
        Returns:
            Chemin vers le fichier d'export créé
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_filename = f"databot_export_{timestamp}.{format_type}"
        export_path = self.export_dir / export_filename
        
        async with DatabaseManager() as db:
            # Récupérer les données
            resources = await db.get_all_resources(limit=100000)
            stats = await db.get_archive_stats()
            
            # Filtrer par status si demandé
            if filter_status:
                from src.core.models import ArchiveStatus
                status_filter = ArchiveStatus(filter_status)
                resources = [r for r in resources if r.status == status_filter]
            
            logger.info(f"Export de {len(resources)} ressources en format {format_type}")
            
            if format_type == "json":
                await self._export_json(resources, stats, export_path)
            elif format_type == "csv":
                await self._export_csv(resources, export_path)
            elif format_type == "html":
                await self._export_html(resources, stats, export_path)
            elif format_type == "xml":
                await self._export_xml(resources, stats, export_path)
            elif format_type == "zip":
                await self._export_zip(resources, stats, export_path, include_files)
            else:
                raise ValueError(f"Format d'export non supporté: {format_type}")
        
        logger.info(f"Export terminé: {export_path}")
        return str(export_path)
    
    async def _export_json(self, resources: List[WebResource], 
                          stats: ArchiveStats, export_path: Path):
        """Export en format JSON"""
        export_data = {
            "metadata": {
                "export_date": datetime.now().isoformat(),
                "export_version": "2.0",
                "total_resources": len(resources),
                "statistics": {
                    "total_discovered": stats.total_discovered,
                    "total_downloaded": stats.total_downloaded,
                    "total_screenshots": stats.total_screenshots,
                    "total_failed": stats.total_failed,
                    "total_size_mb": stats.total_size_mb,
                    "domains_discovered": stats.domains_discovered
                }
            },
            "resources": []
        }
        
        for resource in resources:
            resource_data = {
                "url": resource.url,
                "title": resource.title,
                "content_type": resource.content_type.value if resource.content_type else None,
                "status": resource.status.value,
                "file_path": resource.file_path,
                "screenshot_path": resource.screenshot_path,
                "content_length": resource.content_length,
                "discovered_at": resource.discovered_at.isoformat() if resource.discovered_at else None,
                "archived_at": resource.archived_at.isoformat() if resource.archived_at else None,
                "parent_url": resource.parent_url,
                "depth": resource.depth,
                "tags": resource.tags,
                "metadata": resource.metadata,
                "error_message": resource.error_message
            }
            export_data["resources"].append(resource_data)
        
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    async def _export_csv(self, resources: List[WebResource], export_path: Path):
        """Export en format CSV"""
        fieldnames = [
            'url', 'title', 'content_type', 'status', 'file_path', 
            'screenshot_path', 'content_length', 'discovered_at', 
            'archived_at', 'parent_url', 'depth', 'tags', 'error_message'
        ]
        
        with open(export_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for resource in resources:
                row = {
                    'url': resource.url,
                    'title': resource.title or '',
                    'content_type': resource.content_type.value if resource.content_type else '',
                    'status': resource.status.value,
                    'file_path': resource.file_path or '',
                    'screenshot_path': resource.screenshot_path or '',
                    'content_length': resource.content_length or 0,
                    'discovered_at': resource.discovered_at.isoformat() if resource.discovered_at else '',
                    'archived_at': resource.archived_at.isoformat() if resource.archived_at else '',
                    'parent_url': resource.parent_url or '',
                    'depth': resource.depth,
                    'tags': ','.join(resource.tags) if resource.tags else '',
                    'error_message': resource.error_message or ''
                }
                writer.writerow(row)
    
    async def _export_html(self, resources: List[WebResource], 
                          stats: ArchiveStats, export_path: Path):
        """Export en format HTML"""
        html_content = f'''<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Archive DATA_BOT - Export</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header {{
            border-bottom: 2px solid #007bff;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: #007bff;
            color: white;
            padding: 15px;
            border-radius: 5px;
            text-align: center;
        }}
        .table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        .table th, .table td {{
            padding: 10px;
            border: 1px solid #ddd;
            text-align: left;
        }}
        .table th {{
            background-color: #f8f9fa;
            font-weight: bold;
        }}
        .table tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        .status-downloaded {{ color: #28a745; font-weight: bold; }}
        .status-screenshot {{ color: #17a2b8; font-weight: bold; }}
        .status-failed {{ color: #dc3545; font-weight: bold; }}
        .status-pending {{ color: #ffc107; font-weight: bold; }}
        .url-link {{
            color: #007bff;
            text-decoration: none;
            max-width: 300px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            display: inline-block;
        }}
        .url-link:hover {{ text-decoration: underline; }}
        .search-box {{
            margin: 20px 0;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 5px;
        }}
        .search-box input {{
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 16px;
        }}
    </style>
    <script>
        function filterTable() {{
            const input = document.getElementById('searchInput');
            const filter = input.value.toLowerCase();
            const table = document.getElementById('resourcesTable');
            const rows = table.getElementsByTagName('tr');
            
            for (let i = 1; i < rows.length; i++) {{
                const row = rows[i];
                const cells = row.getElementsByTagName('td');
                let found = false;
                
                for (let j = 0; j < cells.length; j++) {{
                    if (cells[j].textContent.toLowerCase().includes(filter)) {{
                        found = true;
                        break;
                    }}
                }}
                
                row.style.display = found ? '' : 'none';
            }}
        }}
        
        function sortTable(columnIndex) {{
            const table = document.getElementById('resourcesTable');
            const rows = Array.from(table.getElementsByTagName('tr')).slice(1);
            const isAscending = table.getAttribute('data-sort-direction') !== 'asc';
            
            rows.sort((a, b) => {{
                const aText = a.getElementsByTagName('td')[columnIndex].textContent.trim();
                const bText = b.getElementsByTagName('td')[columnIndex].textContent.trim();
                return isAscending ? aText.localeCompare(bText) : bText.localeCompare(aText);
            }});
            
            table.setAttribute('data-sort-direction', isAscending ? 'asc' : 'desc');
            
            const tbody = table.getElementsByTagName('tbody')[0];
            rows.forEach(row => tbody.appendChild(row));
        }}
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 DATA_BOT - Archive Export</h1>
            <p>Export généré le {datetime.now().strftime("%d/%m/%Y à %H:%M:%S")}</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <h3>{stats.total_discovered}</h3>
                <p>Ressources découvertes</p>
            </div>
            <div class="stat-card">
                <h3>{stats.total_downloaded}</h3>
                <p>Fichiers téléchargés</p>
            </div>
            <div class="stat-card">
                <h3>{stats.total_screenshots}</h3>
                <p>Screenshots</p>
            </div>
            <div class="stat-card">
                <h3>{stats.total_size_mb:.2f} MB</h3>
                <p>Taille totale</p>
            </div>
        </div>
        
        <div class="search-box">
            <input type="text" id="searchInput" placeholder="Rechercher dans les ressources..." onkeyup="filterTable()">
        </div>
        
        <table class="table" id="resourcesTable">
            <thead>
                <tr>
                    <th onclick="sortTable(0)" style="cursor: pointer;">Titre ↕</th>
                    <th onclick="sortTable(1)" style="cursor: pointer;">URL ↕</th>
                    <th onclick="sortTable(2)" style="cursor: pointer;">Status ↕</th>
                    <th onclick="sortTable(3)" style="cursor: pointer;">Type ↕</th>
                    <th onclick="sortTable(4)" style="cursor: pointer;">Taille ↕</th>
                    <th onclick="sortTable(5)" style="cursor: pointer;">Date ↕</th>
                </tr>
            </thead>
            <tbody>'''
        
        for resource in resources:
            status_class = f"status-{resource.status.value}"
            title = resource.title or "Sans titre"
            url_display = resource.url[:80] + "..." if len(resource.url) > 80 else resource.url
            content_type = resource.content_type.value if resource.content_type else ""
            size_display = f"{resource.content_length // 1024} KB" if resource.content_length else "-"
            date_display = resource.discovered_at.strftime("%d/%m/%Y") if resource.discovered_at else "-"
            
            html_content += f'''
                <tr>
                    <td>{title}</td>
                    <td><a href="{resource.url}" target="_blank" class="url-link">{url_display}</a></td>
                    <td><span class="{status_class}">{resource.status.value}</span></td>
                    <td>{content_type}</td>
                    <td>{size_display}</td>
                    <td>{date_display}</td>
                </tr>'''
        
        html_content += '''
            </tbody>
        </table>
        
        <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; color: #666;">
            <p>Généré par DATA_BOT v2 - {len(resources)} ressources exportées</p>
        </div>
    </div>
</body>
</html>'''
        
        with open(export_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    async def _export_xml(self, resources: List[WebResource], 
                         stats: ArchiveStats, export_path: Path):
        """Export en format XML"""
        xml_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<databot_archive>
    <metadata>
        <export_date>{datetime.now().isoformat()}</export_date>
        <export_version>2.0</export_version>
        <total_resources>{len(resources)}</total_resources>
        <statistics>
            <total_discovered>{stats.total_discovered}</total_discovered>
            <total_downloaded>{stats.total_downloaded}</total_downloaded>
            <total_screenshots>{stats.total_screenshots}</total_screenshots>
            <total_failed>{stats.total_failed}</total_failed>
            <total_size_mb>{stats.total_size_mb}</total_size_mb>
            <domains_discovered>{stats.domains_discovered}</domains_discovered>
        </statistics>
    </metadata>
    <resources>'''
        
        for resource in resources:
            xml_content += f'''
        <resource>
            <url><![CDATA[{resource.url}]]></url>
            <title><![CDATA[{resource.title or ""}]]></title>
            <content_type>{resource.content_type.value if resource.content_type else ""}</content_type>
            <status>{resource.status.value}</status>
            <file_path><![CDATA[{resource.file_path or ""}]]></file_path>
            <screenshot_path><![CDATA[{resource.screenshot_path or ""}]]></screenshot_path>
            <content_length>{resource.content_length or 0}</content_length>
            <discovered_at>{resource.discovered_at.isoformat() if resource.discovered_at else ""}</discovered_at>
            <archived_at>{resource.archived_at.isoformat() if resource.archived_at else ""}</archived_at>
            <parent_url><![CDATA[{resource.parent_url or ""}]]></parent_url>
            <depth>{resource.depth}</depth>
            <tags>
                {"".join(f"<tag>{tag}</tag>" for tag in (resource.tags or []))}
            </tags>
            <error_message><![CDATA[{resource.error_message or ""}]]></error_message>
        </resource>'''
        
        xml_content += '''
    </resources>
</databot_archive>'''
        
        with open(export_path, 'w', encoding='utf-8') as f:
            f.write(xml_content)
    
    async def _export_zip(self, resources: List[WebResource], 
                         stats: ArchiveStats, export_path: Path, 
                         include_files: bool = False):
        """Export en format ZIP avec fichiers optionnels"""
        with zipfile.ZipFile(export_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Ajouter l'export JSON principal
            json_data = await self._create_json_data(resources, stats)
            zipf.writestr('archive_data.json', json.dumps(json_data, indent=2, ensure_ascii=False))
            
            # Ajouter l'export CSV
            csv_buffer = io.StringIO()
            csv_writer = csv.DictWriter(csv_buffer, fieldnames=[
                'url', 'title', 'content_type', 'status', 'file_path'
            ])
            csv_writer.writeheader()
            for resource in resources:
                csv_writer.writerow({
                    'url': resource.url,
                    'title': resource.title or '',
                    'content_type': resource.content_type.value if resource.content_type else '',
                    'status': resource.status.value,
                    'file_path': resource.file_path or ''
                })
            zipf.writestr('archive_data.csv', csv_buffer.getvalue())
            
            # Ajouter un README
            readme = f"""# DATA_BOT Archive Export

Export généré le: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Version: 2.0

## Contenu

- archive_data.json: Données complètes au format JSON
- archive_data.csv: Données au format CSV
- README.txt: Ce fichier

## Statistiques

- Ressources découvertes: {stats.total_discovered}
- Fichiers téléchargés: {stats.total_downloaded}
- Screenshots: {stats.total_screenshots}
- Échecs: {stats.total_failed}
- Taille totale: {stats.total_size_mb:.2f} MB
- Domaines explorés: {stats.domains_discovered}

## Structure JSON

Le fichier archive_data.json contient:
- metadata: Informations sur l'export et statistiques
- resources: Liste de toutes les ressources archivées

Chaque ressource contient:
- url: URL de la ressource
- title: Titre de la page
- content_type: Type de contenu
- status: Status d'archivage (downloaded, screenshot, failed, etc.)
- file_path: Chemin vers le fichier téléchargé
- screenshot_path: Chemin vers le screenshot
- metadata: Métadonnées additionnelles
- Et d'autres champs...

---
Généré par DATA_BOT v2
"""
            zipf.writestr('README.txt', readme)
            
            # Inclure les fichiers si demandé
            if include_files:
                files_added = 0
                for resource in resources:
                    if resource.file_path and os.path.exists(resource.file_path):
                        try:
                            # Créer un nom de fichier sûr
                            safe_filename = self._make_safe_filename(resource.url, resource.file_path)
                            zipf.write(resource.file_path, f"files/{safe_filename}")
                            files_added += 1
                        except Exception as e:
                            logger.warning(f"Impossible d'ajouter le fichier {resource.file_path}: {e}")
                    
                    if resource.screenshot_path and os.path.exists(resource.screenshot_path):
                        try:
                            safe_filename = self._make_safe_filename(resource.url, resource.screenshot_path)
                            zipf.write(resource.screenshot_path, f"screenshots/{safe_filename}")
                        except Exception as e:
                            logger.warning(f"Impossible d'ajouter le screenshot {resource.screenshot_path}: {e}")
                
                logger.info(f"Ajouté {files_added} fichiers à l'archive ZIP")
    
    async def _create_json_data(self, resources: List[WebResource], 
                              stats: ArchiveStats) -> Dict[str, Any]:
        """Crée les données JSON pour l'export"""
        return {
            "metadata": {
                "export_date": datetime.now().isoformat(),
                "export_version": "2.0",
                "total_resources": len(resources),
                "statistics": {
                    "total_discovered": stats.total_discovered,
                    "total_downloaded": stats.total_downloaded,
                    "total_screenshots": stats.total_screenshots,
                    "total_failed": stats.total_failed,
                    "total_size_mb": stats.total_size_mb,
                    "domains_discovered": stats.domains_discovered
                }
            },
            "resources": [
                {
                    "url": r.url,
                    "title": r.title,
                    "content_type": r.content_type.value if r.content_type else None,
                    "status": r.status.value,
                    "file_path": r.file_path,
                    "screenshot_path": r.screenshot_path,
                    "content_length": r.content_length,
                    "discovered_at": r.discovered_at.isoformat() if r.discovered_at else None,
                    "archived_at": r.archived_at.isoformat() if r.archived_at else None,
                    "parent_url": r.parent_url,
                    "depth": r.depth,
                    "tags": r.tags,
                    "metadata": r.metadata,
                    "error_message": r.error_message
                } for r in resources
            ]
        }
    
    def _make_safe_filename(self, url: str, original_path: str) -> str:
        """Crée un nom de fichier sûr pour l'archive"""
        from urllib.parse import urlparse
        import re
        
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.replace('www.', '')
        
        # Nettoyer le domaine
        domain = re.sub(r'[^\w\-_.]', '_', domain)
        
        # Obtenir l'extension du fichier original
        extension = Path(original_path).suffix
        
        # Créer un nom de fichier unique
        timestamp = str(int(datetime.now().timestamp()))
        safe_name = f"{domain}_{timestamp}{extension}"
        
        return safe_name
    
    async def get_export_history(self) -> List[Dict[str, Any]]:
        """Retourne l'historique des exports"""
        exports = []
        
        if self.export_dir.exists():
            for export_file in self.export_dir.iterdir():
                if export_file.is_file():
                    stat = export_file.stat()
                    exports.append({
                        'filename': export_file.name,
                        'path': str(export_file),
                        'size_mb': stat.st_size / 1024 / 1024,
                        'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        'format': export_file.suffix[1:] if export_file.suffix else 'unknown'
                    })
        
        # Trier par date de création (plus récent en premier)
        exports.sort(key=lambda x: x['created_at'], reverse=True)
        return exports
    
    async def cleanup_old_exports(self, max_exports: int = 10):
        """Nettoie les anciens exports pour économiser l'espace"""
        exports = await self.get_export_history()
        
        if len(exports) > max_exports:
            for export in exports[max_exports:]:
                try:
                    os.remove(export['path'])
                    logger.info(f"Export supprimé: {export['filename']}")
                except Exception as e:
                    logger.warning(f"Impossible de supprimer l'export {export['filename']}: {e}")