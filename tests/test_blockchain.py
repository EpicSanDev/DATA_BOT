"""
Test suite for ArchiveChain blockchain implementation

Tests all core blockchain components including blocks, consensus, tokens,
smart contracts, and archive functionality.
"""

import unittest
import tempfile
import os
import time
from decimal import Decimal
from datetime import datetime, timedelta

# Import blockchain components
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.blockchain.archive_data import ArchiveData, ArchiveMetadata, ArchiveIndex
from src.blockchain.block import Block, ArchiveBlock, ArchiveTransaction
from src.blockchain.blockchain import ArchiveChain
from src.blockchain.consensus import ProofOfArchive, StorageProof, BandwidthProof
from src.blockchain.tokens import ARCToken, TokenTransactionType
from src.blockchain.smart_contracts import ArchiveBounty, PreservationPool, SmartContractManager
from src.blockchain.node import ArchiveNode, NodeType, NodeCapabilities, NodeMetrics

class TestArchiveData(unittest.TestCase):
    """Test archive data structures"""
    
    def setUp(self):
        self.metadata = ArchiveMetadata(
            screenshots=["screenshot1", "screenshot2"],
            external_resources=["css1", "js1"],
            linked_pages=["archive1", "archive2"],
            tags=["technology", "ai"],
            category="tech_news",
            priority=7,
            title="Test Article"
        )
        
        self.archive_data = ArchiveData(
            archive_id="test_archive_123",
            original_url="https://example.com/test",
            capture_timestamp="2025-01-08T10:00:00Z",
            content_type="text/html",
            compression="gzip",
            size_compressed=1024,
            size_original=2048,
            checksum="sha256_test_checksum",
            metadata=self.metadata,
            replication_count=3
        )
    
    def test_archive_data_validation(self):
        """Test archive data validation"""
        self.assertTrue(self.archive_data.validate())
        
        # Test invalid data
        invalid_data = ArchiveData(
            archive_id="",  # Empty ID should fail
            original_url="https://example.com",
            capture_timestamp="invalid_timestamp",
            content_type="text/html",
            compression="gzip",
            size_compressed=1024,
            size_original=2048,
            checksum="test_checksum",
            metadata=self.metadata
        )
        self.assertFalse(invalid_data.validate())
    
    def test_archive_data_serialization(self):
        """Test JSON serialization/deserialization"""
        json_str = self.archive_data.to_json()
        restored_data = ArchiveData.from_json(json_str)
        
        self.assertEqual(self.archive_data.archive_id, restored_data.archive_id)
        self.assertEqual(self.archive_data.original_url, restored_data.original_url)
        self.assertEqual(self.archive_data.metadata.title, restored_data.metadata.title)
    
    def test_archive_index(self):
        """Test archive indexing functionality"""
        index = ArchiveIndex()
        index.add_archive(self.archive_data)
        
        # Test URL lookup
        found_id = index.find_by_url("https://example.com/test")
        self.assertEqual(found_id, "test_archive_123")
        
        # Test content type lookup
        html_archives = index.find_by_content_type("text/html")
        self.assertIn("test_archive_123", html_archives)
        
        # Test tag search
        tech_archives = index.find_by_tag("technology")
        self.assertIn("test_archive_123", tech_archives)
        
        # Test text search
        results = index.search("example.com")
        self.assertIn("test_archive_123", results)

