"""
Analytics API endpoints for DATA_BOT dashboard
Provides visualization data for the enhanced web UI
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict, Counter
import random
import math

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session

from .database import DatabaseManager
from .models import WebResource, ArchiveStatus
from .config import Config

class AnalyticsAPI:
    """API for analytics and visualization data"""
    
    def __init__(self, database_manager: DatabaseManager):
        self.db_manager = database_manager
        self.router = APIRouter(prefix="/api/v4/analytics", tags=["analytics"])
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup API routes"""
        
        @self.router.get("/stats")
        async def get_stats() -> Dict[str, Any]:
            """Get general statistics"""
            try:
                with self.db_manager.get_session() as session:
                    total_sites = session.query(WebResource).count()
                    total_pages = session.query(WebResource).filter(
                        WebResource.status == ArchiveStatus.DOWNLOADED
                    ).count()
                    
                    # Calculate total size
                    total_size_result = session.query(func.sum(WebResource.file_size)).scalar()
                    total_size = total_size_result or 0
                    
                    # Calculate success rate
                    successful = session.query(WebResource).filter(
                        or_(
                            WebResource.status == ArchiveStatus.DOWNLOADED,
                            WebResource.status == ArchiveStatus.SCREENSHOT_TAKEN
                        )
                    ).count()
                    
                    success_rate = round((successful / total_sites * 100) if total_sites > 0 else 0, 1)
                    
                    return {
                        "totalSites": total_sites,
                        "totalPages": total_pages,
                        "totalSize": total_size,
                        "successRate": success_rate,
                        "lastUpdated": datetime.now().isoformat()
                    }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/recent")
        async def get_recent_activity(limit: int = Query(50, ge=1, le=100)) -> List[Dict[str, Any]]:
            """Get recent archival activity"""
            try:
                with self.db_manager.get_session() as session:
                    recent = session.query(WebResource).order_by(
                        WebResource.discovered_at.desc()
                    ).limit(limit).all()
                    
                    activity = []
                    for resource in recent:
                        activity.append({
                            "id": resource.id,
                            "url": resource.url,
                            "status": self._format_status(resource.status),
                            "timestamp": resource.discovered_at.isoformat(),
                            "size": resource.file_size or 0,
                            "duration": random.randint(100, 5000)  # Mock duration
                        })
                    
                    return activity
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/daily")
        async def get_daily_activity(days: int = Query(30, ge=1, le=365)) -> Dict[str, List]:
            """Get daily activity data for charts"""
            try:
                with self.db_manager.get_session() as session:
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=days)
                    
                    # Query daily counts
                    daily_data = session.query(
                        func.date(WebResource.discovered_at).label('date'),
                        func.count(WebResource.id).label('count')
                    ).filter(
                        WebResource.discovered_at >= start_date
                    ).group_by(
                        func.date(WebResource.discovered_at)
                    ).order_by('date').all()
                    
                    # Fill missing dates with 0
                    data_dict = {str(row.date): row.count for row in daily_data}
                    
                    labels = []
                    data = []
                    current_date = start_date
                    
                    while current_date <= end_date:
                        date_str = current_date.strftime('%Y-%m-%d')
                        labels.append(date_str)
                        data.append(data_dict.get(date_str, 0))
                        current_date += timedelta(days=1)
                    
                    return {"labels": labels, "data": data}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/domains")
        async def get_domain_distribution(limit: int = Query(10, ge=5, le=50)) -> Dict[str, List]:
            """Get domain distribution data"""
            try:
                with self.db_manager.get_session() as session:
                    from urllib.parse import urlparse
                    
                    resources = session.query(WebResource.url).all()
                    domain_counts = Counter()
                    
                    for resource in resources:
                        try:
                            domain = urlparse(resource.url).netloc
                            domain_counts[domain] += 1
                        except:
                            continue
                    
                    # Get top domains
                    top_domains = domain_counts.most_common(limit)
                    
                    labels = [domain for domain, _ in top_domains]
                    data = [count for _, count in top_domains]
                    
                    return {"labels": labels, "data": data}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/status")
        async def get_status_distribution() -> Dict[str, List]:
            """Get status distribution data"""
            try:
                with self.db_manager.get_session() as session:
                    status_counts = session.query(
                        WebResource.status,
                        func.count(WebResource.id)
                    ).group_by(WebResource.status).all()
                    
                    status_map = {
                        ArchiveStatus.DOWNLOADED: "Succès",
                        ArchiveStatus.SCREENSHOT_TAKEN: "Succès",
                        ArchiveStatus.FAILED: "Erreur",
                        ArchiveStatus.PROCESSING: "En Cours",
                        ArchiveStatus.PENDING: "En Attente"
                    }
                    
                    data = [0, 0, 0, 0]  # [Succès, Erreur, En Cours, En Attente]
                    
                    for status, count in status_counts:
                        if status in [ArchiveStatus.DOWNLOADED, ArchiveStatus.SCREENSHOT_TAKEN]:
                            data[0] += count
                        elif status == ArchiveStatus.FAILED:
                            data[1] += count
                        elif status == ArchiveStatus.PROCESSING:
                            data[2] += count
                        elif status == ArchiveStatus.PENDING:
                            data[3] += count
                    
                    return {"data": data}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/performance")
        async def get_performance_data(hours: int = Query(24, ge=1, le=168)) -> Dict[str, List]:
            """Get performance metrics over time"""
            try:
                # Mock performance data for demonstration
                # In real implementation, you'd track actual response times
                end_time = datetime.now()
                start_time = end_time - timedelta(hours=hours)
                
                labels = []
                data = []
                
                current_time = start_time
                while current_time <= end_time:
                    labels.append(current_time.strftime('%H:%M'))
                    # Generate realistic response time data
                    base_response = 500
                    variation = random.uniform(0.5, 2.0)
                    data.append(int(base_response * variation))
                    current_time += timedelta(hours=1)
                
                return {"labels": labels, "data": data}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/network")
        async def get_network_graph(limit: int = Query(50, ge=10, le=200)) -> Dict[str, List]:
            """Get network graph data for site interconnections"""
            try:
                with self.db_manager.get_session() as session:
                    from urllib.parse import urlparse
                    
                    # Get most recent resources
                    resources = session.query(WebResource).filter(
                        WebResource.status.in_([
                            ArchiveStatus.DOWNLOADED,
                            ArchiveStatus.SCREENSHOT_TAKEN
                        ])
                    ).order_by(WebResource.discovered_at.desc()).limit(limit).all()
                    
                    # Create nodes and links
                    nodes = []
                    links = []
                    domain_nodes = {}
                    
                    for resource in resources:
                        try:
                            domain = urlparse(resource.url).netloc
                            if domain not in domain_nodes:
                                domain_nodes[domain] = {
                                    "id": domain,
                                    "name": domain,
                                    "value": 1,
                                    "color": self._get_domain_color(domain)
                                }
                                nodes.append(domain_nodes[domain])
                            else:
                                domain_nodes[domain]["value"] += 1
                        except:
                            continue
                    
                    # Create links between domains (simplified)
                    domain_list = list(domain_nodes.keys())
                    for i, domain1 in enumerate(domain_list):
                        for j, domain2 in enumerate(domain_list[i+1:], i+1):
                            if random.random() < 0.1:  # 10% chance of link
                                links.append({
                                    "source": domain1,
                                    "target": domain2,
                                    "value": random.randint(1, 5)
                                })
                    
                    return {"nodes": nodes, "links": links}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/export")
        async def export_analytics_data():
            """Export analytics data as JSON"""
            try:
                # Gather all analytics data
                export_data = {
                    "export_timestamp": datetime.now().isoformat(),
                    "stats": {},
                    "recent_activity": [],
                    "daily_data": {},
                    "domain_distribution": {},
                    "status_distribution": {},
                    "performance_data": {}
                }
                
                # This would call all the above endpoints internally
                # For now, return a simple export structure
                
                with self.db_manager.get_session() as session:
                    all_resources = session.query(WebResource).all()
                    export_data["total_resources"] = len(all_resources)
                    export_data["resources"] = [
                        {
                            "url": r.url,
                            "status": str(r.status),
                            "discovered_at": r.discovered_at.isoformat() if r.discovered_at else None,
                            "file_size": r.file_size,
                            "title": r.title,
                            "domain": r.domain
                        }
                        for r in all_resources[:1000]  # Limit to prevent huge exports
                    ]
                
                # Return as downloadable JSON
                filename = f"/tmp/databot_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                
                return FileResponse(
                    filename,
                    media_type='application/json',
                    filename=f"databot_analytics_{datetime.now().strftime('%Y%m%d')}.json"
                )
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
    
    def _format_status(self, status: ArchiveStatus) -> str:
        """Format status for display"""
        status_map = {
            ArchiveStatus.PENDING: "pending",
            ArchiveStatus.PROCESSING: "warning",
            ArchiveStatus.DOWNLOADED: "success",
            ArchiveStatus.SCREENSHOT_TAKEN: "success",
            ArchiveStatus.FAILED: "error"
        }
        return status_map.get(status, "unknown")
    
    def _get_domain_color(self, domain: str) -> str:
        """Generate consistent color for domain"""
        colors = [
            "#FF6384", "#36A2EB", "#FFCE56", "#4BC0C0",
            "#9966FF", "#FF9F40", "#FF6384", "#C9CBCF",
            "#4CAF50", "#2196F3", "#FF9800", "#9C27B0"
        ]
        hash_value = hash(domain) % len(colors)
        return colors[hash_value]

def create_analytics_router(database_manager: DatabaseManager) -> APIRouter:
    """Create and return analytics router"""
    analytics_api = AnalyticsAPI(database_manager)
    return analytics_api.router