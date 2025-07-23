"""
Smart Contracts for ArchiveChain

Implements archive bounties, preservation pools, and content verification contracts
as described in the ArchiveChain specification.
"""

import json
import hashlib
import time
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum

class ContractState(Enum):
    """Smart contract states"""
    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class BountyStatus(Enum):
    """Archive bounty status"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

@dataclass
class ContractEvent:
    """Smart contract event log"""
    event_type: str
    contract_id: str
    timestamp: float
    data: Dict[str, Any]
    tx_hash: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)

class SmartContract:
    """Base smart contract class"""
    
    def __init__(self, contract_id: str, creator: str):
        self.contract_id = contract_id
        self.creator = creator
        self.created_at = time.time()
        self.state = ContractState.ACTIVE
        self.events: List[ContractEvent] = []
        self.storage: Dict[str, Any] = {}
    
    def emit_event(self, event_type: str, data: Dict[str, Any], tx_hash: str = ""):
        """Emit contract event"""
        event = ContractEvent(
            event_type=event_type,
            contract_id=self.contract_id,
            timestamp=time.time(),
            data=data,
            tx_hash=tx_hash
        )
        self.events.append(event)
    
    def execute(self, function_name: str, params: Dict[str, Any], caller: str) -> Any:
        """Execute contract function"""
        raise NotImplementedError("Must be implemented by subclass")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert contract to dictionary"""
        return {
            "contract_id": self.contract_id,
            "creator": self.creator,
            "created_at": self.created_at,
            "state": self.state.value,
            "events": [event.to_dict() for event in self.events],
            "storage": self.storage
        }

class ArchiveBounty(SmartContract):
    """Archive bounty smart contract as specified in the problem statement"""
    
    def __init__(self, contract_id: str, creator: str, target_url: str, 
                 reward: Decimal, deadline: float):
        super().__init__(contract_id, creator)
        
        self.target_url = target_url
        self.reward = reward
        self.deadline = deadline
        self.status = BountyStatus.OPEN
        self.claimant: Optional[str] = None
        self.archive_hash: Optional[str] = None
        self.submission_time: Optional[float] = None
        self.verification_votes: Dict[str, bool] = {}  # validator -> vote
        self.required_votes = 3  # Minimum votes for verification
        
        # Store in contract storage
        self.storage.update({
            "target_url": target_url,
            "reward": str(reward),
            "deadline": deadline,
            "status": self.status.value
        })
        
        self.emit_event("BountyCreated", {
            "target_url": target_url,
            "reward": str(reward),
            "deadline": deadline
        })
    
    def create_bounty(self, target_url: str, deadline: float, reward: Decimal) -> bool:
        """Create archive bounty (called during initialization)"""
        if time.time() >= deadline:
            return False
        
        self.emit_event("BountyActivated", {
            "target_url": target_url,
            "reward": str(reward)
        })
        return True
    
    def claim_bounty(self, claimant: str, archive_hash: str) -> bool:
        """Claim bounty by submitting archive"""
        # Check if bounty is still open
        if self.status != BountyStatus.OPEN:
            return False
        
        # Check deadline
        if time.time() > self.deadline:
            self.status = BountyStatus.EXPIRED
            self.storage["status"] = self.status.value
            self.emit_event("BountyExpired", {})
            return False
        
        # Set claimant
        self.claimant = claimant
        self.archive_hash = archive_hash
        self.submission_time = time.time()
        self.status = BountyStatus.IN_PROGRESS
        
        # Update storage
        self.storage.update({
            "claimant": claimant,
            "archive_hash": archive_hash,
            "submission_time": self.submission_time,
            "status": self.status.value
        })
        
        self.emit_event("BountyClaimed", {
            "claimant": claimant,
            "archive_hash": archive_hash
        })
        
        return True
    
    def verify_submission(self, validator: str, is_valid: bool) -> bool:
        """Verify bounty submission"""
        if self.status != BountyStatus.IN_PROGRESS:
            return False
        
        # Record vote
        self.verification_votes[validator] = is_valid
        
        self.emit_event("VerificationVote", {
            "validator": validator,
            "vote": is_valid,
            "total_votes": len(self.verification_votes)
        })
        
        # Check if we have enough votes
        if len(self.verification_votes) >= self.required_votes:
            valid_votes = sum(1 for vote in self.verification_votes.values() if vote)
            total_votes = len(self.verification_votes)
            
            # Require majority approval
            if valid_votes > total_votes / 2:
                self._complete_bounty()
            else:
                self._reject_submission()
        
        return True
    
    def _complete_bounty(self):
        """Complete bounty and distribute reward"""
        self.status = BountyStatus.COMPLETED
        self.storage["status"] = self.status.value
        
        self.emit_event("BountyCompleted", {
            "claimant": self.claimant,
            "reward": str(self.reward),
            "archive_hash": self.archive_hash
        })
    
    def _reject_submission(self):
        """Reject submission and reopen bounty"""
        self.status = BountyStatus.OPEN
        self.claimant = None
        self.archive_hash = None
        self.submission_time = None
        self.verification_votes.clear()
        
        self.storage.update({
            "status": self.status.value,
            "claimant": None,
            "archive_hash": None,
            "submission_time": None
        })
        
        self.emit_event("SubmissionRejected", {})
    
    def cancel_bounty(self, caller: str) -> bool:
        """Cancel bounty (only creator can cancel)"""
        if caller != self.creator:
            return False
        
        if self.status in [BountyStatus.COMPLETED, BountyStatus.EXPIRED]:
            return False
        
        self.status = BountyStatus.CANCELLED
        self.storage["status"] = self.status.value
        
        self.emit_event("BountyCancelled", {
            "cancelled_by": caller
        })
        
        return True
    
    def execute(self, function_name: str, params: Dict[str, Any], caller: str) -> Any:
        """Execute bounty contract function"""
        if function_name == "claimBounty":
            return self.claim_bounty(caller, params["archive_hash"])
        elif function_name == "verifySubmission":
            return self.verify_submission(caller, params["is_valid"])
        elif function_name == "cancelBounty":
            return self.cancel_bounty(caller)
        else:
            raise ValueError(f"Unknown function: {function_name}")

