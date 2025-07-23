"""
ArchiveChain Integration Layer

Integrates the ArchiveChain blockchain with the existing DATA_BOT archiving system,
providing seamless blockchain functionality for web archiving operations.
"""

import asyncio
import logging
import time
from decimal import Decimal
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from .config import Config
from .models import WebResource, ArchiveStatus
from .database import DatabaseManager
from .blockchain import ArchiveChain
from .blockchain.archive_data import ArchiveData, ArchiveMetadata
from .blockchain.node import ArchiveNode, NodeType, NodeCapabilities, NodeMetrics
from .blockchain.tokens import ARCToken

logger = logging.getLogger(__name__)

class BlockchainArchiveIntegration:
    """Integration between traditional archiving and blockchain"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.blockchain: Optional[ArchiveChain] = None
        self.local_node: Optional[ArchiveNode] = None
        self.enabled = Config.BLOCKCHAIN_ENABLED
        
        if self.enabled:
            self._initialize_blockchain()
            self._initialize_node()
    
    def _initialize_blockchain(self):
        """Initialize the ArchiveChain blockchain"""
        try:
            # Try to load existing blockchain
            blockchain_path = Path(Config.BLOCKCHAIN_DATA_PATH)
            if blockchain_path.exists():
                logger.info("Loading existing blockchain...")
                self.blockchain = ArchiveChain.load_from_file(str(blockchain_path))
                logger.info(f"Loaded blockchain with {len(self.blockchain.chain)} blocks")
            else:
                logger.info("Creating new blockchain...")
                self.blockchain = ArchiveChain(Config.ARC_GENESIS_ADDRESS)
                # Save initial state
                self._save_blockchain()
                logger.info("Created new ArchiveChain blockchain")
            
        except Exception as e:
            logger.error(f"Failed to initialize blockchain: {e}")
            self.enabled = False
    
    def _initialize_node(self):
        """Initialize local archive node"""
        try:
            # Determine node type
            node_type_mapping = {
                "full_archive": NodeType.FULL_ARCHIVE,
                "light_storage": NodeType.LIGHT_STORAGE,
                "relay": NodeType.RELAY,
                "gateway": NodeType.GATEWAY
            }
            
            node_type = node_type_mapping.get(
                Config.BLOCKCHAIN_NODE_TYPE, 
                NodeType.FULL_ARCHIVE
            )
            
            # Create node capabilities
            capabilities = NodeCapabilities(
                storage_capacity=Config.NODE_STORAGE_CAPACITY,
                available_storage=Config.NODE_STORAGE_CAPACITY,
                bandwidth_capacity=100 * 1024 * 1024,  # 100MB/s default
                cpu_cores=4,  # Default values
                ram_gb=16,
                geographic_region=Config.NODE_GEOGRAPHIC_REGION,
                content_specializations=Config.NODE_CONTENT_SPECIALIZATIONS
            )
            
            # Create node ID based on config
            node_id = f"databot_{Config.NODE_GEOGRAPHIC_REGION}_{int(time.time())}"
            
            # Initialize node
            self.local_node = ArchiveNode(
                node_id=node_id,
                node_type=node_type,
                capabilities=capabilities,
                listen_port=Config.BLOCKCHAIN_LISTEN_PORT
            )
            
            # Register with blockchain network
            if self.blockchain:
                self.blockchain.register_node(self.local_node)
                self.local_node.start()
                logger.info(f"Initialized {node_type.value} node: {node_id}")
            
        except Exception as e:
            logger.error(f"Failed to initialize node: {e}")
            self.local_node = None
    
    async def archive_to_blockchain(self, web_resource: WebResource) -> Optional[str]:
        """Archive a web resource to the blockchain"""
        if not self.enabled or not self.blockchain:
            return None
        
        try:
            # Create archive metadata
            metadata = ArchiveMetadata(
                screenshots=web_resource.screenshots or [],
                external_resources=[],  # Could be extracted from content
                linked_pages=[],        # Could be extracted from links
                tags=web_resource.tags.split(',') if web_resource.tags else [],
                category=web_resource.category or 'uncategorized',
                priority=web_resource.priority or 5,
                title=web_resource.title,
                description=web_resource.content[:200] if web_resource.content else None
            )
            
            # Create archive data
            archive_data = ArchiveData(
                archive_id="",  # Will be calculated
                original_url=web_resource.url,
                capture_timestamp=web_resource.archived_at.isoformat() if web_resource.archived_at else datetime.now().isoformat(),
                content_type=web_resource.content_type or "text/html",
                compression="gzip",  # Default compression
                size_compressed=len(web_resource.content.encode()) if web_resource.content else 0,
                size_original=web_resource.file_size or (len(web_resource.content.encode()) if web_resource.content else 0),
                checksum="",  # Will be calculated
                metadata=metadata
            )
            
            # Calculate archive ID and checksum
            content_bytes = web_resource.content.encode() if web_resource.content else b""
            archive_data.calculate_archive_id(content_bytes)
            archive_data.calculate_checksum(content_bytes)
            
            # Add to blockchain
            archiver_address = self.local_node.node_id if self.local_node else Config.ARC_GENESIS_ADDRESS
            tx_id = self.blockchain.add_archive(archive_data, archiver_address)
            
            # Store on local node if available
            if self.local_node:
                self.local_node.store_archive(
                    archive_data.archive_id,
                    content_bytes,
                    archive_data.to_dict()
                )
            
            # Update web resource with blockchain info
            web_resource.blockchain_tx_id = tx_id
            web_resource.blockchain_archive_id = archive_data.archive_id
            
            # Save to traditional database
            await self.db_manager.update_resource(web_resource)
            
            # Auto-mine if enabled and we have pending transactions
            if Config.BLOCKCHAIN_MINING_ENABLED and self.local_node:
                await self._auto_mine_block()
            
            logger.info(f"Successfully archived {web_resource.url} to blockchain: {tx_id}")
            return tx_id
            
        except Exception as e:
            logger.error(f"Failed to archive to blockchain: {e}")
            return None
    
    async def search_blockchain_archives(self, query: str) -> List[Dict[str, Any]]:
        """Search archives in the blockchain"""
        if not self.enabled or not self.blockchain:
            return []
        
        try:
            results = self.blockchain.search_archives(query)
            
            # Convert to API-friendly format
            formatted_results = []
            for archive in results:
                formatted_results.append({
                    'archive_id': archive.archive_id,
                    'original_url': archive.original_url,
                    'capture_timestamp': archive.capture_timestamp,
                    'content_type': archive.content_type,
                    'size_original': archive.size_original,
                    'size_compressed': archive.size_compressed,
                    'title': archive.metadata.title,
                    'category': archive.metadata.category,
                    'tags': archive.metadata.tags,
                    'priority': archive.metadata.priority,
                    'replication_count': archive.replication_count
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Failed to search blockchain archives: {e}")
            return []
    
    async def get_archive_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Get archive from blockchain by URL"""
        if not self.enabled or not self.blockchain:
            return None
        
        try:
            archive = self.blockchain.get_archive_by_url(url)
            if archive:
                return {
                    'archive_id': archive.archive_id,
                    'original_url': archive.original_url,
                    'capture_timestamp': archive.capture_timestamp,
                    'content_type': archive.content_type,
                    'size_original': archive.size_original,
                    'size_compressed': archive.size_compressed,
                    'checksum': archive.checksum,
                    'metadata': archive.metadata.to_dict(),
                    'block_height': archive.block_height,
                    'replication_count': archive.replication_count,
                    'storage_nodes': archive.storage_nodes
                }
            return None
            
        except Exception as e:
            logger.error(f"Failed to get archive by URL: {e}")
            return None
    
    async def create_archive_bounty(self, creator_address: str, target_url: str, 
                                   reward_amount: float, duration_hours: int = 168) -> Optional[str]:
        """Create an archive bounty"""
        if not self.enabled or not self.blockchain:
            return None
        
        try:
            deadline = time.time() + (duration_hours * 3600)
            bounty_id = self.blockchain.create_archive_bounty(
                creator_address,
                target_url,
                Decimal(str(reward_amount)),
                deadline
            )
            
            logger.info(f"Created archive bounty for {target_url}: {bounty_id}")
            return bounty_id
            
        except Exception as e:
            logger.error(f"Failed to create archive bounty: {e}")
            return None
    
    async def claim_archive_bounty(self, bounty_id: str, claimant_address: str, 
                                  archive_hash: str) -> bool:
        """Claim an archive bounty"""
        if not self.enabled or not self.blockchain:
            return False
        
        try:
            success = self.blockchain.claim_bounty(bounty_id, claimant_address, archive_hash)
            if success:
                logger.info(f"Successfully claimed bounty {bounty_id}")
            return success
            
        except Exception as e:
            logger.error(f"Failed to claim bounty: {e}")
            return False
    
    async def get_token_balance(self, address: str) -> float:
        """Get ARC token balance for an address"""
        if not self.enabled or not self.blockchain:
            return 0.0
        
        try:
            balance = self.blockchain.get_balance(address)
            return float(balance)
            
        except Exception as e:
            logger.error(f"Failed to get token balance: {e}")
            return 0.0
    
    async def transfer_tokens(self, from_address: str, to_address: str, 
                             amount: float) -> Optional[str]:
        """Transfer ARC tokens"""
        if not self.enabled or not self.blockchain:
            return None
        
        try:
            tx_id = self.blockchain.transfer_tokens(
                from_address, 
                to_address, 
                Decimal(str(amount))
            )
            
            logger.info(f"Transferred {amount} ARC from {from_address} to {to_address}")
            return tx_id
            
        except Exception as e:
            logger.error(f"Failed to transfer tokens: {e}")
            return None
    
    async def get_blockchain_stats(self) -> Dict[str, Any]:
        """Get comprehensive blockchain statistics"""
        if not self.enabled or not self.blockchain:
            return {"enabled": False}
        
        try:
            stats = self.blockchain.get_blockchain_stats()
            
            # Add local node info if available
            if self.local_node:
                stats["local_node"] = self.local_node.get_node_info()
            
            # Add integration-specific stats
            stats.update({
                "enabled": True,
                "integration_version": "1.0.0",
                "last_sync": time.time()
            })
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get blockchain stats: {e}")
            return {"enabled": False, "error": str(e)}
    
    async def sync_traditional_archives(self, limit: int = 100) -> int:
        """Sync existing traditional archives to blockchain"""
        if not self.enabled or not self.blockchain:
            return 0
        
        try:
            # Get archives not yet on blockchain
            resources = await self.db_manager.get_resources_without_blockchain(limit)
            synced_count = 0
            
            for resource in resources:
                tx_id = await self.archive_to_blockchain(resource)
                if tx_id:
                    synced_count += 1
                
                # Add delay to avoid overwhelming the system
                await asyncio.sleep(0.1)
            
            logger.info(f"Synced {synced_count} traditional archives to blockchain")
            return synced_count
            
        except Exception as e:
            logger.error(f"Failed to sync traditional archives: {e}")
            return 0
    
    async def _auto_mine_block(self):
        """Automatically mine a block if conditions are met"""
        if not self.blockchain or not self.local_node:
            return
        
        try:
            # Check if we have pending transactions
            if self.blockchain.pending_transactions:
                miner_address = self.local_node.node_id
                new_block = self.blockchain.mine_block(miner_address)
                
                if new_block:
                    logger.info(f"Successfully mined block {new_block.header.block_height}")
                    # Save blockchain state after mining
                    self._save_blockchain()
            
        except Exception as e:
            logger.error(f"Failed to auto-mine block: {e}")
    
    def _save_blockchain(self):
        """Save blockchain state to disk"""
        if self.blockchain:
            try:
                self.blockchain.save_to_file(Config.BLOCKCHAIN_DATA_PATH)
            except Exception as e:
                logger.error(f"Failed to save blockchain: {e}")
    
    async def shutdown(self):
        """Shutdown blockchain integration"""
        if self.local_node:
            self.local_node.stop()
        
        if self.blockchain:
            self._save_blockchain()
        
        logger.info("Blockchain integration shutdown complete")

# Convenience functions for easy integration
async def init_blockchain_integration(db_manager: DatabaseManager) -> BlockchainArchiveIntegration:
    """Initialize blockchain integration"""
    integration = BlockchainArchiveIntegration(db_manager)
    
    if integration.enabled:
        logger.info("ArchiveChain blockchain integration initialized")
    else:
        logger.info("Blockchain integration disabled")
    
    return integration