class TestBlocks(unittest.TestCase):
    """Test block structures"""
    
    def setUp(self):
        self.archive_data = ArchiveData(
            archive_id="test_archive",
            original_url="https://test.com",
            capture_timestamp="2025-01-08T10:00:00Z",
            content_type="text/html",
            compression="gzip",
            size_compressed=1024,
            size_original=2048,
            checksum="test_checksum",
            metadata=ArchiveMetadata(
                screenshots=[],
                external_resources=[],
                linked_pages=[],
                tags=["test"],
                category="test",
                priority=5
            )
        )
    
    def test_basic_block_creation(self):
        """Test basic block creation and mining"""
        block = Block("previous_hash", 1)
        
        tx = ArchiveTransaction(
            tx_id="test_tx",
            tx_type="test",
            archive_data=self.archive_data,
            sender="test_sender",
            receiver="test_receiver"
        )
        
        block.add_transaction(tx)
        self.assertEqual(len(block.transactions), 1)
        
        # Test mining (with low difficulty for testing)
        success = block.mine_block(1)
        self.assertTrue(success)
        self.assertTrue(block.hash.startswith("0"))
    
    def test_archive_block_functionality(self):
        """Test archive-specific block features"""
        block = ArchiveBlock("previous_hash", 1)
        
        tx = ArchiveTransaction(
            tx_id="archive_tx",
            tx_type="archive",
            archive_data=self.archive_data,
            sender="archiver",
            receiver="archive_pool"
        )
        
        block.add_archive_transaction(tx)
        
        # Check archive statistics
        stats = block.get_archive_stats()
        self.assertEqual(stats["archive_count"], 1)
        self.assertEqual(stats["total_size"], 1024)
        self.assertIn("text/html", stats["content_types"])
    
    def test_block_validation(self):
        """Test block validation"""
        block = ArchiveBlock("previous_hash", 1)
        
        tx = ArchiveTransaction(
            tx_id="valid_tx",
            tx_type="archive",
            archive_data=self.archive_data,
            sender="test_sender",
            receiver="test_receiver"  # Add missing receiver
        )
        
        block.add_transaction(tx)
        block.mine_block(1)
        
        self.assertTrue(block.is_valid())

class TestTokens(unittest.TestCase):
    """Test ARC token system"""
    
    def setUp(self):
        self.token_system = ARCToken()
        # Don't create genesis distribution automatically to avoid total supply issues
        # self.token_system.create_genesis_distribution()
    
    def test_token_distribution(self):
        """Test initial token distribution"""
        # Create genesis distribution for this test
        self.token_system.create_genesis_distribution()
        
        stats = self.token_system.get_token_stats()
        
        # Check total supply
        self.assertEqual(Decimal(stats["total_supply"]), ARCToken.TOTAL_SUPPLY)
        
        # Check that pools were created
        self.assertGreater(Decimal(stats["remaining_pools"]["archiving_rewards"]), 0)
        self.assertGreater(Decimal(stats["remaining_pools"]["development"]), 0)
    
    def test_token_transfer(self):
        """Test token transfers"""
        # Give some tokens to test addresses
        self.token_system.mint_tokens("alice", Decimal('1000'), "test")
        self.token_system.mint_tokens("bob", Decimal('500'), "test")
        
        # Test transfer
        tx_id = self.token_system.transfer_tokens("alice", "bob", Decimal('100'))
        self.assertIsNotNone(tx_id)
        
        # Check balances
        self.assertEqual(self.token_system.get_balance("alice"), Decimal('900'))
        self.assertEqual(self.token_system.get_balance("bob"), Decimal('600'))
    
    def test_archive_rewards(self):
        """Test archive reward calculations"""
        # Test different archive sizes and types
        reward1 = self.token_system.calculate_archive_reward(
            1024 * 1024,  # 1MB
            1.5,  # Rarity score
            "text/html"
        )
        
        reward2 = self.token_system.calculate_archive_reward(
            10 * 1024 * 1024,  # 10MB
            2.0,  # Higher rarity
            "application/pdf"
        )
        
        # Larger, rarer content should get more reward
        self.assertGreater(reward2, reward1)
        
        # Rewards should be within expected bounds
        self.assertGreaterEqual(reward1, ARCToken.INITIAL_ARCHIVE_REWARD_MIN)
        self.assertLessEqual(reward2, ARCToken.INITIAL_ARCHIVE_REWARD_MAX * 2.0 * 1.2)  # Max with multipliers
    
    def test_token_staking(self):
        """Test token staking functionality"""
        self.token_system.mint_tokens("staker", Decimal('1000'), "test")
        
        # Stake tokens
        tx_id = self.token_system.stake_tokens("staker", Decimal('500'))
        self.assertIsNotNone(tx_id)
        
        # Check balances
        self.assertEqual(self.token_system.get_balance("staker"), Decimal('500'))
        self.assertEqual(self.token_system.get_staked_balance("staker"), Decimal('500'))
        
        # Unstake tokens
        tx_id = self.token_system.unstake_tokens("staker", Decimal('200'))
        self.assertIsNotNone(tx_id)
        
        self.assertEqual(self.token_system.get_balance("staker"), Decimal('700'))
        self.assertEqual(self.token_system.get_staked_balance("staker"), Decimal('300'))

