"""
Serveur pour plugin navigateur DATA_BOT v3
Gère les communications avec l'extension Chrome/Firefox
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from src.core.models import WebResource, ContentType, ArchiveStatus

logger = logging.getLogger(__name__)

class ArchivePageRequest(BaseModel):
    """Requête d'archivage depuis le plugin"""
    url: str
    title: Optional[str] = None
    content: Optional[str] = None
    html: Optional[str] = None
    screenshot_data: Optional[str] = None  # Base64
    tags: list[str] = []
    metadata: Dict[str, Any] = {}

class QuickNoteRequest(BaseModel):
    """Requête de note rapide depuis le plugin"""
    url: str
    note: str
    selection: Optional[str] = None
    tags: list[str] = []

class PluginStatusResponse(BaseModel):
    """Réponse de statut pour le plugin"""
    active: bool
    version: str
    features: Dict[str, bool]
    stats: Dict[str, int]

class BrowserPluginServer:
    """Serveur pour plugin navigateur"""
    
    def __init__(self, port: int = 8081):
        self.port = port
        self.app = FastAPI(title="DATA_BOT Browser Plugin API", version="3.0")
        self.server = None
        
        # Répertoire pour les fichiers du plugin
        self.plugin_dir = Path(__file__).parent / "browser_plugin"
        
        self._setup_app()
        self._create_plugin_files()
    
    def _setup_app(self):
        """Configure l'application FastAPI"""
        
        # CORS pour permettre les requêtes depuis l'extension
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # En production, spécifier les origines autorisées
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Monter les fichiers statiques du plugin
        if self.plugin_dir.exists():
            self.app.mount("/plugin", StaticFiles(directory=str(self.plugin_dir)), name="plugin")
        
        self._add_routes()
    
    def _add_routes(self):
        """Ajoute les routes API pour le plugin"""
        
        @self.app.get("/")
        async def root():
            """Page d'accueil du serveur plugin"""
            return {"message": "DATA_BOT Browser Plugin Server v3", "port": self.port}
        
        @self.app.get("/plugin/status")
        async def plugin_status():
            """Statut du plugin"""
            return PluginStatusResponse(
                active=True,
                version="3.0",
                features={
                    "quick_archive": True,
                    "full_page_capture": True,
                    "selection_archive": True,
                    "quick_notes": True,
                    "auto_tagging": True
                },
                stats={
                    "pages_archived": 150,  # TODO: Récupérer les vraies stats
                    "notes_saved": 45,
                    "total_size_mb": 1250
                }
            )
        
        @self.app.post("/plugin/archive-page")
        async def archive_page(request: ArchivePageRequest, background_tasks: BackgroundTasks):
            """Archive une page depuis le plugin"""
            try:
                logger.info(f"Archivage demandé depuis plugin: {request.url}")
                
                # Créer une ressource web
                resource = WebResource(
                    url=request.url,
                    title=request.title,
                    content_type=ContentType.WEB_PAGE,
                    tags=request.tags,
                    metadata={
                        **request.metadata,
                        "source": "browser_plugin",
                        "archived_via": "extension",
                        "has_screenshot": bool(request.screenshot_data),
                        "has_html": bool(request.html)
                    }
                )
                
                # Ajouter à la queue d'archivage en arrière-plan
                background_tasks.add_task(self._process_archive_request, resource, request)
                
                return {
                    "success": True,
                    "message": "Page ajoutée à la queue d'archivage",
                    "resource_id": resource.url,
                    "estimated_processing_time": "2-5 minutes"
                }
                
            except Exception as e:
                logger.error(f"Erreur archivage plugin: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/plugin/quick-note")
        async def quick_note(request: QuickNoteRequest):
            """Sauvegarde une note rapide"""
            try:
                logger.info(f"Note rapide depuis plugin: {request.url}")
                
                # TODO: Sauvegarder la note dans la base
                note_data = {
                    "url": request.url,
                    "note": request.note,
                    "selection": request.selection,
                    "tags": request.tags,
                    "created_at": datetime.now().isoformat(),
                    "source": "browser_plugin"
                }
                
                return {
                    "success": True,
                    "message": "Note sauvegardée",
                    "note_id": f"note_{datetime.now().timestamp()}"
                }
                
            except Exception as e:
                logger.error(f"Erreur sauvegarde note: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/plugin/search")
        async def plugin_search(q: str, limit: int = 5):
            """Recherche rapide pour le plugin"""
            try:
                # TODO: Implémenter la recherche réelle
                # Pour le moment, retourner des résultats factices
                results = [
                    {
                        "url": "https://example.com/page1",
                        "title": "Example Page 1",
                        "snippet": "Contenu exemple...",
                        "score": 0.95
                    },
                    {
                        "url": "https://example.com/page2", 
                        "title": "Example Page 2",
                        "snippet": "Autre contenu...",
                        "score": 0.85
                    }
                ]
                
                return {
                    "results": results[:limit],
                    "total": len(results),
                    "query": q
                }
                
            except Exception as e:
                logger.error(f"Erreur recherche plugin: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/plugin/recent")
        async def plugin_recent(limit: int = 10):
            """Ressources récentes pour le plugin"""
            try:
                # TODO: Récupérer les vraies ressources récentes
                recent = [
                    {
                        "url": "https://example.com/recent1",
                        "title": "Recent Page 1",
                        "archived_at": datetime.now().isoformat(),
                        "type": "web_page"
                    }
                ]
                
                return {
                    "recent": recent[:limit],
                    "total": len(recent)
                }
                
            except Exception as e:
                logger.error(f"Erreur ressources récentes: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/plugin/manifest.json")
        async def plugin_manifest():
            """Manifest de l'extension Chrome"""
            return FileResponse(
                path=str(self.plugin_dir / "manifest.json"),
                media_type="application/json"
            )
    
    async def _process_archive_request(self, resource: WebResource, request: ArchivePageRequest):
        """Traite une demande d'archivage en arrière-plan"""
        try:
            logger.info(f"Traitement archivage: {resource.url}")
            
            # TODO: Intégrer avec le système d'archivage principal
            # - Sauvegarder le HTML si fourni
            # - Sauvegarder le screenshot si fourni  
            # - Ajouter à la queue de traitement
            # - Notifier les autres composants
            
            # Simuler le traitement
            await asyncio.sleep(2)
            
            logger.info(f"Archivage terminé: {resource.url}")
            
        except Exception as e:
            logger.error(f"Erreur traitement archivage: {e}")
    
    def _create_plugin_files(self):
        """Crée les fichiers de l'extension navigateur"""
        
        # Créer le répertoire si nécessaire
        self.plugin_dir.mkdir(exist_ok=True)
        
        # Manifest Chrome Extension
        manifest = {
            "manifest_version": 3,
            "name": "DATA_BOT Archive Assistant",
            "version": "3.0",
            "description": "Assistant d'archivage pour DATA_BOT v3",
            "permissions": [
                "activeTab",
                "storage",
                "contextMenus",
                "scripting"
            ],
            "host_permissions": [
                "<all_urls>"
            ],
            "background": {
                "service_worker": "background.js"
            },
            "content_scripts": [
                {
                    "matches": ["<all_urls>"],
                    "js": ["content.js"]
                }
            ],
            "action": {
                "default_popup": "popup.html",
                "default_title": "DATA_BOT Archiver",
                "default_icon": {
                    "16": "icons/icon16.png",
                    "32": "icons/icon32.png",
                    "48": "icons/icon48.png",
                    "128": "icons/icon128.png"
                }
            },
            "icons": {
                "16": "icons/icon16.png",
                "32": "icons/icon32.png", 
                "48": "icons/icon48.png",
                "128": "icons/icon128.png"
            }
        }
        
        # Sauvegarder le manifest
        with open(self.plugin_dir / "manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)
        
        # HTML du popup
        popup_html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { width: 300px; padding: 16px; font-family: system-ui; }
        .header { text-align: center; margin-bottom: 16px; }
        .button { width: 100%; padding: 12px; margin: 8px 0; border: none; 
                 border-radius: 4px; cursor: pointer; font-size: 14px; }
        .primary { background: #2196F3; color: white; }
        .secondary { background: #f5f5f5; color: #333; }
        .status { padding: 8px; border-radius: 4px; margin: 8px 0; font-size: 12px; }
        .success { background: #e8f5e8; color: #2e7d32; }
        .error { background: #ffebee; color: #c62828; }
        .tags-input { width: 100%; padding: 8px; margin: 4px 0; border: 1px solid #ddd; 
                     border-radius: 4px; }
        .quick-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    </style>
</head>
<body>
    <div class="header">
        <h3>📚 DATA_BOT</h3>
        <div id="status" class="status" style="display: none;"></div>
    </div>
    
    <div class="quick-actions">
        <button id="archivePage" class="button primary">📄 Archiver</button>
        <button id="screenshot" class="button secondary">📸 Capture</button>
    </div>
    
    <input id="tags" class="tags-input" placeholder="Tags (séparés par des virgules)">
    
    <button id="quickNote" class="button secondary">📝 Note rapide</button>
    <textarea id="noteText" placeholder="Votre note..." style="width: 100%; height: 60px; margin: 4px 0; padding: 8px; border: 1px solid #ddd; border-radius: 4px; resize: none;"></textarea>
    
    <button id="search" class="button secondary">🔍 Rechercher</button>
    
    <div id="recent" style="margin-top: 16px;">
        <h4>Récent:</h4>
        <div id="recentList"></div>
    </div>
    
    <script src="popup.js"></script>
</body>
</html>
"""
        
        # JavaScript du popup
        popup_js = """
const API_BASE = 'http://localhost:8081';

document.addEventListener('DOMContentLoaded', function() {
    const archiveBtn = document.getElementById('archivePage');
    const screenshotBtn = document.getElementById('screenshot');
    const quickNoteBtn = document.getElementById('quickNote');
    const searchBtn = document.getElementById('search');
    const tagsInput = document.getElementById('tags');
    const noteText = document.getElementById('noteText');
    const status = document.getElementById('status');
    
    function showStatus(message, type = 'success') {
        status.textContent = message;
        status.className = `status ${type}`;
        status.style.display = 'block';
        setTimeout(() => status.style.display = 'none', 3000);
    }
    
    async function getCurrentTab() {
        const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
        return tab;
    }
    
    archiveBtn.addEventListener('click', async function() {
        try {
            const tab = await getCurrentTab();
            const tags = tagsInput.value.split(',').map(t => t.trim()).filter(t => t);
            
            // Injecter un script pour extraire le contenu
            const [result] = await chrome.scripting.executeScript({
                target: {tabId: tab.id},
                function: extractPageContent
            });
            
            const response = await fetch(`${API_BASE}/plugin/archive-page`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    url: tab.url,
                    title: tab.title,
                    content: result.result.content,
                    html: result.result.html,
                    tags: tags
                })
            });
            
            if (response.ok) {
                showStatus('Page ajoutée à l\\'archive!', 'success');
                tagsInput.value = '';
            } else {
                showStatus('Erreur lors de l\\'archivage', 'error');
            }
        } catch (error) {
            showStatus('Erreur: ' + error.message, 'error');
        }
    });
    
    quickNoteBtn.addEventListener('click', async function() {
        if (!noteText.value.trim()) return;
        
        try {
            const tab = await getCurrentTab();
            const tags = tagsInput.value.split(',').map(t => t.trim()).filter(t => t);
            
            const response = await fetch(`${API_BASE}/plugin/quick-note`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    url: tab.url,
                    note: noteText.value,
                    tags: tags
                })
            });
            
            if (response.ok) {
                showStatus('Note sauvegardée!', 'success');
                noteText.value = '';
                tagsInput.value = '';
            } else {
                showStatus('Erreur sauvegarde note', 'error');
            }
        } catch (error) {
            showStatus('Erreur: ' + error.message, 'error');
        }
    });
    
    searchBtn.addEventListener('click', function() {
        chrome.tabs.create({url: 'http://localhost:8080/mobile'});
    });
    
    // Charger les ressources récentes
    loadRecent();
});

function extractPageContent() {
    return {
        content: document.body.innerText.substring(0, 5000),
        html: document.documentElement.outerHTML.substring(0, 50000)
    };
}

async function loadRecent() {
    try {
        const response = await fetch(`${API_BASE}/plugin/recent?limit=3`);
        const data = await response.json();
        
        const recentList = document.getElementById('recentList');
        recentList.innerHTML = '';
        
        data.recent.forEach(item => {
            const div = document.createElement('div');
            div.style.cssText = 'padding: 4px; font-size: 12px; border-bottom: 1px solid #eee;';
            div.innerHTML = `<strong>${item.title}</strong><br><small>${item.url}</small>`;
            recentList.appendChild(div);
        });
    } catch (error) {
        console.error('Erreur chargement récent:', error);
    }
}
"""
        
        # Background script
        background_js = """
// Service Worker pour l'extension DATA_BOT

chrome.runtime.onInstalled.addListener(() => {
    // Créer les menus contextuels
    chrome.contextMenus.create({
        id: 'archivePage',
        title: 'Archiver cette page',
        contexts: ['page']
    });
    
    chrome.contextMenus.create({
        id: 'archiveLink',
        title: 'Archiver ce lien',
        contexts: ['link']
    });
    
    chrome.contextMenus.create({
        id: 'archiveSelection',
        title: 'Archiver la sélection',
        contexts: ['selection']
    });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
    switch(info.menuItemId) {
        case 'archivePage':
            archivePage(tab);
            break;
        case 'archiveLink':
            archiveLink(info.linkUrl, tab);
            break;
        case 'archiveSelection':
            archiveSelection(info.selectionText, tab);
            break;
    }
});

async function archivePage(tab) {
    try {
        // Injecter le script d'extraction
        const [result] = await chrome.scripting.executeScript({
            target: {tabId: tab.id},
            function: extractPageContent
        });
        
        // Envoyer à l'API
        const response = await fetch('http://localhost:8081/plugin/archive-page', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                url: tab.url,
                title: tab.title,
                content: result.result.content,
                html: result.result.html,
                metadata: {source: 'context_menu'}
            })
        });
        
        if (response.ok) {
            // Notification de succès
            chrome.notifications.create({
                type: 'basic',
                iconUrl: 'icons/icon48.png',
                title: 'DATA_BOT',
                message: 'Page ajoutée à l\\'archive!'
            });
        }
    } catch (error) {
        console.error('Erreur archivage:', error);
    }
}

