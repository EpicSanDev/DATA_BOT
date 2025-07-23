"""
Module de planification pour DATA_BOT v2
Système de tâches programmées type cron
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict
from enum import Enum
import re

from src.core.config import Config
from src.database.database import DatabaseManager

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskFrequency(Enum):
    ONCE = "once"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"

@dataclass
class ScheduledTask:
    """Représente une tâche programmée"""
    id: str
    name: str
    task_type: str  # archive, export, cleanup, etc.
    frequency: TaskFrequency
    cron_expression: Optional[str] = None
    parameters: Dict[str, Any] = None
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    created_at: Optional[datetime] = None
    error_message: Optional[str] = None
    run_count: int = 0
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.parameters is None:
            self.parameters = {}
        if self.next_run is None:
            self.next_run = self._calculate_next_run()
    
    def _calculate_next_run(self) -> datetime:
        """Calcule la prochaine exécution"""
        now = datetime.now()
        
        if self.frequency == TaskFrequency.ONCE:
            return now
        elif self.frequency == TaskFrequency.HOURLY:
            return now + timedelta(hours=1)
        elif self.frequency == TaskFrequency.DAILY:
            return now.replace(hour=2, minute=0, second=0, microsecond=0) + timedelta(days=1)
        elif self.frequency == TaskFrequency.WEEKLY:
            days_ahead = 0 - now.weekday()  # Lundi = 0
            if days_ahead <= 0:
                days_ahead += 7
            return (now + timedelta(days=days_ahead)).replace(hour=2, minute=0, second=0, microsecond=0)
        elif self.frequency == TaskFrequency.MONTHLY:
            if now.month == 12:
                next_month = now.replace(year=now.year + 1, month=1, day=1, hour=2, minute=0, second=0, microsecond=0)
            else:
                next_month = now.replace(month=now.month + 1, day=1, hour=2, minute=0, second=0, microsecond=0)
            return next_month
        elif self.frequency == TaskFrequency.CUSTOM and self.cron_expression:
            return self._parse_cron_next_run(self.cron_expression)
        else:
            return now + timedelta(minutes=5)  # Défaut: 5 minutes
    
    def _parse_cron_next_run(self, cron_expr: str) -> datetime:
        """Parse une expression cron simplifiée et calcule la prochaine exécution"""
        # Format simplifié: "minute hour day month weekday"
        # Exemple: "0 2 * * *" = tous les jours à 2h00
        # Exemple: "*/30 * * * *" = toutes les 30 minutes
        
        try:
            parts = cron_expr.split()
            if len(parts) != 5:
                raise ValueError("Expression cron doit avoir 5 parties")
            
            minute, hour, day, month, weekday = parts
            now = datetime.now()
            
            # Calcul simplifié pour les cas courants
            if cron_expr == "0 2 * * *":  # Quotidien à 2h
                next_run = now.replace(hour=2, minute=0, second=0, microsecond=0)
                if next_run <= now:
                    next_run += timedelta(days=1)
                return next_run
            
            elif cron_expr.startswith("*/"):  # Intervalles
                interval = int(cron_expr.split()[0][2:])
                if "hour" in cron_expr:
                    return now + timedelta(hours=interval)
                else:  # minutes par défaut
                    return now + timedelta(minutes=interval)
            
            else:
                # Fallback: toutes les heures
                return now + timedelta(hours=1)
                
        except Exception as e:
            logger.warning(f"Erreur parsing cron '{cron_expr}': {e}")
            return datetime.now() + timedelta(hours=1)
    
    def update_next_run(self):
        """Met à jour la prochaine exécution après completion"""
        if self.frequency == TaskFrequency.ONCE:
            self.status = TaskStatus.COMPLETED
            self.next_run = None
        else:
            self.next_run = self._calculate_next_run()
            self.status = TaskStatus.PENDING

class TaskScheduler:
    """Planificateur de tâches pour DATA_BOT"""
    
    def __init__(self):
        self.tasks: Dict[str, ScheduledTask] = {}
        self.running = False
        self.scheduler_task = None
        
        # Handlers pour différents types de tâches
        self.task_handlers = {
            'archive': self._handle_archive_task,
            'export': self._handle_export_task,
            'cleanup': self._handle_cleanup_task,
            'compression': self._handle_compression_task,
            'duplicate_check': self._handle_duplicate_check_task,
            'proxy_test': self._handle_proxy_test_task
        }
    
    async def start(self):
        """Démarre le planificateur"""
        if self.running:
            return
        
        self.running = True
        logger.info("⏰ Planificateur de tâches démarré")
        
        # Charger les tâches sauvegardées
        await self._load_tasks()
        
        # Créer les tâches par défaut si nécessaire
        await self._create_default_tasks()
        
        # Démarrer la boucle de planification
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
    
    async def stop(self):
        """Arrête le planificateur"""
        self.running = False
        
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        
        # Sauvegarder les tâches
        await self._save_tasks()
        
        logger.info("⏰ Planificateur de tâches arrêté")
    
    async def _scheduler_loop(self):
        """Boucle principale du planificateur"""
        while self.running:
            try:
                await self._check_and_execute_tasks()
                await asyncio.sleep(60)  # Vérifier toutes les minutes
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erreur dans la boucle du planificateur: {e}")
                await asyncio.sleep(60)
    
    async def _check_and_execute_tasks(self):
        """Vérifie et exécute les tâches dues"""
        now = datetime.now()
        
        for task in list(self.tasks.values()):
            if (task.status == TaskStatus.PENDING and 
                task.next_run and 
                task.next_run <= now):
                
                # Exécuter la tâche
                await self._execute_task(task)
    
    async def _execute_task(self, task: ScheduledTask):
        """Exécute une tâche spécifique"""
        logger.info(f"▶️ Exécution de la tâche: {task.name}")
        
        task.status = TaskStatus.RUNNING
        task.last_run = datetime.now()
        task.run_count += 1
        
        try:
            handler = self.task_handlers.get(task.task_type)
            if handler:
                await handler(task)
                task.status = TaskStatus.COMPLETED
                task.error_message = None
                logger.info(f"✅ Tâche terminée: {task.name}")
            else:
                raise ValueError(f"Handler non trouvé pour le type: {task.task_type}")
                
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            logger.error(f"❌ Échec de la tâche {task.name}: {e}")
        
        # Programmer la prochaine exécution
        task.update_next_run()
        
        # Sauvegarder l'état
        await self._save_tasks()
    
    async def _handle_archive_task(self, task: ScheduledTask):
        """Gère les tâches d'archivage"""
        from main import ArchiveBot
        
        mode = task.parameters.get('mode', 'process')
        seed_urls = task.parameters.get('seed_urls', [])
        
        bot = ArchiveBot()
        await bot.start(mode=mode, seed_urls=seed_urls)
    
    async def _handle_export_task(self, task: ScheduledTask):
        """Gère les tâches d'export"""
        from src.utils.export_manager import ExportManager
        
        export_manager = ExportManager()
        format_type = task.parameters.get('format', 'json')
        include_files = task.parameters.get('include_files', False)
        
        await export_manager.export_archive(format_type, include_files)
    
    async def _handle_cleanup_task(self, task: ScheduledTask):
        """Gère les tâches de nettoyage"""
        from src.utils.export_manager import ExportManager
        from src.utils.compression_manager import CompressionManager
        
        # Nettoyer les anciens exports
        export_manager = ExportManager()
        max_exports = task.parameters.get('max_exports', 10)
        await export_manager.cleanup_old_exports(max_exports)
        
        # Nettoyer les artefacts de compression
        compression_manager = CompressionManager()
        await compression_manager.cleanup_compression_artifacts()
    
    async def _handle_compression_task(self, task: ScheduledTask):
        """Gère les tâches de compression"""
        from src.utils.compression_manager import CompressionManager
        
        compression_manager = CompressionManager()
        force_recompress = task.parameters.get('force_recompress', False)
        
        await compression_manager.compress_archive(force_recompress)
    
    async def _handle_duplicate_check_task(self, task: ScheduledTask):
        """Gère les tâches de vérification des doublons"""
        from src.core.duplicate_detector import DuplicateDetector
        
        detector = DuplicateDetector()
        await detector.detect_duplicates()
        await detector.mark_duplicates_in_database()
    
    async def _handle_proxy_test_task(self, task: ScheduledTask):
        """Gère les tâches de test des proxies"""
        from src.utils.proxy_manager import ProxyManager
        
        proxy_manager = ProxyManager()
        await proxy_manager.test_all_proxies()
    
    async def add_task(self, task: ScheduledTask) -> str:
        """Ajoute une nouvelle tâche"""
        if not task.id:
            task.id = f"task_{int(datetime.now().timestamp())}"
        
        self.tasks[task.id] = task
        await self._save_tasks()
        
        logger.info(f"➕ Tâche ajoutée: {task.name} (ID: {task.id})")
        return task.id
    
    async def remove_task(self, task_id: str) -> bool:
        """Supprime une tâche"""
        if task_id in self.tasks:
            del self.tasks[task_id]
            await self._save_tasks()
            logger.info(f"➖ Tâche supprimée: {task_id}")
            return True
        return False
    
    async def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Récupère une tâche par ID"""
        return self.tasks.get(task_id)
    
    async def list_tasks(self) -> List[ScheduledTask]:
        """Liste toutes les tâches"""
        return list(self.tasks.values())
    
    async def cancel_task(self, task_id: str) -> bool:
        """Annule une tâche"""
        task = self.tasks.get(task_id)
        if task and task.status != TaskStatus.RUNNING:
            task.status = TaskStatus.CANCELLED
            await self._save_tasks()
            logger.info(f"🚫 Tâche annulée: {task_id}")
            return True
        return False
    
    async def reschedule_task(self, task_id: str, new_frequency: TaskFrequency, 
                            cron_expression: str = None) -> bool:
        """Reprogramme une tâche"""
        task = self.tasks.get(task_id)
        if task:
            task.frequency = new_frequency
            task.cron_expression = cron_expression
            task.next_run = task._calculate_next_run()
            task.status = TaskStatus.PENDING
            await self._save_tasks()
            logger.info(f"📅 Tâche reprogrammée: {task_id}")
            return True
        return False
    
    async def _create_default_tasks(self):
        """Crée les tâches par défaut"""
        default_tasks = [
            {
                'name': 'Archivage quotidien',
                'task_type': 'archive',
                'frequency': TaskFrequency.DAILY,
                'parameters': {'mode': 'process'}
            },
            {
                'name': 'Export hebdomadaire',
                'task_type': 'export', 
                'frequency': TaskFrequency.WEEKLY,
                'parameters': {'format': 'json', 'include_files': False}
            },
            {
                'name': 'Nettoyage mensuel',
                'task_type': 'cleanup',
                'frequency': TaskFrequency.MONTHLY,
                'parameters': {'max_exports': 10}
            },
            {
                'name': 'Compression automatique',
                'task_type': 'compression',
                'frequency': TaskFrequency.WEEKLY,
                'parameters': {'force_recompress': False}
            },
            {
                'name': 'Vérification doublons',
                'task_type': 'duplicate_check',
                'frequency': TaskFrequency.WEEKLY,
                'parameters': {}
            }
        ]
        
        existing_names = {task.name for task in self.tasks.values()}
        
        for task_def in default_tasks:
            if task_def['name'] not in existing_names:
                task = ScheduledTask(
                    id=f"default_{task_def['task_type']}",
                    name=task_def['name'],
                    task_type=task_def['task_type'],
                    frequency=task_def['frequency'],
                    parameters=task_def['parameters']
                )
                await self.add_task(task)
    
    async def _save_tasks(self):
        """Sauvegarde les tâches en base de données"""
        try:
            tasks_data = {}
            for task_id, task in self.tasks.items():
                tasks_data[task_id] = {
                    **asdict(task),
                    'frequency': task.frequency.value,
                    'status': task.status.value,
                    'created_at': task.created_at.isoformat() if task.created_at else None,
                    'next_run': task.next_run.isoformat() if task.next_run else None,
                    'last_run': task.last_run.isoformat() if task.last_run else None
                }
            
            # Sauvegarder dans un fichier de configuration
            import os
            config_dir = os.path.dirname(Config.DATABASE_PATH)
            tasks_file = os.path.join(config_dir, 'scheduled_tasks.json')
            
            with open(tasks_file, 'w', encoding='utf-8') as f:
                json.dump(tasks_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Erreur sauvegarde tâches: {e}")
    
    async def _load_tasks(self):
        """Charge les tâches depuis la base de données"""
        try:
            import os
            config_dir = os.path.dirname(Config.DATABASE_PATH)
            tasks_file = os.path.join(config_dir, 'scheduled_tasks.json')
            
            if not os.path.exists(tasks_file):
                return
            
            with open(tasks_file, 'r', encoding='utf-8') as f:
                tasks_data = json.load(f)
            
            for task_id, task_dict in tasks_data.items():
                try:
                    # Convertir les dates
                    if task_dict.get('created_at'):
                        task_dict['created_at'] = datetime.fromisoformat(task_dict['created_at'])
                    if task_dict.get('next_run'):
                        task_dict['next_run'] = datetime.fromisoformat(task_dict['next_run'])
                    if task_dict.get('last_run'):
                        task_dict['last_run'] = datetime.fromisoformat(task_dict['last_run'])
                    
                    # Convertir les enums
                    task_dict['frequency'] = TaskFrequency(task_dict['frequency'])
                    task_dict['status'] = TaskStatus(task_dict['status'])
                    
                    task = ScheduledTask(**task_dict)
                    self.tasks[task_id] = task
                    
                except Exception as e:
                    logger.warning(f"Erreur chargement tâche {task_id}: {e}")
            
            logger.info(f"📋 {len(self.tasks)} tâches chargées")
            
        except Exception as e:
            logger.error(f"Erreur chargement tâches: {e}")
    
    async def get_schedule_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du planificateur"""
        now = datetime.now()
        
        stats = {
            'total_tasks': len(self.tasks),
            'pending_tasks': 0,
            'running_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'next_execution': None,
            'tasks_by_type': {},
            'tasks_by_frequency': {}
        }
        
        next_runs = []
        
        for task in self.tasks.values():
            # Compter par statut
            stats[f"{task.status.value}_tasks"] += 1
            
            # Compter par type
            task_type = task.task_type
            stats['tasks_by_type'][task_type] = stats['tasks_by_type'].get(task_type, 0) + 1
            
            # Compter par fréquence
            frequency = task.frequency.value
            stats['tasks_by_frequency'][frequency] = stats['tasks_by_frequency'].get(frequency, 0) + 1
            
            # Prochaine exécution
            if task.next_run and task.status == TaskStatus.PENDING:
                next_runs.append(task.next_run)
        
        if next_runs:
            stats['next_execution'] = min(next_runs).isoformat()
        
        return stats