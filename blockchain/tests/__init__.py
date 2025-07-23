"""
Tests d'intégration pour ArchiveChain
Module de tests automatisés pour l'ensemble de l'infrastructure blockchain
"""

__version__ = "1.0.0"
__author__ = "DATA_BOT Team"

from .integration_tests import IntegrationTestSuite
from .performance_tests import PerformanceTestSuite
from .security_tests import SecurityTestSuite
from .contract_tests import ContractTestSuite

__all__ = [
    'IntegrationTestSuite',
    'PerformanceTestSuite', 
    'SecurityTestSuite',
    'ContractTestSuite'
]