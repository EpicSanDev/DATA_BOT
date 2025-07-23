"""
API Server v3 - Extension du serveur v2 avec interface mobile native (PWA)
et intégrations avancées (Vector Search, Elasticsearch, Distributed)
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Query, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.api_server import APIServer
from src.models import WebResource, ArchiveStatus, ContentType

logger = logging.getLogger(__name__)

class PWAConfig(BaseModel):
    """Configuration PWA"""
    name: str = "DATA_BOT Mobile"
    short_name: str = "DataBot"
    description: str = "Bot d'archivage internet mobile"
    theme_color: str = "#2196F3"
    background_color: str = "#ffffff"
    display: str = "standalone"
    orientation: str = "portrait"

class MobileSearchRequest(BaseModel):
    """Requête de recherche mobile"""
    query: str
    type: str = "all"  # text, vector, semantic
    filters: Optional[Dict[str, Any]] = None
    limit: int = 10
    offset: int = 0

class QuickArchiveRequest(BaseModel):
    """Requête d'archivage rapide depuis mobile"""
    url: str
    title: Optional[str] = None
    tags: List[str] = []
    priority: int = 1

class APIServerV3(APIServer):
    """Serveur API v3 avec interface mobile native (PWA)"""
    
    def __init__(self, host: str = "localhost", port: int = 8080, 
                 enable_pwa: bool = True,
                 vector_manager=None,
                 elasticsearch_manager=None,
                 distributed_manager=None):
        
        super().__init__(host, port)
        
        self.enable_pwa = enable_pwa
        self.vector_manager = vector_manager
        self.elasticsearch_manager = elasticsearch_manager
        self.distributed_manager = distributed_manager
        
        self.pwa_config = PWAConfig()
        
        # Répertoires pour l'interface mobile
        self.mobile_dir = Path(__file__).parent / "mobile"
        self.templates_dir = Path(__file__).parent / "templates"
        
        if enable_pwa:
            self._setup_mobile_interface()
    
    def _setup_mobile_interface(self):
        """Configure l'interface mobile PWA"""
        
        # Créer les répertoires si nécessaire
        self.mobile_dir.mkdir(exist_ok=True)
        self.templates_dir.mkdir(exist_ok=True)
        
        # Templates Jinja2
        if self.templates_dir.exists():
            self.templates = Jinja2Templates(directory=str(self.templates_dir))
        
        # Monter les fichiers statiques mobiles
        if self.mobile_dir.exists():
            self.app.mount("/mobile", StaticFiles(directory=str(self.mobile_dir)), name="mobile")
        
        # Routes PWA
        self._add_pwa_routes()
        
        # Routes API v3 mobiles
        self._add_mobile_api_routes()
        
        logger.info("📱 Interface mobile PWA configurée")
    
    def _add_pwa_routes(self):
        """Ajoute les routes PWA"""
        
        @self.app.get("/mobile", response_class=HTMLResponse)
        @self.app.get("/mobile/", response_class=HTMLResponse)
        async def mobile_app(request: Request):
            """Page principale de l'app mobile"""
            return self.templates.TemplateResponse("mobile_app.html", {
                "request": request,
                "pwa_config": self.pwa_config.dict(),
                "api_base": f"http://{self.host}:{self.port}/api/v3"
            })
        
        @self.app.get("/mobile/manifest.json")
        async def pwa_manifest():
            """Manifest PWA"""
            manifest = {
                "name": self.pwa_config.name,
                "short_name": self.pwa_config.short_name,
                "description": self.pwa_config.description,
                "start_url": "/mobile/",
                "display": self.pwa_config.display,
                "orientation": self.pwa_config.orientation,
                "theme_color": self.pwa_config.theme_color,
                "background_color": self.pwa_config.background_color,
                "icons": [
                    {
                        "src": "/mobile/icons/icon-192.png",
                        "sizes": "192x192",
                        "type": "image/png"
                    },
                    {
                        "src": "/mobile/icons/icon-512.png", 
                        "sizes": "512x512",
                        "type": "image/png"
                    }
                ]
            }
            return JSONResponse(manifest)
        
        @self.app.get("/mobile/sw.js")
        async def service_worker():
            """Service Worker pour PWA"""
            sw_content = self._generate_service_worker()
            return Response(sw_content, media_type="application/javascript")
    
    def _add_mobile_api_routes(self):
        """Ajoute les routes API spécifiques mobiles"""
        
        @self.app.post("/api/v3/mobile/quick-archive")
        async def mobile_quick_archive(request: QuickArchiveRequest):
            """Archivage rapide depuis mobile"""
            try:
                # Créer une ressource web
                resource = WebResource(
                    url=request.url,
                    title=request.title,
                    tags=request.tags,
                    metadata={"source": "mobile", "priority": request.priority}
                )
                
                # TODO: Ajouter à la queue d'archivage
                # Ici on devrait utiliser le distributed_manager si disponible
                
                return {
                    "success": True,
                    "message": "URL ajoutée à la queue d'archivage",
                    "resource_id": resource.url  # Temporaire
                }
                
            except Exception as e:
                logger.error(f"Erreur archivage rapide mobile: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v3/mobile/search")
        async def mobile_search(request: MobileSearchRequest):
            """Recherche optimisée mobile"""
            try:
                results = []
                
                if request.type == "vector" and self.vector_manager:
                    # Recherche vectorielle sémantique
                    vector_results = await self.vector_manager.semantic_search(
                        query=request.query,
                        limit=request.limit
                    )
                    results.extend([{
                        "type": "vector",
                        "url": r.url,
                        "title": r.title,
                        "score": r.score,
                        "snippet": r.snippet
                    } for r in vector_results])
                
                elif request.type == "elasticsearch" and self.elasticsearch_manager:
                    # Recherche Elasticsearch
                    es_results = await self.elasticsearch_manager.advanced_search(
                        query=request.query,
                        filters=request.filters,
                        limit=request.limit,
                        offset=request.offset
                    )
                    results.extend([{
                        "type": "elasticsearch",
                        "url": hit.url,
                        "title": hit.title,
                        "score": hit.score,
                        "snippet": hit.snippet,
                        "highlights": hit.highlights
                    } for hit in es_results.hits])
                
                else:
                    # Recherche classique dans la base de données
                    # TODO: Implémenter la recherche classique
                    pass
                
                return {
                    "results": results,
                    "total": len(results),
                    "query": request.query,
                    "type": request.type
                }
                
            except Exception as e:
                logger.error(f"Erreur recherche mobile: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v3/mobile/status")
        async def mobile_status():
            """Statut système pour mobile"""
            try:
                status = {
                    "timestamp": datetime.now().isoformat(),
                    "version": "3.0",
                    "features": {
                        "vector_search": self.vector_manager is not None,
                        "elasticsearch": self.elasticsearch_manager is not None,
                        "distributed": self.distributed_manager is not None,
                        "pwa": self.enable_pwa
                    },
                    "stats": {
                        # TODO: Récupérer les vraies stats
                        "total_resources": 0,
                        "active_tasks": 0,
                        "cluster_nodes": 1 if self.distributed_manager else 1
                    }
                }
                
                if self.distributed_manager:
                    cluster_status = await self.distributed_manager.get_cluster_status()
                    status["cluster"] = {
                        "coordinator": cluster_status.coordinator,
                        "workers": len(cluster_status.workers),
                        "active_tasks": cluster_status.active_tasks,
                        "pending_tasks": cluster_status.pending_tasks
                    }
                
                return status
                
            except Exception as e:
                logger.error(f"Erreur statut mobile: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v3/mobile/recent")
        async def mobile_recent(limit: int = Query(10, ge=1, le=100)):
            """Ressources récentes pour mobile"""
            try:
                # TODO: Récupérer les ressources récentes depuis la base
                recent_resources = []
                
                return {
                    "resources": recent_resources,
                    "total": len(recent_resources)
                }
                
            except Exception as e:
                logger.error(f"Erreur ressources récentes mobile: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/v3/mobile/sync")
        async def mobile_sync():
            """Synchronisation pour mode offline"""
            try:
                # TODO: Implémenter la synchronisation offline
                sync_data = {
                    "last_sync": datetime.now().isoformat(),
                    "pending_uploads": 0,
                    "new_downloads": 0
                }
                
                return sync_data
                
            except Exception as e:
                logger.error(f"Erreur synchronisation mobile: {e}")
                raise HTTPException(status_code=500, detail=str(e))
    
    def _generate_service_worker(self) -> str:
        """Génère le Service Worker pour la PWA"""
        return """
// Service Worker pour DATA_BOT Mobile PWA
const CACHE_NAME = 'databot-v3-cache';
const urlsToCache = [
  '/mobile/',
  '/mobile/app.js',
  '/mobile/app.css',
  '/mobile/icons/icon-192.png',
  '/mobile/icons/icon-512.png'
];

self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function(cache) {
        return cache.addAll(urlsToCache);
      })
  );
});

self.addEventListener('fetch', function(event) {
  event.respondWith(
    caches.match(event.request)
      .then(function(response) {
        // Cache hit - return response
        if (response) {
          return response;
        }
        return fetch(event.request);
      }
    )
  );
});

// Sync en arrière-plan
self.addEventListener('sync', function(event) {
  if (event.tag === 'background-sync') {
    event.waitUntil(doBackgroundSync());
  }
});

async function doBackgroundSync() {
  try {
    const response = await fetch('/api/v3/mobile/sync', {
      method: 'POST'
    });
    console.log('Synchronisation terminée:', await response.json());
  } catch (error) {
    console.error('Erreur synchronisation:', error);
  }
}

// Notifications push
self.addEventListener('push', function(event) {
  const options = {
    body: event.data ? event.data.text() : 'Nouvelle notification DATA_BOT',
    icon: '/mobile/icons/icon-192.png',
    badge: '/mobile/icons/icon-192.png'
  };

  event.waitUntil(
    self.registration.showNotification('DATA_BOT', options)
  );
});
"""
    
    def start(self):
        """Démarre le serveur API v3"""
        super().start()
        
        if self.enable_pwa:
            logger.info(f"📱 Interface mobile PWA disponible sur: http://{self.host}:{self.port}/mobile")
            logger.info(f"🔗 API v3 disponible sur: http://{self.host}:{self.port}/api/v3")