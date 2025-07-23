"""
Gestionnaire de concurrence pour ArchiveChain

Ce module fournit des mécanismes robustes pour gérer la concurrence et prévenir
les race conditions dans les opérations critiques de la blockchain.

SÉCURITÉ: Implémente des verrous atomiques et des transactions sécurisées
"""

import time
import threading
import uuid
import hashlib
import functools
from typing import Dict, Any, Optional, Callable, Union, Set, List
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum

from .exceptions import ConcurrencyError
from .error_handler import RobustnessLogger


class LockType(Enum):
    """Types de verrous disponibles"""
    SHARED = "shared"      # Lecture partagée
    EXCLUSIVE = "exclusive"  # Écriture exclusive
    UPGRADE = "upgrade"     # Peut être upgradé de shared à exclusive


@dataclass
class LockInfo:
    """Information sur un verrou actif"""
    lock_id: str
    resource_id: str
    lock_type: LockType
    owner_thread: str
    acquired_at: float
    expires_at: Optional[float] = None
    operation_context: Optional[str] = None


class AtomicLock:
    """Verrou atomique avec support pour différents types d'accès"""
    
    def __init__(self, resource_id: str, timeout: float = 30.0):
        self.resource_id = resource_id
        self.timeout = timeout
        self.logger = RobustnessLogger(f"lock_{resource_id}")
        
        # Verrous internes
        self._lock = threading.RLock()
        self._shared_locks: Set[str] = set()
        self._exclusive_lock: Optional[str] = None
        self._lock_queue: List[Dict[str, Any]] = []
        
        # Statistiques
        self.stats = {
            "total_acquisitions": 0,
            "total_releases": 0,
            "total_timeouts": 0,
            "total_contentions": 0,
            "max_wait_time": 0.0,
            "current_holders": 0
        }
    
    @contextmanager
    def acquire(self, lock_type: LockType = LockType.EXCLUSIVE, 
                operation_context: Optional[str] = None):
        """
        Gestionnaire de contexte pour acquérir un verrou atomique
        
        Args:
            lock_type: Type de verrou à acquérir
            operation_context: Contexte de l'opération pour le debugging
        """
        lock_id = self._generate_lock_id()
        thread_id = str(threading.current_thread().ident)
        
        acquired = False
        start_time = time.time()
        
        try:
            # Tenter d'acquérir le verrou
            acquired = self._acquire_lock(lock_id, lock_type, thread_id, operation_context)
            
            if not acquired:
                wait_time = time.time() - start_time
                self.stats["total_timeouts"] += 1
                self.stats["max_wait_time"] = max(self.stats["max_wait_time"], wait_time)
                
                raise ConcurrencyError(
                    f"Failed to acquire {lock_type.value} lock for {self.resource_id}",
                    resource_id=self.resource_id,
                    operation_type=operation_context
                )
            
            # Mettre à jour les statistiques
            wait_time = time.time() - start_time
            self.stats["total_acquisitions"] += 1
            self.stats["max_wait_time"] = max(self.stats["max_wait_time"], wait_time)
            self.stats["current_holders"] += 1
            
            self.logger.debug(
                f"Lock acquired: {lock_id}",
                context={
                    "lock_id": lock_id,
                    "lock_type": lock_type.value,
                    "resource_id": self.resource_id,
                    "thread_id": thread_id,
                    "wait_time": wait_time,
                    "operation_context": operation_context
                }
            )
            
            yield lock_id
            
        finally:
            if acquired:
                self._release_lock(lock_id, lock_type, thread_id)
                self.stats["total_releases"] += 1
                self.stats["current_holders"] -= 1
                
                self.logger.debug(
                    f"Lock released: {lock_id}",
                    context={
                        "lock_id": lock_id,
                        "resource_id": self.resource_id,
                        "thread_id": thread_id
                    }
                )
    
    def _acquire_lock(self, lock_id: str, lock_type: LockType, 
                     thread_id: str, operation_context: Optional[str]) -> bool:
        """Acquiert le verrou de manière atomique"""
        end_time = time.time() + self.timeout
        
        while time.time() < end_time:
            with self._lock:
                if self._can_acquire_lock(lock_type, thread_id):
                    self._grant_lock(lock_id, lock_type, thread_id, operation_context)
                    return True
                else:
                    # Ajouter à la queue d'attente
                    self._add_to_queue(lock_id, lock_type, thread_id, operation_context)
                    self.stats["total_contentions"] += 1
            
            # Attendre un peu avant de réessayer
            time.sleep(0.01)  # 10ms
        
        return False
    
    def _can_acquire_lock(self, lock_type: LockType, thread_id: str) -> bool:
        """Vérifie si le verrou peut être acquis"""
        if lock_type == LockType.SHARED:
            # Verrou partagé : OK si pas de verrou exclusif
            return self._exclusive_lock is None
        
        elif lock_type == LockType.EXCLUSIVE:
            # Verrou exclusif : OK si aucun autre verrou
            return self._exclusive_lock is None and len(self._shared_locks) == 0
        
        elif lock_type == LockType.UPGRADE:
            # Upgrade : OK si le thread détient déjà un verrou partagé et pas d'exclusif
            return (thread_id in self._shared_locks and 
                   self._exclusive_lock is None and 
                   len(self._shared_locks) == 1)
        
        return False
    
    def _grant_lock(self, lock_id: str, lock_type: LockType, 
                   thread_id: str, operation_context: Optional[str]):
        """Accorde le verrou"""
        if lock_type == LockType.SHARED:
            self._shared_locks.add(lock_id)
        
        elif lock_type == LockType.EXCLUSIVE:
            self._exclusive_lock = lock_id
        
        elif lock_type == LockType.UPGRADE:
            # Retirer le verrou partagé et accorder l'exclusif
            shared_locks_to_remove = [lid for lid in self._shared_locks 
                                    if lid.endswith(thread_id)]
            for lid in shared_locks_to_remove:
                self._shared_locks.discard(lid)
            self._exclusive_lock = lock_id
    
    def _release_lock(self, lock_id: str, lock_type: LockType, thread_id: str):
        """Libère le verrou"""
        with self._lock:
            if lock_type == LockType.SHARED:
                self._shared_locks.discard(lock_id)
            
            elif lock_type in [LockType.EXCLUSIVE, LockType.UPGRADE]:
                if self._exclusive_lock == lock_id:
                    self._exclusive_lock = None
            
            # Traiter la queue d'attente
            self._process_queue()
    
    def _add_to_queue(self, lock_id: str, lock_type: LockType, 
                     thread_id: str, operation_context: Optional[str]):
        """Ajoute une demande à la queue d'attente"""
        queue_entry = {
            "lock_id": lock_id,
            "lock_type": lock_type,
            "thread_id": thread_id,
            "operation_context": operation_context,
            "queued_at": time.time()
        }
        
        # Insérer selon la priorité (exclusif en premier)
        if lock_type == LockType.EXCLUSIVE:
            self._lock_queue.insert(0, queue_entry)
        else:
            self._lock_queue.append(queue_entry)
    
    def _process_queue(self):
        """Traite la queue d'attente pour accorder les verrous en attente"""
        processed = []
        
        for entry in self._lock_queue:
            if self._can_acquire_lock(entry["lock_type"], entry["thread_id"]):
                self._grant_lock(
                    entry["lock_id"], 
                    entry["lock_type"], 
                    entry["thread_id"],
                    entry["operation_context"]
                )
                processed.append(entry)
        
        # Retirer les entrées traitées
        for entry in processed:
            self._lock_queue.remove(entry)
    
    def _generate_lock_id(self) -> str:
        """Génère un ID unique pour le verrou"""
        thread_id = str(threading.current_thread().ident)
        timestamp = str(time.time())
        unique_id = str(uuid.uuid4())
        
        lock_data = f"{self.resource_id}:{thread_id}:{timestamp}:{unique_id}"
        return hashlib.sha256(lock_data.encode()).hexdigest()[:16]
    
    def get_lock_info(self) -> Dict[str, Any]:
        """Retourne les informations sur l'état du verrou"""
        with self._lock:
            return {
                "resource_id": self.resource_id,
                "shared_locks": list(self._shared_locks),
                "exclusive_lock": self._exclusive_lock,
                "queue_length": len(self._lock_queue),
                "stats": self.stats.copy()
            }