class PreservationPool(SmartContract):
    """Preservation pool for maintaining important archives"""
    
    def __init__(self, contract_id: str, creator: str, target_archives: List[str], 
                 initial_funding: Decimal):
        super().__init__(contract_id, creator)
        
        self.target_archives = target_archives
        self.total_funding = initial_funding
        self.monthly_reward = initial_funding / 12  # Distribute over 12 months
        self.contributors: Dict[str, Decimal] = {creator: initial_funding}
        self.last_distribution = time.time()
        self.active_preservers: Dict[str, Dict[str, Any]] = {}  # node_id -> preservation info
        
        # Store in contract storage
        self.storage.update({
            "target_archives": target_archives,
            "total_funding": str(initial_funding),
            "monthly_reward": str(self.monthly_reward),
            "contributors": {addr: str(amount) for addr, amount in self.contributors.items()}
        })
        
        self.emit_event("PoolCreated", {
            "target_archives": target_archives,
            "initial_funding": str(initial_funding)
        })
    
    def contribute_to_pool(self, contributor: str, amount: Decimal) -> bool:
        """Add funds to preservation pool"""
        if amount <= Decimal('0'):
            return False
        
        self.total_funding += amount
        self.contributors[contributor] = self.contributors.get(contributor, Decimal('0')) + amount
        
        # Recalculate monthly reward
        self.monthly_reward = self.total_funding / 12
        
        # Update storage
        self.storage["total_funding"] = str(self.total_funding)
        self.storage["monthly_reward"] = str(self.monthly_reward)
        self.storage["contributors"][contributor] = str(self.contributors[contributor])
        
        self.emit_event("ContributionAdded", {
            "contributor": contributor,
            "amount": str(amount),
            "total_funding": str(self.total_funding)
        })
        
        return True
    
    def register_preserver(self, node_id: str, archives_stored: List[str]) -> bool:
        """Register node as preserver for target archives"""
        # Check if node stores required archives
        required_archives = set(self.target_archives)
        stored_archives = set(archives_stored)
        
        if not required_archives.issubset(stored_archives):
            return False
        
        self.active_preservers[node_id] = {
            "archives_stored": archives_stored,
            "registration_time": time.time(),
            "last_verification": time.time(),
            "total_earned": Decimal('0')
        }
        
        self.emit_event("PreserverRegistered", {
            "node_id": node_id,
            "archives_count": len(archives_stored)
        })
        
        return True
    
    def verify_preservation(self, node_id: str, verification_proof: str) -> bool:
        """Verify that node is still preserving archives"""
        if node_id not in self.active_preservers:
            return False
        
        # Update verification time
        self.active_preservers[node_id]["last_verification"] = time.time()
        
        self.emit_event("PreservationVerified", {
            "node_id": node_id,
            "verification_time": time.time()
        })
        
        return True
    
    def distribute_rewards(self) -> Dict[str, Decimal]:
        """Distribute monthly rewards to active preservers"""
        current_time = time.time()
        month_in_seconds = 30 * 24 * 3600
        
        # Check if it's time for distribution
        if current_time - self.last_distribution < month_in_seconds:
            return {}
        
        # Filter active preservers (verified in last 30 days)
        active_nodes = []
        for node_id, info in self.active_preservers.items():
            if current_time - info["last_verification"] <= month_in_seconds:
                active_nodes.append(node_id)
        
        if not active_nodes:
            return {}
        
        # Calculate reward per node
        reward_per_node = self.monthly_reward / len(active_nodes)
        rewards = {}
        
        for node_id in active_nodes:
            rewards[node_id] = reward_per_node
            self.active_preservers[node_id]["total_earned"] += reward_per_node
        
        self.last_distribution = current_time
        self.total_funding -= self.monthly_reward
        
        # Update storage
        self.storage["total_funding"] = str(self.total_funding)
        
        self.emit_event("RewardsDistributed", {
            "recipients": len(active_nodes),
            "total_distributed": str(self.monthly_reward),
            "reward_per_node": str(reward_per_node)
        })
        
        return rewards
    
    def execute(self, function_name: str, params: Dict[str, Any], caller: str) -> Any:
        """Execute preservation pool function"""
        if function_name == "contribute":
            return self.contribute_to_pool(caller, Decimal(params["amount"]))
        elif function_name == "registerPreserver":
            return self.register_preserver(caller, params["archives_stored"])
        elif function_name == "verifyPreservation":
            return self.verify_preservation(caller, params["verification_proof"])
        elif function_name == "distributeRewards":
            return self.distribute_rewards()
        else:
            raise ValueError(f"Unknown function: {function_name}")

