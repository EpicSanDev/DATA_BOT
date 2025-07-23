"""
Gestionnaire d'erreurs centralisé pour ArchiveChain

Ce module fournit un système de gestion d'erreurs robuste avec logging sécurisé,
mécanismes de retry, et protection contre les fuites d'informations sensibles.

SÉCURITÉ: Toutes les données sensibles sont automatiquement masquées dans les logs
"""

import logging
import time
import json
import hashlib
import functools
from typing import Dict, Any, Optional, Callable, Union, List
from enum import Enum
from pathlib import Path

from .exceptions import BlockchainError, create_contextual_exception


class LogLevel(Enum):
    """Niveaux de logging sécurisé"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class SensitiveDataPattern:
    """Patterns pour identifier et masquer les données sensibles"""
    
    PATTERNS = {
        'private_key': r'[0-9a-fA-F]{64}',
        'signature': r'[0-9a-fA-F]{128,}',
        'password': r'password|pwd|secret',
        'token': r'token|key|auth',
        'address': r'0x[0-9a-fA-F]{40}',
        'hash': r'[0-9a-fA-F]{32,64}'
    }
    
    @classmethod
    def mask_sensitive_data(cls, data: Any) -> Any:
        """Masque automatiquement les données sensibles"""
        if isinstance(data, dict):
            return {k: cls._mask_value(k, v) for k, v in data.items()}
        elif isinstance(data, list):
            return [cls.mask_sensitive_data(item) for item in data]
        elif isinstance(data, str):
            return cls._mask_string(data)
        else:
            return data
    
    @classmethod
    def _mask_value(cls, key: str, value: Any) -> Any:
        """Masque la valeur selon la clé"""
        key_lower = str(key).lower()
        sensitive_keys = ['password', 'secret', 'private', 'key', 'token', 'signature']
        
        if any(sensitive in key_lower for sensitive in sensitive_keys):
            return "***MASKED***"
        
        return cls.mask_sensitive_data(value)
    
    @classmethod
    def _mask_string(cls, text: str) -> str:
        """Masque les patterns sensibles dans une chaîne"""
        if len(text) > 1000:  # Tronquer les chaînes très longues
            return text[:997] + "..."
        
        # Pour les hashes et addresses, masquer partiellement
        if len(text) == 64 and all(c in '0123456789abcdefABCDEF' for c in text):
            return text[:8] + "..." + text[-8:]
        
        return text


class RobustnessLogger:
    """Logger spécialisé pour la robustesse avec masquage automatique"""
    
    def __init__(self, name: str, log_dir: str = "logs"):
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Configuration du logger
        self.logger = logging.getLogger(f"archivechain.{name}")
        self.logger.setLevel(logging.DEBUG)
        
        # Éviter les doublons de handlers
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """Configure les handlers de logging"""
        # Handler pour fichier général
        file_handler = logging.FileHandler(
            self.log_dir / f"archivechain_{self.name}.log"
        )
        file_handler.setLevel(logging.INFO)
        
        # Handler pour erreurs critiques
        error_handler = logging.FileHandler(
            self.log_dir / f"archivechain_errors.log"
        )
        error_handler.setLevel(logging.ERROR)
        
        # Handler console pour développement
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        
        # Format sécurisé
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        for handler in [file_handler, error_handler, console_handler]:
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def log(self, level: LogLevel, message: str, context: Optional[Dict[str, Any]] = None,
            exception: Optional[Exception] = None):
        """Log avec masquage automatique des données sensibles"""
        
        # Masquer les données sensibles
        safe_context = SensitiveDataPattern.mask_sensitive_data(context or {})
        
        # Créer le message de log
        log_data = {
            "message": message,
            "context": safe_context,
            "timestamp": time.time(),
            "component": self.name
        }
        
        if exception:
            log_data["exception"] = {
                "type": type(exception).__name__,
                "message": str(exception),
                "context": getattr(exception, 'context', {}) if hasattr(exception, 'context') else {}
            }
        
        # Log selon le niveau
        log_message = json.dumps(log_data, indent=2)
        
        if level == LogLevel.DEBUG:
            self.logger.debug(log_message)
        elif level == LogLevel.INFO:
            self.logger.info(log_message)
        elif level == LogLevel.WARNING:
            self.logger.warning(log_message)
        elif level == LogLevel.ERROR:
            self.logger.error(log_message)
        elif level == LogLevel.CRITICAL:
            self.logger.critical(log_message)
    
    def debug(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Log de debug"""
        self.log(LogLevel.DEBUG, message, context)
    
    def info(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Log d'information"""
        self.log(LogLevel.INFO, message, context)
    
    def warning(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Log d'avertissement"""
        self.log(LogLevel.WARNING, message, context)
    
    def error(self, message: str, context: Optional[Dict[str, Any]] = None, 
              exception: Optional[Exception] = None):
        """Log d'erreur"""
        self.log(LogLevel.ERROR, message, context, exception)
    
    def critical(self, message: str, context: Optional[Dict[str, Any]] = None,
                 exception: Optional[Exception] = None):
        """Log critique"""
        self.log(LogLevel.CRITICAL, message, context, exception)


class RetryConfig:
    """Configuration pour les mécanismes de retry"""
    
    def __init__(self, max_attempts: int = 3, delay: float = 1.0, 
                 backoff_factor: float = 2.0, max_delay: float = 60.0):
        self.max_attempts = max_attempts
        self.delay = delay
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay


class ErrorHandler:
    """Gestionnaire d'erreurs centralisé avec retry et recovery"""
    
    def __init__(self):
        self.logger = RobustnessLogger("error_handler")
        self.error_counts: Dict[str, int] = {}
        self.circuit_breakers: Dict[str, Dict[str, Any]] = {}
    
    def handle_error(self, error: Exception, context: str, 
                     operation_id: Optional[str] = None,
                     retry_config: Optional[RetryConfig] = None) -> BlockchainError:
        """
        Gère une erreur de manière robuste et sécurisée
        
        Args:
            error: L'exception originale
            context: Contexte de l'erreur (transaction, consensus, etc.)
            operation_id: Identifiant unique de l'opération
            retry_config: Configuration pour les tentatives de retry
            
        Returns:
            Exception métier appropriée
        """
        
        # Générer un ID unique pour tracer l'erreur
        error_id = self._generate_error_id(error, context, operation_id)
        
        # Incrémenter le compteur d'erreurs
        error_key = f"{context}:{type(error).__name__}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        # Logger l'erreur de manière sécurisée
        self.logger.error(
            f"Error handled: {error_id}",
            context={
                "error_id": error_id,
                "error_type": type(error).__name__,
                "context": context,
                "operation_id": operation_id,
                "error_count": self.error_counts[error_key],
                "original_message": str(error)[:200]  # Tronquer pour sécurité
            },
            exception=error
        )
        
        # Créer une exception métier appropriée
        blockchain_error = self._create_contextual_error(error, context, error_id)
        
        # Vérifier le circuit breaker
        self._check_circuit_breaker(context, error_key)
        
        return blockchain_error
    
    def _generate_error_id(self, error: Exception, context: str, 
                          operation_id: Optional[str]) -> str:
        """Génère un ID unique pour tracer l'erreur"""
        error_data = f"{context}:{type(error).__name__}:{time.time()}"
        if operation_id:
            error_data += f":{operation_id}"
        
        return hashlib.sha256(error_data.encode()).hexdigest()[:16]
    
    def _create_contextual_error(self, original_error: Exception, 
                                context: str, error_id: str) -> BlockchainError:
        """Crée une exception métier contextuelle"""
        
        # Si c'est déjà une erreur blockchain, la retourner
        if isinstance(original_error, BlockchainError):
            return original_error
        
        # Mapper vers une exception appropriée
        error_message = f"Operation failed: {str(original_error)[:100]}"
        
        return create_contextual_exception(
            context, 
            error_message,
            error_id=error_id,
            original_error_type=type(original_error).__name__
        )
    
    def _check_circuit_breaker(self, context: str, error_key: str):
        """Vérifie et active le circuit breaker si nécessaire"""
        error_threshold = 10  # Seuil d'activation du circuit breaker
        time_window = 300  # 5 minutes
        
        current_time = time.time()
        
        if error_key not in self.circuit_breakers:
            self.circuit_breakers[error_key] = {
                "error_count": 0,
                "first_error_time": current_time,
                "is_open": False,
                "last_attempt_time": current_time
            }
        
        breaker = self.circuit_breakers[error_key]
        
        # Reset si la fenêtre de temps est dépassée
        if current_time - breaker["first_error_time"] > time_window:
            breaker["error_count"] = 1
            breaker["first_error_time"] = current_time
            breaker["is_open"] = False
        else:
            breaker["error_count"] += 1
        
        # Activer le circuit breaker si seuil dépassé
        if breaker["error_count"] >= error_threshold and not breaker["is_open"]:
            breaker["is_open"] = True
            self.logger.critical(
                f"Circuit breaker activated for {error_key}",
                context={
                    "error_key": error_key,
                    "error_count": breaker["error_count"],
                    "time_window": time_window
                }
            )
    
    def is_circuit_breaker_open(self, context: str, error_type: str) -> bool:
        """Vérifie si le circuit breaker est ouvert"""
        error_key = f"{context}:{error_type}"
        breaker = self.circuit_breakers.get(error_key, {})
        
        if breaker.get("is_open", False):
            # Vérifier si on peut tenter une nouvelle tentative (half-open state)
            current_time = time.time()
            cooldown_period = 60  # 1 minute de cooldown
            
            if current_time - breaker.get("last_attempt_time", 0) > cooldown_period:
                # Passer en état half-open
                breaker["last_attempt_time"] = current_time
                return False
            
            return True
        
        return False
    
    def reset_circuit_breaker(self, context: str, error_type: str):
        """Reset manuel du circuit breaker"""
        error_key = f"{context}:{error_type}"
        if error_key in self.circuit_breakers:
            self.circuit_breakers[error_key]["is_open"] = False
            self.circuit_breakers[error_key]["error_count"] = 0
            
            self.logger.info(
                f"Circuit breaker reset for {error_key}",
                context={"error_key": error_key}
            )
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Retourne les statistiques d'erreurs"""
        return {
            "error_counts": self.error_counts.copy(),
            "circuit_breakers": {
                key: {
                    "error_count": breaker["error_count"],
                    "is_open": breaker["is_open"],
                    "first_error_time": breaker["first_error_time"]
                }
                for key, breaker in self.circuit_breakers.items()
            },
            "total_errors": sum(self.error_counts.values())
        }


def robust_operation(context: str, retry_config: Optional[RetryConfig] = None,
                    circuit_breaker: bool = True):
    """
    Décorateur pour rendre une opération robuste avec gestion d'erreurs automatique
    
    Args:
        context: Contexte de l'opération (transaction, consensus, etc.)
        retry_config: Configuration des tentatives de retry
        circuit_breaker: Activer la protection circuit breaker
    """
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            error_handler = ErrorHandler()
            config = retry_config or RetryConfig()
            
            # Vérifier le circuit breaker
            if circuit_breaker and error_handler.is_circuit_breaker_open(context, func.__name__):
                raise create_contextual_exception(
                    context,
                    f"Circuit breaker is open for {func.__name__}",
                    operation=func.__name__
                )
            
            last_error = None
            
            for attempt in range(config.max_attempts):
                try:
                    # Tenter l'opération
                    result = func(*args, **kwargs)
                    
                    # Succès - reset du circuit breaker si applicable
                    if circuit_breaker and attempt > 0:
                        error_handler.reset_circuit_breaker(context, func.__name__)
                    
                    return result
                    
                except Exception as e:
                    last_error = e
                    
                    # Ne pas retry sur certaines erreurs critiques
                    if isinstance(e, (ValidationError, SignatureError)):
                        break
                    
                    # Attendre avant la prochaine tentative
                    if attempt < config.max_attempts - 1:
                        delay = min(
                            config.delay * (config.backoff_factor ** attempt),
                            config.max_delay
                        )
                        time.sleep(delay)
            
            # Toutes les tentatives ont échoué
            handled_error = error_handler.handle_error(
                last_error, 
                context, 
                operation_id=f"{func.__name__}_{int(time.time())}"
            )
            
            raise handled_error
            
        return wrapper
    return decorator


# Instance globale du gestionnaire d'erreurs
global_error_handler = ErrorHandler()