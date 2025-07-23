#!/usr/bin/env python3
"""
ArchiveChain Demo Script

Demonstrates the complete ArchiveChain blockchain functionality including:
- Archive storage and retrieval
- Token operations and rewards
- Smart contracts (bounties and preservation pools)
- Proof of Archive consensus
- Node network operations
"""

import asyncio
import json
import time
from decimal import Decimal
from datetime import datetime
from pathlib import Path

# Add src to path
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.blockchain.blockchain import ArchiveChain
from src.blockchain.archive_data import ArchiveData, ArchiveMetadata
from src.blockchain.node import ArchiveNode, NodeType, NodeCapabilities
from src.blockchain.consensus import StorageProof, BandwidthProof
from src.core.config import Config

class ArchiveChainDemo:
    """Demo class showcasing ArchiveChain functionality"""
    
    def __init__(self):
        self.blockchain = ArchiveChain("demo_genesis")
        self.nodes = {}
        self.demo_data = []
        
    def print_header(self, title: str):
        """Print formatted section header"""
        print(f"\n{'='*60}")
        print(f" {title}")
        print(f"{'='*60}")
    
    def print_step(self, step: str, data: dict = None):
        """Print formatted step"""
        print(f"\n🔹 {step}")
        if data:
            print(f"   Result: {json.dumps(data, indent=2, default=str)}")
    
    def create_demo_archives(self):
        """Create sample archive data for demo"""
        demo_archives = [
            {
                "url": "https://news.ycombinator.com",
                "content": "<html><head><title>Hacker News</title></head><body>Latest tech news...</body></html>",
                "content_type": "text/html",
                "tags": ["technology", "news", "startup"],
                "category": "news",
                "priority": 8
            },
            {
                "url": "https://github.com/torvalds/linux",
                "content": "# Linux Kernel\n\nThe Linux kernel source code repository...",
                "content_type": "text/markdown",
                "tags": ["linux", "kernel", "opensource"],
                "category": "development",
                "priority": 9
            },
            {
                "url": "https://arxiv.org/abs/2301.00001",
                "content": "Scientific paper about distributed systems and blockchain consensus...",
                "content_type": "application/pdf",
                "tags": ["research", "blockchain", "consensus"],
                "category": "academic",
                "priority": 7
            }
        ]
        
        archives = []
        for data in demo_archives:
            metadata = ArchiveMetadata(
                screenshots=[],
                external_resources=[],
                linked_pages=[],
                tags=data["tags"],
                category=data["category"],
                priority=data["priority"],
                title=data["url"].split("/")[-1]
            )
            
            content_bytes = data["content"].encode()
            archive_data = ArchiveData(
                archive_id="",  # Will be calculated
                original_url=data["url"],
                capture_timestamp=datetime.now().isoformat(),
                content_type=data["content_type"],
                compression="gzip",
                size_compressed=len(content_bytes) // 2,  # Simulate compression
                size_original=len(content_bytes),
                checksum="",  # Will be calculated
                metadata=metadata
            )
            
            # Calculate ID and checksum
            archive_data.calculate_archive_id(content_bytes)
            archive_data.calculate_checksum(content_bytes)
            
            archives.append((archive_data, content_bytes))
        
        return archives
    
    def demo_basic_blockchain_operations(self):
        """Demo basic blockchain operations"""
        self.print_header("BASIC BLOCKCHAIN OPERATIONS")
        
        # Show genesis block
        genesis = self.blockchain.chain[0]
        self.print_step("Genesis block created", {
            "height": genesis.header.block_height,
            "hash": genesis.hash[:16] + "...",
            "timestamp": genesis.header.timestamp
        })
        
        # Show initial token stats
        token_stats = self.blockchain.token_system.get_token_stats()
        self.print_step("Initial token distribution", {
            "total_supply": token_stats["total_supply"],
            "archiving_rewards_pool": token_stats["remaining_pools"]["archiving_rewards"],
            "development_pool": token_stats["remaining_pools"]["development"]
        })
    
    def demo_archive_operations(self):
        """Demo archive storage and retrieval"""
        self.print_header("ARCHIVE OPERATIONS")
        
        archives = self.create_demo_archives()
        
        for i, (archive_data, content_bytes) in enumerate(archives):
            archiver_address = f"archiver_{i+1}"
            
            # Add archive to blockchain
            tx_id = self.blockchain.add_archive(archive_data, archiver_address)
            
            self.print_step(f"Archive added: {archive_data.original_url}", {
                "transaction_id": tx_id,
                "archive_id": archive_data.archive_id[:16] + "...",
                "size_original": archive_data.size_original,
                "archiver": archiver_address
            })
            
            # Check archiver received rewards
            balance = self.blockchain.get_balance(archiver_address)
            self.print_step(f"Archiver {archiver_address} reward", {
                "balance": str(balance),
                "currency": "ARC"
            })
        
        # Mine a block with pending transactions
        miner_address = "demo_miner"
        new_block = self.blockchain.mine_block(miner_address)
        
        if new_block:
            self.print_step("Block mined successfully", {
                "block_height": new_block.header.block_height,
                "hash": new_block.hash[:16] + "...",
                "transaction_count": len(new_block.transactions),
                "archive_count": new_block.archive_count,
                "miner": miner_address
            })
            
            # Check miner rewards
            miner_balance = self.blockchain.get_balance(miner_address)
            self.print_step("Miner reward", {
                "balance": str(miner_balance),
                "currency": "ARC"
            })
    
    def demo_search_functionality(self):
        """Demo search and retrieval"""
        self.print_header("SEARCH AND RETRIEVAL")
        
        # Search by different criteria
        search_queries = ["linux", "technology", "news"]
        
        for query in search_queries:
            results = self.blockchain.search_archives(query)
            self.print_step(f"Search results for '{query}'", {
                "count": len(results),
                "urls": [archive.original_url for archive in results]
            })
        
        # Get specific archive by URL
        test_url = "https://github.com/torvalds/linux"
        archive = self.blockchain.get_archive_by_url(test_url)
        
        if archive:
            self.print_step(f"Archive retrieved by URL", {
                "url": archive.original_url,
                "capture_time": archive.capture_timestamp,
                "size": archive.size_original,
                "tags": archive.metadata.tags
            })
    
    def demo_smart_contracts(self):
        """Demo smart contract functionality"""
        self.print_header("SMART CONTRACTS")
        
        # Give some tokens to contract creator from existing pools
        creator = "contract_creator"
        # Transfer from archiving rewards pool instead of minting new tokens
        available_rewards = self.blockchain.token_system.pools["archiving_rewards"]
        allocation = min(Decimal('10000'), available_rewards)
        
        self.blockchain.token_system.pools["archiving_rewards"] -= allocation
        self.blockchain.token_system.balances[creator] = allocation
        
        # Create archive bounty
        bounty_id = self.blockchain.create_archive_bounty(
            creator,
            "https://important-document.com",
            Decimal('1000'),
            time.time() + 86400  # 24 hours
        )
        
        self.print_step("Archive bounty created", {
            "bounty_id": bounty_id,
            "target_url": "https://important-document.com",
            "reward": "1000 ARC",
            "creator": creator
        })
        
        # Check creator balance after creating bounty
        creator_balance = self.blockchain.get_balance(creator)
        self.print_step("Creator balance after bounty", {
            "balance": str(creator_balance),
            "escrow": "1000 ARC"
        })
        
        # Claim the bounty
        claimant = "bounty_hunter"
        archive_hash = "demo_archive_hash_12345"
        
        success = self.blockchain.claim_bounty(bounty_id, claimant, archive_hash)
        self.print_step("Bounty claim attempt", {
            "success": success,
            "claimant": claimant,
            "bounty_id": bounty_id
        })
    
    def demo_node_operations(self):
        """Demo node network operations"""
        self.print_header("NODE NETWORK OPERATIONS")
        
        # Create different types of nodes
        node_configs = [
            {
                "id": "full_node_1",
                "type": NodeType.FULL_ARCHIVE,
                "storage": 100 * 1024 * 1024 * 1024,  # 100GB
                "region": "us-east-1"
            },
            {
                "id": "light_node_1", 
                "type": NodeType.LIGHT_STORAGE,
                "storage": 10 * 1024 * 1024 * 1024,   # 10GB
                "region": "eu-west-1"
            },
            {
                "id": "gateway_node_1",
                "type": NodeType.GATEWAY,
                "storage": 1 * 1024 * 1024 * 1024,    # 1GB
                "region": "ap-southeast-1"
            }
        ]
        
        for config in node_configs:
            capabilities = NodeCapabilities(
                storage_capacity=config["storage"],
                available_storage=config["storage"],
                bandwidth_capacity=100 * 1024 * 1024,  # 100MB/s
                cpu_cores=4,
                ram_gb=16,
                geographic_region=config["region"],
                content_specializations=["text/html", "application/pdf"]
            )
            
            node = ArchiveNode(config["id"], config["type"], capabilities)
            node.start()
            
            # Register with blockchain
            self.blockchain.register_node(node)
            self.nodes[config["id"]] = node
            
            self.print_step(f"Node registered: {config['id']}", {
                "type": config["type"].value,
                "storage_capacity": f"{config['storage'] // (1024**3)}GB",
                "region": config["region"],
                "status": node.status.value
            })
        
        # Show network statistics
        network_stats = self.blockchain.node_network.get_network_stats()
        self.print_step("Network statistics", network_stats)
    
    def demo_consensus_proofs(self):
        """Demo Proof of Archive consensus"""
        self.print_header("PROOF OF ARCHIVE CONSENSUS")
        
        if not self.nodes:
            print("⚠️  No nodes available for consensus demo")
            return
        
        node_id = list(self.nodes.keys())[0]
        node = self.nodes[node_id]
        
        # Simulate storage proof
        archive_id = "demo_archive_for_proof"
        challenge = self.blockchain.consensus.generate_storage_challenge(node_id, archive_id)
        
        # Node generates response (simulated)
        import hashlib
        expected_checksum = "demo_checksum_123"
        response = hashlib.sha256(f"{expected_checksum}{challenge}".encode()).hexdigest()
        
        success = self.blockchain.verify_archive_storage(node_id, archive_id, response)
        
        self.print_step("Storage proof verification", {
            "node_id": node_id,
            "archive_id": archive_id,
            "challenge": challenge[:16] + "...",
            "verified": success
        })
        
        # Simulate bandwidth proof
        bandwidth_success = self.blockchain.submit_bandwidth_proof(
            node_id,
            bytes_served=500 * 1024 * 1024,  # 500MB
            request_count=1000,
            avg_response_time=1500,  # 1.5 seconds
            period_start=time.time() - 3600,  # 1 hour ago
            period_end=time.time()
        )
        
        self.print_step("Bandwidth proof submitted", {
            "node_id": node_id,
            "bytes_served": "500MB",
            "requests": 1000,
            "avg_response_time": "1.5s",
            "verified": bandwidth_success
        })
        
        # Show consensus scores
        storage_score = self.blockchain.consensus.calculate_storage_score(node_id)
        bandwidth_score = self.blockchain.consensus.calculate_bandwidth_score(node_id)
        total_score = self.blockchain.consensus.calculate_total_score(node_id)
        
        self.print_step("Consensus scores", {
            "node_id": node_id,
            "storage_score": f"{storage_score:.3f}",
            "bandwidth_score": f"{bandwidth_score:.3f}",
            "total_score": f"{total_score:.3f}"
        })
    
    def demo_token_operations(self):
        """Demo token operations and economics"""
        self.print_header("TOKEN OPERATIONS")
        
        # Create test addresses and allocate tokens from pools
        alice = "alice_address"
        bob = "bob_address"
        charlie = "charlie_address"
        
        # Give Alice some tokens from development pool
        available_dev = self.blockchain.token_system.pools["development"]
        allocation = min(Decimal('5000'), available_dev)
        
        self.blockchain.token_system.pools["development"] -= allocation
        self.blockchain.token_system.balances[alice] = allocation
        
        # Transfer tokens between addresses
        tx_id1 = self.blockchain.transfer_tokens(alice, bob, Decimal('1000'))
        tx_id2 = self.blockchain.transfer_tokens(alice, charlie, Decimal('500'))
        
        self.print_step("Token transfers completed", {
            "alice_to_bob": {"amount": "1000 ARC", "tx_id": tx_id1},
            "alice_to_charlie": {"amount": "500 ARC", "tx_id": tx_id2}
        })
        
        # Show final balances
        balances = {
            "alice": str(self.blockchain.get_balance(alice)),
            "bob": str(self.blockchain.get_balance(bob)),
            "charlie": str(self.blockchain.get_balance(charlie))
        }
        
        self.print_step("Final token balances", balances)
        
        # Demonstrate staking
        stake_tx = self.blockchain.token_system.stake_tokens(alice, Decimal('1000'))
        self.print_step("Token staking", {
            "staker": alice,
            "amount": "1000 ARC",
            "tx_id": stake_tx,
            "liquid_balance": str(self.blockchain.get_balance(alice)),
            "staked_balance": str(self.blockchain.token_system.get_staked_balance(alice))
        })
    
    def demo_blockchain_stats(self):
        """Show comprehensive blockchain statistics"""
        self.print_header("BLOCKCHAIN STATISTICS")
        
        stats = self.blockchain.get_blockchain_stats()
        
        # Format stats for display
        formatted_stats = {
            "Chain Info": {
                "blocks": stats["chain_length"],
                "pending_transactions": stats["pending_transactions"],
                "difficulty": stats["difficulty"]
            },
            "Archives": {
                "total_archives": stats["total_archives"],
                "total_storage_bytes": f"{stats['total_storage_bytes']:,}",
                "total_transactions": stats["total_transactions"]
            },
            "Network": {
                "total_nodes": stats["network_stats"]["total_nodes"],
                "online_nodes": stats["network_stats"]["online_nodes"],
                "node_types": stats["network_stats"].get("node_types", {})
            },
            "Tokens": {
                "circulation_supply": stats["token_stats"]["circulation_supply"],
                "total_burned": stats["token_stats"]["total_burned"],
                "total_staked": stats["token_stats"]["total_staked"]
            }
        }
        
        for category, data in formatted_stats.items():
            self.print_step(category, data)
    
    def run_complete_demo(self):
        """Run the complete ArchiveChain demo"""
        print("🚀 ArchiveChain Blockchain Demo Starting...")
        print("   This demo showcases the complete decentralized web archiving blockchain")
        
        try:
            self.demo_basic_blockchain_operations()
            self.demo_archive_operations()
            self.demo_search_functionality()
            self.demo_node_operations()
            self.demo_consensus_proofs()
            self.demo_smart_contracts()
            self.demo_token_operations()
            self.demo_blockchain_stats()
            
            self.print_header("DEMO COMPLETED SUCCESSFULLY")
            print("✅ All ArchiveChain features demonstrated successfully!")
            print("📊 The blockchain is now ready for production use")
            
            # Save blockchain state
            demo_path = "demo_blockchain.json"
            self.blockchain.save_to_file(demo_path)
            print(f"💾 Blockchain state saved to: {demo_path}")
            
        except Exception as e:
            print(f"\n❌ Demo failed with error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            # Cleanup nodes
            for node in self.nodes.values():
                node.stop()

if __name__ == "__main__":
    demo = ArchiveChainDemo()
    demo.run_complete_demo()