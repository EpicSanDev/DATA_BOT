"""
Mécanismes de récupération pour ArchiveChain

Ce module fournit des systèmes robustes de récupération automatique,
de sauvegarde et de rollback pour maintenir la stabilité du système.

SÉCURITÉ: Tous les mécanismes incluent une vérification d'intégrité
"""

import json
import time
import os
import shutil
import hashlib
import threading
from typing import Dict, Any, List, Optional, Callable, Union
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta

from .exceptions import BlockchainError, create_contextual_exception
from .error_handler import RobustnessLogger


class RecoveryType(Enum):
    """Types de récupération disponibles"""
    AUTO_RETRY = "auto_retry"
    CHECKPOINT_ROLLBACK = "checkpoint_rollback"
    STATE_REPAIR = "state_repair"
    EMERGENCY_STOP = "emergency_stop"


class CheckpointType(Enum):
    """Types de checkpoints"""
    SCHEDULED = "scheduled"
    MANUAL = "manual"
    PRE_OPERATION = "pre_operation"
    EMERGENCY = "emergency"


@dataclass
class Checkpoint:
    """Point de sauvegarde du système"""
    checkpoint_id: str
    checkpoint_type: CheckpointType
    created_at: float
    description: str
    state_hash: str
    file_path: str
    size_bytes: int
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire"""
        data = asdict(self)
        data['checkpoint_type'] = self.checkpoint_type.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Checkpoint':
        """Crée depuis un dictionnaire"""
        data['checkpoint_type'] = CheckpointType(data['checkpoint_type'])
        return cls(**data)


@dataclass
class RecoveryOperation:
    """Opération de récupération"""
    operation_id: str
    recovery_type: RecoveryType
    started_at: float
    completed_at: Optional[float]
    success: Optional[bool]
    error_message: Optional[str]
    checkpoint_used: Optional[str]
    affected_components: List[str]
    recovery_steps: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire"""
        data = asdict(self)
        data['recovery_type'] = self.recovery_type.value
        return data


