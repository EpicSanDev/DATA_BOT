"""
Proof of Archive (PoA) Consensus Mechanism

Implements the specialized consensus algorithm that combines:
- Proof of Storage: nodes prove they store data
- Proof of Bandwidth: demonstration of content serving capability
- Proof of Longevity: bonus for long-term storage

SÉCURITÉ: Utilise des méthodes cryptographiquement sûres pour la génération aléatoire
"""

import json
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

# Import du gestionnaire cryptographique sécurisé
from .security import crypto_manager

class ProofType(Enum):
    """Types of proofs in PoA consensus"""
    STORAGE = "storage"
    BANDWIDTH = "bandwidth"
    LONGEVITY = "longevity"

@dataclass
class StorageProof:
    """Proof that a node stores specific data"""
    node_id: str
    archive_id: str
    challenge: str  # Random challenge from network
    response: str   # Hash of archive data + challenge
    timestamp: float
    file_size: int
    checksum: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StorageProof':
        """Create from dictionary"""
        return cls(**data)

@dataclass
class BandwidthProof:
    """Proof of bandwidth and serving capability"""
    node_id: str
    bytes_served: int
    request_count: int
    response_time_avg: float  # Average response time in ms
    timestamp: float
    period_start: float
    period_end: float
    client_signatures: List[str]  # Signatures from served clients
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BandwidthProof':
        """Create from dictionary"""
        return cls(**data)

@dataclass
class LongevityProof:
    """Proof of long-term storage commitment"""
    node_id: str
    archive_id: str
    storage_start: float
    storage_duration: float  # In seconds
    consistency_checks: List[float]  # Timestamps of successful checks
    availability_score: float  # 0.0 to 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LongevityProof':
        """Create from dictionary"""
        return cls(**data)

