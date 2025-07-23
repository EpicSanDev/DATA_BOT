"""
ARC Token System for ArchiveChain

Implements the ARC token economics, distribution, rewards, and burning mechanisms
as described in the ArchiveChain specification.

SÉCURITÉ: Intègre la validation obligatoire des signatures ECDSA et SafeMath
"""

import json
import hashlib
import time
from decimal import Decimal, ROUND_DOWN
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

# Import des modules de sécurité
from .security import signature_manager, safe_add, safe_subtract, safe_multiply, SafeMath

class TokenTransactionType(Enum):
    """Types of token transactions"""
    MINT = "mint"
    TRANSFER = "transfer"
    BURN = "burn"
    REWARD = "reward"
    STAKE = "stake"
    UNSTAKE = "unstake"
    FEE = "fee"

@dataclass
class TokenTransaction:
    """Token transaction record"""
    tx_id: str
    tx_type: TokenTransactionType
    from_address: str
    to_address: str
    amount: Decimal
    fee: Decimal
    timestamp: float
    metadata: Dict[str, Any]
    signature: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['tx_type'] = self.tx_type.value
        data['amount'] = str(self.amount)
        data['fee'] = str(self.fee)
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TokenTransaction':
        """Create from dictionary"""
        data['tx_type'] = TokenTransactionType(data['tx_type'])
        data['amount'] = Decimal(data['amount'])
        data['fee'] = Decimal(data['fee'])
        return cls(**data)
    
    def sign_transaction(self, private_key) -> bool:
        """
        Signe la transaction de token avec une clé privée ECDSA
        
        CORRECTION CRITIQUE: Implémente la signature obligatoire des transactions de tokens
        
        Args:
            private_key: Clé privée ECDSA pour signer
            
        Returns:
            True si la signature a réussi
        """
        try:
            transaction_data = self.to_dict()
            self.signature = signature_manager.sign_transaction(transaction_data, private_key)
            return True
        except Exception:
            return False
    
    def verify_signature(self) -> bool:
        """
        Vérifie la signature de la transaction de token
        
        Returns:
            True si la signature est valide
        """
        if not self.signature:
            return False
        
        try:
            transaction_data = self.to_dict()
            return signature_manager.verify_transaction_signature(
                transaction_data,
                self.signature,
                self.from_address
            )
        except Exception:
            return False
    
    def is_signed(self) -> bool:
        """
        Vérifie si la transaction de token est signée
        
        Returns:
            True si la transaction a une signature
        """
        return bool(self.signature and self.signature.strip())

