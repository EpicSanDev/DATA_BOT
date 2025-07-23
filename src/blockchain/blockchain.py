"""
ArchiveChain Blockchain Implementation

Main blockchain class that combines all components: blocks, consensus, tokens,
smart contracts, and nodes into a cohesive decentralized archiving system.
"""

import json
import hashlib
import time
import os
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict

from .block import Block, ArchiveBlock, ArchiveTransaction
from .archive_data import ArchiveData, ArchiveIndex
from .consensus import ProofOfArchive, StorageProof, BandwidthProof, LongevityProof
from .tokens import ARCToken, TokenTransaction, TokenTransactionType
from .smart_contracts import SmartContractManager, ArchiveBounty, PreservationPool, ContentVerification
from .node import ArchiveNode, NodeNetwork, NodeType

class ArchiveChain:
    """Main ArchiveChain blockchain implementation"""
    
    def __init__(self, genesis_address: str = "genesis"):
        # Core blockchain components
        self.chain: List[ArchiveBlock] = []
        self.pending_transactions: List[ArchiveTransaction] = []
        self.difficulty = 2  # Mining difficulty
        self.mining_reward = Decimal('50')
        
        # Archive-specific components
        self.archive_index = ArchiveIndex()
        self.consensus = ProofOfArchive()
        self.token_system = ARCToken()
        self.smart_contracts = SmartContractManager()
        self.node_network = NodeNetwork()
        
        # Blockchain state
        self.genesis_address = genesis_address
        self.block_time_target = 600  # 10 minutes between blocks
        self.max_block_size = 1024 * 1024  # 1MB max block size
        
        # Statistics
        self.stats = {
            "total_archives": 0,
            "total_storage_bytes": 0,
            "total_transactions": 0,
            "total_rewards_distributed": Decimal('0'),
            "start_time": time.time()
        }
        
        # Create genesis block
        self._create_genesis_block()
        
        # Initialize token distribution
        self.token_system.create_genesis_distribution()
    
    def _create_genesis_block(self):
        """Create the genesis block"""
        genesis_block = ArchiveBlock("0", 0)
        genesis_block.header.timestamp = time.time()
        genesis_block.header.difficulty = 1
        
        # Add genesis transaction
        genesis_tx = ArchiveTransaction(
            tx_id="genesis",
            tx_type="genesis",
            archive_data=None,
            sender="0x0",
            receiver=self.genesis_address,
            amount=0,
            timestamp=time.time()
        )
        
        genesis_block.add_transaction(genesis_tx)
        genesis_block.mine_block(1)
        
        self.chain.append(genesis_block)
    
    def get_latest_block(self) -> ArchiveBlock:
        """Get the latest block in the chain"""
        return self.chain[-1]
    
    def add_archive(self, archive_data: ArchiveData, archiver_address: str) -> str:
        """Add new archive to the blockchain"""
        # Validate archive data
        if not archive_data.validate():
            raise ValueError("Invalid archive data")
        
        # Check if archive already exists
        if self.archive_index.find_by_url(archive_data.original_url):
            raise ValueError("Archive already exists for this URL")
        
        # Create archive transaction
        tx_id = self._generate_transaction_id()
        transaction = ArchiveTransaction(
            tx_id=tx_id,
            tx_type="archive",
            archive_data=archive_data,
            sender=archiver_address,
            receiver="archive_pool",
            amount=0,
            timestamp=time.time()
        )
        
        # Add to pending transactions
        self.pending_transactions.append(transaction)
        
        # Update archive index
        self.archive_index.add_archive(archive_data)
        
        # Calculate and distribute archive reward
        reward = self.token_system.calculate_archive_reward(
            archive_data.size_original,
            self._calculate_rarity_score(archive_data),
            archive_data.content_type
        )
        
        self.token_system.reward_archive_contribution(
            archiver_address,
            archive_data.size_original,
            self._calculate_rarity_score(archive_data),
            archive_data.content_type,
            "initial_archive"
        )
        
        # Update statistics
        self.stats["total_archives"] += 1
        self.stats["total_storage_bytes"] += archive_data.size_original
        self.stats["total_rewards_distributed"] += reward
        
        return tx_id
    
    def verify_archive_storage(self, node_id: str, archive_id: str, 
                              challenge_response: str) -> bool:
        """Verify that a node is storing an archive"""
        # Find the archive
        archive_tx = self._find_archive_transaction(archive_id)
        if not archive_tx or not archive_tx.archive_data:
            return False
        
        archive_data = archive_tx.archive_data
        
        # Generate storage challenge
        challenge = self.consensus.generate_storage_challenge(node_id, archive_id)
        
        # Create storage proof
        storage_proof = StorageProof(
            node_id=node_id,
            archive_id=archive_id,
            challenge=challenge,
            response=challenge_response,
            timestamp=time.time(),
            file_size=archive_data.size_compressed,
            checksum=archive_data.checksum
        )
        
        # Verify the proof
        return self.consensus.verify_storage_proof(storage_proof, archive_data.checksum)
    
    def submit_bandwidth_proof(self, node_id: str, bytes_served: int, 
                              request_count: int, avg_response_time: float,
                              period_start: float, period_end: float) -> bool:
        """Submit bandwidth proof for a node"""
        proof = BandwidthProof(
            node_id=node_id,
            bytes_served=bytes_served,
            request_count=request_count,
            response_time_avg=avg_response_time,
            timestamp=time.time(),
            period_start=period_start,
            period_end=period_end,
            client_signatures=[]  # Would be populated with actual signatures
        )
        
        if self.consensus.verify_bandwidth_proof(proof):
            # Calculate and distribute bandwidth reward
            reward = self.token_system.calculate_bandwidth_reward(bytes_served)
            
            if reward > Decimal('0'):
                self.token_system.reward_archive_contribution(
                    node_id,
                    bytes_served,
                    1.0,  # Base rarity for bandwidth
                    "bandwidth",
                    "bandwidth_reward"
                )
            
            return True
        
        return False
    
    def create_archive_bounty(self, creator: str, target_url: str, 
                             reward: Decimal, deadline: float) -> str:
        """Create an archive bounty smart contract"""
        contract_id = self._generate_contract_id()
        
        bounty = self.smart_contracts.deploy_contract(
            "ArchiveBounty",
            contract_id,
            creator,
            target_url=target_url,
            reward=reward,
            deadline=deadline
        )
        
        # Transfer reward tokens to escrow
        self.token_system.transfer_tokens(creator, contract_id, reward)
        
        return contract_id
    
    def claim_bounty(self, bounty_id: str, claimant: str, archive_hash: str) -> bool:
        """Claim an archive bounty"""
        try:
            return self.smart_contracts.execute_contract(
                bounty_id,
                "claimBounty",
                {"archive_hash": archive_hash},
                claimant
            )
        except Exception:
            return False
    
    def create_preservation_pool(self, creator: str, target_archives: List[str],
                                initial_funding: Decimal) -> str:
        """Create a preservation pool smart contract"""
        contract_id = self._generate_contract_id()
        
        pool = self.smart_contracts.deploy_contract(
            "PreservationPool",
            contract_id,
            creator,
            target_archives=target_archives,
            initial_funding=initial_funding
        )
        
        # Transfer funding to pool
        self.token_system.transfer_tokens(creator, contract_id, initial_funding)
        
        return contract_id
    
    def mine_block(self, miner_address: str) -> Optional[ArchiveBlock]:
        """Mine a new block with pending transactions"""
        if not self.pending_transactions:
            return None
        
        # Check if miner has the right to create a block
        if not self.consensus.validate_block_creation_right(miner_address, ""):
            return None
        
        # Create new block
        previous_hash = self.get_latest_block().hash
        new_block = ArchiveBlock(previous_hash, len(self.chain))
        
        # Add transactions to block (respect size limit)
        current_size = 0
        transactions_added = []
        
        for tx in self.pending_transactions:
            tx_size = len(json.dumps(tx.to_dict()).encode())
            if current_size + tx_size > self.max_block_size:
                break
            
            new_block.add_archive_transaction(tx)
            transactions_added.append(tx)
            current_size += tx_size
        
        # Add mining reward transaction
        reward_tx = ArchiveTransaction(
            tx_id=self._generate_transaction_id(),
            tx_type="reward",
            archive_data=None,
            sender="mining_pool",
            receiver=miner_address,
            amount=int(self.mining_reward),
            timestamp=time.time()
        )
        new_block.add_transaction(reward_tx)
        
        # Mine the block
        if new_block.mine_block(self.difficulty):
            # Add block to chain
            self.chain.append(new_block)
            
            # Remove processed transactions
            for tx in transactions_added:
                self.pending_transactions.remove(tx)
            
            # Distribute mining reward
            self.token_system.mint_tokens(miner_address, self.mining_reward, "mining_reward")
            
            # Update difficulty if needed
            self._adjust_difficulty()
            
            # Update statistics
            self.stats["total_transactions"] += len(new_block.transactions)
            
            return new_block
        
        return None
    
    def validate_chain(self) -> bool:
        """Validate the entire blockchain"""
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]
            
            # Validate block
            if not current_block.is_valid():
                return False
            
            # Check if block points to previous block
            if current_block.header.previous_hash != previous_block.hash:
                return False
            
            # Validate transactions
            for tx in current_block.transactions:
                if not self._validate_transaction(tx):
                    return False
        
        return True
    
    def get_balance(self, address: str) -> Decimal:
        """Get ARC token balance for an address"""
        return self.token_system.get_balance(address)
    
    def transfer_tokens(self, from_address: str, to_address: str, 
                       amount: Decimal) -> str:
        """Transfer ARC tokens between addresses"""
        return self.token_system.transfer_tokens(from_address, to_address, amount)
    
    def search_archives(self, query: str) -> List[ArchiveData]:
        """Search archives using the index"""
        archive_ids = self.archive_index.search(query)
        archives = []
        
        for archive_id in archive_ids:
            archive_tx = self._find_archive_transaction(archive_id)
            if archive_tx and archive_tx.archive_data:
                archives.append(archive_tx.archive_data)
        
        return archives
    
    def get_archive_by_url(self, url: str) -> Optional[ArchiveData]:
        """Get archive by original URL"""
        archive_id = self.archive_index.find_by_url(url)
        if archive_id:
            archive_tx = self._find_archive_transaction(archive_id)
            if archive_tx:
                return archive_tx.archive_data
        return None
    
    def get_node_stats(self, node_id: str) -> Dict[str, Any]:
        """Get statistics for a specific node"""
        node = self.node_network.nodes.get(node_id)
        if not node:
            return {}
        
        return node.get_node_info()
    
    def get_blockchain_stats(self) -> Dict[str, Any]:
        """Get comprehensive blockchain statistics"""
        latest_block = self.get_latest_block()
        
        return {
            **self.stats,
            "chain_length": len(self.chain),
            "pending_transactions": len(self.pending_transactions),
            "difficulty": self.difficulty,
            "latest_block_hash": latest_block.hash,
            "latest_block_height": latest_block.header.block_height,
            "consensus_stats": self.consensus.get_consensus_stats(),
            "token_stats": self.token_system.get_token_stats(),
            "network_stats": self.node_network.get_network_stats(),
            "smart_contracts": len(self.smart_contracts.get_all_contracts())
        }
    
    def register_node(self, node: ArchiveNode) -> bool:
        """Register a new node with the network"""
        return self.node_network.add_node(node)
    
    def find_archive_providers(self, archive_id: str) -> List[str]:
        """Find nodes that store a specific archive"""
        providers = []
        for node_id, node in self.node_network.nodes.items():
            if archive_id in node.stored_archives:
                providers.append(node_id)
        return providers
    
    def replicate_archive(self, archive_id: str, target_replication: int = 3) -> bool:
        """Ensure an archive is replicated across multiple nodes"""
        current_providers = self.find_archive_providers(archive_id)
        
        if len(current_providers) >= target_replication:
            return True
        
        # Find archive data
        archive_tx = self._find_archive_transaction(archive_id)
        if not archive_tx or not archive_tx.archive_data:
            return False
        
        archive_data = archive_tx.archive_data
        needed_replicas = target_replication - len(current_providers)
        
        # Find suitable nodes for replication
        suitable_nodes = self.node_network.find_best_storage_nodes(
            archive_data.content_type,
            archive_data.size_compressed,
            needed_replicas
        )
        
        # Remove nodes that already have the archive
        suitable_nodes = [
            node_id for node_id in suitable_nodes 
            if node_id not in current_providers
        ]
        
        # Initiate replication
        replicated_count = 0
        for node_id in suitable_nodes[:needed_replicas]:
            node = self.node_network.nodes.get(node_id)
            if node:
                # In real implementation, this would transfer the actual data
                success = node.store_archive(
                    archive_id,
                    b"archive_data_placeholder",  # Would be real data
                    archive_data.to_dict()
                )
                if success:
                    replicated_count += 1
        
        return replicated_count > 0
    
    def _calculate_rarity_score(self, archive_data: ArchiveData) -> float:
        """Calculate rarity score for archive content"""
        # Simple rarity calculation based on content type and size
        base_score = 1.0
        
        # Content type rarity
        content_type_scores = {
            "text/html": 1.0,
            "application/pdf": 1.2,
            "video/*": 0.8,
            "image/*": 0.9,
            "application/json": 1.1
        }
        
        content_score = content_type_scores.get(archive_data.content_type, 1.0)
        
        # Size factor (larger content is rarer)
        size_factor = min(2.0, 1.0 + (archive_data.size_original / (100 * 1024 * 1024)))
        
        return base_score * content_score * size_factor
    
    def _find_archive_transaction(self, archive_id: str) -> Optional[ArchiveTransaction]:
        """Find transaction containing specific archive"""
        for block in self.chain:
            for tx in block.transactions:
                if (tx.archive_data and 
                    tx.archive_data.archive_id == archive_id):
                    return tx
        return None
    
    def _validate_transaction(self, tx: ArchiveTransaction) -> bool:
        """Validate a transaction"""
        # Basic validation
        if not tx.tx_id or not tx.sender:
            return False
        
        # Validate archive data if present
        if tx.archive_data and not tx.archive_data.validate():
            return False
        
        # Additional validation logic would go here
        return True
    
    def _adjust_difficulty(self):
        """Adjust mining difficulty based on block time"""
        if len(self.chain) < 10:  # Need some blocks to calculate
            return
        
        # Calculate average block time for last 10 blocks
        recent_blocks = self.chain[-10:]
        time_diffs = []
        
        for i in range(1, len(recent_blocks)):
            time_diff = recent_blocks[i].header.timestamp - recent_blocks[i-1].header.timestamp
            time_diffs.append(time_diff)
        
        avg_block_time = sum(time_diffs) / len(time_diffs)
        
        # Adjust difficulty
        if avg_block_time < self.block_time_target * 0.8:  # Too fast
            self.difficulty += 1
        elif avg_block_time > self.block_time_target * 1.2:  # Too slow
            self.difficulty = max(1, self.difficulty - 1)
    
    def _generate_transaction_id(self) -> str:
        """Generate unique transaction ID"""
        timestamp = str(time.time())
        nonce = str(len(self.pending_transactions))
        return hashlib.sha256((timestamp + nonce).encode()).hexdigest()[:16]
    
    def _generate_contract_id(self) -> str:
        """Generate unique smart contract ID"""
        timestamp = str(time.time())
        nonce = str(len(self.smart_contracts.get_all_contracts()))
        return hashlib.sha256((timestamp + nonce + "contract").encode()).hexdigest()[:16]
    
    def save_to_file(self, filepath: str):
        """Save blockchain state to file"""
        state = {
            "chain": [block.to_dict() for block in self.chain],
            "pending_transactions": [tx.to_dict() for tx in self.pending_transactions],
            "difficulty": self.difficulty,
            "stats": {
                **self.stats,
                "total_rewards_distributed": str(self.stats["total_rewards_distributed"])
            },
            "token_system": self.token_system.to_dict(),
            "genesis_address": self.genesis_address
        }
        
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'ArchiveChain':
        """Load blockchain state from file"""
        with open(filepath, 'r') as f:
            state = json.load(f)
        
        # Create new blockchain instance
        blockchain = cls(state["genesis_address"])
        
        # Load chain
        blockchain.chain = []
        for block_data in state["chain"]:
            block = ArchiveBlock.from_dict(block_data)
            blockchain.chain.append(block)
        
        # Load pending transactions
        blockchain.pending_transactions = []
        for tx_data in state["pending_transactions"]:
            tx = ArchiveTransaction.from_dict(tx_data)
            blockchain.pending_transactions.append(tx)
        
        # Load other state
        blockchain.difficulty = state["difficulty"]
        blockchain.stats = state["stats"]
        blockchain.stats["total_rewards_distributed"] = Decimal(
            blockchain.stats["total_rewards_distributed"]
        )
        
        # Load token system
        blockchain.token_system = ARCToken.from_dict(state["token_system"])
        
        # Rebuild archive index
        blockchain.archive_index = ArchiveIndex()
        for block in blockchain.chain:
            for tx in block.transactions:
                if tx.archive_data:
                    blockchain.archive_index.add_archive(tx.archive_data)
        
        return blockchain