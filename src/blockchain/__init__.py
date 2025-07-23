"""
ArchiveChain - Blockchain for Decentralized Web Archiving

This module implements a specialized blockchain for the ArchiveChain project,
designed for decentralized web archiving with Proof of Archive consensus.
"""

__version__ = "1.0.0"
__author__ = "ArchiveChain Team"

from .block import Block, ArchiveBlock
from .blockchain import ArchiveChain
from .consensus import ProofOfArchive
from .tokens import ARCToken
from .smart_contracts import ArchiveBounty, PreservationPool
from .node import ArchiveNode, NodeType
from .archive_data import ArchiveData, ArchiveMetadata

__all__ = [
    'Block',
    'ArchiveBlock', 
    'ArchiveChain',
    'ProofOfArchive',
    'ARCToken',
    'ArchiveBounty',
    'PreservationPool',
    'ArchiveNode',
    'NodeType',
    'ArchiveData',
    'ArchiveMetadata'
]