class TestConsensus(unittest.TestCase):
    """Test Proof of Archive consensus"""
    
    def setUp(self):
        self.consensus = ProofOfArchive()
    
    def test_storage_proof(self):
        """Test storage proof verification"""
        node_id = "test_node_1"
        archive_id = "test_archive_1"
        
        # Generate challenge
        challenge = self.consensus.generate_storage_challenge(node_id, archive_id)
        self.assertIsNotNone(challenge)
        
        # Create valid proof
        expected_checksum = "test_checksum"
        import hashlib
        response = hashlib.sha256(f"{expected_checksum}{challenge}".encode()).hexdigest()
        
        proof = StorageProof(
            node_id=node_id,
            archive_id=archive_id,
            challenge=challenge,
            response=response,
            timestamp=time.time(),
            file_size=10 * 1024 * 1024,  # 10MB
            checksum=expected_checksum
        )
        
        # Verify proof
        self.assertTrue(self.consensus.verify_storage_proof(proof, expected_checksum))
    
    def test_bandwidth_proof(self):
        """Test bandwidth proof verification"""
        proof = BandwidthProof(
            node_id="test_node_2",
            bytes_served=500 * 1024 * 1024,  # 500MB
            request_count=1000,
            response_time_avg=2000,  # 2 seconds
            timestamp=time.time(),
            period_start=time.time() - 3600,  # 1 hour ago
            period_end=time.time(),
            client_signatures=["sig1", "sig2", "sig3"]  # At least 10% of requests
        )
        
        self.assertTrue(self.consensus.verify_bandwidth_proof(proof))
    
    def test_consensus_scoring(self):
        """Test consensus scoring system"""
        node_id = "test_node_3"
        
        # Add some proofs
        storage_proof = StorageProof(
            node_id=node_id,
            archive_id="archive1",
            challenge="test_challenge",
            response="test_response",
            timestamp=time.time(),
            file_size=100 * 1024 * 1024,  # 100MB
            checksum="test_checksum"
        )
        
        # Manually add to consensus (bypassing verification for test)
        self.consensus.storage_proofs[node_id] = [storage_proof]
        
        # Calculate score
        score = self.consensus.calculate_total_score(node_id)
        self.assertGreater(score, 0.0)
        self.assertLessEqual(score, 1.0)

class TestSmartContracts(unittest.TestCase):
    """Test smart contract functionality"""
    
    def setUp(self):
        self.contract_manager = SmartContractManager()
    
    def test_archive_bounty(self):
        """Test archive bounty contract"""
        # Deploy bounty contract
        bounty = self.contract_manager.deploy_contract(
            "ArchiveBounty",
            "bounty_1",
            "creator_address",
            target_url="https://important-site.com",
            reward=Decimal('500'),
            deadline=time.time() + 86400  # 24 hours from now
        )
        
        self.assertIsInstance(bounty, ArchiveBounty)
        
        # Claim bounty
        success = bounty.claim_bounty("claimer_address", "archive_hash_123")
        self.assertTrue(success)
        
        # Verify submission (simulate validator votes)
        bounty.verify_submission("validator1", True)
        bounty.verify_submission("validator2", True)
        bounty.verify_submission("validator3", True)
        
        # Check if bounty is completed
        self.assertEqual(bounty.status.value, "completed")
    
    def test_preservation_pool(self):
        """Test preservation pool contract"""
        # Deploy preservation pool
        pool = self.contract_manager.deploy_contract(
            "PreservationPool",
            "pool_1", 
            "creator_address",
            target_archives=["archive1", "archive2", "archive3"],
            initial_funding=Decimal('10000')
        )
        
        self.assertIsInstance(pool, PreservationPool)
        
        # Register preserver
        success = pool.register_preserver(
            "preserver_node",
            ["archive1", "archive2", "archive3", "archive4"]  # Has all required + extra
        )
        self.assertTrue(success)
        
        # Verify preservation
        success = pool.verify_preservation("preserver_node", "proof_data")
        self.assertTrue(success)

