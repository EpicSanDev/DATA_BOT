"""
Gestionnaire distribué pour DATA_BOT v3
Mode distribué multi-machines avec coordination et répartition des tâches
"""

import asyncio
import logging
import json
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

try:
    import aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    import aiofiles
    AIOFILES_AVAILABLE = True
except ImportError:
    AIOFILES_AVAILABLE = False

from src.models import WebResource, ArchiveStatus
from src.database import DatabaseManager

logger = logging.getLogger(__name__)

class NodeType(Enum):
    COORDINATOR = "coordinator"
    WORKER = "worker"
    HYBRID = "hybrid"

class TaskType(Enum):
    ARCHIVE = "archive"
    SCREENSHOT = "screenshot"
    EXTRACT = "extract"
    INDEX = "index"
    COMPRESS = "compress"
    EXPORT = "export"

class TaskStatus(Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class DistributedTask:
    """Tâche distribuée"""
    id: str
    type: TaskType
    status: TaskStatus
    data: Dict[str, Any]
    priority: int = 1
    created_at: datetime = None
    assigned_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    assigned_to: Optional[str] = None
    retries: int = 0
    max_retries: int = 3
    timeout: int = 300  # 5 minutes par défaut
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.metadata is None:
            self.metadata = {}

@dataclass
class WorkerNode:
    """Nœud worker"""
    id: str
    host: str
    port: int
    capabilities: Set[TaskType]
    status: str = "active"
    last_heartbeat: datetime = None
    current_tasks: int = 0
    max_tasks: int = 5
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.last_heartbeat is None:
            self.last_heartbeat = datetime.now()
        if self.metadata is None:
            self.metadata = {}

@dataclass
class ClusterStatus:
    """Statut du cluster"""
    coordinator: str
    workers: List[WorkerNode]
    active_tasks: int
    pending_tasks: int
    completed_tasks: int
    failed_tasks: int
    total_capacity: int
    cluster_health: str

class DistributedManager:
    """Gestionnaire de traitement distribué"""
    
    def __init__(self, node_type: str = "hybrid", 
                 coordinator_host: str = "localhost", 
                 coordinator_port: int = 8082,
                 redis_host: str = "localhost",
                 redis_port: int = 6379):
        
        self.node_type = NodeType(node_type.lower())
        self.coordinator_host = coordinator_host
        self.coordinator_port = coordinator_port
        self.redis_host = redis_host
        self.redis_port = redis_port
        
        self.node_id = str(uuid.uuid4())
        self.redis = None
        self.db_manager = DatabaseManager()
        
        # État local
        self.is_coordinator = self.node_type in [NodeType.COORDINATOR, NodeType.HYBRID]
        self.is_worker = self.node_type in [NodeType.WORKER, NodeType.HYBRID]
        self.running = False
        
        # Worker state
        self.current_tasks: Dict[str, DistributedTask] = {}
        self.max_concurrent_tasks = 3
        self.capabilities = {TaskType.ARCHIVE, TaskType.SCREENSHOT, TaskType.EXTRACT}
        
        # Coordinator state
        self.workers: Dict[str, WorkerNode] = {}
        self.task_queue: Dict[str, DistributedTask] = {}
        
        # Configuration
        self.heartbeat_interval = 30  # secondes
        self.task_timeout = 300  # 5 minutes
        self.worker_timeout = 90  # 1.5 minutes
        
    async def initialize(self):
        """Initialise le gestionnaire distribué"""
        logger.info(f"🌐 Initialisation du gestionnaire distribué: {self.node_type.value}")
        
        # Connexion Redis pour la coordination
        if REDIS_AVAILABLE:
            try:
                self.redis = await aioredis.from_url(
                    f"redis://{self.redis_host}:{self.redis_port}",
                    decode_responses=True
                )
                # Tester la connexion
                await self.redis.ping()
                logger.info("✅ Connexion Redis établie")
            except Exception as e:
                logger.warning(f"Redis non disponible, mode local: {e}")
                self.redis = None
        else:
            logger.warning("Redis non installé, mode local uniquement")
        
        # Enregistrer ce nœud
        await self._register_node()
        
        logger.info("✅ Gestionnaire distribué initialisé")
    
    async def _register_node(self):
        """Enregistre ce nœud dans le cluster"""
        if self.redis:
            node_info = {
                "id": self.node_id,
                "type": self.node_type.value,
                "host": self.coordinator_host,
                "port": self.coordinator_port,
                "capabilities": [cap.value for cap in self.capabilities],
                "registered_at": datetime.now().isoformat(),
                "max_tasks": self.max_concurrent_tasks
            }
            
            await self.redis.hset(
                "databot:nodes",
                self.node_id,
                json.dumps(node_info)
            )
            
            logger.info(f"📝 Nœud enregistré: {self.node_id}")
    
    async def run_coordinator(self):
        """Lance le mode coordinateur"""
        if not self.is_coordinator:
            raise ValueError("Ce nœud n'est pas configuré comme coordinateur")
        
        logger.info("👑 Démarrage du coordinateur")
        self.running = True
        
        # Tâches du coordinateur
        tasks = [
            asyncio.create_task(self._coordinator_loop()),
            asyncio.create_task(self._heartbeat_monitor()),
            asyncio.create_task(self._task_scheduler()),
            asyncio.create_task(self._cleanup_tasks())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Erreur coordinateur: {e}")
        finally:
            self.running = False
    
    async def run_worker(self):
        """Lance le mode worker"""
        if not self.is_worker:
            raise ValueError("Ce nœud n'est pas configuré comme worker")
        
        logger.info("👷 Démarrage du worker")
        self.running = True
        
        # Tâches du worker
        tasks = [
            asyncio.create_task(self._worker_loop()),
            asyncio.create_task(self._send_heartbeat()),
            asyncio.create_task(self._task_executor())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Erreur worker: {e}")
        finally:
            self.running = False
    
    async def _coordinator_loop(self):
        """Boucle principale du coordinateur"""
        while self.running:
            try:
                # Découvrir les workers
                await self._discover_workers()
                
                # Assigner les tâches
                await self._assign_tasks()
                
                # Surveiller les tâches
                await self._monitor_tasks()
                
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Erreur boucle coordinateur: {e}")
                await asyncio.sleep(10)
    
    async def _worker_loop(self):
        """Boucle principale du worker"""
        while self.running:
            try:
                # Vérifier les nouvelles tâches
                await self._check_for_tasks()
                
                # Mettre à jour le statut
                await self._update_worker_status()
                
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Erreur boucle worker: {e}")
                await asyncio.sleep(10)
    
    async def _discover_workers(self):
        """Découvre les workers disponibles"""
        if not self.redis:
            return
        
        try:
            nodes = await self.redis.hgetall("databot:nodes")
            
            # Nettoyer la liste des workers
            self.workers.clear()
            
            for node_id, node_data in nodes.items():
                if node_id == self.node_id:
                    continue
                
                try:
                    info = json.loads(node_data)
                    if info["type"] in ["worker", "hybrid"]:
                        worker = WorkerNode(
                            id=node_id,
                            host=info["host"],
                            port=info["port"],
                            capabilities={TaskType(cap) for cap in info["capabilities"]},
                            max_tasks=info.get("max_tasks", 5)
                        )
                        self.workers[node_id] = worker
                except Exception as e:
                    logger.warning(f"Worker invalide {node_id}: {e}")
            
            logger.debug(f"Workers découverts: {len(self.workers)}")
            
        except Exception as e:
            logger.error(f"Erreur découverte workers: {e}")
    
    async def _assign_tasks(self):
        """Assigne les tâches aux workers"""
        if not self.redis:
            return
        
        try:
            # Récupérer les tâches en attente
            pending_tasks = await self.redis.lrange("databot:tasks:pending", 0, -1)
            
            for task_data in pending_tasks:
                try:
                    task_info = json.loads(task_data)
                    task = DistributedTask(**task_info)
                    
                    # Trouver un worker disponible
                    worker = await self._find_available_worker(task.type)
                    if worker:
                        # Assigner la tâche
                        await self._assign_task_to_worker(task, worker)
                        
                        # Retirer de la queue
                        await self.redis.lrem("databot:tasks:pending", 1, task_data)
                        
                except Exception as e:
                    logger.error(f"Erreur assignation tâche: {e}")
            
        except Exception as e:
            logger.error(f"Erreur assignation tâches: {e}")
    
    async def _find_available_worker(self, task_type: TaskType) -> Optional[WorkerNode]:
        """Trouve un worker disponible pour un type de tâche"""
        best_worker = None
        min_load = float('inf')
        
        for worker in self.workers.values():
            # Vérifier les capacités
            if task_type not in worker.capabilities:
                continue
            
            # Vérifier la disponibilité
            if worker.current_tasks >= worker.max_tasks:
                continue
            
            # Vérifier la santé
            if worker.status != "active":
                continue
            
            # Calculer la charge
            load = worker.current_tasks / worker.max_tasks
            if load < min_load:
                min_load = load
                best_worker = worker
        
        return best_worker
    
    async def _assign_task_to_worker(self, task: DistributedTask, worker: WorkerNode):
        """Assigne une tâche à un worker"""
        try:
            task.assigned_to = worker.id
            task.assigned_at = datetime.now()
            task.status = TaskStatus.ASSIGNED
            
            # Ajouter à la queue du worker
            await self.redis.lpush(
                f"databot:tasks:worker:{worker.id}",
                json.dumps(asdict(task), default=str)
            )
            
            # Mettre à jour le statut
            await self.redis.hset(
                "databot:tasks:status",
                task.id,
                json.dumps(asdict(task), default=str)
            )
            
            # Incrémenter le compteur du worker
            worker.current_tasks += 1
            
            logger.info(f"Tâche {task.id} assignée au worker {worker.id}")
            
        except Exception as e:
            logger.error(f"Erreur assignation tâche au worker: {e}")
    
    async def _check_for_tasks(self):
        """Vérifie les nouvelles tâches pour ce worker"""
        if not self.redis:
            return
        
        try:
            # Récupérer les tâches assignées
            task_data = await self.redis.rpop(f"databot:tasks:worker:{self.node_id}")
            
            if task_data:
                task_info = json.loads(task_data)
                task = DistributedTask(**task_info)
                
                # Vérifier si on peut traiter cette tâche
                if (len(self.current_tasks) < self.max_concurrent_tasks and
                    task.type in self.capabilities):
                    
                    # Commencer le traitement
                    self.current_tasks[task.id] = task
                    asyncio.create_task(self._execute_task(task))
                    
                    logger.info(f"Tâche {task.id} prise en charge")
                else:
                    # Remettre dans la queue
                    await self.redis.lpush(f"databot:tasks:worker:{self.node_id}", task_data)
            
        except Exception as e:
            logger.error(f"Erreur vérification tâches: {e}")
    
    async def _execute_task(self, task: DistributedTask):
        """Exécute une tâche"""
        try:
            task.status = TaskStatus.RUNNING
            await self._update_task_status(task)
            
            logger.info(f"Exécution tâche {task.id} ({task.type.value})")
            
            # Exécuter selon le type
            if task.type == TaskType.ARCHIVE:
                await self._execute_archive_task(task)
            elif task.type == TaskType.SCREENSHOT:
                await self._execute_screenshot_task(task)
            elif task.type == TaskType.EXTRACT:
                await self._execute_extract_task(task)
            elif task.type == TaskType.INDEX:
                await self._execute_index_task(task)
            else:
                raise ValueError(f"Type de tâche non supporté: {task.type}")
            
            # Marquer comme terminée
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            
            logger.info(f"Tâche {task.id} terminée avec succès")
            
        except Exception as e:
            logger.error(f"Erreur exécution tâche {task.id}: {e}")
            task.status = TaskStatus.FAILED
            task.metadata["error"] = str(e)
            task.retries += 1
        
        finally:
            # Mettre à jour le statut
            await self._update_task_status(task)
            
            # Retirer de la liste locale
            if task.id in self.current_tasks:
                del self.current_tasks[task.id]
    
    async def _execute_archive_task(self, task: DistributedTask):
        """Exécute une tâche d'archivage"""
        url = task.data.get("url")
        if not url:
            raise ValueError("URL manquante pour l'archivage")
        
        # TODO: Intégrer avec le système d'archivage principal
        # Simuler le traitement
        await asyncio.sleep(2)
        
        logger.info(f"Archivage simulé: {url}")
    
    async def _execute_screenshot_task(self, task: DistributedTask):
        """Exécute une tâche de capture d'écran"""
        url = task.data.get("url")
        if not url:
            raise ValueError("URL manquante pour la capture")
        
        # TODO: Intégrer avec le système de capture
        await asyncio.sleep(1)
        
        logger.info(f"Capture simulée: {url}")
    
    async def _execute_extract_task(self, task: DistributedTask):
        """Exécute une tâche d'extraction de contenu"""
        file_path = task.data.get("file_path")
        if not file_path:
            raise ValueError("Chemin de fichier manquant")
        
        # TODO: Intégrer avec l'extraction de contenu
        await asyncio.sleep(1)
        
        logger.info(f"Extraction simulée: {file_path}")
    
    async def _execute_index_task(self, task: DistributedTask):
        """Exécute une tâche d'indexation"""
        resource_id = task.data.get("resource_id")
        if not resource_id:
            raise ValueError("ID de ressource manquant")
        
        # TODO: Intégrer avec l'indexation vectorielle/ES
        await asyncio.sleep(1)
        
        logger.info(f"Indexation simulée: {resource_id}")
    
    async def _update_task_status(self, task: DistributedTask):
        """Met à jour le statut d'une tâche"""
        if self.redis:
            try:
                await self.redis.hset(
                    "databot:tasks:status",
                    task.id,
                    json.dumps(asdict(task), default=str)
                )
            except Exception as e:
                logger.error(f"Erreur mise à jour statut tâche: {e}")
    
    async def submit_task(self, task_type: TaskType, data: Dict[str, Any], 
                         priority: int = 1) -> str:
        """Soumet une nouvelle tâche"""
        task = DistributedTask(
            id=str(uuid.uuid4()),
            type=task_type,
            status=TaskStatus.PENDING,
            data=data,
            priority=priority
        )
        
        if self.redis:
            # Ajouter à la queue Redis
            await self.redis.lpush(
                "databot:tasks:pending",
                json.dumps(asdict(task), default=str)
            )
        else:
            # Mode local - traiter immédiatement
            asyncio.create_task(self._execute_task(task))
        
        logger.info(f"Tâche soumise: {task.id} ({task_type.value})")
        return task.id
    
    async def get_cluster_status(self) -> ClusterStatus:
        """Récupère le statut du cluster"""
        try:
            if self.redis:
                # Compter les tâches
                pending = await self.redis.llen("databot:tasks:pending")
                status_data = await self.redis.hgetall("databot:tasks:status")
                
                active_tasks = 0
                completed_tasks = 0
                failed_tasks = 0
                
                for task_data in status_data.values():
                    try:
                        task_info = json.loads(task_data)
                        status = task_info["status"]
                        if status in ["assigned", "running"]:
                            active_tasks += 1
                        elif status == "completed":
                            completed_tasks += 1
                        elif status == "failed":
                            failed_tasks += 1
                    except Exception:
                        continue
            else:
                pending = 0
                active_tasks = len(self.current_tasks)
                completed_tasks = 0
                failed_tasks = 0
            
            total_capacity = sum(worker.max_tasks for worker in self.workers.values())
            if self.is_worker:
                total_capacity += self.max_concurrent_tasks
            
            # Déterminer la santé du cluster
            if total_capacity == 0:
                health = "no_workers"
            elif active_tasks / max(total_capacity, 1) > 0.8:
                health = "overloaded"
            elif len(self.workers) == 0 and self.is_coordinator:
                health = "coordinator_only"
            else:
                health = "healthy"
            
            return ClusterStatus(
                coordinator=self.node_id if self.is_coordinator else "unknown",
                workers=list(self.workers.values()),
                active_tasks=active_tasks,
                pending_tasks=pending,
                completed_tasks=completed_tasks,
                failed_tasks=failed_tasks,
                total_capacity=total_capacity,
                cluster_health=health
            )
            
        except Exception as e:
            logger.error(f"Erreur récupération statut cluster: {e}")
            return ClusterStatus(
                coordinator="error",
                workers=[],
                active_tasks=0,
                pending_tasks=0,
                completed_tasks=0,
                failed_tasks=0,
                total_capacity=0,
                cluster_health="error"
            )
    
    async def _send_heartbeat(self):
        """Envoie le heartbeat (pour workers)"""
        while self.running:
            try:
                if self.redis:
                    heartbeat_data = {
                        "timestamp": datetime.now().isoformat(),
                        "current_tasks": len(self.current_tasks),
                        "status": "active"
                    }
                    
                    await self.redis.hset(
                        f"databot:heartbeat:{self.node_id}",
                        mapping=heartbeat_data
                    )
                    
                    # Expiration du heartbeat
                    await self.redis.expire(f"databot:heartbeat:{self.node_id}", self.worker_timeout)
                
                await asyncio.sleep(self.heartbeat_interval)
                
            except Exception as e:
                logger.error(f"Erreur heartbeat: {e}")
                await asyncio.sleep(self.heartbeat_interval)
    
    async def shutdown(self):
        """Arrête le gestionnaire distribué"""
        logger.info("🛑 Arrêt du gestionnaire distribué")
        self.running = False
        
        # Désenregistrer le nœud
        if self.redis:
            try:
                await self.redis.hdel("databot:nodes", self.node_id)
                await self.redis.delete(f"databot:heartbeat:{self.node_id}")
                await self.redis.close()
            except Exception as e:
                logger.error(f"Erreur désenregistrement: {e}")
        
        logger.info("✅ Gestionnaire distribué arrêté")