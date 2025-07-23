"""
Node Management for ArchiveChain

Implements different types of nodes (Full Archive, Light Storage, Relay, Gateway)
and handles peer-to-peer communication as specified in the ArchiveChain architecture.
"""

import json
import hashlib
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

class NodeType(Enum):
    """Types of nodes in ArchiveChain network"""
    FULL_ARCHIVE = "full_archive"      # Store complete archives (>10TB)
    LIGHT_STORAGE = "light_storage"    # Partial storage with specialization (1-10TB)
    RELAY = "relay"                    # Facilitate communications without massive storage
    GATEWAY = "gateway"                # Public interfaces for web access

class NodeStatus(Enum):
    """Node operational status"""
    OFFLINE = "offline"
    STARTING = "starting"
    SYNCING = "syncing"
    ONLINE = "online"
    MAINTENANCE = "maintenance"
    ERROR = "error"

@dataclass
class NodeCapabilities:
    """Node capabilities and specifications"""
    storage_capacity: int  # Total storage capacity in bytes
    available_storage: int  # Available storage in bytes
    bandwidth_capacity: int  # Bandwidth capacity in bytes/sec
    cpu_cores: int
    ram_gb: int
    geographic_region: str
    content_specializations: List[str]  # Content types this node specializes in
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NodeCapabilities':
        """Create from dictionary"""
        return cls(**data)

@dataclass
class NodeMetrics:
    """Node performance metrics"""
    uptime_percentage: float
    average_response_time: float  # milliseconds
    total_bytes_served: int
    total_requests_served: int
    storage_utilization: float  # 0.0 to 1.0
    last_updated: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NodeMetrics':
        """Create from dictionary"""
        return cls(**data)

