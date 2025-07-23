"""
Exceptions métier spécifiques pour ArchiveChain

Ce module définit toutes les exceptions spécifiques au domaine blockchain
pour remplacer les gestions d'erreurs génériques dangereuses.

SÉCURITÉ: Toutes les exceptions masquent automatiquement les données sensibles
"""

import time
from typing import Optional, Dict, Any


class BlockchainError(Exception):
    """Exception de base pour toutes les erreurs blockchain"""
    
    def __init__(self, message: str, error_code: str = "BLOCKCHAIN_ERROR", 
                 context: Optional[Dict[str, Any]] = None, sensitive_data: bool = False):
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        self.timestamp = time.time()
        self.sensitive_data = sensitive_data
        
        # Masquer les données sensibles dans les logs
        if sensitive_data:
            super().__init__(f"[{error_code}] Sensitive operation failed")
        else:
            super().__init__(f"[{error_code}] {message}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'exception en dictionnaire pour le logging"""
        return {
            "error_code": self.error_code,
            "message": self.message if not self.sensitive_data else "***MASKED***",
            "context": self.context if not self.sensitive_data else {"masked": True},
            "timestamp": self.timestamp,
            "type": self.__class__.__name__
        }


class InvalidTransactionError(BlockchainError):
    """Erreurs liées aux transactions invalides"""
    
    def __init__(self, message: str, transaction_id: Optional[str] = None, 
                 validation_errors: Optional[list] = None):
        super().__init__(
            message, 
            "INVALID_TRANSACTION",
            context={
                "transaction_id": transaction_id,
                "validation_errors": validation_errors or []
            }
        )


class ConsensusError(BlockchainError):
    """Erreurs liées au mécanisme de consensus"""
    
    def __init__(self, message: str, node_id: Optional[str] = None, 
                 consensus_state: Optional[str] = None):
        super().__init__(
            message,
            "CONSENSUS_ERROR", 
            context={
                "node_id": node_id,
                "consensus_state": consensus_state
            }
        )


class NetworkError(BlockchainError):
    """Erreurs liées au réseau et communication P2P"""
    
    def __init__(self, message: str, peer_id: Optional[str] = None,
                 connection_type: Optional[str] = None):
        super().__init__(
            message,
            "NETWORK_ERROR",
            context={
                "peer_id": peer_id,
                "connection_type": connection_type
            }
        )


class StorageError(BlockchainError):
    """Erreurs liées au stockage des archives"""
    
    def __init__(self, message: str, archive_id: Optional[str] = None,
                 storage_operation: Optional[str] = None):
        super().__init__(
            message,
            "STORAGE_ERROR",
            context={
                "archive_id": archive_id,
                "storage_operation": storage_operation
            }
        )


class ValidationError(BlockchainError):
    """Erreurs de validation des données"""
    
    def __init__(self, message: str, field_name: Optional[str] = None,
                 expected_format: Optional[str] = None, actual_value: Optional[str] = None):
        super().__init__(
            message,
            "VALIDATION_ERROR",
            context={
                "field_name": field_name,
                "expected_format": expected_format,
                "actual_value": actual_value if actual_value and len(str(actual_value)) < 100 else "***TRUNCATED***"
            }
        )


class ConcurrencyError(BlockchainError):
    """Erreurs liées à la concurrence et aux race conditions"""
    
    def __init__(self, message: str, resource_id: Optional[str] = None,
                 operation_type: Optional[str] = None):
        super().__init__(
            message,
            "CONCURRENCY_ERROR",
            context={
                "resource_id": resource_id,
                "operation_type": operation_type
            }
        )


class SignatureError(BlockchainError):
    """Erreurs liées aux signatures cryptographiques"""
    
    def __init__(self, message: str, signature_type: Optional[str] = None):
        super().__init__(
            message,
            "SIGNATURE_ERROR",
            context={"signature_type": signature_type},
            sensitive_data=True  # Les erreurs de signature sont toujours sensibles
        )


class ContractExecutionError(BlockchainError):
    """Erreurs d'exécution des contrats intelligents"""
    
    def __init__(self, message: str, contract_id: Optional[str] = None,
                 function_name: Optional[str] = None, execution_step: Optional[str] = None):
        super().__init__(
            message,
            "CONTRACT_ERROR",
            context={
                "contract_id": contract_id,
                "function_name": function_name,
                "execution_step": execution_step
            }
        )


class TokenOperationError(BlockchainError):
    """Erreurs liées aux opérations sur les tokens ARC"""
    
    def __init__(self, message: str, operation_type: Optional[str] = None,
                 address: Optional[str] = None, amount: Optional[str] = None):
        super().__init__(
            message,
            "TOKEN_ERROR",
            context={
                "operation_type": operation_type,
                "address": address,
                "amount": amount
            }
        )


class ArchiveIntegrityError(BlockchainError):
    """Erreurs d'intégrité des archives"""
    
    def __init__(self, message: str, archive_id: Optional[str] = None,
                 integrity_check: Optional[str] = None):
        super().__init__(
            message,
            "ARCHIVE_INTEGRITY_ERROR",
            context={
                "archive_id": archive_id,
                "integrity_check": integrity_check
            }
        )


class NodeOperationError(BlockchainError):
    """Erreurs d'opération des nœuds du réseau"""
    
    def __init__(self, message: str, node_id: Optional[str] = None,
                 operation: Optional[str] = None, node_status: Optional[str] = None):
        super().__init__(
            message,
            "NODE_ERROR",
            context={
                "node_id": node_id,
                "operation": operation,
                "node_status": node_status
            }
        )


class MiningError(BlockchainError):
    """Erreurs liées au processus de mining"""
    
    def __init__(self, message: str, block_height: Optional[int] = None,
                 difficulty: Optional[int] = None, miner_id: Optional[str] = None):
        super().__init__(
            message,
            "MINING_ERROR",
            context={
                "block_height": block_height,
                "difficulty": difficulty,
                "miner_id": miner_id
            }
        )


class ResourceExhaustionError(BlockchainError):
    """Erreurs de dépassement de limites de ressources"""
    
    def __init__(self, message: str, resource_type: Optional[str] = None,
                 current_usage: Optional[str] = None, limit: Optional[str] = None):
        super().__init__(
            message,
            "RESOURCE_EXHAUSTION",
            context={
                "resource_type": resource_type,
                "current_usage": current_usage,
                "limit": limit
            }
        )


# Utilitaires pour mapping des exceptions
EXCEPTION_MAPPING = {
    "transaction": InvalidTransactionError,
    "consensus": ConsensusError,
    "network": NetworkError,
    "storage": StorageError,
    "validation": ValidationError,
    "concurrency": ConcurrencyError,
    "signature": SignatureError,
    "contract": ContractExecutionError,
    "token": TokenOperationError,
    "archive": ArchiveIntegrityError,
    "node": NodeOperationError,
    "mining": MiningError,
    "resource": ResourceExhaustionError
}


def get_exception_for_context(context: str) -> type:
    """Retourne la classe d'exception appropriée pour un contexte donné"""
    return EXCEPTION_MAPPING.get(context, BlockchainError)


def create_contextual_exception(context: str, message: str, **kwargs) -> BlockchainError:
    """Crée une exception contextuelle appropriée"""
    exception_class = get_exception_for_context(context)
    return exception_class(message, **kwargs)