class CheckpointManager:
    """Gestionnaire de points de sauvegarde"""
    
    def __init__(self, checkpoint_dir: str = "checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(exist_ok=True)
        self.logger = RobustnessLogger("checkpoint_manager")
        
        self.checkpoints: Dict[str, Checkpoint] = {}
        self.checkpoint_lock = threading.RLock()
        self.max_checkpoints = 50  # Limite du nombre de checkpoints
        
        # Charger les checkpoints existants
        self._load_existing_checkpoints()
    
    def create_checkpoint(self, state_data: Dict[str, Any], 
                         checkpoint_type: CheckpointType = CheckpointType.MANUAL,
                         description: str = "Manual checkpoint") -> str:
        """
        Crée un nouveau checkpoint
        
        Args:
            state_data: Données d'état à sauvegarder
            checkpoint_type: Type de checkpoint
            description: Description du checkpoint
            
        Returns:
            ID du checkpoint créé
        """
        
        checkpoint_id = self._generate_checkpoint_id(checkpoint_type, description)
        
        with self.checkpoint_lock:
            try:
                # Sérialiser les données
                serialized_data = json.dumps(state_data, indent=2, sort_keys=True)
                
                # Calculer le hash d'intégrité
                state_hash = hashlib.sha256(serialized_data.encode()).hexdigest()
                
                # Chemin du fichier
                file_path = self.checkpoint_dir / f"{checkpoint_id}.json"
                
                # Écrire le fichier
                with open(file_path, 'w') as f:
                    f.write(serialized_data)
                
                # Créer l'objet checkpoint
                checkpoint = Checkpoint(
                    checkpoint_id=checkpoint_id,
                    checkpoint_type=checkpoint_type,
                    created_at=time.time(),
                    description=description,
                    state_hash=state_hash,
                    file_path=str(file_path),
                    size_bytes=len(serialized_data.encode()),
                    metadata={
                        "components": list(state_data.keys()),
                        "total_size": len(serialized_data),
                        "creation_method": "json_serialization"
                    }
                )
                
                # Stocker le checkpoint
                self.checkpoints[checkpoint_id] = checkpoint
                
                # Nettoyer les anciens checkpoints si nécessaire
                self._cleanup_old_checkpoints()
                
                # Sauvegarder l'index des checkpoints
                self._save_checkpoint_index()
                
                self.logger.info(
                    f"Checkpoint created: {checkpoint_id}",
                    context={
                        "checkpoint_id": checkpoint_id,
                        "checkpoint_type": checkpoint_type.value,
                        "description": description,
                        "size_bytes": checkpoint.size_bytes,
                        "components": len(state_data)
                    }
                )
                
                return checkpoint_id
                
            except Exception as e:
                self.logger.error(
                    f"Failed to create checkpoint: {checkpoint_id}",
                    context={
                        "checkpoint_id": checkpoint_id,
                        "error": str(e)
                    },
                    exception=e
                )
                raise create_contextual_exception(
                    "storage", 
                    f"Failed to create checkpoint: {str(e)}",
                    checkpoint_id=checkpoint_id
                )
    
    def restore_checkpoint(self, checkpoint_id: str) -> Dict[str, Any]:
        """
        Restaure un checkpoint
        
        Args:
            checkpoint_id: ID du checkpoint à restaurer
            
        Returns:
            Données d'état restaurées
        """
        
        with self.checkpoint_lock:
            if checkpoint_id not in self.checkpoints:
                raise create_contextual_exception(
                    "storage",
                    f"Checkpoint not found: {checkpoint_id}",
                    checkpoint_id=checkpoint_id
                )
            
            checkpoint = self.checkpoints[checkpoint_id]
            
            try:
                # Lire le fichier
                with open(checkpoint.file_path, 'r') as f:
                    serialized_data = f.read()
                
                # Vérifier l'intégrité
                actual_hash = hashlib.sha256(serialized_data.encode()).hexdigest()
                if actual_hash != checkpoint.state_hash:
                    raise create_contextual_exception(
                        "storage",
                        f"Checkpoint integrity check failed: {checkpoint_id}",
                        checkpoint_id=checkpoint_id,
                        expected_hash=checkpoint.state_hash,
                        actual_hash=actual_hash
                    )
                
                # Désérialiser
                state_data = json.loads(serialized_data)
                
                self.logger.info(
                    f"Checkpoint restored: {checkpoint_id}",
                    context={
                        "checkpoint_id": checkpoint_id,
                        "checkpoint_type": checkpoint.checkpoint_type.value,
                        "created_at": checkpoint.created_at,
                        "components": len(state_data)
                    }
                )
                
                return state_data
                
            except Exception as e:
                self.logger.error(
                    f"Failed to restore checkpoint: {checkpoint_id}",
                    context={
                        "checkpoint_id": checkpoint_id,
                        "error": str(e)
                    },
                    exception=e
                )
                raise create_contextual_exception(
                    "storage",
                    f"Failed to restore checkpoint: {str(e)}",
                    checkpoint_id=checkpoint_id
                )
    
    def list_checkpoints(self, checkpoint_type: Optional[CheckpointType] = None) -> List[Checkpoint]:
        """Liste les checkpoints disponibles"""
        with self.checkpoint_lock:
            checkpoints = list(self.checkpoints.values())
            
            if checkpoint_type:
                checkpoints = [cp for cp in checkpoints if cp.checkpoint_type == checkpoint_type]
            
            # Trier par date de création (plus récent en premier)
            checkpoints.sort(key=lambda x: x.created_at, reverse=True)
            
            return checkpoints
    
    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """Supprime un checkpoint"""
        with self.checkpoint_lock:
            if checkpoint_id not in self.checkpoints:
                return False
            
            checkpoint = self.checkpoints[checkpoint_id]
            
            try:
                # Supprimer le fichier
                if os.path.exists(checkpoint.file_path):
                    os.remove(checkpoint.file_path)
                
                # Supprimer de la mémoire
                del self.checkpoints[checkpoint_id]
                
                # Sauvegarder l'index mis à jour
                self._save_checkpoint_index()
                
                self.logger.info(
                    f"Checkpoint deleted: {checkpoint_id}",
                    context={"checkpoint_id": checkpoint_id}
                )
                
                return True
                
            except Exception as e:
                self.logger.error(
                    f"Failed to delete checkpoint: {checkpoint_id}",
                    context={
                        "checkpoint_id": checkpoint_id,
                        "error": str(e)
                    },
                    exception=e
                )
                return False
    
    def _generate_checkpoint_id(self, checkpoint_type: CheckpointType, description: str) -> str:
        """Génère un ID unique pour le checkpoint"""
        timestamp = str(time.time())
        type_str = checkpoint_type.value
        desc_hash = hashlib.sha256(description.encode()).hexdigest()[:8]
        
        checkpoint_data = f"{type_str}:{timestamp}:{desc_hash}"
        return hashlib.sha256(checkpoint_data.encode()).hexdigest()[:16]
    
    def _cleanup_old_checkpoints(self):
        """Nettoie les anciens checkpoints"""
        if len(self.checkpoints) <= self.max_checkpoints:
            return
        
        # Trier par date de création
        sorted_checkpoints = sorted(
            self.checkpoints.items(),
            key=lambda x: x[1].created_at
        )
        
        # Supprimer les plus anciens (mais garder au moins 10 emergency/manual)
        protected_types = {CheckpointType.EMERGENCY, CheckpointType.MANUAL}
        protected_count = sum(
            1 for _, cp in sorted_checkpoints 
            if cp.checkpoint_type in protected_types
        )
        
        min_protected = min(10, protected_count)
        deleted_count = 0
        
        for checkpoint_id, checkpoint in sorted_checkpoints:
            if len(self.checkpoints) - deleted_count <= self.max_checkpoints:
                break
            
            # Protéger les checkpoints critiques récents
            if checkpoint.checkpoint_type in protected_types and min_protected > 0:
                min_protected -= 1
                continue
            
            # Supprimer le checkpoint
            if self.delete_checkpoint(checkpoint_id):
                deleted_count += 1
        
        if deleted_count > 0:
            self.logger.info(
                f"Cleaned up {deleted_count} old checkpoints",
                context={
                    "deleted_count": deleted_count,
                    "remaining_count": len(self.checkpoints)
                }
            )
    
    def _load_existing_checkpoints(self):
        """Charge les checkpoints existants au démarrage"""
        index_file = self.checkpoint_dir / "checkpoint_index.json"
        
        if not index_file.exists():
            return
        
        try:
            with open(index_file, 'r') as f:
                index_data = json.load(f)
            
            for cp_data in index_data.get("checkpoints", []):
                try:
                    checkpoint = Checkpoint.from_dict(cp_data)
                    
                    # Vérifier que le fichier existe
                    if os.path.exists(checkpoint.file_path):
                        self.checkpoints[checkpoint.checkpoint_id] = checkpoint
                    else:
                        self.logger.warning(
                            f"Checkpoint file missing: {checkpoint.file_path}",
                            context={"checkpoint_id": checkpoint.checkpoint_id}
                        )
                
                except Exception as e:
                    self.logger.error(
                        f"Failed to load checkpoint from index",
                        context={"error": str(e)},
                        exception=e
                    )
            
            self.logger.info(
                f"Loaded {len(self.checkpoints)} existing checkpoints",
                context={"checkpoint_count": len(self.checkpoints)}
            )
            
        except Exception as e:
            self.logger.error(
                f"Failed to load checkpoint index",
                context={"error": str(e)},
                exception=e
            )
    
    def _save_checkpoint_index(self):
        """Sauvegarde l'index des checkpoints"""
        index_file = self.checkpoint_dir / "checkpoint_index.json"
        
        try:
            index_data = {
                "last_updated": time.time(),
                "checkpoint_count": len(self.checkpoints),
                "checkpoints": [cp.to_dict() for cp in self.checkpoints.values()]
            }
            
            with open(index_file, 'w') as f:
                json.dump(index_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(
                f"Failed to save checkpoint index",
                context={"error": str(e)},
                exception=e
            )


class RecoveryManager:
    """Gestionnaire principal de récupération"""
    
    def __init__(self, checkpoint_manager: CheckpointManager):
        self.checkpoint_manager = checkpoint_manager
        self.logger = RobustnessLogger("recovery_manager")
        
        self.recovery_operations: Dict[str, RecoveryOperation] = {}
        self.recovery_lock = threading.RLock()
        
        # Configuration de récupération
        self.recovery_config = {
            "max_retry_attempts": 3,
            "retry_delay_base": 1.0,
            "retry_delay_multiplier": 2.0,
            "auto_checkpoint_interval": 300,  # 5 minutes
            "emergency_threshold": 10,  # Nombre d'erreurs avant emergency stop
        }
        
        # Compteurs d'erreurs pour emergency stop
        self.error_counters: Dict[str, int] = {}
        self.last_reset_time = time.time()
    
    def create_pre_operation_checkpoint(self, operation_name: str, 
                                      state_data: Dict[str, Any]) -> str:
        """Crée un checkpoint avant une opération critique"""
        description = f"Pre-operation checkpoint for {operation_name}"
        
        return self.checkpoint_manager.create_checkpoint(
            state_data,
            CheckpointType.PRE_OPERATION,
            description
        )
    
    def auto_recover_operation(self, operation_func: Callable, 
                              operation_name: str,
                              state_data: Dict[str, Any],
                              *args, **kwargs) -> Any:
        """
        Exécute une opération avec récupération automatique
        
        Args:
            operation_func: Fonction à exécuter
            operation_name: Nom de l'opération
            state_data: État actuel du système
            *args, **kwargs: Arguments pour la fonction
            
        Returns:
            Résultat de l'opération
        """
        
        operation_id = self._generate_operation_id(operation_name)
        
        # Créer un checkpoint pré-opération
        checkpoint_id = self.create_pre_operation_checkpoint(operation_name, state_data)
        
        # Initialiser l'opération de récupération
        recovery_op = RecoveryOperation(
            operation_id=operation_id,
            recovery_type=RecoveryType.AUTO_RETRY,
            started_at=time.time(),
            completed_at=None,
            success=None,
            error_message=None,
            checkpoint_used=checkpoint_id,
            affected_components=[operation_name],
            recovery_steps=[]
        )
        
        with self.recovery_lock:
            self.recovery_operations[operation_id] = recovery_op
        
        # Tenter l'opération avec retry automatique
        max_attempts = self.recovery_config["max_retry_attempts"]
        base_delay = self.recovery_config["retry_delay_base"]
        multiplier = self.recovery_config["retry_delay_multiplier"]
        
        last_error = None
        
        for attempt in range(max_attempts):
            try:
                self.logger.debug(
                    f"Attempting operation: {operation_name} (attempt {attempt + 1}/{max_attempts})",
                    context={
                        "operation_id": operation_id,
                        "operation_name": operation_name,
                        "attempt": attempt + 1
                    }
                )
                
                # Exécuter l'opération
                result = operation_func(*args, **kwargs)
                
                # Succès !
                recovery_op.completed_at = time.time()
                recovery_op.success = True
                recovery_op.recovery_steps.append({
                    "step": "operation_success",
                    "attempt": attempt + 1,
                    "timestamp": time.time()
                })
                
                self.logger.info(
                    f"Operation succeeded: {operation_name}",
                    context={
                        "operation_id": operation_id,
                        "attempts_used": attempt + 1,
                        "total_time": recovery_op.completed_at - recovery_op.started_at
                    }
                )
                
                return result
                
            except Exception as e:
                last_error = e
                
                recovery_op.recovery_steps.append({
                    "step": "operation_failed",
                    "attempt": attempt + 1,
                    "error": str(e),
                    "timestamp": time.time()
                })
                
                self.logger.warning(
                    f"Operation failed (attempt {attempt + 1}): {operation_name}",
                    context={
                        "operation_id": operation_id,
                        "attempt": attempt + 1,
                        "error": str(e)
                    },
                    exception=e
                )
                
                # Vérifier si on doit déclencher emergency stop
                self._check_emergency_threshold(operation_name)
                
                # Attendre avant de retry (sauf pour la dernière tentative)
                if attempt < max_attempts - 1:
                    delay = base_delay * (multiplier ** attempt)
                    time.sleep(delay)
                    
                    recovery_op.recovery_steps.append({
                        "step": "retry_delay",
                        "delay_seconds": delay,
                        "timestamp": time.time()
                    })
        
        # Toutes les tentatives ont échoué
        recovery_op.completed_at = time.time()
        recovery_op.success = False
        recovery_op.error_message = str(last_error)
        
        self.logger.error(
            f"Operation failed after all retries: {operation_name}",
            context={
                "operation_id": operation_id,
                "total_attempts": max_attempts,
                "final_error": str(last_error)
            },
            exception=last_error
        )
        
        # Tenter de restaurer le checkpoint
        try:
            self.rollback_to_checkpoint(checkpoint_id, operation_name)
            recovery_op.recovery_steps.append({
                "step": "checkpoint_rollback",
                "checkpoint_id": checkpoint_id,
                "timestamp": time.time()
            })
        except Exception as rollback_error:
            self.logger.critical(
                f"Failed to rollback after operation failure: {operation_name}",
                context={
                    "operation_id": operation_id,
                    "checkpoint_id": checkpoint_id,
                    "rollback_error": str(rollback_error)
                },
                exception=rollback_error
            )
        
        # Propager l'erreur finale
        raise create_contextual_exception(
            "recovery",
            f"Operation failed after {max_attempts} attempts: {str(last_error)}",
            operation_id=operation_id,
            operation_name=operation_name,
            attempts=max_attempts
        )
    
    def rollback_to_checkpoint(self, checkpoint_id: str, 
                              reason: str = "Manual rollback") -> Dict[str, Any]:
        """
        Effectue un rollback vers un checkpoint spécifique
        
        Args:
            checkpoint_id: ID du checkpoint vers lequel rollback
            reason: Raison du rollback
            
        Returns:
            État restauré
        """
        
        operation_id = self._generate_operation_id("rollback")
        
        recovery_op = RecoveryOperation(
            operation_id=operation_id,
            recovery_type=RecoveryType.CHECKPOINT_ROLLBACK,
            started_at=time.time(),
            completed_at=None,
            success=None,
            error_message=None,
            checkpoint_used=checkpoint_id,
            affected_components=["system_state"],
            recovery_steps=[]
        )
        
        with self.recovery_lock:
            self.recovery_operations[operation_id] = recovery_op
        
        try:
            # Restaurer le checkpoint
            restored_state = self.checkpoint_manager.restore_checkpoint(checkpoint_id)
            
            recovery_op.completed_at = time.time()
            recovery_op.success = True
            recovery_op.recovery_steps.append({
                "step": "state_restored",
                "checkpoint_id": checkpoint_id,
                "reason": reason,
                "timestamp": time.time()
            })
            
            self.logger.info(
                f"Rollback completed successfully",
                context={
                    "operation_id": operation_id,
                    "checkpoint_id": checkpoint_id,
                    "reason": reason,
                    "components_restored": len(restored_state)
                }
            )
            
            return restored_state
            
        except Exception as e:
            recovery_op.completed_at = time.time()
            recovery_op.success = False
            recovery_op.error_message = str(e)
            
            self.logger.error(
                f"Rollback failed",
                context={
                    "operation_id": operation_id,
                    "checkpoint_id": checkpoint_id,
                    "error": str(e)
                },
                exception=e
            )
            
            raise create_contextual_exception(
                "recovery",
                f"Rollback failed: {str(e)}",
                operation_id=operation_id,
                checkpoint_id=checkpoint_id
            )
    
    def _check_emergency_threshold(self, operation_name: str):
        """Vérifie si le seuil d'emergency stop est atteint"""
        current_time = time.time()
        
        # Reset des compteurs toutes les heures
        if current_time - self.last_reset_time > 3600:
            self.error_counters.clear()
            self.last_reset_time = current_time
        
        # Incrémenter le compteur d'erreurs
        self.error_counters[operation_name] = self.error_counters.get(operation_name, 0) + 1
        
        # Vérifier le seuil
        if self.error_counters[operation_name] >= self.recovery_config["emergency_threshold"]:
            self.logger.critical(
                f"Emergency threshold reached for operation: {operation_name}",
                context={
                    "operation_name": operation_name,
                    "error_count": self.error_counters[operation_name],
                    "threshold": self.recovery_config["emergency_threshold"]
                }
            )
            
            # Déclencher emergency stop (pourrait être implémenté selon les besoins)
            # Pour l'instant, on se contente de logger
    
    def _generate_operation_id(self, operation_name: str) -> str:
        """Génère un ID unique pour l'opération de récupération"""
        timestamp = str(time.time())
        op_hash = hashlib.sha256(operation_name.encode()).hexdigest()[:8]
        
        op_data = f"{operation_name}:{timestamp}:{op_hash}"
        return hashlib.sha256(op_data.encode()).hexdigest()[:16]
    
    def get_recovery_statistics(self) -> Dict[str, Any]:
        """Retourne les statistiques de récupération"""
        with self.recovery_lock:
            total_operations = len(self.recovery_operations)
            successful_operations = sum(
                1 for op in self.recovery_operations.values() 
                if op.success is True
            )
            failed_operations = sum(
                1 for op in self.recovery_operations.values() 
                if op.success is False
            )
            
            return {
                "total_recovery_operations": total_operations,
                "successful_recoveries": successful_operations,
                "failed_recoveries": failed_operations,
                "success_rate": successful_operations / total_operations if total_operations > 0 else 0,
                "error_counters": self.error_counters.copy(),
                "available_checkpoints": len(self.checkpoint_manager.checkpoints),
                "recovery_config": self.recovery_config.copy()
            }


# Instances globales
global_checkpoint_manager = CheckpointManager()
global_recovery_manager = RecoveryManager(global_checkpoint_manager)