class ContentVerification(SmartContract):
    """Content verification contract for automatic integrity checking"""
    
    def __init__(self, contract_id: str, creator: str):
        super().__init__(contract_id, creator)
        
        self.verified_content: Dict[str, Dict[str, Any]] = {}  # archive_id -> verification info
        self.verifiers: Dict[str, float] = {}  # verifier -> reputation score
        self.verification_threshold = 3  # Minimum verifications needed
        
    def submit_verification(self, verifier: str, archive_id: str, 
                          checksum: str, is_valid: bool) -> bool:
        """Submit content verification"""
        if archive_id not in self.verified_content:
            self.verified_content[archive_id] = {
                "verifications": [],
                "consensus": None,
                "final_checksum": None
            }
        
        # Add verification
        verification = {
            "verifier": verifier,
            "checksum": checksum,
            "is_valid": is_valid,
            "timestamp": time.time()
        }
        
        self.verified_content[archive_id]["verifications"].append(verification)
        
        # Update verifier reputation
        if verifier not in self.verifiers:
            self.verifiers[verifier] = 1.0  # Starting reputation
        
        self.emit_event("VerificationSubmitted", {
            "verifier": verifier,
            "archive_id": archive_id,
            "is_valid": is_valid
        })
        
        # Check if we have enough verifications
        verifications = self.verified_content[archive_id]["verifications"]
        if len(verifications) >= self.verification_threshold:
            self._determine_consensus(archive_id)
        
        return True
    
    def _determine_consensus(self, archive_id: str):
        """Determine consensus on content validity"""
        verifications = self.verified_content[archive_id]["verifications"]
        
        # Weight votes by verifier reputation
        total_weight = 0.0
        weighted_valid = 0.0
        
        for verification in verifications:
            verifier = verification["verifier"]
            reputation = self.verifiers.get(verifier, 1.0)
            
            total_weight += reputation
            if verification["is_valid"]:
                weighted_valid += reputation
        
        # Determine consensus
        validity_ratio = weighted_valid / total_weight if total_weight > 0 else 0
        is_consensus_valid = validity_ratio > 0.6  # 60% threshold
        
        # Find most common checksum among valid verifications
        valid_checksums = [
            v["checksum"] for v in verifications 
            if v["is_valid"]
        ]
        
        if valid_checksums:
            # Use most frequent checksum
            checksum_counts = {}
            for checksum in valid_checksums:
                checksum_counts[checksum] = checksum_counts.get(checksum, 0) + 1
            
            final_checksum = max(checksum_counts.items(), key=lambda x: x[1])[0]
        else:
            final_checksum = None
        
        # Update consensus
        self.verified_content[archive_id]["consensus"] = is_consensus_valid
        self.verified_content[archive_id]["final_checksum"] = final_checksum
        
        # Update verifier reputations based on consensus
        self._update_verifier_reputations(archive_id, is_consensus_valid)
        
        self.emit_event("ConsensusReached", {
            "archive_id": archive_id,
            "is_valid": is_consensus_valid,
            "final_checksum": final_checksum,
            "validity_ratio": validity_ratio
        })
    
    def _update_verifier_reputations(self, archive_id: str, consensus_valid: bool):
        """Update verifier reputations based on consensus"""
        verifications = self.verified_content[archive_id]["verifications"]
        
        for verification in verifications:
            verifier = verification["verifier"]
            verifier_vote = verification["is_valid"]
            
            # Reward correct votes, penalize incorrect ones
            if verifier_vote == consensus_valid:
                self.verifiers[verifier] = min(2.0, self.verifiers[verifier] + 0.1)
            else:
                self.verifiers[verifier] = max(0.1, self.verifiers[verifier] - 0.1)
    
    def get_verification_status(self, archive_id: str) -> Optional[Dict[str, Any]]:
        """Get verification status for content"""
        return self.verified_content.get(archive_id)
    
    def execute(self, function_name: str, params: Dict[str, Any], caller: str) -> Any:
        """Execute verification contract function"""
        if function_name == "submitVerification":
            return self.submit_verification(
                caller, 
                params["archive_id"],
                params["checksum"], 
                params["is_valid"]
            )
        elif function_name == "getStatus":
            return self.get_verification_status(params["archive_id"])
        else:
            raise ValueError(f"Unknown function: {function_name}")

