"""
Module de Sécurité pour ArchiveChain

Ce module regroupe tous les composants de sécurité pour corriger les vulnérabilités
critiques identifiées dans l'audit de sécurité blockchain.

Composants :
- CryptoManager : Gestion cryptographique sécurisée
- SignatureManager : Signatures ECDSA complètes  
- SafeMath : Protection contre les overflows
- SecurityUtils : Utilitaires de sécurité généraux
"""

from .crypto_manager import SecureCryptoManager, crypto_manager
from .signature_manager import SignatureManager, KeyPair, signature_manager
from .safe_math import (
    SafeMath, SafeMathError, OverflowError, UnderflowError, 
    DivisionByZeroError, InvalidAmountError,
    safe_add, safe_subtract, safe_multiply, safe_divide, validate_amount
)

__all__ = [
    # Classes principales
    'SecureCryptoManager',
    'SignatureManager', 
    'SafeMath',
    'KeyPair',
    
    # Instances globales
    'crypto_manager',
    'signature_manager',
    
    # Exceptions
    'SafeMathError',
    'OverflowError', 
    'UnderflowError',
    'DivisionByZeroError',
    'InvalidAmountError',
    
    # Fonctions d'aide
    'safe_add',
    'safe_subtract', 
    'safe_multiply',
    'safe_divide',
    'validate_amount'
]

# Version du module de sécurité
__version__ = "1.0.0"