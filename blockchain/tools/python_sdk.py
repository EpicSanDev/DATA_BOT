"""
SDK Python pour ArchiveChain
Interface simple et intuitive pour interagir avec la blockchain ArchiveChain
"""

import requests
import json
import time
import logging
from typing import Dict, List, Optional, Any, Union
from decimal import Decimal
from dataclasses import dataclass

# Import des modules ArchiveChain
import sys
sys.path.append('../..')
from src.blockchain.blockchain import ArchiveChain
from src.blockchain.archive_data import ArchiveData
from src.blockchain.tokens import TokenTransaction
from src.blockchain.smart_contracts import DeploymentConfig

@dataclass
class SDKConfig:
    """Configuration du SDK"""
    api_url: str = "http://localhost:5000"
    timeout: int = 30
    retries: int = 3
    api_key: Optional[str] = None
    
class ArchiveChainException(Exception):
    """Exception spécifique au SDK ArchiveChain"""
    pass

class ArchiveChainSDK:
    """
    SDK Python pour ArchiveChain - Interface simple pour développeurs
    
    Exemple d'utilisation:
    ```python
    sdk = ArchiveChainSDK()
    
    # Créer une archive
    result = sdk.create_archive("https://example.com", "mon_adresse")
    
    # Transférer des tokens
    sdk.transfer_tokens("from_addr", "to_addr", "100.0")
    
    # Déployer un contrat
    sdk.deploy_bounty_contract("https://target.com", "500.0", deadline)
    ```
    """
    
    def __init__(self, config: Optional[SDKConfig] = None, blockchain: Optional[ArchiveChain] = None):
        self.config = config or SDKConfig()
        self.blockchain = blockchain  # Pour mode local
        self.session = requests.Session()
        self.logger = self._setup_logger()
        
        # Configuration des headers
        if self.config.api_key:
            self.session.headers.update({"Authorization": f"Bearer {self.config.api_key}"})
        
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "ArchiveChain-SDK/1.0.0"
        })
    
    def _setup_logger(self) -> logging.Logger:
        """Configure le logger du SDK"""
        logger = logging.getLogger('ArchiveChainSDK')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - SDK - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Effectue une requête API avec gestion d'erreurs et retry"""
        url = f"{self.config.api_url}{endpoint}"
        
        for attempt in range(self.config.retries):
            try:
                if method.upper() == 'GET':
                    response = self.session.get(url, timeout=self.config.timeout)
                elif method.upper() == 'POST':
                    response = self.session.post(url, json=data, timeout=self.config.timeout)
                elif method.upper() == 'PUT':
                    response = self.session.put(url, json=data, timeout=self.config.timeout)
                elif method.upper() == 'DELETE':
                    response = self.session.delete(url, timeout=self.config.timeout)
                else:
                    raise ValueError(f"Méthode HTTP non supportée: {method}")
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Tentative {attempt + 1} échouée: {str(e)}")
                if attempt == self.config.retries - 1:
                    raise ArchiveChainException(f"Échec après {self.config.retries} tentatives: {str(e)}")
                time.sleep(2 ** attempt)  # Backoff exponentiel
    
    def _use_local_blockchain(self, operation: str, *args, **kwargs):
        """Utilise la blockchain locale si disponible"""
        if not self.blockchain:
            raise ArchiveChainException("Mode local non disponible - blockchain non fournie")
        
        try:
            if operation == "create_archive":
                return self.blockchain.add_archive(*args, **kwargs)
            elif operation == "transfer_tokens":
                return self.blockchain.transfer_tokens(*args, **kwargs)
            elif operation == "get_balance":
                return self.blockchain.get_balance(*args, **kwargs)
            elif operation == "search_archives":
                return self.blockchain.search_archives(*args, **kwargs)
            else:
                raise ValueError(f"Opération locale non supportée: {operation}")
                
        except Exception as e:
            raise ArchiveChainException(f"Erreur blockchain locale: {str(e)}")
    
    # ==================== MÉTHODES BLOCKCHAIN ====================
    
    def get_blockchain_stats(self) -> Dict[str, Any]:
        """Récupère les statistiques de la blockchain"""
        if self.blockchain:
            return self.blockchain.get_blockchain_stats()
        
        response = self._make_request('GET', '/stats')
        return response.get('data', {})
    
    def get_latest_block(self) -> Dict[str, Any]:
        """Récupère le dernier bloc"""
        response = self._make_request('GET', '/blocks/latest')
        return response.get('data', {})
    
    def get_block_by_height(self, height: int) -> Dict[str, Any]:
        """Récupère un bloc par sa hauteur"""
        response = self._make_request('GET', f'/blocks/{height}')
        return response.get('data', {})
    
    def get_blocks(self, page: int = 1, limit: int = 10) -> Dict[str, Any]:
        """Récupère une liste de blocs avec pagination"""
        response = self._make_request('GET', f'/blocks?page={page}&limit={limit}')
        return response.get('data', {})
    
    # ==================== MÉTHODES ARCHIVES ====================
    
    def create_archive(self, url: str, archiver_address: str, 
                      metadata: Optional[Dict] = None) -> str:
        """
        Crée une nouvelle archive
        
        Args:
            url: URL à archiver
            archiver_address: Adresse de l'archiveur
            metadata: Métadonnées optionnelles
            
        Returns:
            ID de la transaction
        """
        if self.blockchain:
            # Mode local
            archive_data = ArchiveData(
                archive_id="",
                original_url=url,
                archived_url="",
                timestamp=time.time(),
                size_original=1024,  # Simulé
                size_compressed=1024,
                checksum="",
                content_type="text/html",
                metadata=metadata or {}
            )
            return self._use_local_blockchain("create_archive", archive_data, archiver_address)
        
        # Mode API
        data = {
            "url": url,
            "archiver_address": archiver_address,
            "metadata": metadata or {}
        }
        
        response = self._make_request('POST', '/archives/create', data)
        return response.get('data', {}).get('transaction_id', '')
    
    def get_archive(self, archive_id: str) -> Optional[Dict[str, Any]]:
        """Récupère une archive par son ID"""
        try:
            response = self._make_request('GET', f'/archives/{archive_id}')
            return response.get('data')
        except ArchiveChainException:
            return None
    
    def search_archives(self, query: str) -> List[Dict[str, Any]]:
        """Recherche des archives"""
        if self.blockchain:
            archives = self._use_local_blockchain("search_archives", query)
            return [self._serialize_archive_data(archive) for archive in archives]
        
        data = {"query": query}
        response = self._make_request('POST', '/archives/search', data)
        return response.get('data', {}).get('archives', [])
    
    def get_archives(self, page: int = 1, limit: int = 10) -> Dict[str, Any]:
        """Récupère une liste d'archives"""
        response = self._make_request('GET', f'/archives?page={page}&limit={limit}')
        return response.get('data', {})
    
    # ==================== MÉTHODES TOKENS ====================
    
    def get_balance(self, address: str) -> Dict[str, str]:
        """Récupère le solde d'une adresse"""
        if self.blockchain:
            balance = self._use_local_blockchain("get_balance", address)
            staked = self.blockchain.token_system.get_staked_balance(address)
            return {
                "balance": str(balance),
                "staked_balance": str(staked),
                "total_balance": str(balance + staked)
            }
        
        response = self._make_request('GET', f'/tokens/balance/{address}')
        return response.get('data', {})
    
    def transfer_tokens(self, from_address: str, to_address: str, 
                       amount: Union[str, Decimal], fee: Union[str, Decimal] = "0") -> str:
        """
        Transfère des tokens entre adresses
        
        Args:
            from_address: Adresse source
            to_address: Adresse destination
            amount: Montant à transférer
            fee: Frais de transaction
            
        Returns:
            ID de la transaction
        """
        if self.blockchain:
            return self._use_local_blockchain(
                "transfer_tokens", 
                from_address, 
                to_address, 
                Decimal(str(amount)), 
                Decimal(str(fee))
            )
        
        data = {
            "from_address": from_address,
            "to_address": to_address,
            "amount": str(amount),
            "fee": str(fee)
        }
        
        response = self._make_request('POST', '/tokens/transfer', data)
        return response.get('data', {}).get('transaction_id', '')
    
    def get_token_stats(self) -> Dict[str, Any]:
        """Récupère les statistiques des tokens"""
        if self.blockchain:
            return self.blockchain.token_system.get_token_stats()
        
        response = self._make_request('GET', '/tokens/stats')
        return response.get('data', {})
    
    def stake_tokens(self, address: str, amount: Union[str, Decimal]) -> str:
        """Met en stake des tokens"""
        data = {
            "address": address,
            "amount": str(amount)
        }
        
        response = self._make_request('POST', '/staking/stake', data)
        return response.get('data', {}).get('transaction_id', '')
    
    def unstake_tokens(self, address: str, amount: Union[str, Decimal]) -> str:
        """Retire des tokens du stake"""
        data = {
            "address": address,
            "amount": str(amount)
        }
        
        response = self._make_request('POST', '/staking/unstake', data)
        return response.get('data', {}).get('transaction_id', '')
    
    # ==================== MÉTHODES SMART CONTRACTS ====================
    
    def deploy_bounty_contract(self, target_url: str, reward: Union[str, Decimal], 
                              deadline: float, creator: str) -> str:
        """
        Déploie un contrat de bounty d'archive
        
        Args:
            target_url: URL cible à archiver
            reward: Récompense en tokens ARC
            deadline: Timestamp de deadline
            creator: Adresse du créateur
            
        Returns:
            ID du contrat déployé
        """
        if self.blockchain:
            return self.blockchain.create_archive_bounty(creator, target_url, Decimal(str(reward)), deadline)
        
        data = {
            "contract_type": "ArchiveBounty",
            "creator": creator,
            "constructor_params": {
                "target_url": target_url,
                "reward": str(reward),
                "deadline": deadline
            }
        }
        
        response = self._make_request('POST', '/contracts/deploy', data)
        return response.get('data', {}).get('contract_id', '')
    
    def deploy_preservation_pool(self, target_archives: List[str], 
                               initial_funding: Union[str, Decimal], creator: str) -> str:
        """Déploie un contrat de pool de préservation"""
        if self.blockchain:
            return self.blockchain.create_preservation_pool(creator, target_archives, Decimal(str(initial_funding)))
        
        data = {
            "contract_type": "PreservationPool",
            "creator": creator,
            "constructor_params": {
                "target_archives": target_archives,
                "initial_funding": str(initial_funding)
            }
        }
        
        response = self._make_request('POST', '/contracts/deploy', data)
        return response.get('data', {}).get('contract_id', '')
    
    def get_contract(self, contract_id: str) -> Optional[Dict[str, Any]]:
        """Récupère un contrat par son ID"""
        try:
            response = self._make_request('GET', f'/contracts/{contract_id}')
            return response.get('data')
        except ArchiveChainException:
            return None
    
    def execute_contract(self, contract_id: str, function_name: str, 
                        params: Dict[str, Any], caller: str) -> Any:
        """Exécute une fonction de contrat"""
        if self.blockchain:
            return self.blockchain.smart_contracts.execute_contract(
                contract_id, function_name, params, caller
            )
        
        data = {
            "function_name": function_name,
            "params": params,
            "caller": caller
        }
        
        response = self._make_request('POST', f'/contracts/{contract_id}/execute', data)
        return response.get('data')
    
    def claim_bounty(self, bounty_id: str, claimant: str, archive_hash: str) -> bool:
        """Réclame une bounty d'archive"""
        params = {"archive_hash": archive_hash}
        result = self.execute_contract(bounty_id, "claimBounty", params, claimant)
        return bool(result)
    
    # ==================== MÉTHODES TRANSACTIONS ====================
    
    def get_transaction(self, tx_id: str) -> Optional[Dict[str, Any]]:
        """Récupère une transaction par son ID"""
        try:
            response = self._make_request('GET', f'/transactions/{tx_id}')
            return response.get('data')
        except ArchiveChainException:
            return None
    
    def get_transactions(self, page: int = 1, limit: int = 10) -> Dict[str, Any]:
        """Récupère une liste de transactions"""
        response = self._make_request('GET', f'/transactions?page={page}&limit={limit}')
        return response.get('data', {})
    
    def get_token_transactions(self, address: str, page: int = 1, limit: int = 10) -> Dict[str, Any]:
        """Récupère les transactions de tokens pour une adresse"""
        response = self._make_request('GET', f'/tokens/transactions/{address}?page={page}&limit={limit}')
        return response.get('data', {})
    
    # ==================== MÉTHODES UTILITAIRES ====================
    
    def wait_for_transaction(self, tx_id: str, timeout: int = 60) -> Optional[Dict[str, Any]]:
        """Attend qu'une transaction soit confirmée"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            tx = self.get_transaction(tx_id)
            if tx and tx.get('status') != 'pending':
                return tx
            time.sleep(2)
        
        return None
    
    def wait_for_confirmation(self, tx_id: str, confirmations: int = 1, timeout: int = 300) -> bool:
        """Attend un nombre spécifique de confirmations"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            tx = self.get_transaction(tx_id)
            if tx:
                tx_confirmations = tx.get('confirmations', 0)
                if tx_confirmations >= confirmations:
                    return True
            time.sleep(5)
        
        return False
    
    def estimate_fee(self, operation: str, **kwargs) -> Decimal:
        """Estime les frais pour une opération"""
        # Estimation basique - dans la réalité, ceci interrogerait l'API
        fee_table = {
            "transfer": Decimal("0.01"),
            "archive": Decimal("0.05"),
            "contract_deploy": Decimal("0.1"),
            "contract_execute": Decimal("0.02")
        }
        
        return fee_table.get(operation, Decimal("0.01"))
    
    def _serialize_archive_data(self, archive_data: ArchiveData) -> Dict[str, Any]:
        """Sérialise les données d'archive pour l'API"""
        return {
            "archive_id": archive_data.archive_id,
            "original_url": archive_data.original_url,
            "archived_url": archive_data.archived_url,
            "timestamp": archive_data.timestamp,
            "size_original": archive_data.size_original,
            "size_compressed": archive_data.size_compressed,
            "content_type": archive_data.content_type,
            "checksum": archive_data.checksum,
            "metadata": archive_data.metadata
        }
    
    # ==================== MÉTHODES AVANCÉES ====================
    
    def batch_create_archives(self, urls: List[str], archiver_address: str) -> List[str]:
        """Crée plusieurs archives en lot"""
        transaction_ids = []
        
        for url in urls:
            try:
                tx_id = self.create_archive(url, archiver_address)
                transaction_ids.append(tx_id)
                self.logger.info(f"Archive créée pour {url}: {tx_id}")
            except Exception as e:
                self.logger.error(f"Erreur lors de la création d'archive pour {url}: {e}")
                transaction_ids.append(None)
        
        return transaction_ids
    
    def monitor_address(self, address: str, callback: callable, poll_interval: int = 10):
        """Surveille une adresse pour les nouvelles transactions"""
        last_tx_count = 0
        
        while True:
            try:
                transactions = self.get_token_transactions(address, limit=100)
                current_tx_count = transactions.get('pagination', {}).get('total', 0)
                
                if current_tx_count > last_tx_count:
                    new_transactions = transactions.get('transactions', [])[:current_tx_count - last_tx_count]
                    for tx in new_transactions:
                        callback(tx)
                    
                    last_tx_count = current_tx_count
                
                time.sleep(poll_interval)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.logger.error(f"Erreur lors de la surveillance: {e}")
                time.sleep(poll_interval)
    
    def get_network_status(self) -> Dict[str, Any]:
        """Récupère le statut du réseau"""
        try:
            response = self._make_request('GET', '/health')
            return {
                "status": response.get('status', 'unknown'),
                "blockchain_height": response.get('blockchain_height', 0),
                "pending_transactions": response.get('pending_transactions', 0),
                "timestamp": response.get('timestamp', time.time())
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": time.time()
            }
    
    def close(self):
        """Ferme la session SDK"""
        self.session.close()
        self.logger.info("Session SDK fermée")

# Factory function pour créer des instances SDK
def create_sdk(api_url: str = "http://localhost:5000", 
               api_key: Optional[str] = None,
               blockchain: Optional[ArchiveChain] = None) -> ArchiveChainSDK:
    """
    Factory function pour créer une instance SDK
    
    Args:
        api_url: URL de l'API ArchiveChain
        api_key: Clé API optionnelle
        blockchain: Instance blockchain pour mode local
        
    Returns:
        Instance du SDK configurée
    """
    config = SDKConfig(api_url=api_url, api_key=api_key)
    return ArchiveChainSDK(config, blockchain)