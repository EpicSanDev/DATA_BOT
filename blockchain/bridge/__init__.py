"""
Ponts inter-chaînes pour ArchiveChain
Module pour connecter ArchiveChain à d'autres blockchains (Ethereum, Polygon, etc.)
"""

__version__ = "1.0.0"
__author__ = "DATA_BOT Team"

from .bridge_manager import BridgeManager
from .ethereum_bridge import EthereumBridge
from .polygon_bridge import PolygonBridge
from .cross_chain_validator import CrossChainValidator

__all__ = [
    'BridgeManager',
    'EthereumBridge',
    'PolygonBridge',
    'CrossChainValidator'
]