function extractPageContent() {
    return {
        content: document.body.innerText.substring(0, 5000),
        html: document.documentElement.outerHTML.substring(0, 50000)
    };
}
"""
        
        # Content script
        content_js = """
// Content script pour DATA_BOT
// Injecté dans toutes les pages pour la détection et l'interaction

console.log('DATA_BOT content script loaded');

// Écouter les messages du popup/background
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'extractContent') {
        const content = {
            text: document.body.innerText,
            html: document.documentElement.outerHTML,
            title: document.title,
            url: window.location.href,
            meta: extractMetadata()
        };
        sendResponse(content);
    }
});

function extractMetadata() {
    const meta = {};
    
    // Meta tags
    document.querySelectorAll('meta').forEach(tag => {
        const name = tag.getAttribute('name') || tag.getAttribute('property');
        const content = tag.getAttribute('content');
        if (name && content) {
            meta[name] = content;
        }
    });
    
    // Links
    meta.links = Array.from(document.querySelectorAll('a[href]')).map(a => ({
        href: a.href,
        text: a.textContent.trim()
    })).slice(0, 50);
    
    return meta;
}
"""
        
        # Sauvegarder les fichiers JavaScript
        with open(self.plugin_dir / "popup.html", "w") as f:
            f.write(popup_html)
        
        with open(self.plugin_dir / "popup.js", "w") as f:
            f.write(popup_js)
        
        with open(self.plugin_dir / "background.js", "w") as f:
            f.write(background_js)
        
        with open(self.plugin_dir / "content.js", "w") as f:
            f.write(content_js)
        
        # Créer le répertoire des icônes
        icons_dir = self.plugin_dir / "icons"
        icons_dir.mkdir(exist_ok=True)
        
        logger.info(f"📁 Fichiers du plugin créés dans: {self.plugin_dir}")
    
    async def start(self):
        """Démarre le serveur plugin"""
        logger.info(f"🔌 Démarrage du serveur plugin sur le port {self.port}")
        
        config = uvicorn.Config(
            app=self.app,
            host="localhost",
            port=self.port,
            log_level="info"
        )
        
        self.server = uvicorn.Server(config)
        
        # Démarrer en arrière-plan
        asyncio.create_task(self.server.serve())
        
        logger.info(f"✅ Serveur plugin démarré: http://localhost:{self.port}")
        logger.info(f"📦 Extension disponible: http://localhost:{self.port}/plugin/")
    
    async def stop(self):
        """Arrête le serveur plugin"""
        if self.server:
            self.server.should_exit = True
        logger.info("🔌 Serveur plugin arrêté")