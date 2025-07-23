#!/usr/bin/env python3
"""
Serveur de démonstration pour l'interface web DATA_BOT v2
"""

import json
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
import threading
import os
import sys

# Mock data for demonstration
MOCK_STATS = {
    'total_discovered': 1247,
    'total_downloaded': 892,
    'total_screenshots': 231,
    'total_size_mb': 156.7
}

MOCK_RESOURCES = [
    {
        'title': 'Python Documentation',
        'url': 'https://docs.python.org/3/',
        'status': 'downloaded',
        'discovered_at': '2024-01-15T10:30:00'
    },
    {
        'title': 'GitHub Repository',
        'url': 'https://github.com/example/project',
        'status': 'screenshot', 
        'discovered_at': '2024-01-15T11:15:00'
    },
    {
        'title': 'Tech News Article',
        'url': 'https://techcrunch.com/2024/01/15/ai-breakthrough',
        'status': 'downloaded',
        'discovered_at': '2024-01-15T12:00:00'
    },
    {
        'title': 'Research Paper',
        'url': 'https://arxiv.org/abs/2401.12345',
        'status': 'pending',
        'discovered_at': '2024-01-15T12:30:00'
    }
]

class DemoAPIHandler(BaseHTTPRequestHandler):
    """Gestionnaire des requêtes pour la démo"""
    
    def do_GET(self):
        """Gestion des requêtes GET"""
        try:
            path = self.path.split('?')[0]
            
            if path == '/api/stats':
                self._send_json_response(MOCK_STATS)
            elif path == '/api/resources':
                self._send_json_response({'resources': MOCK_RESOURCES})
            elif path == '/api/search':
                query = self._get_query_param('q')
                results = [r for r in MOCK_RESOURCES if query.lower() in r['title'].lower() or query.lower() in r['url'].lower()]
                self._send_json_response({'query': query, 'results': results})
            elif path == '/':
                self._serve_web_interface()
            else:
                self._send_error(404, "Endpoint not found")
                
        except Exception as e:
            print(f"Erreur API GET: {e}")
            self._send_error(500, str(e))
    
    def do_POST(self):
        """Gestion des requêtes POST"""
        try:
            path = self.path
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            if path == '/api/resources':
                data = json.loads(post_data) if post_data else {}
                self._send_json_response({'status': 'added', 'url': data.get('url', '')}, status=201)
            elif path == '/api/archive/start':
                self._send_json_response({'status': 'started', 'message': 'Archive process initiated (demo)'})
            else:
                self._send_error(404, "Endpoint not found")
                
        except Exception as e:
            print(f"Erreur API POST: {e}")
            self._send_error(500, str(e))
    
    def _get_query_param(self, param_name):
        """Récupère un paramètre de requête"""
        if '?' in self.path:
            query_string = self.path.split('?')[1]
            for param in query_string.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    if key == param_name:
                        return value
        return ''
    
    def _serve_web_interface(self):
        """Sert l'interface web de démonstration"""
        html_content = self._generate_web_interface()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))
    
    def _generate_web_interface(self) -> str:
        """Génère l'interface web HTML (même que dans api_server.py)"""
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
        .status-screenshot { color: #17a2b8; font-weight: bold; }
        .demo-badge { background: #ff6b35; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; margin-left: 10px; }
        .feature-list { background: #e8f5e8; padding: 15px; border-radius: 5px; margin: 15px 0; }
        .feature-list h4 { color: #155724; margin-top: 0; }
        .feature-list ul { margin: 10px 0; }
        .feature-list li { margin: 5px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 DATA_BOT v2 - Interface de Gestion <span class="demo-badge">DEMO</span></h1>
            <p>Système d'archivage web intelligent avec IA</p>
        </div>
        
        <div class="feature-list">
            <h4>🚀 Nouvelles fonctionnalités v2 implémentées:</h4>
            <ul>
                <li>✅ <strong>Interface web de gestion</strong> - Interface moderne et responsive</li>
                <li>✅ <strong>Support d'autres modèles IA</strong> - OpenAI, LLM locaux, fallback</li>
                <li>✅ <strong>Export en différents formats</strong> - JSON, CSV, HTML, XML, ZIP</li>
                <li>✅ <strong>Détection de doublons</strong> - URL, contenu, titre, similarité</li>
                <li>✅ <strong>Compression intelligente</strong> - GZIP/ZIP adaptatif par type</li>
                <li>✅ <strong>API REST complète</strong> - Endpoints pour toutes les fonctions</li>
                <li>✅ <strong>Support de proxies</strong> - Rotation, test, failover automatique</li>
                <li>✅ <strong>Archivage programmé</strong> - Scheduler type cron intégré</li>
            </ul>
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
                alert('Ressource ajoutée avec succès (mode démo)');
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
                    container.innerHTML = '<p>Aucun résultat trouvé pour "' + query + '".</p>';
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
            alert(`Export ${format.toUpperCase()} démarré (mode démo)`);
        }
        
        function clearCache() {
            if (confirm('Êtes-vous sûr de vouloir vider le cache ?')) {
                alert('Cache vidé (mode démo)');
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
    
    def _send_json_response(self, data, status: int = 200):
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
        """Désactive les logs pour la démo"""
        pass

def start_demo_server(port=8080):
    """Démarre le serveur de démonstration"""
    try:
        server = HTTPServer(('localhost', port), DemoAPIHandler)
        print(f"🌐 Serveur de démonstration DATA_BOT v2 démarré")
        print(f"📱 Interface web: http://localhost:{port}")
        print("🛑 Appuyez sur Ctrl+C pour arrêter")
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Arrêt du serveur de démonstration")
    except Exception as e:
        print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    start_demo_server(port)