class ArchiveNode:
    """Archive node implementation"""
    
    def __init__(self, node_id: str, node_type: NodeType, capabilities: NodeCapabilities,
                 listen_address: str = "0.0.0.0", listen_port: int = 8333):
        self.node_id = node_id
        self.node_type = node_type
        self.capabilities = capabilities
        self.listen_address = listen_address
        self.listen_port = listen_port
        
        # Node state
        self.status = NodeStatus.OFFLINE
        self.start_time = time.time()
        self.last_seen = time.time()
        
        # Network
        self.peers: Set[str] = set()  # Connected peer node IDs
        self.known_nodes: Dict[str, Dict[str, Any]] = {}  # All known nodes
        
        # Storage
        self.stored_archives: Dict[str, Dict[str, Any]] = {}  # archive_id -> metadata
        self.pending_archives: Set[str] = set()  # Archives being downloaded
        
        # Metrics
        self.metrics = NodeMetrics(
            uptime_percentage=0.0,
            average_response_time=0.0,
            total_bytes_served=0,
            total_requests_served=0,
            storage_utilization=0.0,
            last_updated=time.time()
        )
        
        # DHT (Distributed Hash Table) for content discovery
        self.dht_table: Dict[str, List[str]] = {}  # hash -> [node_ids]
    
    def start(self) -> bool:
        """Start the node"""
        try:
            self.status = NodeStatus.STARTING
            self._initialize_storage()
            self._start_networking()
            self.status = NodeStatus.ONLINE
            return True
        except Exception as e:
            self.status = NodeStatus.ERROR
            print(f"Failed to start node {self.node_id}: {e}")
            return False
    
    def stop(self):
        """Stop the node"""
        self.status = NodeStatus.OFFLINE
        self.peers.clear()
    
    def _initialize_storage(self):
        """Initialize storage subsystem"""
        # Calculate storage utilization
        used_storage = sum(
            metadata.get("size", 0) 
            for metadata in self.stored_archives.values()
        )
        
        self.metrics.storage_utilization = (
            used_storage / self.capabilities.storage_capacity 
            if self.capabilities.storage_capacity > 0 else 0.0
        )
    
    def _start_networking(self):
        """Start networking subsystem"""
        # In a real implementation, this would start actual network listeners
        pass
    
    def connect_to_peer(self, peer_id: str, peer_address: str, peer_port: int) -> bool:
        """Connect to another node"""
        try:
            # In real implementation, establish actual network connection
            self.peers.add(peer_id)
            self.known_nodes[peer_id] = {
                "address": peer_address,
                "port": peer_port,
                "last_seen": time.time(),
                "connection_time": time.time()
            }
            return True
        except Exception:
            return False
    
    def disconnect_from_peer(self, peer_id: str):
        """Disconnect from a peer"""
        self.peers.discard(peer_id)
        if peer_id in self.known_nodes:
            del self.known_nodes[peer_id]
    
    def broadcast_to_peers(self, message: Dict[str, Any]) -> int:
        """Broadcast message to all connected peers"""
        successful_sends = 0
        for peer_id in self.peers:
            if self._send_to_peer(peer_id, message):
                successful_sends += 1
        return successful_sends
    
    def _send_to_peer(self, peer_id: str, message: Dict[str, Any]) -> bool:
        """Send message to specific peer"""
        # In real implementation, send over network
        # For now, just simulate successful send
        return peer_id in self.known_nodes
    
    def store_archive(self, archive_id: str, archive_data: bytes, metadata: Dict[str, Any]) -> bool:
        """Store archive on this node"""
        # Check storage capacity
        archive_size = len(archive_data)
        used_storage = sum(
            meta.get("size", 0) 
            for meta in self.stored_archives.values()
        )
        
        if used_storage + archive_size > self.capabilities.available_storage:
            return False
        
        # Check content specialization
        content_type = metadata.get("content_type", "")
        if (self.capabilities.content_specializations and 
            content_type not in self.capabilities.content_specializations):
            return False
        
        # Store archive
        self.stored_archives[archive_id] = {
            **metadata,
            "size": archive_size,
            "stored_at": time.time(),
            "access_count": 0,
            "last_accessed": time.time()
        }
        
        # Update DHT
        archive_hash = hashlib.sha256(archive_id.encode()).hexdigest()[:8]
        if archive_hash not in self.dht_table:
            self.dht_table[archive_hash] = []
        self.dht_table[archive_hash].append(self.node_id)
        
        # Update metrics
        self.capabilities.available_storage -= archive_size
        self._update_storage_utilization()
        
        # Announce to network
        self._announce_new_archive(archive_id)
        
        return True
    
    def retrieve_archive(self, archive_id: str) -> Optional[bytes]:
        """Retrieve archive from this node"""
        if archive_id not in self.stored_archives:
            return None
        
        # Update access metrics
        self.stored_archives[archive_id]["access_count"] += 1
        self.stored_archives[archive_id]["last_accessed"] = time.time()
        
        self.metrics.total_requests_served += 1
        
        # In real implementation, read from storage
        # For now, return placeholder
        return b"archive_data_placeholder"
    
    def find_archive_providers(self, archive_id: str) -> List[str]:
        """Find nodes that store a specific archive"""
        archive_hash = hashlib.sha256(archive_id.encode()).hexdigest()[:8]
        
        # Check local DHT
        local_providers = self.dht_table.get(archive_hash, [])
        
        # Query peers for additional providers
        query_message = {
            "type": "archive_query",
            "archive_id": archive_id,
            "archive_hash": archive_hash,
            "requester": self.node_id
        }
        
        self.broadcast_to_peers(query_message)
        
        return local_providers
    
    def _announce_new_archive(self, archive_id: str):
        """Announce new archive to network"""
        announcement = {
            "type": "archive_announcement",
            "archive_id": archive_id,
            "provider": self.node_id,
            "timestamp": time.time()
        }
        
        self.broadcast_to_peers(announcement)
    
    def _update_storage_utilization(self):
        """Update storage utilization metric"""
        used_storage = sum(
            metadata.get("size", 0) 
            for metadata in self.stored_archives.values()
        )
        
        self.metrics.storage_utilization = (
            used_storage / self.capabilities.storage_capacity 
            if self.capabilities.storage_capacity > 0 else 0.0
        )
        
        self.metrics.last_updated = time.time()
    
    def handle_message(self, message: Dict[str, Any], sender_id: str) -> Optional[Dict[str, Any]]:
        """Handle incoming message from peer"""
        message_type = message.get("type")
        
        if message_type == "archive_query":
            return self._handle_archive_query(message, sender_id)
        elif message_type == "archive_announcement":
            return self._handle_archive_announcement(message, sender_id)
        elif message_type == "node_discovery":
            return self._handle_node_discovery(message, sender_id)
        elif message_type == "ping":
            return self._handle_ping(message, sender_id)
        else:
            return None
    
    def _handle_archive_query(self, message: Dict[str, Any], sender_id: str) -> Dict[str, Any]:
        """Handle archive location query"""
        archive_id = message.get("archive_id")
        archive_hash = message.get("archive_hash")
        
        providers = []
        
        # Check if we have the archive
        if archive_id in self.stored_archives:
            providers.append(self.node_id)
        
        # Check DHT
        if archive_hash in self.dht_table:
            providers.extend(self.dht_table[archive_hash])
        
        return {
            "type": "archive_query_response",
            "archive_id": archive_id,
            "providers": list(set(providers)),  # Remove duplicates
            "responder": self.node_id
        }
    
    def _handle_archive_announcement(self, message: Dict[str, Any], sender_id: str) -> Dict[str, Any]:
        """Handle new archive announcement"""
        archive_id = message.get("archive_id")
        provider = message.get("provider")
        
        # Update DHT
        archive_hash = hashlib.sha256(archive_id.encode()).hexdigest()[:8]
        if archive_hash not in self.dht_table:
            self.dht_table[archive_hash] = []
        
        if provider not in self.dht_table[archive_hash]:
            self.dht_table[archive_hash].append(provider)
        
        return {"type": "acknowledgment"}
    
    def _handle_node_discovery(self, message: Dict[str, Any], sender_id: str) -> Dict[str, Any]:
        """Handle node discovery request"""
        return {
            "type": "node_info",
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "capabilities": self.capabilities.to_dict(),
            "metrics": self.metrics.to_dict(),
            "listen_address": self.listen_address,
            "listen_port": self.listen_port
        }
    
    def _handle_ping(self, message: Dict[str, Any], sender_id: str) -> Dict[str, Any]:
        """Handle ping request"""
        return {
            "type": "pong",
            "timestamp": time.time(),
            "node_id": self.node_id
        }
    
    def get_node_info(self) -> Dict[str, Any]:
        """Get comprehensive node information"""
        uptime = time.time() - self.start_time
        
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "status": self.status.value,
            "capabilities": self.capabilities.to_dict(),
            "metrics": self.metrics.to_dict(),
            "network": {
                "listen_address": self.listen_address,
                "listen_port": self.listen_port,
                "connected_peers": len(self.peers),
                "known_nodes": len(self.known_nodes)
            },
            "storage": {
                "archives_stored": len(self.stored_archives),
                "dht_entries": len(self.dht_table),
                "storage_utilization": self.metrics.storage_utilization
            },
            "uptime_seconds": uptime,
            "last_seen": self.last_seen
        }
    
    def perform_maintenance(self):
        """Perform routine maintenance tasks"""
        current_time = time.time()
        
        # Clean up old DHT entries
        self._cleanup_dht()
        
        # Update metrics
        self._update_uptime_metrics()
        
        # Check peer connections
        self._check_peer_health()
        
        # Optimize storage
        if self.node_type in [NodeType.FULL_ARCHIVE, NodeType.LIGHT_STORAGE]:
            self._optimize_storage()
        
        self.last_seen = current_time
    
    def _cleanup_dht(self):
        """Clean up old DHT entries"""
        # Remove entries for nodes we haven't seen recently
        current_time = time.time()
        stale_threshold = 24 * 3600  # 24 hours
        
        for archive_hash in list(self.dht_table.keys()):
            providers = self.dht_table[archive_hash]
            active_providers = []
            
            for provider in providers:
                if provider == self.node_id:
                    active_providers.append(provider)
                elif provider in self.known_nodes:
                    last_seen = self.known_nodes[provider].get("last_seen", 0)
                    if current_time - last_seen <= stale_threshold:
                        active_providers.append(provider)
            
            if active_providers:
                self.dht_table[archive_hash] = active_providers
            else:
                del self.dht_table[archive_hash]
    
    def _update_uptime_metrics(self):
        """Update uptime metrics"""
        current_time = time.time()
        total_time = current_time - self.start_time
        
        if self.status == NodeStatus.ONLINE:
            # Simple uptime calculation (would be more sophisticated in production)
            self.metrics.uptime_percentage = min(100.0, (total_time / max(total_time, 1)) * 100)
        
        self.metrics.last_updated = current_time
    
    def _check_peer_health(self):
        """Check health of peer connections"""
        current_time = time.time()
        timeout_threshold = 300  # 5 minutes
        
        unhealthy_peers = []
        for peer_id in self.peers:
            if peer_id in self.known_nodes:
                last_seen = self.known_nodes[peer_id].get("last_seen", 0)
                if current_time - last_seen > timeout_threshold:
                    unhealthy_peers.append(peer_id)
        
        # Disconnect from unhealthy peers
        for peer_id in unhealthy_peers:
            self.disconnect_from_peer(peer_id)
    
    def _optimize_storage(self):
        """Optimize storage by removing least accessed content when near capacity"""
        storage_threshold = 0.9  # 90% capacity
        
        if self.metrics.storage_utilization > storage_threshold:
            # Sort archives by access patterns (least recently used first)
            archives_by_access = sorted(
                self.stored_archives.items(),
                key=lambda x: (x[1]["access_count"], x[1]["last_accessed"])
            )
            
            # Remove least accessed archives until under threshold
            target_utilization = 0.8  # Target 80% utilization
            
            for archive_id, metadata in archives_by_access:
                if self.metrics.storage_utilization <= target_utilization:
                    break
                
                # Remove archive
                archive_size = metadata["size"]
                del self.stored_archives[archive_id]
                self.capabilities.available_storage += archive_size
                
                # Update DHT
                archive_hash = hashlib.sha256(archive_id.encode()).hexdigest()[:8]
                if archive_hash in self.dht_table:
                    if self.node_id in self.dht_table[archive_hash]:
                        self.dht_table[archive_hash].remove(self.node_id)
                    if not self.dht_table[archive_hash]:
                        del self.dht_table[archive_hash]
                
                self._update_storage_utilization()

