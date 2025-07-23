"""
Réseau P2P décentralisé pour ArchiveChain
Module pour la configuration et gestion du réseau peer-to-peer
"""

__version__ = "1.0.0"
__author__ = "DATA_BOT Team"

from .p2p_manager import P2PManager
from .dht_manager import DHTManager
from .node_discovery import NodeDiscovery
from .block_propagation import BlockPropagator
from .sync_manager import SyncManager

__all__ = [
    'P2PManager',
    'DHTManager',
    'NodeDiscovery', 
    'BlockPropagator',
    'SyncManager'
]