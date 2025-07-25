"""
Block structures for ArchiveChain

Implements the block structure specifically designed for archiving with
archive metadata, content index, and storage proofs.

SÉCURITÉ: Intègre la validation obligatoire des signatures ECDSA
ROBUSTESSE: Intègre la gestion d'erreurs robuste et la validation des données
"""

import json
import hashlib
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

from .archive_data import ArchiveData
from .security import signature_manager

# Import des modules de robustesse
from .utils.exceptions import (
    SignatureError, InvalidTransactionError, MiningError,
    ValidationError, create_contextual_exception
)
from .utils.error_handler import robust_operation, RetryConfig, global_error_handler
from .utils.validators import DataValidator

@dataclass
class BlockHeader:
    """Block header containing essential block information"""
    previous_hash: str  # Hash of previous block
    merkle_root: str   # Merkle root of all transactions/archives
    timestamp: float   # Unix timestamp
    nonce: int         # Proof of work nonce
    difficulty: int    # Mining difficulty
    block_height: int  # Block number in chain
    version: str = "1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BlockHeader':
        """Create from dictionary"""
        return cls(**data)
    
    def calculate_hash(self) -> str:
        """Calculate hash of the block header"""
        header_string = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(header_string.encode()).hexdigest()

@dataclass
class ArchiveTransaction:
    """Transaction representing an archive operation"""
    tx_id: str
    tx_type: str  # 'archive', 'verify', 'reward'
    archive_data: Optional[ArchiveData]
    sender: str   # Node ID performing the transaction
    receiver: Optional[str]  # For reward transactions
    amount: int = 0  # ARC tokens involved
    fee: int = 0     # Transaction fee
    timestamp: float = None
    signature: str = ""
    
    def __post_init__(self):
        """Initialize timestamp if not provided"""
        if self.timestamp is None:
            self.timestamp = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        if self.archive_data:
            data['archive_data'] = self.archive_data.to_dict()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ArchiveTransaction':
        """Create from dictionary"""
        archive_data_dict = data.pop('archive_data', None)
        if archive_data_dict:
            archive_data = ArchiveData.from_dict(archive_data_dict)
            return cls(archive_data=archive_data, **data)
        return cls(**data)
    
    def calculate_hash(self) -> str:
        """Calculate transaction hash"""
        tx_string = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(tx_string.encode()).hexdigest()
    
    @robust_operation("signature", RetryConfig(max_attempts=2))
    def sign_transaction(self, private_key) -> bool:
        """
        Signe la transaction avec une clé privée ECDSA avec gestion d'erreurs robuste
        
        CORRECTION CRITIQUE: Remplace except Exception par une gestion d'erreurs spécifique
        
        Args:
            private_key: Clé privée ECDSA pour signer
            
        Returns:
            True si la signature a réussi
            
        Raises:
            SignatureError: Si la signature échoue
            ValidationError: Si les données sont invalides
        """
        if not private_key:
            raise ValidationError(
                "Private key cannot be empty",
                field_name="private_key",
                expected_format="non_empty_key"
            )
        
        try:
            # Valider les données de transaction avant signature
            transaction_data = self.to_dict()
            
            # Vérifier que les données essentielles sont présentes
            required_fields = ['tx_id', 'tx_type', 'sender', 'timestamp']
            for field in required_fields:
                if field not in transaction_data or not transaction_data[field]:
                    raise ValidationError(
                        f"Missing required field for signature: {field}",
                        field_name=field,
                        expected_format="non_empty_value"
                    )
            
            # Signer la transaction
            self.signature = signature_manager.sign_transaction(transaction_data, private_key)
            
            if not self.signature:
                raise SignatureError(
                    "Signature operation returned empty result",
                    signature_type="transaction_signature"
                )
            
            return True
            
        except (ValidationError, SignatureError):
            # Propager les erreurs spécifiques
            raise
            
        except ValueError as e:
            raise ValidationError(
                f"Invalid data for signing: {str(e)}",
                field_name="transaction_data",
                actual_value=str(e)
            )
            
        except TypeError as e:
            raise ValidationError(
                f"Invalid data type for signing: {str(e)}",
                field_name="transaction_data",
                actual_value=str(e)
            )
            
        except Exception as e:
            # Gérer les erreurs inattendues de manière sécurisée
            handled_error = global_error_handler.handle_error(
                e,
                "signature",
                f"sign_transaction_{self.tx_id}"
            )
            raise handled_error
    
    @robust_operation("signature", RetryConfig(max_attempts=2))
    def verify_signature(self) -> bool:
        """
        Vérifie la signature de la transaction avec gestion d'erreurs robuste
        
        CORRECTION CRITIQUE: Remplace except Exception par une gestion d'erreurs spécifique
        
        Returns:
            True si la signature est valide
            
        Raises:
            SignatureError: Si la vérification de signature échoue
            ValidationError: Si les données sont invalides
        """
        if not self.signature or not self.signature.strip():
            raise SignatureError(
                "Transaction signature is missing or empty",
                signature_type="transaction_signature"
            )
        
        if not self.sender or not self.sender.strip():
            raise ValidationError(
                "Transaction sender is missing",
                field_name="sender",
                expected_format="non_empty_string"
            )
        
        try:
            # Préparer les données de transaction
            transaction_data = self.to_dict()
            
            # Vérifier que les données essentielles sont présentes
            if not transaction_data.get('tx_id'):
                raise ValidationError(
                    "Transaction ID missing from data",
                    field_name="tx_id",
                    expected_format="non_empty_string"
                )
            
            # Vérifier la signature
            is_valid = signature_manager.verify_transaction_signature(
                transaction_data,
                self.signature,
                self.sender
            )
            
            if not isinstance(is_valid, bool):
                raise SignatureError(
                    "Signature verification returned non-boolean result",
                    signature_type="transaction_signature"
                )
            
            return is_valid
            
        except (SignatureError, ValidationError):
            # Propager les erreurs spécifiques
            raise
            
        except ValueError as e:
            raise ValidationError(
                f"Invalid data for signature verification: {str(e)}",
                field_name="transaction_data",
                actual_value=str(e)
            )
            
        except TypeError as e:
            raise ValidationError(
                f"Invalid data type for signature verification: {str(e)}",
                field_name="transaction_data",
                actual_value=str(e)
            )
            
        except Exception as e:
            # Gérer les erreurs inattendues de manière sécurisée
            handled_error = global_error_handler.handle_error(
                e,
                "signature",
                f"verify_signature_{self.tx_id}"
            )
            raise handled_error
    
    def is_signed(self) -> bool:
        """
        Vérifie si la transaction est signée
        
        Returns:
            True si la transaction a une signature
        """
        return bool(self.signature and self.signature.strip())