class SmartContractManager:
    """Manager for all smart contracts"""
    
    def __init__(self):
        self.contracts: Dict[str, SmartContract] = {}
        self.contract_types: Dict[str, type] = {
            "ArchiveBounty": ArchiveBounty,
            "PreservationPool": PreservationPool,
            "ContentVerification": ContentVerification
        }
    
    def deploy_contract(self, contract_type: str, contract_id: str, 
                       creator: str, **kwargs) -> SmartContract:
        """Deploy new smart contract"""
        if contract_type not in self.contract_types:
            raise ValueError(f"Unknown contract type: {contract_type}")
        
        if contract_id in self.contracts:
            raise ValueError(f"Contract ID already exists: {contract_id}")
        
        contract_class = self.contract_types[contract_type]
        contract = contract_class(contract_id, creator, **kwargs)
        
        self.contracts[contract_id] = contract
        return contract
    
    def get_contract(self, contract_id: str) -> Optional[SmartContract]:
        """Get contract by ID"""
        return self.contracts.get(contract_id)
    
    def execute_contract(self, contract_id: str, function_name: str, 
                        params: Dict[str, Any], caller: str) -> Any:
        """Execute contract function"""
        contract = self.get_contract(contract_id)
        if not contract:
            raise ValueError(f"Contract not found: {contract_id}")
        
        return contract.execute(function_name, params, caller)
    
    def get_contracts_by_type(self, contract_type: str) -> List[SmartContract]:
        """Get all contracts of specific type"""
        return [
            contract for contract in self.contracts.values()
            if type(contract).__name__ == contract_type
        ]
    
    def get_all_contracts(self) -> Dict[str, SmartContract]:
        """Get all contracts"""
        return self.contracts.copy()