class ARCToken:
    """ARC Token implementation with economics from ArchiveChain spec"""
    
    # Token configuration from spec
    TOTAL_SUPPLY = Decimal('1000000000')  # 1 billion ARC tokens
    ARCHIVING_REWARDS_POOL = TOTAL_SUPPLY * Decimal('0.40')  # 40% for 10 years
    DEVELOPMENT_POOL = TOTAL_SUPPLY * Decimal('0.25')       # 25% vesting 4 years
    COMMUNITY_RESERVE = TOTAL_SUPPLY * Decimal('0.20')      # 20% community
    PUBLIC_SALE = TOTAL_SUPPLY * Decimal('0.15')          # 15% public/private sale
    
    # Reward rates (ARC tokens)
    INITIAL_ARCHIVE_REWARD_MIN = Decimal('100')
    INITIAL_ARCHIVE_REWARD_MAX = Decimal('500')
    STORAGE_REWARD_MIN = Decimal('10')
    STORAGE_REWARD_MAX = Decimal('50')
    BANDWIDTH_REWARD_MIN = Decimal('1')
    BANDWIDTH_REWARD_MAX = Decimal('5')
    DISCOVERY_REWARD_MIN = Decimal('25')
    DISCOVERY_REWARD_MAX = Decimal('100')
    
    # Burning and fees
    TRANSACTION_FEE_BURN_RATE = Decimal('0.10')  # 10% of fees burned
    
    def __init__(self):
        self.balances: Dict[str, Decimal] = {}
        self.staked_balances: Dict[str, Decimal] = {}
        self.stake_rewards: Dict[str, Dict[str, Any]] = {}
        self.transactions: List[TokenTransaction] = []
        self.total_burned = Decimal('0')
        self.total_minted = Decimal('0')
        self.circulation_supply = Decimal('0')
        
        # Initialize distribution pools
        self.pools = {
            'archiving_rewards': self.ARCHIVING_REWARDS_POOL,
            'development': self.DEVELOPMENT_POOL,
            'community': self.COMMUNITY_RESERVE,
            'public_sale': self.PUBLIC_SALE
        }
    
    def create_genesis_distribution(self):
        """Create initial token distribution"""
        # Genesis addresses (would be real addresses in production)
        genesis_addresses = {
            'development_wallet': self.DEVELOPMENT_POOL,
            'community_dao': self.COMMUNITY_RESERVE,
            'public_sale_contract': self.PUBLIC_SALE,
            'archiving_rewards_pool': self.ARCHIVING_REWARDS_POOL
        }
        
        for address, amount in genesis_addresses.items():
            self.mint_tokens(address, amount, "genesis_distribution")
    
    def mint_tokens(self, to_address: str, amount: Decimal, reason: str) -> str:
        """
        Mint new tokens using SafeMath operations
        
        CORRECTION CRITIQUE: Utilise SafeMath pour éviter les overflows
        """
        # Validate amount with SafeMath
        amount = SafeMath.validate_amount(amount)
        
        # Validate supply limits with SafeMath
        SafeMath.validate_supply_limits(self.total_minted, amount)
        
        tx_id = self.generate_tx_id()
        transaction = TokenTransaction(
            tx_id=tx_id,
            tx_type=TokenTransactionType.MINT,
            from_address="0x0",  # Mint from zero address
            to_address=to_address,
            amount=amount,
            fee=Decimal('0'),
            timestamp=time.time(),
            metadata={"reason": reason}
        )
        
        # Update balances using SafeMath operations
        current_balance = self.balances.get(to_address, Decimal('0'))
        self.balances[to_address] = safe_add(current_balance, amount)
        self.total_minted = safe_add(self.total_minted, amount)
        self.circulation_supply = safe_add(self.circulation_supply, amount)
        self.transactions.append(transaction)
        
        return tx_id
    
    def transfer_tokens(self, from_address: str, to_address: str, amount: Decimal, fee: Decimal = Decimal('0')) -> str:
        """
        Transfer tokens between addresses using SafeMath operations
        
        CORRECTION CRITIQUE: Utilise SafeMath pour sécuriser les transferts
        """
        # Validate amounts with SafeMath
        amount = SafeMath.validate_amount(amount)
        fee = SafeMath.validate_amount(fee)
        
        # Calculate total transaction amount
        total_amount = safe_add(amount, fee)
        
        # Validate balance operation
        current_balance = self.get_balance(from_address)
        SafeMath.validate_balance_operation(current_balance, total_amount, 'subtract')
        
        tx_id = self.generate_tx_id()
        transaction = TokenTransaction(
            tx_id=tx_id,
            tx_type=TokenTransactionType.TRANSFER,
            from_address=from_address,
            to_address=to_address,
            amount=amount,
            fee=fee,
            timestamp=time.time(),
            metadata={}
        )
        
        # Update balances using SafeMath operations
        self.balances[from_address] = safe_subtract(self.balances[from_address], total_amount)
        current_to_balance = self.balances.get(to_address, Decimal('0'))
        self.balances[to_address] = safe_add(current_to_balance, amount)
        
        # Burn transaction fees using SafeMath
        if fee > Decimal('0'):
            burn_amount = safe_multiply(fee, self.TRANSACTION_FEE_BURN_RATE)
            self.burn_tokens(burn_amount, "transaction_fee_burn")
        
        self.transactions.append(transaction)
        return tx_id
    
    def burn_tokens(self, amount: Decimal, reason: str) -> str:
        """Burn tokens from circulation"""
        tx_id = self.generate_tx_id()
        transaction = TokenTransaction(
            tx_id=tx_id,
            tx_type=TokenTransactionType.BURN,
            from_address="burn_pool",
            to_address="0x0",
            amount=amount,
            fee=Decimal('0'),
            timestamp=time.time(),
            metadata={"reason": reason}
        )
        
        self.total_burned += amount
        self.circulation_supply -= amount
        self.transactions.append(transaction)
        
        return tx_id
    
    def stake_tokens(self, address: str, amount: Decimal) -> str:
        """Stake tokens for quality assurance"""
        if self.get_balance(address) < amount:
            raise ValueError("Insufficient balance for staking")
        
        tx_id = self.generate_tx_id()
        transaction = TokenTransaction(
            tx_id=tx_id,
            tx_type=TokenTransactionType.STAKE,
            from_address=address,
            to_address="stake_pool",
            amount=amount,
            fee=Decimal('0'),
            timestamp=time.time(),
            metadata={"stake_start": time.time()}
        )
        
        # Move tokens to staked balance
        self.balances[address] -= amount
        self.staked_balances[address] = self.staked_balances.get(address, Decimal('0')) + amount
        
        # Initialize staking rewards
        if address not in self.stake_rewards:
            self.stake_rewards[address] = {
                'last_reward_time': time.time(),
                'total_rewards': Decimal('0')
            }
        
        self.transactions.append(transaction)
        return tx_id
    
    def unstake_tokens(self, address: str, amount: Decimal) -> str:
        """Unstake tokens"""
        if self.get_staked_balance(address) < amount:
            raise ValueError("Insufficient staked balance")
        
        tx_id = self.generate_tx_id()
        transaction = TokenTransaction(
            tx_id=tx_id,
            tx_type=TokenTransactionType.UNSTAKE,
            from_address="stake_pool",
            to_address=address,
            amount=amount,
            fee=Decimal('0'),
            timestamp=time.time(),
            metadata={"unstake_time": time.time()}
        )
        
        # Move tokens back to regular balance
        self.staked_balances[address] -= amount
        self.balances[address] = self.balances.get(address, Decimal('0')) + amount
        
        self.transactions.append(transaction)
        return tx_id
    
    def calculate_archive_reward(self, size_bytes: int, rarity_score: float, content_type: str) -> Decimal:
        """Calculate reward for archiving content"""
        # Base reward based on size
        size_factor = min(size_bytes / (1024 * 1024), 100)  # Max factor for 100MB
        
        # Rarity multiplier (0.1 to 2.0)
        rarity_multiplier = max(0.1, min(rarity_score, 2.0))
        
        # Content type multiplier
        content_multipliers = {
            'text/html': 1.0,
            'application/pdf': 1.2,
            'video/*': 0.8,  # Videos are large but common
            'image/*': 0.9,
            'application/json': 1.1
        }
        content_multiplier = content_multipliers.get(content_type, 1.0)
        
        # Calculate reward (convert all to Decimal)
        size_factor_decimal = Decimal(str(size_factor / 100))
        base_reward = self.INITIAL_ARCHIVE_REWARD_MIN + (
            (self.INITIAL_ARCHIVE_REWARD_MAX - self.INITIAL_ARCHIVE_REWARD_MIN) * 
            size_factor_decimal
        )
        
        final_reward = base_reward * Decimal(str(rarity_multiplier)) * Decimal(str(content_multiplier))
        return final_reward.quantize(Decimal('0.01'), rounding=ROUND_DOWN)
    
    def calculate_storage_reward(self, storage_days: int, size_bytes: int) -> Decimal:
        """Calculate monthly storage reward"""
        # Convert days to months
        months = Decimal(str(storage_days)) / Decimal('30.0')
        
        # Size factor in GB
        size_gb = Decimal(str(size_bytes)) / Decimal(str(1024 * 1024 * 1024))
        
        # Base reward per GB per month
        size_gb_factor = min(size_gb / Decimal('100'), Decimal('1.0'))  # Scale up to 100GB
        reward_per_gb_month = self.STORAGE_REWARD_MIN + (
            (self.STORAGE_REWARD_MAX - self.STORAGE_REWARD_MIN) * size_gb_factor
        )
        
        monthly_reward = reward_per_gb_month * size_gb * months
        return monthly_reward.quantize(Decimal('0.01'), rounding=ROUND_DOWN)
    
    def calculate_bandwidth_reward(self, bytes_served: int) -> Decimal:
        """Calculate bandwidth reward for serving content"""
        gb_served = Decimal(str(bytes_served)) / Decimal(str(1024 * 1024 * 1024))
        
        gb_factor = min(gb_served / Decimal('1000'), Decimal('1.0'))  # Scale up to 1TB
        reward_per_gb = self.BANDWIDTH_REWARD_MIN + (
            (self.BANDWIDTH_REWARD_MAX - self.BANDWIDTH_REWARD_MIN) * gb_factor
        )
        
        total_reward = reward_per_gb * gb_served
        return total_reward.quantize(Decimal('0.01'), rounding=ROUND_DOWN)
    
    def reward_archive_contribution(self, address: str, archive_size: int, rarity_score: float, 
                                   content_type: str, contribution_type: str) -> str:
        """Reward various types of archive contributions"""
        if contribution_type == "initial_archive":
            amount = self.calculate_archive_reward(archive_size, rarity_score, content_type)
        elif contribution_type == "content_discovery":
            amount = self.DISCOVERY_REWARD_MIN + (
                Decimal(str(rarity_score)) * (self.DISCOVERY_REWARD_MAX - self.DISCOVERY_REWARD_MIN)
            )
        else:
            raise ValueError(f"Unknown contribution type: {contribution_type}")
        
        # Check if rewards pool has sufficient funds
        if self.pools['archiving_rewards'] < amount:
            # Reduce reward if pool is running low
            amount = min(amount, self.pools['archiving_rewards'])
        
        if amount <= Decimal('0'):
            raise ValueError("Insufficient rewards pool")
        
        tx_id = self.generate_tx_id()
        transaction = TokenTransaction(
            tx_id=tx_id,
            tx_type=TokenTransactionType.REWARD,
            from_address="archiving_rewards_pool",
            to_address=address,
            amount=amount,
            fee=Decimal('0'),
            timestamp=time.time(),
            metadata={
                "contribution_type": contribution_type,
                "archive_size": archive_size,
                "rarity_score": rarity_score,
                "content_type": content_type
            }
        )
        
        # Update balances
        self.pools['archiving_rewards'] -= amount
        self.balances[address] = self.balances.get(address, Decimal('0')) + amount
        
        self.transactions.append(transaction)
        return tx_id
    
    def get_balance(self, address: str) -> Decimal:
        """Get token balance for address"""
        return self.balances.get(address, Decimal('0'))
    
    def get_staked_balance(self, address: str) -> Decimal:
        """Get staked token balance for address"""
        return self.staked_balances.get(address, Decimal('0'))
    
    def get_total_balance(self, address: str) -> Decimal:
        """Get total balance (regular + staked)"""
        return self.get_balance(address) + self.get_staked_balance(address)
    
    def get_token_stats(self) -> Dict[str, Any]:
        """Get comprehensive token statistics"""
        return {
            'total_supply': str(self.TOTAL_SUPPLY),
            'total_minted': str(self.total_minted),
            'circulation_supply': str(self.circulation_supply),
            'total_burned': str(self.total_burned),
            'remaining_pools': {
                pool: str(amount) for pool, amount in self.pools.items()
            },
            'total_staked': str(sum(self.staked_balances.values())),
            'total_transactions': len(self.transactions),
            'burn_rate': str(self.TRANSACTION_FEE_BURN_RATE * 100) + '%'
        }
    
    def generate_tx_id(self) -> str:
        """Generate unique transaction ID"""
        timestamp = str(time.time())
        nonce = str(len(self.transactions))
        return hashlib.sha256((timestamp + nonce).encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert token state to dictionary"""
        return {
            'balances': {addr: str(balance) for addr, balance in self.balances.items()},
            'staked_balances': {addr: str(balance) for addr, balance in self.staked_balances.items()},
            'stake_rewards': self.stake_rewards,
            'transactions': [tx.to_dict() for tx in self.transactions],
            'total_burned': str(self.total_burned),
            'total_minted': str(self.total_minted),
            'circulation_supply': str(self.circulation_supply),
            'pools': {pool: str(amount) for pool, amount in self.pools.items()}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ARCToken':
        """Create token instance from dictionary"""
        token = cls()
        
        # Restore balances
        token.balances = {addr: Decimal(balance) for addr, balance in data['balances'].items()}
        token.staked_balances = {addr: Decimal(balance) for addr, balance in data['staked_balances'].items()}
        token.stake_rewards = data['stake_rewards']
        
        # Restore transactions
        token.transactions = [TokenTransaction.from_dict(tx_data) for tx_data in data['transactions']]
        
        # Restore stats
        token.total_burned = Decimal(data['total_burned'])
        token.total_minted = Decimal(data['total_minted'])
        token.circulation_supply = Decimal(data['circulation_supply'])
        token.pools = {pool: Decimal(amount) for pool, amount in data['pools'].items()}
        
        return token