class MerkleTree:
    """Simple Merkle tree implementation for transactions"""
    
    def __init__(self, transactions: List[ArchiveTransaction]):
        self.transactions = transactions
        self.tree = self.build_tree()
    
    def build_tree(self) -> List[List[str]]:
        """Build Merkle tree from transactions"""
        if not self.transactions:
            return [["0" * 64]]  # Empty tree
        
        # Start with transaction hashes
        current_level = [tx.calculate_hash() for tx in self.transactions]
        tree = [current_level.copy()]
        
        # Build tree bottom up
        while len(current_level) > 1:
            next_level = []
            
            # Process pairs
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                
                # Hash the pair
                combined = left + right
                parent_hash = hashlib.sha256(combined.encode()).hexdigest()
                next_level.append(parent_hash)
            
            tree.append(next_level)
            current_level = next_level
        
        return tree
    
    def get_root(self) -> str:
        """Get Merkle root"""
        if not self.tree:
            return "0" * 64
        return self.tree[-1][0]
    
    def get_proof(self, tx_index: int) -> List[Dict[str, Any]]:
        """Generate Merkle proof for a transaction"""
        if tx_index >= len(self.transactions):
            return []
        
        proof = []
        current_index = tx_index
        
        for level in self.tree[:-1]:  # Exclude root level
            if len(level) <= 1:
                break
            
            # Find sibling
            if current_index % 2 == 0:  # Left child
                sibling_index = current_index + 1
                position = "right"
            else:  # Right child
                sibling_index = current_index - 1
                position = "left"
            
            if sibling_index < len(level):
                sibling_hash = level[sibling_index]
            else:
                sibling_hash = level[current_index]  # Duplicate for odd number
            
            proof.append({
                "hash": sibling_hash,
                "position": position
            })
            
            current_index //= 2
        
        return proof

