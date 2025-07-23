"""
Module SafeMath pour ArchiveChain

Ce module implémente des opérations mathématiques sécurisées pour corriger
la vulnérabilité critique : tokens.py:111-112
- Protection contre les overflows d'entiers
- Validation stricte des montants
- Limites de sécurité pour les calculs de rewards
- Opérations arithmétiques sécurisées
"""

from decimal import Decimal, ROUND_DOWN, ROUND_UP, InvalidOperation, DivisionByZero
from typing import Union, Optional
import sys


class SafeMathError(Exception):
    """Exception pour les erreurs SafeMath"""
    pass


class OverflowError(SafeMathError):
    """Exception pour les dépassements de capacité"""
    pass


class UnderflowError(SafeMathError):
    """Exception pour les sous-dépassements"""
    pass


class DivisionByZeroError(SafeMathError):
    """Exception pour la division par zéro"""
    pass


class InvalidAmountError(SafeMathError):
    """Exception pour les montants invalides"""
    pass


class SafeMath:
    """
    Classe SafeMath pour les opérations arithmétiques sécurisées
    
    Corrige la vulnérabilité critique : tokens.py:111-112
    Implémente SafeMath pour éviter les overflows et sécuriser les calculs
    """
    
    # Limites de sécurité pour ArchiveChain
    MAX_TOKEN_SUPPLY = Decimal('1000000000')  # 1 milliard ARC tokens max
    MAX_SINGLE_AMOUNT = Decimal('100000000')   # 100 millions par transaction max
    MAX_REWARD_AMOUNT = Decimal('10000')       # 10k tokens de reward max
    MIN_AMOUNT = Decimal('0.000001')           # 1 microtoken minimum
    
    # Précision maximale (6 décimales)
    DECIMAL_PLACES = 6
    
    @classmethod
    def validate_amount(cls, amount: Union[Decimal, str, int, float]) -> Decimal:
        """
        Valide et normalise un montant
        
        Args:
            amount: Montant à valider
            
        Returns:
            Montant validé sous forme de Decimal
            
        Raises:
            InvalidAmountError: Si le montant est invalide
        """
        try:
            if isinstance(amount, (str, int, float)):
                amount = Decimal(str(amount))
            elif not isinstance(amount, Decimal):
                raise InvalidAmountError(f"Type de montant invalide: {type(amount)}")
            
            # Vérifie que le montant n'est pas NaN ou infini
            if not amount.is_finite():
                raise InvalidAmountError("Le montant doit être un nombre fini")
            
            # Normalise la précision
            amount = amount.quantize(
                Decimal('0.' + '0' * cls.DECIMAL_PLACES), 
                rounding=ROUND_DOWN
            )
            
            # Vérifie les limites
            if amount < 0:
                raise InvalidAmountError("Le montant ne peut pas être négatif")
            
            if amount > cls.MAX_SINGLE_AMOUNT:
                raise InvalidAmountError(f"Montant trop élevé (max: {cls.MAX_SINGLE_AMOUNT})")
            
            return amount
            
        except (InvalidOperation, ValueError) as e:
            raise InvalidAmountError(f"Montant invalide: {e}")
    
    @classmethod
    def safe_add(cls, a: Union[Decimal, str, int, float], 
                 b: Union[Decimal, str, int, float]) -> Decimal:
        """
        Addition sécurisée avec vérification d'overflow
        
        Args:
            a: Premier opérande
            b: Deuxième opérande
            
        Returns:
            Résultat de l'addition
            
        Raises:
            OverflowError: Si le résultat dépasse les limites
        """
        a_val = cls.validate_amount(a)
        b_val = cls.validate_amount(b)
        
        # Vérifie l'overflow avant le calcul
        if a_val + b_val > cls.MAX_TOKEN_SUPPLY:
            raise OverflowError(f"Addition overflow: {a_val} + {b_val} > {cls.MAX_TOKEN_SUPPLY}")
        
        result = a_val + b_val
        return cls.validate_amount(result)
    
    @classmethod
    def safe_subtract(cls, a: Union[Decimal, str, int, float], 
                     b: Union[Decimal, str, int, float]) -> Decimal:
        """
        Soustraction sécurisée avec vérification d'underflow
        
        Args:
            a: Minuende
            b: Soustracteur
            
        Returns:
            Résultat de la soustraction
            
        Raises:
            UnderflowError: Si le résultat est négatif
        """
        a_val = cls.validate_amount(a)
        b_val = cls.validate_amount(b)
        
        # Vérifie l'underflow
        if a_val < b_val:
            raise UnderflowError(f"Soustraction underflow: {a_val} - {b_val} < 0")
        
        result = a_val - b_val
        return cls.validate_amount(result)
    
    @classmethod
    def safe_multiply(cls, a: Union[Decimal, str, int, float], 
                     b: Union[Decimal, str, int, float]) -> Decimal:
        """
        Multiplication sécurisée avec vérification d'overflow
        
        Args:
            a: Premier facteur
            b: Deuxième facteur
            
        Returns:
            Résultat de la multiplication
            
        Raises:
            OverflowError: Si le résultat dépasse les limites
        """
        a_val = cls.validate_amount(a)
        b_val = cls.validate_amount(b)
        
        # Vérifie l'overflow potentiel
        if a_val > 0 and b_val > cls.MAX_TOKEN_SUPPLY / a_val:
            raise OverflowError(f"Multiplication overflow: {a_val} * {b_val}")
        
        result = a_val * b_val
        
        if result > cls.MAX_TOKEN_SUPPLY:
            raise OverflowError(f"Résultat de multiplication trop élevé: {result}")
        
        return cls.validate_amount(result)
    
    @classmethod
    def safe_divide(cls, a: Union[Decimal, str, int, float], 
                   b: Union[Decimal, str, int, float]) -> Decimal:
        """
        Division sécurisée avec vérification de division par zéro
        
        Args:
            a: Dividende
            b: Diviseur
            
        Returns:
            Résultat de la division
            
        Raises:
            DivisionByZeroError: Si le diviseur est zéro
        """
        a_val = cls.validate_amount(a)
        b_val = cls.validate_amount(b)
        
        if b_val == 0:
            raise DivisionByZeroError("Division par zéro")
        
        try:
            result = a_val / b_val
            return cls.validate_amount(result)
        except (InvalidOperation, DivisionByZero) as e:
            raise DivisionByZeroError(f"Erreur de division: {e}")
    
    @classmethod
    def safe_percentage(cls, amount: Union[Decimal, str, int, float], 
                       percentage: Union[Decimal, str, int, float]) -> Decimal:
        """
        Calcul sécurisé de pourcentage
        
        Args:
            amount: Montant de base
            percentage: Pourcentage (ex: 10 pour 10%)
            
        Returns:
            Résultat du calcul de pourcentage
        """
        amount_val = cls.validate_amount(amount)
        percentage_val = cls.validate_amount(percentage)
        
        if percentage_val > 100:
            raise InvalidAmountError("Le pourcentage ne peut pas dépasser 100%")
        
        return cls.safe_multiply(amount_val, percentage_val / 100)
    
    @classmethod
    def calculate_reward_safely(cls, base_amount: Union[Decimal, str, int, float],
                               multiplier: Union[Decimal, str, int, float],
                               max_reward: Optional[Union[Decimal, str, int, float]] = None) -> Decimal:
        """
        Calcule un reward de manière sécurisée avec limites
        
        Corrige spécifiquement la vulnérabilité tokens.py:111-112
        
        Args:
            base_amount: Montant de base
            multiplier: Multiplicateur
            max_reward: Reward maximum (optionnel)
            
        Returns:
            Reward calculé de manière sécurisée
        """
        base_val = cls.validate_amount(base_amount)
        mult_val = cls.validate_amount(multiplier)
        
        # Applique le multiplicateur de manière sécurisée
        reward = cls.safe_multiply(base_val, mult_val)
        
        # Applique la limite de reward maximum
        max_limit = cls.validate_amount(max_reward) if max_reward else cls.MAX_REWARD_AMOUNT
        
        if reward > max_limit:
            reward = max_limit
        
        return reward
    
    @classmethod
    def validate_balance_operation(cls, current_balance: Union[Decimal, str, int, float],
                                  operation_amount: Union[Decimal, str, int, float],
                                  operation_type: str) -> bool:
        """
        Valide une opération sur un solde
        
        Args:
            current_balance: Solde actuel
            operation_amount: Montant de l'opération
            operation_type: Type d'opération ('add' ou 'subtract')
            
        Returns:
            True si l'opération est valide
            
        Raises:
            SafeMathError: Si l'opération est invalide
        """
        balance_val = cls.validate_amount(current_balance)
        amount_val = cls.validate_amount(operation_amount)
        
        if operation_type == 'add':
            if balance_val + amount_val > cls.MAX_TOKEN_SUPPLY:
                raise OverflowError("L'opération dépasserait la limite de tokens")
            return True
        
        elif operation_type == 'subtract':
            if balance_val < amount_val:
                raise UnderflowError("Solde insuffisant pour l'opération")
            return True
        
        else:
            raise InvalidAmountError(f"Type d'opération invalide: {operation_type}")
    
    @classmethod
    def calculate_transaction_fee(cls, amount: Union[Decimal, str, int, float],
                                 fee_percentage: Union[Decimal, str, int, float] = Decimal('0.001')) -> Decimal:
        """
        Calcule les frais de transaction de manière sécurisée
        
        Args:
            amount: Montant de la transaction
            fee_percentage: Pourcentage de frais (défaut: 0.1%)
            
        Returns:
            Frais de transaction calculés
        """
        amount_val = cls.validate_amount(amount)
        fee_pct = cls.validate_amount(fee_percentage)
        
        # Calcule les frais avec un minimum
        fee = cls.safe_multiply(amount_val, fee_pct)
        min_fee = cls.MIN_AMOUNT
        
        return max(fee, min_fee)
    
    @classmethod
    def sum_amounts_safely(cls, amounts: list) -> Decimal:
        """
        Additionne une liste de montants de manière sécurisée
        
        Args:
            amounts: Liste des montants à additionner
            
        Returns:
            Somme totale sécurisée
        """
        total = Decimal('0')
        
        for amount in amounts:
            total = cls.safe_add(total, amount)
        
        return total
    
    @classmethod
    def validate_supply_limits(cls, current_supply: Union[Decimal, str, int, float],
                              mint_amount: Union[Decimal, str, int, float]) -> bool:
        """
        Valide que le mint ne dépasse pas les limites de supply
        
        Args:
            current_supply: Supply actuel
            mint_amount: Montant à minter
            
        Returns:
            True si le mint est autorisé
            
        Raises:
            OverflowError: Si le mint dépasserait la limite
        """
        current_val = cls.validate_amount(current_supply)
        mint_val = cls.validate_amount(mint_amount)
        
        if current_val + mint_val > cls.MAX_TOKEN_SUPPLY:
            raise OverflowError(f"Mint dépasserait la supply maximale: {current_val + mint_val} > {cls.MAX_TOKEN_SUPPLY}")
        
        return True
    
    @classmethod
    def get_safe_math_limits(cls) -> dict:
        """
        Retourne les limites de sécurité configurées
        
        Returns:
            Dictionnaire avec les limites
        """
        return {
            "max_token_supply": str(cls.MAX_TOKEN_SUPPLY),
            "max_single_amount": str(cls.MAX_SINGLE_AMOUNT),
            "max_reward_amount": str(cls.MAX_REWARD_AMOUNT),
            "min_amount": str(cls.MIN_AMOUNT),
            "decimal_places": cls.DECIMAL_PLACES
        }


# Fonctions d'aide pour un usage simple
def safe_add(a, b):
    """Fonction d'aide pour addition sécurisée"""
    return SafeMath.safe_add(a, b)


def safe_subtract(a, b):
    """Fonction d'aide pour soustraction sécurisée"""
    return SafeMath.safe_subtract(a, b)


def safe_multiply(a, b):
    """Fonction d'aide pour multiplication sécurisée"""
    return SafeMath.safe_multiply(a, b)


def safe_divide(a, b):
    """Fonction d'aide pour division sécurisée"""
    return SafeMath.safe_divide(a, b)


def validate_amount(amount):
    """Fonction d'aide pour validation de montant"""
    return SafeMath.validate_amount(amount)