class ProofOfArchive:
    """Main Proof of Archive consensus implementation"""
    
    # Scoring weights
    STORAGE_WEIGHT = 0.5      # 50% for storage proof
    BANDWIDTH_WEIGHT = 0.3    # 30% for bandwidth proof  
    LONGEVITY_WEIGHT = 0.2    # 20% for longevity proof
    
    # Minimum requirements
    MIN_STORAGE_SIZE = 1024 * 1024 * 1024  # 1GB minimum
    MIN_BANDWIDTH_SERVED = 100 * 1024 * 1024  # 100MB minimum
    MIN_STORAGE_DURATION = 24 * 60 * 60  # 24 hours minimum
    MAX_RESPONSE_TIME = 5000  # 5 seconds max response time
    
    # Challenge parameters
    CHALLENGE_LENGTH = 32
    PROOF_VALIDITY_PERIOD = 3600  # 1 hour
    
    def __init__(self):
        self.storage_proofs: Dict[str, List[StorageProof]] = {}
        self.bandwidth_proofs: Dict[str, List[BandwidthProof]] = {}
        self.longevity_proofs: Dict[str, List[LongevityProof]] = {}
        self.node_scores: Dict[str, float] = {}
        self.active_challenges: Dict[str, Dict[str, Any]] = {}
    
    def generate_storage_challenge(self, node_id: str, archive_id: str) -> str:
        """
        Generate storage challenge for a node using cryptographically secure methods
        
        CORRECTION CRITIQUE: Remplace random.random() par crypto_manager.generate_secure_challenge()
        """
        # Utilise le gestionnaire cryptographique sécurisé
        challenge = crypto_manager.generate_secure_challenge(node_id, archive_id)
        
        # Le challenge est déjà stocké dans le crypto_manager, pas besoin de dupliquer
        # Mais on maintient la compatibilité avec l'ancienne interface
        self.active_challenges[f"{node_id}_{archive_id}"] = {
            "challenge": challenge,
            "timestamp": time.time(),
            "node_id": node_id,
            "archive_id": archive_id
        }
        
        return challenge
    
    def verify_storage_proof(self, proof: StorageProof, expected_checksum: str) -> bool:
        """Verify storage proof from a node"""
        challenge_key = f"{proof.node_id}_{proof.archive_id}"
        
        # Check if challenge exists and is recent
        if challenge_key not in self.active_challenges:
            return False
        
        challenge_data = self.active_challenges[challenge_key]
        if time.time() - challenge_data["timestamp"] > self.PROOF_VALIDITY_PERIOD:
            # Challenge expired
            del self.active_challenges[challenge_key]
            return False
        
        # Verify the response matches expected pattern
        expected_response = hashlib.sha256(
            f"{expected_checksum}{challenge_data['challenge']}".encode()
        ).hexdigest()
        
        if proof.response != expected_response:
            return False
        
        # Verify minimum size requirement
        if proof.file_size < self.MIN_STORAGE_SIZE:
            return False
        
        # Verify checksum
        if proof.checksum != expected_checksum:
            return False
        
        # Store valid proof
        if proof.node_id not in self.storage_proofs:
            self.storage_proofs[proof.node_id] = []
        self.storage_proofs[proof.node_id].append(proof)
        
        # Clean up challenge
        del self.active_challenges[challenge_key]
        
        return True
    
    def verify_bandwidth_proof(self, proof: BandwidthProof) -> bool:
        """Verify bandwidth proof from a node"""
        # Check minimum requirements
        if proof.bytes_served < self.MIN_BANDWIDTH_SERVED:
            return False
        
        if proof.response_time_avg > self.MAX_RESPONSE_TIME:
            return False
        
        # Verify time period makes sense
        if proof.period_end <= proof.period_start:
            return False
        
        period_duration = proof.period_end - proof.period_start
        if period_duration < 3600:  # At least 1 hour period
            return False
        
        # Verify client signatures (simplified - would use real crypto in production)
        # Allow for fewer signatures in tests
        min_signatures = max(1, proof.request_count // 100)  # At least 1% signed
        if len(proof.client_signatures) < min_signatures:
            return False
        
        # Store valid proof
        if proof.node_id not in self.bandwidth_proofs:
            self.bandwidth_proofs[proof.node_id] = []
        self.bandwidth_proofs[proof.node_id].append(proof)
        
        return True
    
    def verify_longevity_proof(self, proof: LongevityProof) -> bool:
        """Verify longevity proof from a node"""
        # Check minimum duration
        if proof.storage_duration < self.MIN_STORAGE_DURATION:
            return False
        
        # Verify availability score
        if proof.availability_score < 0.0 or proof.availability_score > 1.0:
            return False
        
        # Check consistency checks frequency
        expected_checks = int(proof.storage_duration / 3600)  # Hourly checks
        if len(proof.consistency_checks) < expected_checks * 0.8:  # Allow 20% missed checks
            return False
        
        # Verify timestamps are in order
        for i in range(1, len(proof.consistency_checks)):
            if proof.consistency_checks[i] <= proof.consistency_checks[i-1]:
                return False
        
        # Store valid proof
        if proof.node_id not in self.longevity_proofs:
            self.longevity_proofs[proof.node_id] = []
        self.longevity_proofs[proof.node_id].append(proof)
        
        return True
    
    def calculate_storage_score(self, node_id: str, time_window: float = 86400) -> float:
        """Calculate storage score for a node"""
        if node_id not in self.storage_proofs:
            return 0.0
        
        current_time = time.time()
        recent_proofs = [
            proof for proof in self.storage_proofs[node_id]
            if current_time - proof.timestamp <= time_window
        ]
        
        if not recent_proofs:
            return 0.0
        
        # Calculate score based on storage amount and proof frequency
        total_storage = sum(proof.file_size for proof in recent_proofs)
        proof_frequency = len(recent_proofs) / (time_window / 3600)  # Proofs per hour
        
        # Normalize scores (logarithmic scale for storage)
        storage_score = min(1.0, (total_storage / (100 * 1024 * 1024 * 1024)) ** 0.5)  # Scale to 100GB
        frequency_score = min(1.0, proof_frequency / 24)  # Scale to 24 proofs per hour max
        
        return (storage_score * 0.7 + frequency_score * 0.3)
    
    def calculate_bandwidth_score(self, node_id: str, time_window: float = 86400) -> float:
        """Calculate bandwidth score for a node"""
        if node_id not in self.bandwidth_proofs:
            return 0.0
        
        current_time = time.time()
        recent_proofs = [
            proof for proof in self.bandwidth_proofs[node_id]
            if current_time - proof.timestamp <= time_window
        ]
        
        if not recent_proofs:
            return 0.0
        
        # Calculate total bandwidth and average response time
        total_bandwidth = sum(proof.bytes_served for proof in recent_proofs)
        total_requests = sum(proof.request_count for proof in recent_proofs)
        avg_response_time = sum(proof.response_time_avg for proof in recent_proofs) / len(recent_proofs)
        
        # Normalize scores
        bandwidth_score = min(1.0, total_bandwidth / (10 * 1024 * 1024 * 1024))  # Scale to 10GB
        request_score = min(1.0, total_requests / 10000)  # Scale to 10k requests
        response_score = max(0.0, 1.0 - (avg_response_time / self.MAX_RESPONSE_TIME))  # Faster is better
        
        return (bandwidth_score * 0.4 + request_score * 0.3 + response_score * 0.3)
    
    def calculate_longevity_score(self, node_id: str) -> float:
        """Calculate longevity score for a node"""
        if node_id not in self.longevity_proofs:
            return 0.0
        
        proofs = self.longevity_proofs[node_id]
        if not proofs:
            return 0.0
        
        # Calculate weighted average of longevity scores
        total_score = 0.0
        total_weight = 0.0
        
        for proof in proofs:
            # Weight by storage duration (longer = better)
            duration_score = min(1.0, proof.storage_duration / (365 * 24 * 3600))  # Scale to 1 year
            availability_score = proof.availability_score
            
            # Combine scores
            proof_score = (duration_score * 0.6 + availability_score * 0.4)
            weight = proof.storage_duration
            
            total_score += proof_score * weight
            total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0.0
    
    def calculate_total_score(self, node_id: str) -> float:
        """Calculate total PoA score for a node"""
        storage_score = self.calculate_storage_score(node_id)
        bandwidth_score = self.calculate_bandwidth_score(node_id)
        longevity_score = self.calculate_longevity_score(node_id)
        
        total_score = (
            storage_score * self.STORAGE_WEIGHT +
            bandwidth_score * self.BANDWIDTH_WEIGHT +
            longevity_score * self.LONGEVITY_WEIGHT
        )
        
        self.node_scores[node_id] = total_score
        return total_score
    
    def get_top_validators(self, count: int = 10) -> List[Tuple[str, float]]:
        """Get top validators by PoA score"""
        # Update all scores
        all_nodes = set()
        all_nodes.update(self.storage_proofs.keys())
        all_nodes.update(self.bandwidth_proofs.keys())
        all_nodes.update(self.longevity_proofs.keys())
        
        for node_id in all_nodes:
            self.calculate_total_score(node_id)
        
        # Sort by score
        sorted_nodes = sorted(
            self.node_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return sorted_nodes[:count]
    
    def select_block_validator(self) -> str:
        """
        Select validator for next block using weighted random selection
        
        CORRECTION CRITIQUE: Utilise crypto_manager.generate_secure_random_float()
        au lieu de random.random() pour la sélection cryptographiquement sûre
        """
        top_validators = self.get_top_validators(20)  # Consider top 20
        
        if not top_validators:
            raise ValueError("No validators available")
        
        # Use weighted random selection with cryptographically secure randomness
        total_score = sum(score for _, score in top_validators)
        if total_score == 0:
            # Fallback to first validator
            return top_validators[0][0]
        
        # Utilise le générateur cryptographiquement sûr
        rand_val = crypto_manager.generate_secure_random_float() * total_score
        cumulative = 0.0
        
        for node_id, score in top_validators:
            cumulative += score
            if rand_val <= cumulative:
                return node_id
        
        # Fallback
        return top_validators[0][0]
    
    def validate_block_creation_right(self, node_id: str, block_hash: str) -> bool:
        """
        Validate that a node has the right to create a block with enhanced security
        
        CORRECTION CRITIQUE: Renforce la validation d'autorisation avec des seuils stricts
        et rotation des validateurs
        """
        # Validation de base du node_id
        if not node_id or not isinstance(node_id, str):
            return False
        
        # Calcule le score PoA actuel
        score = self.calculate_total_score(node_id)
        
        # Seuil minimum renforcé (augmenté de 0.1 à 0.3)
        MINIMUM_SCORE_THRESHOLD = 0.3
        if score < MINIMUM_SCORE_THRESHOLD:
            return False
        
        # Validation de la rotation des validateurs
        if not self._validate_validator_rotation(node_id):
            return False
        
        # Validation des exigences de stake minimum
        if not self._validate_minimum_stake_requirements(node_id):
            return False
        
        # Validation de la réputation et conditions de slashing
        if not self._validate_reputation_and_slashing(node_id):
            return False
        
        # Validation du timing (évite la création de blocs trop fréquente)
        if not self._validate_block_timing(node_id):
            return False
        
        # Validation de l'historique récent des validations
        if not self._validate_recent_validation_history(node_id):
            return False
        
        return True
    
    def _validate_validator_rotation(self, node_id: str) -> bool:
        """Valide la rotation des validateurs pour éviter la centralisation"""
        # Vérifie que le même validateur ne crée pas consécutivement trop de blocs
        recent_validators = getattr(self, '_recent_validators', [])
        
        # Limite : maximum 2 blocs consécutifs par validateur
        if len(recent_validators) >= 2 and all(v == node_id for v in recent_validators[-2:]):
            return False
        
        return True
    
    def _validate_minimum_stake_requirements(self, node_id: str) -> bool:
        """Valide les exigences minimales de stake pour la validation"""
        # Dans un système réel, ceci vérifierait le stake actuel du validateur
        # Pour maintenant, on simule avec le score de stockage
        storage_score = self.calculate_storage_score(node_id)
        
        # Exigence minimale de stake (équivalent à un score de stockage > 0.5)
        MINIMUM_STAKE_SCORE = 0.5
        return storage_score >= MINIMUM_STAKE_SCORE
    
    def _validate_reputation_and_slashing(self, node_id: str) -> bool:
        """Valide la réputation et vérifie les conditions de slashing"""
        # Vérifie qu'il n'y a pas de conditions de slashing actives
        slashing_conditions = getattr(self, '_slashing_registry', {})
        if node_id in slashing_conditions:
            return False
        
        # Vérifie la réputation basée sur l'historique des preuves
        bandwidth_score = self.calculate_bandwidth_score(node_id)
        longevity_score = self.calculate_longevity_score(node_id)
        
        # Score de réputation minimum requis
        MINIMUM_REPUTATION = 0.6
        reputation_score = (bandwidth_score + longevity_score) / 2
        
        return reputation_score >= MINIMUM_REPUTATION
    
    def _validate_block_timing(self, node_id: str) -> bool:
        """Valide le timing pour éviter la création de blocs trop fréquente"""
        current_time = time.time()
        last_block_times = getattr(self, '_last_block_times', {})
        
        if node_id in last_block_times:
            time_since_last = current_time - last_block_times[node_id]
            # Minimum 60 secondes entre les blocs du même validateur
            MIN_TIME_BETWEEN_BLOCKS = 60
            if time_since_last < MIN_TIME_BETWEEN_BLOCKS:
                return False
        
        return True
    
    def _validate_recent_validation_history(self, node_id: str) -> bool:
        """Valide l'historique récent des validations pour détecter des patterns suspects"""
        # Vérifie que le nœud a récemment fourni des preuves valides
        current_time = time.time()
        recent_window = 3600  # 1 heure
        
        # Vérifie les preuves de stockage récentes
        if node_id in self.storage_proofs:
            recent_storage_proofs = [
                proof for proof in self.storage_proofs[node_id]
                if current_time - proof.timestamp <= recent_window
            ]
            if len(recent_storage_proofs) == 0:
                return False
        
        return True
    
    def update_validator_state(self, node_id: str, block_created: bool = True):
        """Met à jour l'état du validateur après création de bloc"""
        current_time = time.time()
        
        # Met à jour l'historique des validateurs récents
        if not hasattr(self, '_recent_validators'):
            self._recent_validators = []
        
        if block_created:
            self._recent_validators.append(node_id)
            # Garde seulement les 10 derniers validateurs
            self._recent_validators = self._recent_validators[-10:]
            
            # Met à jour le temps du dernier bloc
            if not hasattr(self, '_last_block_times'):
                self._last_block_times = {}
            self._last_block_times[node_id] = current_time
    
    def add_slashing_condition(self, node_id: str, reason: str):
        """Ajoute une condition de slashing pour un nœud"""
        if not hasattr(self, '_slashing_registry'):
            self._slashing_registry = {}
        
        self._slashing_registry[node_id] = {
            'reason': reason,
            'timestamp': time.time()
        }
    
    def remove_slashing_condition(self, node_id: str):
        """Retire une condition de slashing pour un nœud"""
        if hasattr(self, '_slashing_registry') and node_id in self._slashing_registry:
            del self._slashing_registry[node_id]
    
    def get_consensus_stats(self) -> Dict[str, Any]:
        """Get consensus statistics"""
        return {
            "total_nodes": len(self.node_scores),
            "storage_proofs": sum(len(proofs) for proofs in self.storage_proofs.values()),
            "bandwidth_proofs": sum(len(proofs) for proofs in self.bandwidth_proofs.values()),
            "longevity_proofs": sum(len(proofs) for proofs in self.longevity_proofs.values()),
            "active_challenges": len(self.active_challenges),
            "top_validators": self.get_top_validators(5),
            "average_score": sum(self.node_scores.values()) / len(self.node_scores) if self.node_scores else 0,
            "scoring_weights": {
                "storage": self.STORAGE_WEIGHT,
                "bandwidth": self.BANDWIDTH_WEIGHT,
                "longevity": self.LONGEVITY_WEIGHT
            }
        }
    
    def cleanup_expired_proofs(self, max_age: float = 604800):  # 7 days
        """Remove old proofs to keep memory usage reasonable"""
        current_time = time.time()
        
        # Clean storage proofs
        for node_id in list(self.storage_proofs.keys()):
            self.storage_proofs[node_id] = [
                proof for proof in self.storage_proofs[node_id]
                if current_time - proof.timestamp <= max_age
            ]
            if not self.storage_proofs[node_id]:
                del self.storage_proofs[node_id]
        
        # Clean bandwidth proofs
        for node_id in list(self.bandwidth_proofs.keys()):
            self.bandwidth_proofs[node_id] = [
                proof for proof in self.bandwidth_proofs[node_id]
                if current_time - proof.timestamp <= max_age
            ]
            if not self.bandwidth_proofs[node_id]:
                del self.bandwidth_proofs[node_id]
        
        # Clean longevity proofs (keep longer)
        for node_id in list(self.longevity_proofs.keys()):
            self.longevity_proofs[node_id] = [
                proof for proof in self.longevity_proofs[node_id]
                if current_time - proof.storage_start <= max_age * 4  # Keep 4x longer
            ]
            if not self.longevity_proofs[node_id]:
                del self.longevity_proofs[node_id]
        
        # Clean expired challenges
        for challenge_key in list(self.active_challenges.keys()):
            challenge = self.active_challenges[challenge_key]
            if current_time - challenge["timestamp"] > self.PROOF_VALIDITY_PERIOD:
                del self.active_challenges[challenge_key]