class TestNodes(unittest.TestCase):
    """Test node functionality"""
    
    def setUp(self):
        self.capabilities = NodeCapabilities(
            storage_capacity=10 * 1024 * 1024 * 1024,  # 10GB
            available_storage=8 * 1024 * 1024 * 1024,   # 8GB available
            bandwidth_capacity=100 * 1024 * 1024,       # 100MB/s
            cpu_cores=4,
            ram_gb=16,
            geographic_region="us-east-1",
            content_specializations=["text/html", "application/pdf"]
        )
        
        self.node = ArchiveNode(
            "test_node_1",
            NodeType.FULL_ARCHIVE,
            self.capabilities
        )
    
    def test_node_startup(self):
        """Test node startup and basic functionality"""
        success = self.node.start()
        self.assertTrue(success)
        self.assertEqual(self.node.status.value, "online")
    
    def test_archive_storage(self):
        """Test archive storage on node"""
        self.node.start()
        
        # Store an archive
        archive_data = b"test archive content"
        metadata = {
            "content_type": "text/html",
            "size": len(archive_data),
            "url": "https://test.com"
        }
        
        success = self.node.store_archive("archive_123", archive_data, metadata)
        self.assertTrue(success)
        
        # Verify storage
        self.assertIn("archive_123", self.node.stored_archives)
        
        # Retrieve archive
        retrieved = self.node.retrieve_archive("archive_123")
        self.assertIsNotNone(retrieved)
    
    def test_peer_connectivity(self):
        """Test peer-to-peer connectivity"""
        self.node.start()
        
        # Connect to peer
        success = self.node.connect_to_peer("peer_1", "192.168.1.100", 8333)
        self.assertTrue(success)
        self.assertIn("peer_1", self.node.peers)
        
        # Disconnect from peer
        self.node.disconnect_from_peer("peer_1")
        self.assertNotIn("peer_1", self.node.peers)

