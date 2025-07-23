"""
Scripts de déploiement automatisés pour ArchiveChain
Module pour l'automatisation du déploiement et de la migration des smart contracts
"""

__version__ = "1.0.0"
__author__ = "DATA_BOT Team"

from .contract_deployer import ContractDeployer
from .migration_manager import MigrationManager
from .verification_manager import VerificationManager
from .template_manager import TemplateManager

__all__ = [
    'ContractDeployer',
    'MigrationManager', 
    'VerificationManager',
    'TemplateManager'
]