class Block:
    """Basic block structure"""
    
    def __init__(self, previous_hash: str, block_height: int):
        self.header = BlockHeader(
            previous_hash=previous_hash,
            merkle_root="",
            timestamp=time.time(),
            nonce=0,
            difficulty=1,
            block_height=block_height
        )
        self.transactions: List[ArchiveTransaction] = []
        self.hash = ""
    
    def add_transaction(self, transaction: ArchiveTransaction):
        """Add transaction to block"""
        self.transactions.append(transaction)
        self.update_merkle_root()
    
    def update_merkle_root(self):
        """Update Merkle root after adding transactions"""
        merkle_tree = MerkleTree(self.transactions)
        self.header.merkle_root = merkle_tree.get_root()
    
    def calculate_hash(self) -> str:
        """Calculate block hash"""
        return self.header.calculate_hash()
    
    def mine_block(self, difficulty: int) -> bool:
        """Mine block with given difficulty"""
        self.header.difficulty = difficulty
        target = "0" * difficulty
        
        while True:
            self.hash = self.calculate_hash()
            if self.hash.startswith(target):
                return True
            self.header.nonce += 1
            
            # Prevent infinite loop in tests
            if self.header.nonce > 1000000:
                return False
    
    def is_valid(self) -> bool:
        """Validate block"""
        # Check hash
        if self.hash != self.calculate_hash():
            return False
        
        # Check difficulty
        target = "0" * self.header.difficulty
        if not self.hash.startswith(target):
            return False
        
        # Validate transactions
        for tx in self.transactions:
            if not self.validate_transaction(tx):
                return False
        
        return True
    
    def validate_transaction(self, tx: ArchiveTransaction) -> bool:
        """
        Validate a transaction with mandatory signature verification
        
        CORRECTION CRITIQUE: Validation obligatoire des signatures pour toutes les transactions
        """
        # Basic validation
        if not tx.tx_id or not tx.sender:
            return False
        
        # OBLIGATOIRE: Vérification de la signature ECDSA
        if not tx.is_signed():
            return False
        
        if not tx.verify_signature():
            return False
        
        # Validate archive data if present
        if tx.archive_data and not tx.archive_data.validate():
            return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert block to dictionary"""
        return {
            "header": self.header.to_dict(),
            "transactions": [tx.to_dict() for tx in self.transactions],
            "hash": self.hash
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Block':
        """Create block from dictionary"""
        header_data = data["header"]
        header = BlockHeader.from_dict(header_data)
        
        block = cls(header.previous_hash, header.block_height)
        block.header = header
        
        # Add transactions
        for tx_data in data["transactions"]:
            tx = ArchiveTransaction.from_dict(tx_data)
            block.transactions.append(tx)
        
        block.hash = data["hash"]
        return block

class ArchiveBlock(Block):
    """Specialized block for archive operations with additional metadata"""
    
    def __init__(self, previous_hash: str, block_height: int):
        super().__init__(previous_hash, block_height)
        
        # Archive-specific data
        self.archive_count = 0
        self.total_archive_size = 0
        self.storage_proofs: List[Dict[str, Any]] = []
        self.content_index: Dict[str, List[str]] = {}  # content_type -> archive_ids
        self.replication_info: Dict[str, List[str]] = {}  # archive_id -> node_ids
    
    def add_archive_transaction(self, tx: ArchiveTransaction):
        """Add archive transaction with additional processing"""
        self.add_transaction(tx)
        
        if tx.archive_data:
            # Update archive statistics
            self.archive_count += 1
            self.total_archive_size += tx.archive_data.size_compressed
            
            # Update content index
            content_type = tx.archive_data.content_type
            if content_type not in self.content_index:
                self.content_index[content_type] = []
            self.content_index[content_type].append(tx.archive_data.archive_id)
            
            # Update replication info
            archive_id = tx.archive_data.archive_id
            self.replication_info[archive_id] = tx.archive_data.storage_nodes.copy()
    
    def add_storage_proof(self, proof: Dict[str, Any]):
        """Add proof of storage for validation"""
        self.storage_proofs.append(proof)
    
    def get_archive_stats(self) -> Dict[str, Any]:
        """Get archive statistics for this block"""
        return {
            "archive_count": self.archive_count,
            "total_size": self.total_archive_size,
            "content_types": list(self.content_index.keys()),
            "unique_archives": len(self.replication_info),
            "total_replicas": sum(len(nodes) for nodes in self.replication_info.values())
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with archive-specific data"""
        data = super().to_dict()
        data.update({
            "archive_count": self.archive_count,
            "total_archive_size": self.total_archive_size,
            "storage_proofs": self.storage_proofs,
            "content_index": self.content_index,
            "replication_info": self.replication_info
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ArchiveBlock':
        """Create from dictionary"""
        # Create base block first
        block = super().from_dict(data)
        
        # Convert to ArchiveBlock
        archive_block = cls(block.header.previous_hash, block.header.block_height)
        archive_block.header = block.header
        archive_block.transactions = block.transactions
        archive_block.hash = block.hash
        
        # Add archive-specific data
        archive_block.archive_count = data.get("archive_count", 0)
        archive_block.total_archive_size = data.get("total_archive_size", 0)
        archive_block.storage_proofs = data.get("storage_proofs", [])
        archive_block.content_index = data.get("content_index", {})
        archive_block.replication_info = data.get("replication_info", {})
        
        return archive_block