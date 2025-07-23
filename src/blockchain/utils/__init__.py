"""
Modules utilitaires pour la robustesse d'ArchiveChain

Ce package contient tous les modules nécessaires pour améliorer la robustesse,
la gestion d'erreurs, et la stabilité du système blockchain ArchiveChain.
"""

from .exceptions import *
from .error_handler import ErrorHandler, RobustnessLogger
from .concurrency import ConcurrencyManager, AtomicLock
from .validators import DataValidator, URLValidator, MetadataValidator
from .recovery import RecoveryManager, CheckpointManager
from .monitoring import HealthMonitor, SystemMetrics

__all__ = [
    # Exceptions
    'BlockchainError', 'InvalidTransactionError', 'ConsensusError', 
    'NetworkError', 'StorageError', 'ValidationError', 'ConcurrencyError',
    
    # Error handling
    'ErrorHandler', 'RobustnessLogger',
    
    # Concurrency
    'ConcurrencyManager', 'AtomicLock',
    
    # Validation
    'DataValidator', 'URLValidator', 'MetadataValidator',
    
    # Recovery
    'RecoveryManager', 'CheckpointManager',
    
    # Monitoring
    'HealthMonitor', 'SystemMetrics'
]

# Version de robustesse
ROBUSTNESS_VERSION = "1.0.0"