class TestBlockchain(unittest.TestCase):
    """Test complete blockchain functionality"""
    
    def setUp(self):
        self.blockchain = ArchiveChain("genesis_address")
    
    def test_genesis_block(self):
        """Test genesis block creation"""
        self.assertEqual(len(self.blockchain.chain), 1)
        genesis = self.blockchain.chain[0]
        self.assertEqual(genesis.header.block_height, 0)
        self.assertEqual(genesis.header.previous_hash, "0")
    
    def test_archive_addition(self):
        """Test adding archives to blockchain"""
        archive_data = ArchiveData(
            archive_id="blockchain_test_archive",
            original_url="https://blockchain-test.com",
            capture_timestamp="2025-01-08T10:00:00Z",
            content_type="text/html",
            compression="gzip",
            size_compressed=2048,
            size_original=4096,
            checksum="blockchain_test_checksum",
            metadata=ArchiveMetadata(
                screenshots=[],
                external_resources=[],
                linked_pages=[],
                tags=["blockchain", "test"],
                category="test",
                priority=8
            )
        )
        
        tx_id = self.blockchain.add_archive(archive_data, "archiver_address")
        self.assertIsNotNone(tx_id)
        
        # Check that archive was indexed
        found_archive = self.blockchain.get_archive_by_url("https://blockchain-test.com")
        self.assertIsNotNone(found_archive)
        self.assertEqual(found_archive.archive_id, "blockchain_test_archive")
    
    def test_block_mining(self):
        """Test block mining functionality"""
        # Add some transactions first
        archive_data = ArchiveData(
            archive_id="mining_test_archive",
            original_url="https://mining-test.com",
            capture_timestamp="2025-01-08T10:00:00Z",
            content_type="text/html", 
            compression="gzip",
            size_compressed=1024,
            size_original=2048,
            checksum="mining_test_checksum",
            metadata=ArchiveMetadata(
                screenshots=[],
                external_resources=[],
                linked_pages=[],
                tags=["mining", "test"],
                category="test",
                priority=5
            )
        )
        
        self.blockchain.add_archive(archive_data, "miner_address")
        
        # Mine a block
        new_block = self.blockchain.mine_block("miner_address")
        self.assertIsNotNone(new_block)
        self.assertEqual(len(self.blockchain.chain), 2)
        
        # Check miner received reward
        balance = self.blockchain.get_balance("miner_address")
        self.assertGreater(balance, Decimal('0'))
    
    def test_token_operations(self):
        """Test token operations through blockchain"""
        # Give some tokens to test addresses
        self.blockchain.token_system.mint_tokens("alice", Decimal('1000'), "test")
        self.blockchain.token_system.mint_tokens("bob", Decimal('500'), "test")
        
        # Transfer tokens
        tx_id = self.blockchain.transfer_tokens("alice", "bob", Decimal('200'))
        self.assertIsNotNone(tx_id)
        
        # Check balances
        alice_balance = self.blockchain.get_balance("alice")
        bob_balance = self.blockchain.get_balance("bob")
        
        self.assertEqual(alice_balance, Decimal('800'))
        self.assertEqual(bob_balance, Decimal('700'))
    
    def test_smart_contract_integration(self):
        """Test smart contract integration with blockchain"""
        # Give creator some tokens
        self.blockchain.token_system.mint_tokens("creator", Decimal('1000'), "test")
        
        # Create archive bounty
        bounty_id = self.blockchain.create_archive_bounty(
            "creator",
            "https://bounty-target.com",
            Decimal('500'),
            time.time() + 86400
        )
        
        self.assertIsNotNone(bounty_id)
        
        # Check that tokens were transferred to escrow
        creator_balance = self.blockchain.get_balance("creator")
        self.assertEqual(creator_balance, Decimal('500'))  # 1000 - 500 for bounty
    
    def test_search_functionality(self):
        """Test archive search functionality"""
        # Add some test archives
        for i in range(3):
            archive_data = ArchiveData(
                archive_id=f"search_test_{i}",
                original_url=f"https://search-test-{i}.com",
                capture_timestamp="2025-01-08T10:00:00Z",
                content_type="text/html",
                compression="gzip",
                size_compressed=1024,
                size_original=2048,
                checksum=f"search_checksum_{i}",
                metadata=ArchiveMetadata(
                    screenshots=[],
                    external_resources=[],
                    linked_pages=[],
                    tags=["search", "test", f"tag_{i}"],
                    category="test",
                    priority=5
                )
            )
            
            self.blockchain.add_archive(archive_data, "searcher")
        
        # Search archives
        results = self.blockchain.search_archives("search-test")
        self.assertEqual(len(results), 3)
        
        # Search by specific tag
        results = self.blockchain.search_archives("tag_1")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].archive_id, "search_test_1")
    
    def test_blockchain_persistence(self):
        """Test saving and loading blockchain state"""
        # Add some data to blockchain
        archive_data = ArchiveData(
            archive_id="persistence_test",
            original_url="https://persistence-test.com",
            capture_timestamp="2025-01-08T10:00:00Z", 
            content_type="text/html",
            compression="gzip",
            size_compressed=1024,
            size_original=2048,
            checksum="persistence_checksum",
            metadata=ArchiveMetadata(
                screenshots=[],
                external_resources=[],
                linked_pages=[],
                tags=["persistence"],
                category="test",
                priority=7
            )
        )
        
        self.blockchain.add_archive(archive_data, "persister")
        self.blockchain.mine_block("miner")
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
        
        try:
            self.blockchain.save_to_file(temp_path)
            
            # Load blockchain from file
            loaded_blockchain = ArchiveChain.load_from_file(temp_path)
            
            # Verify data was preserved
            self.assertEqual(len(loaded_blockchain.chain), len(self.blockchain.chain))
            
            found_archive = loaded_blockchain.get_archive_by_url("https://persistence-test.com")
            self.assertIsNotNone(found_archive)
            self.assertEqual(found_archive.archive_id, "persistence_test")
            
        finally:
            os.unlink(temp_path)
    
    def test_blockchain_validation(self):
        """Test blockchain validation"""
        # Add some blocks
        archive_data = ArchiveData(
            archive_id="validation_test",
            original_url="https://validation-test.com",
            capture_timestamp="2025-01-08T10:00:00Z",
            content_type="text/html",
            compression="gzip", 
            size_compressed=1024,
            size_original=2048,
            checksum="validation_checksum",
            metadata=ArchiveMetadata(
                screenshots=[],
                external_resources=[],
                linked_pages=[],
                tags=["validation"],
                category="test",
                priority=6
            )
        )
        
        self.blockchain.add_archive(archive_data, "validator")
        self.blockchain.mine_block("miner")
        
        # Validate entire chain
        self.assertTrue(self.blockchain.validate_chain())

if __name__ == '__main__':
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestArchiveData,
        TestBlocks,
        TestTokens,
        TestConsensus,
        TestSmartContracts,
        TestNodes,
        TestBlockchain
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Exit with appropriate code
    exit(0 if result.wasSuccessful() else 1)