class NodeNetwork:
    """Manages the network of ArchiveChain nodes"""
    
    def __init__(self):
        self.nodes: Dict[str, ArchiveNode] = {}
        self.bootstrap_nodes: List[str] = []
        self.network_stats = {
            "total_nodes": 0,
            "online_nodes": 0,
            "total_storage": 0,
            "total_archives": 0,
            "network_start_time": time.time()
        }
    
    def add_node(self, node: ArchiveNode) -> bool:
        """Add node to network"""
        if node.node_id in self.nodes:
            return False
        
        self.nodes[node.node_id] = node
        self._update_network_stats()
        return True
    
    def remove_node(self, node_id: str) -> bool:
        """Remove node from network"""
        if node_id not in self.nodes:
            return False
        
        node = self.nodes[node_id]
        node.stop()
        del self.nodes[node_id]
        self._update_network_stats()
        return True
    
    def discover_nodes(self, requesting_node_id: str) -> List[Dict[str, Any]]:
        """Help a node discover other nodes in the network"""
        requesting_node = self.nodes.get(requesting_node_id)
        if not requesting_node:
            return []
        
        # Return info about online nodes (excluding the requester)
        discovered_nodes = []
        for node_id, node in self.nodes.items():
            if node_id != requesting_node_id and node.status == NodeStatus.ONLINE:
                discovered_nodes.append(node.get_node_info())
        
        return discovered_nodes
    
    def find_best_storage_nodes(self, content_type: str, size: int, 
                               count: int = 3) -> List[str]:
        """Find best nodes for storing specific content"""
        suitable_nodes = []
        
        for node_id, node in self.nodes.items():
            if node.status != NodeStatus.ONLINE:
                continue
            
            # Check storage capacity
            if node.capabilities.available_storage < size:
                continue
            
            # Check content specialization
            if (node.capabilities.content_specializations and 
                content_type not in node.capabilities.content_specializations):
                continue
            
            # Calculate suitability score
            score = self._calculate_storage_score(node, size)
            suitable_nodes.append((node_id, score))
        
        # Sort by score and return top candidates
        suitable_nodes.sort(key=lambda x: x[1], reverse=True)
        return [node_id for node_id, _ in suitable_nodes[:count]]
    
    def _calculate_storage_score(self, node: ArchiveNode, size: int) -> float:
        """Calculate storage suitability score for a node"""
        # Factors: available storage, utilization, performance, geographic diversity
        
        # Storage factor (prefer nodes with more available storage)
        storage_factor = node.capabilities.available_storage / (1024 * 1024 * 1024)  # GB
        storage_factor = min(storage_factor / 100, 1.0)  # Normalize to 100GB
        
        # Utilization factor (prefer less utilized nodes)
        utilization_factor = 1.0 - node.metrics.storage_utilization
        
        # Performance factor
        performance_factor = (
            node.metrics.uptime_percentage / 100.0 * 0.5 +
            max(0, 1.0 - node.metrics.average_response_time / 1000.0) * 0.5
        )
        
        # Geographic factor (simplified - prefer diverse regions)
        # In production, this would consider actual geographic distribution
        geographic_factor = 1.0
        
        total_score = (
            storage_factor * 0.3 +
            utilization_factor * 0.3 +
            performance_factor * 0.3 +
            geographic_factor * 0.1
        )
        
        return total_score
    
    def _update_network_stats(self):
        """Update network-wide statistics"""
        self.network_stats["total_nodes"] = len(self.nodes)
        self.network_stats["online_nodes"] = sum(
            1 for node in self.nodes.values() 
            if node.status == NodeStatus.ONLINE
        )
        
        self.network_stats["total_storage"] = sum(
            node.capabilities.storage_capacity 
            for node in self.nodes.values()
        )
        
        self.network_stats["total_archives"] = sum(
            len(node.stored_archives) 
            for node in self.nodes.values()
        )
    
    def get_network_stats(self) -> Dict[str, Any]:
        """Get comprehensive network statistics"""
        self._update_network_stats()
        
        # Add more detailed stats
        node_types = {}
        for node in self.nodes.values():
            node_type = node.node_type.value
            node_types[node_type] = node_types.get(node_type, 0) + 1
        
        total_peers = sum(len(node.peers) for node in self.nodes.values())
        avg_peers = total_peers / len(self.nodes) if self.nodes else 0
        
        return {
            **self.network_stats,
            "node_types": node_types,
            "average_peers_per_node": avg_peers,
            "network_uptime": time.time() - self.network_stats["network_start_time"]
        }