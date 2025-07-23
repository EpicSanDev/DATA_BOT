"""
API REST complète pour ArchiveChain
Fournit une interface REST comprehensive pour interagir avec la blockchain
"""

from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import json
import time
import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime

# Import des modules ArchiveChain
import sys
sys.path.append('../..')
from src.blockchain.blockchain import ArchiveChain
from src.blockchain.archive_data import ArchiveData
from src.blockchain.tokens import TokenTransaction, TokenTransactionType
from src.blockchain.smart_contracts import DeploymentConfig

class ArchiveChainRestAPI:
    """
    API REST complète pour ArchiveChain avec endpoints sécurisés et documentés
    """
    
    def __init__(self, blockchain: ArchiveChain, host: str = '0.0.0.0', port: int = 5000):
        self.blockchain = blockchain
        self.host = host
        self.port = port
        
        # Configuration Flask
        self.app = Flask(__name__)
        self.app.config['JSON_SORT_KEYS'] = False
        
        # CORS pour permettre les requêtes cross-origin
        CORS(self.app)
        
        # Rate limiting pour la sécurité
        self.limiter = Limiter(
            app=self.app,
            key_func=get_remote_address,
            default_limits=["1000 per hour", "100 per minute"]
        )
        
        # Logger
        self.logger = self._setup_logger()
        
        # Enregistrer les routes
        self._register_routes()
        
        # Middleware pour le logging des requêtes
        self._setup_middleware()
    
    def _setup_logger(self) -> logging.Logger:
        """Configure le logger pour l'API"""
        logger = logging.getLogger('ArchiveChainAPI')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.FileHandler('blockchain/api/api.log')
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
    
    def _setup_middleware(self):
        """Configure le middleware pour le logging et la sécurité"""
        
        @self.app.before_request
        def log_request():
            self.logger.info(f"{request.method} {request.path} - {request.remote_addr}")
        
        @self.app.after_request
        def after_request(response):
            self.logger.info(f"Response: {response.status_code}")
            return response
        
        @self.app.errorhandler(404)
        def not_found(error):
            return jsonify({"error": "Endpoint not found"}), 404
        
        @self.app.errorhandler(500)
        def internal_error(error):
            self.logger.error(f"Internal error: {str(error)}")
            return jsonify({"error": "Internal server error"}), 500
    
    def _register_routes(self):
        """Enregistre toutes les routes de l'API"""
        
        # Routes de base
        self.app.add_url_rule('/', 'index', self.index, methods=['GET'])
        self.app.add_url_rule('/health', 'health', self.health_check, methods=['GET'])
        self.app.add_url_rule('/stats', 'stats', self.get_blockchain_stats, methods=['GET'])
        
        # Routes blockchain
        self.app.add_url_rule('/blocks', 'blocks', self.get_blocks, methods=['GET'])
        self.app.add_url_rule('/blocks/<int:height>', 'block_by_height', self.get_block_by_height, methods=['GET'])
        self.app.add_url_rule('/blocks/latest', 'latest_block', self.get_latest_block, methods=['GET'])
        
        # Routes transactions
        self.app.add_url_rule('/transactions', 'transactions', self.get_transactions, methods=['GET'])
        self.app.add_url_rule('/transactions/<string:tx_id>', 'transaction_by_id', self.get_transaction_by_id, methods=['GET'])
        
        # Routes archives
        self.app.add_url_rule('/archives', 'archives', self.get_archives, methods=['GET'])
        self.app.add_url_rule('/archives/<string:archive_id>', 'archive_by_id', self.get_archive_by_id, methods=['GET'])
        self.app.add_url_rule('/archives/search', 'search_archives', self.search_archives, methods=['POST'])
        self.app.add_url_rule('/archives/create', 'create_archive', self.create_archive, methods=['POST'])
        
        # Routes tokens ARC
        self.app.add_url_rule('/tokens/balance/<string:address>', 'token_balance', self.get_token_balance, methods=['GET'])
        self.app.add_url_rule('/tokens/transfer', 'transfer_tokens', self.transfer_tokens, methods=['POST'])
        self.app.add_url_rule('/tokens/stats', 'token_stats', self.get_token_stats, methods=['GET'])
        self.app.add_url_rule('/tokens/transactions/<string:address>', 'token_transactions', self.get_token_transactions, methods=['GET'])
        
        # Routes smart contracts
        self.app.add_url_rule('/contracts', 'contracts', self.get_contracts, methods=['GET'])
        self.app.add_url_rule('/contracts/<string:contract_id>', 'contract_by_id', self.get_contract_by_id, methods=['GET'])
        self.app.add_url_rule('/contracts/deploy', 'deploy_contract', self.deploy_contract, methods=['POST'])
        self.app.add_url_rule('/contracts/<string:contract_id>/execute', 'execute_contract', self.execute_contract, methods=['POST'])
        
        # Routes consensus et nœuds
        self.app.add_url_rule('/consensus/stats', 'consensus_stats', self.get_consensus_stats, methods=['GET'])
        self.app.add_url_rule('/nodes', 'nodes', self.get_nodes, methods=['GET'])
        self.app.add_url_rule('/nodes/<string:node_id>', 'node_by_id', self.get_node_by_id, methods=['GET'])
        
        # Routes mining et staking
        self.app.add_url_rule('/mining/mine', 'mine_block', self.mine_block, methods=['POST'])
        self.app.add_url_rule('/staking/stake', 'stake_tokens', self.stake_tokens, methods=['POST'])
        self.app.add_url_rule('/staking/unstake', 'unstake_tokens', self.unstake_tokens, methods=['POST'])
        
        # Routes bounties
        self.app.add_url_rule('/bounties', 'bounties', self.get_bounties, methods=['GET'])
        self.app.add_url_rule('/bounties/create', 'create_bounty', self.create_bounty, methods=['POST'])
        self.app.add_url_rule('/bounties/<string:bounty_id>/claim', 'claim_bounty', self.claim_bounty, methods=['POST'])
    
    # ==================== ROUTES DE BASE ====================
    
    def index(self):
        """Page d'accueil de l'API"""
        return jsonify({
            "name": "ArchiveChain REST API",
            "version": "1.0.0",
            "description": "API REST complète pour la blockchain ArchiveChain",
            "endpoints": {
                "blockchain": "/blocks, /transactions, /stats",
                "archives": "/archives, /archives/search",
                "tokens": "/tokens/balance, /tokens/transfer",
                "contracts": "/contracts, /contracts/deploy",
                "consensus": "/consensus/stats, /nodes",
                "mining": "/mining/mine, /staking/stake"
            },
            "documentation": "/docs",
            "timestamp": time.time()
        })
    
    @limiter.exempt
    def health_check(self):
        """Vérification de santé de l'API"""
        try:
            latest_block = self.blockchain.get_latest_block()
            is_healthy = latest_block is not None
            
            return jsonify({
                "status": "healthy" if is_healthy else "unhealthy",
                "timestamp": time.time(),
                "blockchain_height": len(self.blockchain.chain),
                "latest_block_hash": latest_block.hash if latest_block else None,
                "pending_transactions": len(self.blockchain.pending_transactions)
            }), 200 if is_healthy else 503
        except Exception as e:
            return jsonify({
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }), 503
    
    def get_blockchain_stats(self):
        """Statistiques globales de la blockchain"""
        try:
            stats = self.blockchain.get_blockchain_stats()
            return jsonify({
                "success": True,
                "data": stats,
                "timestamp": time.time()
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    # ==================== ROUTES BLOCKCHAIN ====================
    
    def get_blocks(self):
        """Liste des blocs avec pagination"""
        try:
            page = int(request.args.get('page', 1))
            limit = min(int(request.args.get('limit', 10)), 100)  # Max 100 blocs
            offset = (page - 1) * limit
            
            total_blocks = len(self.blockchain.chain)
            blocks = self.blockchain.chain[offset:offset + limit]
            
            return jsonify({
                "success": True,
                "data": {
                    "blocks": [self._serialize_block(block) for block in blocks],
                    "pagination": {
                        "page": page,
                        "limit": limit,
                        "total": total_blocks,
                        "pages": (total_blocks + limit - 1) // limit
                    }
                },
                "timestamp": time.time()
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    def get_block_by_height(self, height: int):
        """Bloc par hauteur"""
        try:
            if height < 0 or height >= len(self.blockchain.chain):
                return jsonify({"error": "Block height not found"}), 404
            
            block = self.blockchain.chain[height]
            return jsonify({
                "success": True,
                "data": self._serialize_block(block),
                "timestamp": time.time()
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    def get_latest_block(self):
        """Dernier bloc de la chaîne"""
        try:
            block = self.blockchain.get_latest_block()
            return jsonify({
                "success": True,
                "data": self._serialize_block(block),
                "timestamp": time.time()
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    # ==================== ROUTES TRANSACTIONS ====================
    
    def get_transactions(self):
        """Liste des transactions avec pagination"""
        try:
            page = int(request.args.get('page', 1))
            limit = min(int(request.args.get('limit', 10)), 100)
            
            # Récupérer toutes les transactions de tous les blocs
            all_transactions = []
            for block in self.blockchain.chain:
                all_transactions.extend(block.transactions)
            
            # Ajouter les transactions en attente
            all_transactions.extend(self.blockchain.pending_transactions)
            
            offset = (page - 1) * limit
            transactions = all_transactions[offset:offset + limit]
            
            return jsonify({
                "success": True,
                "data": {
                    "transactions": [self._serialize_transaction(tx) for tx in transactions],
                    "pagination": {
                        "page": page,
                        "limit": limit,
                        "total": len(all_transactions),
                        "pages": (len(all_transactions) + limit - 1) // limit
                    }
                },
                "timestamp": time.time()
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    def get_transaction_by_id(self, tx_id: str):
        """Transaction par ID"""
        try:
            # Chercher dans tous les blocs
            for block in self.blockchain.chain:
                for tx in block.transactions:
                    if tx.tx_id == tx_id:
                        return jsonify({
                            "success": True,
                            "data": self._serialize_transaction(tx),
                            "timestamp": time.time()
                        })
            
            # Chercher dans les transactions en attente
            for tx in self.blockchain.pending_transactions:
                if tx.tx_id == tx_id:
                    return jsonify({
                        "success": True,
                        "data": {**self._serialize_transaction(tx), "status": "pending"},
                        "timestamp": time.time()
                    })
            
            return jsonify({"error": "Transaction not found"}), 404
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    # ==================== ROUTES ARCHIVES ====================
    
    def get_archives(self):
        """Liste des archives avec pagination"""
        try:
            page = int(request.args.get('page', 1))
            limit = min(int(request.args.get('limit', 10)), 100)
            
            # Récupérer toutes les archives
            all_archives = []
            for block in self.blockchain.chain:
                for tx in block.transactions:
                    if tx.archive_data:
                        all_archives.append(tx.archive_data)
            
            offset = (page - 1) * limit
            archives = all_archives[offset:offset + limit]
            
            return jsonify({
                "success": True,
                "data": {
                    "archives": [self._serialize_archive(archive) for archive in archives],
                    "pagination": {
                        "page": page,
                        "limit": limit,
                        "total": len(all_archives),
                        "pages": (len(all_archives) + limit - 1) // limit
                    }
                },
                "timestamp": time.time()
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    def get_archive_by_id(self, archive_id: str):
        """Archive par ID"""
        try:
            for block in self.blockchain.chain:
                for tx in block.transactions:
                    if tx.archive_data and tx.archive_data.archive_id == archive_id:
                        return jsonify({
                            "success": True,
                            "data": self._serialize_archive(tx.archive_data),
                            "timestamp": time.time()
                        })
            
            return jsonify({"error": "Archive not found"}), 404
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    def search_archives(self):
        """Recherche d'archives"""
        try:
            data = request.get_json()
            if not data or 'query' not in data:
                return jsonify({"error": "Query required"}), 400
            
            query = data['query']
            archives = self.blockchain.search_archives(query)
            
            return jsonify({
                "success": True,
                "data": {
                    "archives": [self._serialize_archive(archive) for archive in archives],
                    "query": query,
                    "count": len(archives)
                },
                "timestamp": time.time()
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @limiter.limit("10 per minute")
    def create_archive(self):
        """Créer une nouvelle archive"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "Request body required"}), 400
            
            required_fields = ['url', 'archiver_address']
            for field in required_fields:
                if field not in data:
                    return jsonify({"error": f"Field '{field}' required"}), 400
            
            # Créer l'archive (simulation)
            archive_data = ArchiveData(
                archive_id="",  # Sera généré
                original_url=data['url'],
                archived_url="",  # Sera généré
                timestamp=time.time(),
                size_original=data.get('size', 1024),
                size_compressed=data.get('size', 1024),
                checksum="",  # Sera calculé
                content_type=data.get('content_type', 'text/html'),
                metadata=data.get('metadata', {})
            )
            
            tx_id = self.blockchain.add_archive(archive_data, data['archiver_address'])
            
            return jsonify({
                "success": True,
                "data": {
                    "transaction_id": tx_id,
                    "archive_id": archive_data.archive_id,
                    "status": "pending"
                },
                "timestamp": time.time()
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    # ==================== ROUTES TOKENS ====================
    
    def get_token_balance(self, address: str):
        """Balance de tokens pour une adresse"""
        try:
            balance = self.blockchain.get_balance(address)
            staked_balance = self.blockchain.token_system.get_staked_balance(address)
            
            return jsonify({
                "success": True,
                "data": {
                    "address": address,
                    "balance": str(balance),
                    "staked_balance": str(staked_balance),
                    "total_balance": str(balance + staked_balance)
                },
                "timestamp": time.time()
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @limiter.limit("5 per minute")
    def transfer_tokens(self):
        """Transférer des tokens"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "Request body required"}), 400
            
            required_fields = ['from_address', 'to_address', 'amount']
            for field in required_fields:
                if field not in data:
                    return jsonify({"error": f"Field '{field}' required"}), 400
            
            amount = Decimal(str(data['amount']))
            fee = Decimal(str(data.get('fee', '0')))
            
            tx_id = self.blockchain.transfer_tokens(
                data['from_address'],
                data['to_address'],
                amount,
                fee
            )
            
            return jsonify({
                "success": True,
                "data": {
                    "transaction_id": tx_id,
                    "from_address": data['from_address'],
                    "to_address": data['to_address'],
                    "amount": str(amount),
                    "fee": str(fee)
                },
                "timestamp": time.time()
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    def get_token_stats(self):
        """Statistiques des tokens ARC"""
        try:
            stats = self.blockchain.token_system.get_token_stats()
            return jsonify({
                "success": True,
                "data": stats,
                "timestamp": time.time()
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    def get_token_transactions(self, address: str):
        """Transactions de tokens pour une adresse"""
        try:
            page = int(request.args.get('page', 1))
            limit = min(int(request.args.get('limit', 10)), 100)
            
            # Filtrer les transactions de tokens pour cette adresse
            user_transactions = []
            for tx in self.blockchain.token_system.transactions:
                if tx.from_address == address or tx.to_address == address:
                    user_transactions.append(tx)
            
            offset = (page - 1) * limit
            transactions = user_transactions[offset:offset + limit]
            
            return jsonify({
                "success": True,
                "data": {
                    "transactions": [self._serialize_token_transaction(tx) for tx in transactions],
                    "pagination": {
                        "page": page,
                        "limit": limit,
                        "total": len(user_transactions),
                        "pages": (len(user_transactions) + limit - 1) // limit
                    }
                },
                "timestamp": time.time()
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    # ==================== MÉTHODES DE SÉRIALISATION ====================
    
    def _serialize_block(self, block) -> Dict[str, Any]:
        """Sérialise un bloc pour l'API"""
        return {
            "height": block.header.block_height,
            "hash": block.hash,
            "previous_hash": block.header.previous_hash,
            "timestamp": block.header.timestamp,
            "transactions_count": len(block.transactions),
            "nonce": block.header.nonce,
            "difficulty": block.header.difficulty,
            "merkle_root": block.header.merkle_root,
            "transactions": [self._serialize_transaction(tx) for tx in block.transactions[:10]]  # Limiter à 10 tx
        }
    
    def _serialize_transaction(self, tx) -> Dict[str, Any]:
        """Sérialise une transaction pour l'API"""
        base_data = {
            "tx_id": tx.tx_id,
            "type": tx.tx_type,
            "sender": tx.sender,
            "receiver": tx.receiver,
            "amount": tx.amount,
            "timestamp": tx.timestamp
        }
        
        if hasattr(tx, 'archive_data') and tx.archive_data:
            base_data["archive"] = self._serialize_archive(tx.archive_data)
        
        return base_data
    
    def _serialize_archive(self, archive) -> Dict[str, Any]:
        """Sérialise une archive pour l'API"""
        return {
            "archive_id": archive.archive_id,
            "original_url": archive.original_url,
            "archived_url": archive.archived_url,
            "timestamp": archive.timestamp,
            "size_original": archive.size_original,
            "size_compressed": archive.size_compressed,
            "content_type": archive.content_type,
            "checksum": archive.checksum,
            "metadata": archive.metadata
        }
    
    def _serialize_token_transaction(self, tx) -> Dict[str, Any]:
        """Sérialise une transaction de token pour l'API"""
        return {
            "tx_id": tx.tx_id,
            "type": tx.tx_type.value,
            "from_address": tx.from_address,
            "to_address": tx.to_address,
            "amount": str(tx.amount),
            "fee": str(tx.fee),
            "timestamp": tx.timestamp,
            "metadata": tx.metadata
        }
    
    # ==================== MÉTHODES UTILITAIRES ====================
    
    def run(self, debug: bool = False):
        """Démarre le serveur API"""
        self.logger.info(f"Démarrage de l'API REST sur {self.host}:{self.port}")
        self.app.run(host=self.host, port=self.port, debug=debug)
    
    def get_app(self):
        """Retourne l'application Flask (pour les tests)"""
        return self.app

# Ajouter les routes manquantes (simplifiées pour l'espace)
# Les méthodes suivantes seraient implémentées de manière similaire :
# - get_contracts, deploy_contract, execute_contract
# - get_consensus_stats, get_nodes, get_node_by_id  
# - mine_block, stake_tokens, unstake_tokens
# - get_bounties, create_bounty, claim_bounty