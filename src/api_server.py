"""
API REST pour DATA_BOT v2
Utilise le serveur HTTP intégré de Python pour une solution légère
"""

import json
import logging
import asyncio
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from typing import Dict, Any, Optional
from datetime import datetime

from src.config import Config
from src.database import DatabaseManager
from src.models import ArchiveStatus, WebResource

logger = logging.getLogger(__name__)

class APIHandler(BaseHTTPRequestHandler):
    """Gestionnaire des requêtes API REST"""
    
    def do_GET(self):
        """Gestion des requêtes GET"""
        try:
            path = self.path.split('?')[0]
            query_params = self._parse_query_params()
            
            if path == '/api/stats':
                self._handle_stats()
            elif path == '/api/resources':
                self._handle_list_resources(query_params)
            elif path.startswith('/api/resources/'):
                resource_id = path.split('/')[-1]
                self._handle_get_resource(resource_id)
            elif path == '/api/search':
                query = query_params.get('q', [''])[0]
                self._handle_search(query)
            elif path == '/api/export':
                format_type = query_params.get('format', ['json'])[0]
                self._handle_export(format_type)
            elif path == '/':
                self._serve_web_interface()
            else:
                self._send_error(404, "Endpoint not found")
                
        except Exception as e:
            logger.error(f"Erreur API GET: {e}")
            self._send_error(500, str(e))
    
    def do_POST(self):
        """Gestion des requêtes POST"""
        try:
            path = self.path
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            if path == '/api/resources':
                data = json.loads(post_data) if post_data else {}
                self._handle_add_resource(data)
            elif path == '/api/archive/start':
                data = json.loads(post_data) if post_data else {}
                self._handle_start_archive(data)
            elif path == '/api/schedule':
                data = json.loads(post_data) if post_data else {}
                self._handle_schedule_task(data)
            else:
                self._send_error(404, "Endpoint not found")
                
        except Exception as e:
            logger.error(f"Erreur API POST: {e}")
            self._send_error(500, str(e))
    
    def do_DELETE(self):
        """Gestion des requêtes DELETE"""
        try:
            path = self.path
            if path.startswith('/api/resources/'):
                resource_id = path.split('/')[-1]
                self._handle_delete_resource(resource_id)
            else:
                self._send_error(404, "Endpoint not found")
                
        except Exception as e:
            logger.error(f"Erreur API DELETE: {e}")
            self._send_error(500, str(e))
    
    def _parse_query_params(self) -> Dict[str, list]:
        """Parse les paramètres de requête"""
        if '?' not in self.path:
            return {}
        query_string = self.path.split('?')[1]
        return urllib.parse.parse_qs(query_string)
    
    def _handle_stats(self):
        """Récupère les statistiques"""
        async def get_stats():
            async with DatabaseManager() as db:
                stats = await db.get_archive_stats()
                return {
                    'total_discovered': stats.total_discovered,
                    'total_downloaded': stats.total_downloaded,
                    'total_screenshots': stats.total_screenshots,
                    'total_failed': stats.total_failed,
                    'total_size_mb': stats.total_size_mb,
                    'domains_discovered': stats.domains_discovered,
                    'last_update': stats.last_update.isoformat() if stats.last_update else None
                }
        
        stats = asyncio.run(get_stats())
        self._send_json_response(stats)
    
    def _handle_list_resources(self, query_params: Dict[str, list]):
        """Liste les ressources avec pagination"""
        async def get_resources():
            limit = int(query_params.get('limit', ['50'])[0])
            offset = int(query_params.get('offset', ['0'])[0])
            status = query_params.get('status', [None])[0]
            
            async with DatabaseManager() as db:
                if status:
                    status_enum = ArchiveStatus(status)
                    resources = await db.get_resources_by_status(status_enum, limit, offset)
                else:
                    resources = await db.get_all_resources(limit, offset)
                
                return [self._resource_to_dict(r) for r in resources]
        
        resources = asyncio.run(get_resources())
        self._send_json_response({'resources': resources})
    
    def _handle_get_resource(self, resource_id: str):
        """Récupère une ressource spécifique"""
        async def get_resource():
            async with DatabaseManager() as db:
                resource = await db.get_resource_by_id(int(resource_id))
                return self._resource_to_dict(resource) if resource else None
        
        resource = asyncio.run(get_resource())
        if resource:
            self._send_json_response(resource)
        else:
            self._send_error(404, "Resource not found")
    
    def _handle_search(self, query: str):
        """Recherche dans les ressources"""
        async def search():
            async with DatabaseManager() as db:
                resources = await db.search_resources(query)
                return [self._resource_to_dict(r) for r in resources]
        
        results = asyncio.run(search())
        self._send_json_response({'query': query, 'results': results})
    
    def _handle_export(self, format_type: str):
        """Exporte les données en différents formats"""
        async def export_data():
            async with DatabaseManager() as db:
                resources = await db.get_all_resources(limit=10000)
                
                if format_type == 'csv':
                    return self._export_csv(resources)
                elif format_type == 'html':
                    return self._export_html(resources)
                else:  # json par défaut
                    return self._export_json(resources)
        
        data, content_type = asyncio.run(export_data())
        
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Disposition', f'attachment; filename="archive_export.{format_type}"')
        self.end_headers()
        self.wfile.write(data.encode('utf-8'))
    
    def _handle_add_resource(self, data: Dict[str, Any]):
        """Ajoute une nouvelle ressource à archiver"""
        async def add_resource():
            url = data.get('url')
            if not url:
                raise ValueError("URL required")
            
            resource = WebResource(
                url=url,
                title=data.get('title'),
                depth=data.get('depth', 0)
            )
            
            async with DatabaseManager() as db:
                await db.save_resource(resource)
                return {'id': resource.url, 'status': 'added'}
        
        result = asyncio.run(add_resource())
        self._send_json_response(result, status=201)
    
    def _handle_start_archive(self, data: Dict[str, Any]):
        """Démarre un processus d'archivage"""
        # Pour l'instant, retourne juste une confirmation
        # Dans une implémentation complète, cela déclencherait le bot
        result = {
            'status': 'started',
            'mode': data.get('mode', 'continuous'),
            'message': 'Archive process initiated'
        }
        self._send_json_response(result)
    
    def _handle_schedule_task(self, data: Dict[str, Any]):
        """Programme une tâche d'archivage"""
        # Implémentation basique du scheduling
        result = {
            'status': 'scheduled',
            'task_id': f"task_{datetime.now().timestamp()}",
            'schedule': data.get('schedule', 'daily'),
            'message': 'Task scheduled successfully'
        }
        self._send_json_response(result, status=201)
    
    def _handle_delete_resource(self, resource_id: str):
        """Supprime une ressource"""
        async def delete_resource():
            async with DatabaseManager() as db:
                success = await db.delete_resource(int(resource_id))
                return {'deleted': success}
        
        result = asyncio.run(delete_resource())
        self._send_json_response(result)
    
    def _serve_web_interface(self):
        """Sert l'interface web de gestion"""
        html_content = self._generate_web_interface()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))
    
    def _generate_web_interface(self) -> str:
        """Génère l'interface web HTML"""
        return '''<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DATA_BOT v2 - Interface de Gestion</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { border-bottom: 2px solid #007bff; padding-bottom: 10px; margin-bottom: 20px; }
        .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
        .stat-card { background: #007bff; color: white; padding: 15px; border-radius: 5px; text-align: center; }
        .btn { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin: 5px; }
        .btn:hover { background: #0056b3; }
        .btn-danger { background: #dc3545; }
        .btn-danger:hover { background: #c82333; }
        .form-group { margin: 10px 0; }
        .form-group label { display: block; margin-bottom: 5px; font-weight: bold; }
        .form-group input, .form-group select { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
        .table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        .table th, .table td { padding: 10px; border: 1px solid #ddd; text-align: left; }
        .table th { background-color: #f8f9fa; }
        .status-downloaded { color: #28a745; font-weight: bold; }
        .status-failed { color: #dc3545; font-weight: bold; }
        .status-pending { color: #ffc107; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 DATA_BOT v2 - Interface de Gestion</h1>
            <p>Système d'archivage web intelligent avec IA</p>
        </div>
        
        <div class="section">
            <h2>📊 Statistiques</h2>
            <div class="stats" id="stats">
                <div class="stat-card">
                    <h3 id="total-discovered">-</h3>
                    <p>Ressources découvertes</p>
                </div>
                <div class="stat-card">
                    <h3 id="total-downloaded">-</h3>
                    <p>Fichiers téléchargés</p>
                </div>
                <div class="stat-card">
                    <h3 id="total-screenshots">-</h3>
                    <p>Screenshots</p>
                </div>
                <div class="stat-card">
                    <h3 id="total-size">-</h3>
                    <p>Taille totale (MB)</p>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>🚀 Actions</h2>
            <button class="btn" onclick="startArchive()">Démarrer l'archivage</button>
            <button class="btn" onclick="exportData('json')">Exporter JSON</button>
            <button class="btn" onclick="exportData('csv')">Exporter CSV</button>
            <button class="btn" onclick="exportData('html')">Exporter HTML</button>
            <button class="btn btn-danger" onclick="clearCache()">Vider le cache</button>
        </div>
        
        <div class="section">
            <h2>➕ Ajouter une URL</h2>
            <div class="form-group">
                <label for="new-url">URL à archiver:</label>
                <input type="url" id="new-url" placeholder="https://example.com">
            </div>
            <div class="form-group">
                <label for="new-title">Titre (optionnel):</label>
                <input type="text" id="new-title" placeholder="Titre de la ressource">
            </div>
            <button class="btn" onclick="addResource()">Ajouter à l'archive</button>
        </div>
        
        <div class="section">
            <h2>🔍 Recherche</h2>
            <div class="form-group">
                <input type="text" id="search-query" placeholder="Rechercher dans l'archive...">
                <button class="btn" onclick="searchArchive()">Rechercher</button>
            </div>
            <div id="search-results"></div>
        </div>
        
        <div class="section">
            <h2>📋 Ressources récentes</h2>
            <div id="recent-resources">
                <p>Chargement...</p>
            </div>
        </div>
    </div>
    
    <script>
        async function loadStats() {
            try {
                const response = await fetch('/api/stats');
                const stats = await response.json();
                document.getElementById('total-discovered').textContent = stats.total_discovered;
                document.getElementById('total-downloaded').textContent = stats.total_downloaded;
                document.getElementById('total-screenshots').textContent = stats.total_screenshots;
                document.getElementById('total-size').textContent = stats.total_size_mb.toFixed(2);
            } catch (error) {
                console.error('Erreur lors du chargement des stats:', error);
            }
        }
        
        async function loadRecentResources() {
            try {
                const response = await fetch('/api/resources?limit=10');
                const data = await response.json();
                const container = document.getElementById('recent-resources');
                
                if (data.resources.length === 0) {
                    container.innerHTML = '<p>Aucune ressource trouvée.</p>';
                    return;
                }
                
                const table = document.createElement('table');
                table.className = 'table';
                table.innerHTML = `
                    <thead>
                        <tr>
                            <th>Titre</th>
                            <th>URL</th>
                            <th>Status</th>
                            <th>Date</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.resources.map(r => `
                            <tr>
                                <td>${r.title || 'Sans titre'}</td>
                                <td><a href="${r.url}" target="_blank">${r.url.substring(0, 50)}...</a></td>
                                <td><span class="status-${r.status}">${r.status}</span></td>
                                <td>${new Date(r.discovered_at).toLocaleDateString()}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                `;
                container.innerHTML = '';
                container.appendChild(table);
            } catch (error) {
                console.error('Erreur lors du chargement des ressources:', error);
                document.getElementById('recent-resources').innerHTML = '<p>Erreur de chargement.</p>';
            }
        }
        
        async function startArchive() {
            try {
                const response = await fetch('/api/archive/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ mode: 'continuous' })
                });
                const result = await response.json();
                alert('Archivage démarré: ' + result.message);
            } catch (error) {
                alert('Erreur: ' + error.message);
            }
        }
        
        async function addResource() {
            const url = document.getElementById('new-url').value;
            const title = document.getElementById('new-title').value;
            
            if (!url) {
                alert('Veuillez saisir une URL');
                return;
            }
            
            try {
                const response = await fetch('/api/resources', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url, title })
                });
                const result = await response.json();
                alert('Ressource ajoutée avec succès');
                document.getElementById('new-url').value = '';
                document.getElementById('new-title').value = '';
                loadRecentResources();
            } catch (error) {
                alert('Erreur: ' + error.message);
            }
        }
        
        async function searchArchive() {
            const query = document.getElementById('search-query').value;
            if (!query) return;
            
            try {
                const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
                const data = await response.json();
                const container = document.getElementById('search-results');
                
                if (data.results.length === 0) {
                    container.innerHTML = '<p>Aucun résultat trouvé.</p>';
                    return;
                }
                
                const table = document.createElement('table');
                table.className = 'table';
                table.innerHTML = `
                    <thead>
                        <tr>
                            <th>Titre</th>
                            <th>URL</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.results.map(r => `
                            <tr>
                                <td>${r.title || 'Sans titre'}</td>
                                <td><a href="${r.url}" target="_blank">${r.url}</a></td>
                                <td><span class="status-${r.status}">${r.status}</span></td>
                            </tr>
                        `).join('')}
                    </tbody>
                `;
                container.innerHTML = '';
                container.appendChild(table);
            } catch (error) {
                console.error('Erreur de recherche:', error);
            }
        }
        
        function exportData(format) {
            window.open(`/api/export?format=${format}`, '_blank');
        }
        
        function clearCache() {
            if (confirm('Êtes-vous sûr de vouloir vider le cache ?')) {
                alert('Fonctionnalité à implémenter');
            }
        }
        
        // Chargement initial
        document.addEventListener('DOMContentLoaded', function() {
            loadStats();
            loadRecentResources();
            
            // Rafraîchissement automatique toutes les 30 secondes
            setInterval(() => {
                loadStats();
                loadRecentResources();
            }, 30000);
        });
    </script>
</body>
</html>'''
    
    def _resource_to_dict(self, resource: WebResource) -> Dict[str, Any]:
        """Convertit une ressource en dictionnaire"""
        return {
            'url': resource.url,
            'title': resource.title,
            'content_type': resource.content_type.value if resource.content_type else None,
            'file_path': resource.file_path,
            'screenshot_path': resource.screenshot_path,
            'content_length': resource.content_length,
            'status': resource.status.value,
            'discovered_at': resource.discovered_at.isoformat() if resource.discovered_at else None,
            'archived_at': resource.archived_at.isoformat() if resource.archived_at else None,
            'parent_url': resource.parent_url,
            'depth': resource.depth,
            'tags': resource.tags,
            'metadata': resource.metadata
        }
    
    def _export_json(self, resources: list) -> tuple:
        """Exporte en JSON"""
        data = [self._resource_to_dict(r) for r in resources]
        return json.dumps(data, indent=2, ensure_ascii=False), 'application/json'
    
    def _export_csv(self, resources: list) -> tuple:
        """Exporte en CSV"""
        lines = ['URL,Title,Status,Content Type,File Path,Discovered At']
        for r in resources:
            line = f'"{r.url}","{r.title or ""}","{r.status.value}","{r.content_type.value if r.content_type else ""}","{r.file_path or ""}","{r.discovered_at.isoformat() if r.discovered_at else ""}"'
            lines.append(line)
        return '\n'.join(lines), 'text/csv'
    
    def _export_html(self, resources: list) -> tuple:
        """Exporte en HTML"""
        rows = []
        for r in resources:
            rows.append(f'''
                <tr>
                    <td><a href="{r.url}" target="_blank">{r.title or "Sans titre"}</a></td>
                    <td>{r.url}</td>
                    <td>{r.status.value}</td>
                    <td>{r.content_type.value if r.content_type else ""}</td>
                    <td>{r.discovered_at.strftime("%Y-%m-%d %H:%M") if r.discovered_at else ""}</td>
                </tr>
            ''')
        
        html = f'''<!DOCTYPE html>
<html>
<head>
    <title>Export Archive DATA_BOT</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 10px; border: 1px solid #ddd; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <h1>Archive DATA_BOT - Export</h1>
    <p>Généré le {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    <table>
        <thead>
            <tr>
                <th>Titre</th>
                <th>URL</th>
                <th>Status</th>
                <th>Type</th>
                <th>Découvert le</th>
            </tr>
        </thead>
        <tbody>
            {"".join(rows)}
        </tbody>
    </table>
</body>
</html>'''
        return html, 'text/html'
    
    def _send_json_response(self, data: Any, status: int = 200):
        """Envoie une réponse JSON"""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        json_data = json.dumps(data, ensure_ascii=False, default=str)
        self.wfile.write(json_data.encode('utf-8'))
    
    def _send_error(self, status: int, message: str):
        """Envoie une erreur JSON"""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        error_data = json.dumps({'error': message}, ensure_ascii=False)
        self.wfile.write(error_data.encode('utf-8'))
    
    def log_message(self, format, *args):
        """Personnalise les logs du serveur"""
        logger.info(f"API {self.address_string()} - {format % args}")


class APIServer:
    """Serveur API REST pour DATA_BOT"""
    
    def __init__(self, host: str = 'localhost', port: int = 8080):
        self.host = host
        self.port = port
        self.server = None
        self.thread = None
    
    def start(self):
        """Démarre le serveur API"""
        try:
            self.server = HTTPServer((self.host, self.port), APIHandler)
            self.thread = Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            logger.info(f"🌐 Serveur API démarré sur http://{self.host}:{self.port}")
            logger.info(f"📱 Interface web disponible sur http://{self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Erreur démarrage serveur API: {e}")
            return False
    
    def stop(self):
        """Arrête le serveur API"""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            if self.thread:
                self.thread.join(timeout=5)
            logger.info("🛑 Serveur API arrêté")
    
    def is_running(self) -> bool:
        """Vérifie si le serveur est en cours d'exécution"""
        return self.thread is not None and self.thread.is_alive()