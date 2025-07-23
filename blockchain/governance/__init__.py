"""
Gouvernance on-chain pour ArchiveChain
Module pour la gouvernance décentralisée et mise à jour des paramètres
"""

__version__ = "1.0.0"
__author__ = "DATA_BOT Team"

from .governance_manager import GovernanceManager
from .proposal_system import ProposalSystem
from .voting_mechanism import VotingMechanism
from .parameter_updater import ParameterUpdater

__all__ = [
    'GovernanceManager',
    'ProposalSystem',
    'VotingMechanism',
    'ParameterUpdater'
]