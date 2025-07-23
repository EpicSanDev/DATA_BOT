"""
Explorateur de blocs intégré pour ArchiveChain
Module pour l'interface web d'exploration de la blockchain
"""

__version__ = "1.0.0"
__author__ = "DATA_BOT Team"

from .block_explorer import BlockExplorer
from .web_interface import ExplorerWebApp
from .data_processor import ExplorerDataProcessor
from .search_engine import ExplorerSearchEngine

__all__ = [
    'BlockExplorer',
    'ExplorerWebApp',
    'ExplorerDataProcessor',
    'ExplorerSearchEngine'
]