class ConcurrencyManager:
    """Gestionnaire global de concurrence pour ArchiveChain"""
    
    def __init__(self):
        self.locks: Dict[str, AtomicLock] = {}
        self.global_lock = threading.RLock()
        self.logger = RobustnessLogger("concurrency_manager")
        
        # Transactions atomiques
        self.active_transactions: Dict[str, Dict[str, Any]] = {}
        self.transaction_lock = threading.RLock()
    
    def get_lock(self, resource_id: str, timeout: float = 30.0) -> AtomicLock:
        """Obtient ou crée un verrou pour une ressource"""
        with self.global_lock:
            if resource_id not in self.locks:
                self.locks[resource_id] = AtomicLock(resource_id, timeout)
            return self.locks[resource_id]
    
    @contextmanager
    def atomic_operation(self, resource_ids: List[str], 
                        operation_context: str = "atomic_operation",
                        lock_type: LockType = LockType.EXCLUSIVE):
        """
        Gestionnaire de contexte pour opérations atomiques multi-ressources
        
        Args:
            resource_ids: Liste des ressources à verrouiller
            operation_context: Contexte de l'opération
            lock_type: Type de verrou à utiliser
        """
        
        # Trier les IDs pour éviter les deadlocks
        sorted_ids = sorted(resource_ids)
        acquired_locks = []
        transaction_id = self._generate_transaction_id(operation_context)
        
        try:
            # Acquérir tous les verrous dans l'ordre trié
            for resource_id in sorted_ids:
                lock = self.get_lock(resource_id)
                lock_context = lock.acquire(lock_type, operation_context)
                lock_id = lock_context.__enter__()
                acquired_locks.append((lock_context, lock_id, resource_id))
            
            # Enregistrer la transaction
            self._register_transaction(transaction_id, sorted_ids, operation_context)
            
            self.logger.info(
                f"Atomic operation started: {transaction_id}",
                context={
                    "transaction_id": transaction_id,
                    "resource_ids": sorted_ids,
                    "operation_context": operation_context,
                    "locks_acquired": len(acquired_locks)
                }
            )
            
            yield transaction_id
            
        except Exception as e:
            self.logger.error(
                f"Atomic operation failed: {transaction_id}",
                context={
                    "transaction_id": transaction_id,
                    "error": str(e),
                    "operation_context": operation_context
                },
                exception=e
            )
            raise
            
        finally:
            # Libérer tous les verrous dans l'ordre inverse
            for lock_context, lock_id, resource_id in reversed(acquired_locks):
                try:
                    lock_context.__exit__(None, None, None)
                except Exception as e:
                    self.logger.error(
                        f"Failed to release lock for {resource_id}",
                        context={
                            "resource_id": resource_id,
                            "lock_id": lock_id,
                            "transaction_id": transaction_id
                        },
                        exception=e
                    )
            
            # Désenregistrer la transaction
            self._unregister_transaction(transaction_id)
            
            self.logger.info(
                f"Atomic operation completed: {transaction_id}",
                context={
                    "transaction_id": transaction_id,
                    "operation_context": operation_context
                }
            )
    
    def _register_transaction(self, transaction_id: str, resource_ids: List[str], 
                             operation_context: str):
        """Enregistre une transaction atomique"""
        with self.transaction_lock:
            self.active_transactions[transaction_id] = {
                "resource_ids": resource_ids,
                "operation_context": operation_context,
                "started_at": time.time(),
                "thread_id": str(threading.current_thread().ident)
            }
    
    def _unregister_transaction(self, transaction_id: str):
        """Désenregistre une transaction atomique"""
        with self.transaction_lock:
            if transaction_id in self.active_transactions:
                del self.active_transactions[transaction_id]
    
    def _generate_transaction_id(self, operation_context: str) -> str:
        """Génère un ID unique pour la transaction"""
        thread_id = str(threading.current_thread().ident)
        timestamp = str(time.time())
        unique_id = str(uuid.uuid4())
        
        tx_data = f"{operation_context}:{thread_id}:{timestamp}:{unique_id}"
        return hashlib.sha256(tx_data.encode()).hexdigest()[:16]
    
    def get_concurrency_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de concurrence"""
        with self.global_lock:
            lock_stats = {}
            for resource_id, lock in self.locks.items():
                lock_stats[resource_id] = lock.get_lock_info()
        
        with self.transaction_lock:
            active_tx_count = len(self.active_transactions)
            active_tx_contexts = [
                tx["operation_context"] 
                for tx in self.active_transactions.values()
            ]
        
        return {
            "total_locks": len(self.locks),
            "active_transactions": active_tx_count,
            "transaction_contexts": active_tx_contexts,
            "lock_statistics": lock_stats
        }
    
    def detect_deadlocks(self) -> List[Dict[str, Any]]:
        """Détecte les deadlocks potentiels"""
        potential_deadlocks = []
        
        with self.transaction_lock:
            # Analyser les transactions actives pour détecter des cycles
            for tx_id, tx_info in self.active_transactions.items():
                tx_age = time.time() - tx_info["started_at"]
                
                # Transaction trop longue = deadlock potentiel
                if tx_age > 60:  # 1 minute
                    potential_deadlocks.append({
                        "transaction_id": tx_id,
                        "age_seconds": tx_age,
                        "resource_ids": tx_info["resource_ids"],
                        "operation_context": tx_info["operation_context"],
                        "thread_id": tx_info["thread_id"]
                    })
        
        return potential_deadlocks
    
    def cleanup_stale_locks(self, max_age_seconds: float = 300):
        """Nettoie les verrous périmés (5 minutes par défaut)"""
        current_time = time.time()
        cleaned_count = 0
        
        with self.global_lock:
            stale_locks = []
            
            for resource_id, lock in self.locks.items():
                lock_info = lock.get_lock_info()
                
                # Vérifier s'il y a des verrous très anciens
                if (lock_info["shared_locks"] or lock_info["exclusive_lock"]) and \
                   current_time - lock.stats.get("last_acquisition", current_time) > max_age_seconds:
                    stale_locks.append(resource_id)
            
            # Supprimer les verrous périmés
            for resource_id in stale_locks:
                del self.locks[resource_id]
                cleaned_count += 1
        
        if cleaned_count > 0:
            self.logger.warning(
                f"Cleaned up {cleaned_count} stale locks",
                context={
                    "cleaned_count": cleaned_count,
                    "max_age_seconds": max_age_seconds
                }
            )
        
        return cleaned_count


# Instance globale du gestionnaire de concurrence
global_concurrency_manager = ConcurrencyManager()


def atomic_contract_operation(contract_id: str, operation_name: str):
    """
    Décorateur pour rendre les opérations de contrat atomiques
    
    Usage:
        @atomic_contract_operation("contract_123", "verify_submission")
        def verify_submission(self, ...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            resource_ids = [f"contract:{contract_id}"]
            
            with global_concurrency_manager.atomic_operation(
                resource_ids, 
                f"{operation_name}_{contract_id}"
            ):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator