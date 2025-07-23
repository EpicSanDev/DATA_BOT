"""
ArchiveChain API Integration

Adds blockchain endpoints to the existing DATA_BOT API server,
providing RESTful access to blockchain functionality.
"""

import asyncio
import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any

from flask import Flask, jsonify, request
from flask_cors import CORS

from ..blockchain_integration import BlockchainArchiveIntegration
from ..config import Config

logger = logging.getLogger(__name__)

class ArchiveChainAPI:
    """REST API for ArchiveChain blockchain functionality"""
    
    def __init__(self, blockchain_integration: BlockchainArchiveIntegration):
        self.blockchain = blockchain_integration
        self.app = Flask(__name__)
        CORS(self.app)
        self._register_routes()
    
    def _register_routes(self):
        """Register all blockchain API routes"""
        
        @self.app.route('/api/blockchain/status', methods=['GET'])
        async def get_blockchain_status():
            """Get blockchain status and statistics"""
            try:
                stats = await self.blockchain.get_blockchain_stats()
                return jsonify({
                    'success': True,
                    'data': stats
                })
            except Exception as e:
                logger.error(f"Error getting blockchain status: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/blockchain/archives/search', methods=['GET'])
        async def search_blockchain_archives():
            """Search archives in the blockchain"""
            try:
                query = request.args.get('q', '')
                if not query:
                    return jsonify({
                        'success': False,
                        'error': 'Query parameter "q" is required'
                    }), 400
                
                results = await self.blockchain.search_blockchain_archives(query)
                return jsonify({
                    'success': True,
                    'data': {
                        'query': query,
                        'results': results,
                        'count': len(results)
                    }
                })
            except Exception as e:
                logger.error(f"Error searching blockchain archives: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/blockchain/archives/<path:url>', methods=['GET'])
        async def get_archive_by_url(url):
            """Get archive from blockchain by URL"""
            try:
                archive = await self.blockchain.get_archive_by_url(url)
                if archive:
                    return jsonify({
                        'success': True,
                        'data': archive
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': 'Archive not found'
                    }), 404
            except Exception as e:
                logger.error(f"Error getting archive by URL: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/blockchain/bounties', methods=['POST'])
        async def create_bounty():
            """Create an archive bounty"""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({
                        'success': False,
                        'error': 'JSON data required'
                    }), 400
                
                required_fields = ['creator_address', 'target_url', 'reward_amount']
                for field in required_fields:
                    if field not in data:
                        return jsonify({
                            'success': False,
                            'error': f'Missing required field: {field}'
                        }), 400
                
                bounty_id = await self.blockchain.create_archive_bounty(
                    data['creator_address'],
                    data['target_url'],
                    float(data['reward_amount']),
                    data.get('duration_hours', 168)  # Default 7 days
                )
                
                if bounty_id:
                    return jsonify({
                        'success': True,
                        'data': {
                            'bounty_id': bounty_id,
                            'target_url': data['target_url'],
                            'reward_amount': data['reward_amount']
                        }
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': 'Failed to create bounty'
                    }), 500
                    
            except Exception as e:
                logger.error(f"Error creating bounty: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/blockchain/bounties/<bounty_id>/claim', methods=['POST'])
        async def claim_bounty(bounty_id):
            """Claim an archive bounty"""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({
                        'success': False,
                        'error': 'JSON data required'
                    }), 400
                
                required_fields = ['claimant_address', 'archive_hash']
                for field in required_fields:
                    if field not in data:
                        return jsonify({
                            'success': False,
                            'error': f'Missing required field: {field}'
                        }), 400
                
                success = await self.blockchain.claim_archive_bounty(
                    bounty_id,
                    data['claimant_address'],
                    data['archive_hash']
                )
                
                return jsonify({
                    'success': success,
                    'data': {
                        'bounty_id': bounty_id,
                        'claimed': success
                    }
                })
                
            except Exception as e:
                logger.error(f"Error claiming bounty: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/blockchain/tokens/balance/<address>', methods=['GET'])
        async def get_token_balance(address):
            """Get ARC token balance for an address"""
            try:
                balance = await self.blockchain.get_token_balance(address)
                return jsonify({
                    'success': True,
                    'data': {
                        'address': address,
                        'balance': balance,
                        'currency': 'ARC'
                    }
                })
            except Exception as e:
                logger.error(f"Error getting token balance: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/blockchain/tokens/transfer', methods=['POST'])
        async def transfer_tokens():
            """Transfer ARC tokens between addresses"""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({
                        'success': False,
                        'error': 'JSON data required'
                    }), 400
                
                required_fields = ['from_address', 'to_address', 'amount']
                for field in required_fields:
                    if field not in data:
                        return jsonify({
                            'success': False,
                            'error': f'Missing required field: {field}'
                        }), 400
                
                tx_id = await self.blockchain.transfer_tokens(
                    data['from_address'],
                    data['to_address'],
                    float(data['amount'])
                )
                
                if tx_id:
                    return jsonify({
                        'success': True,
                        'data': {
                            'transaction_id': tx_id,
                            'from_address': data['from_address'],
                            'to_address': data['to_address'],
                            'amount': data['amount']
                        }
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': 'Transfer failed'
                    }), 500
                    
            except Exception as e:
                logger.error(f"Error transferring tokens: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/blockchain/nodes', methods=['GET'])
        async def get_network_nodes():
            """Get information about network nodes"""
            try:
                if not self.blockchain.blockchain or not self.blockchain.local_node:
                    return jsonify({
                        'success': False,
                        'error': 'Blockchain not available'
                    }), 503
                
                network_stats = self.blockchain.blockchain.node_network.get_network_stats()
                local_node_info = self.blockchain.local_node.get_node_info()
                
                return jsonify({
                    'success': True,
                    'data': {
                        'network_stats': network_stats,
                        'local_node': local_node_info
                    }
                })
                
            except Exception as e:
                logger.error(f"Error getting network nodes: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/blockchain/sync', methods=['POST'])
        async def sync_traditional_archives():
            """Sync traditional archives to blockchain"""
            try:
                data = request.get_json() or {}
                limit = data.get('limit', 100)
                
                if limit > 1000:  # Prevent excessive load
                    limit = 1000
                
                synced_count = await self.blockchain.sync_traditional_archives(limit)
                
                return jsonify({
                    'success': True,
                    'data': {
                        'synced_count': synced_count,
                        'limit': limit
                    }
                })
                
            except Exception as e:
                logger.error(f"Error syncing archives: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/blockchain/chain/blocks', methods=['GET'])
        async def get_blockchain_blocks():
            """Get blockchain blocks with pagination"""
            try:
                if not self.blockchain.blockchain:
                    return jsonify({
                        'success': False,
                        'error': 'Blockchain not available'
                    }), 503
                
                page = int(request.args.get('page', 1))
                per_page = min(int(request.args.get('per_page', 10)), 100)
                
                total_blocks = len(self.blockchain.blockchain.chain)
                start_idx = (page - 1) * per_page
                end_idx = min(start_idx + per_page, total_blocks)
                
                blocks = []
                for i in range(start_idx, end_idx):
                    block = self.blockchain.blockchain.chain[i]
                    blocks.append({
                        'height': block.header.block_height,
                        'hash': block.hash,
                        'timestamp': block.header.timestamp,
                        'transaction_count': len(block.transactions),
                        'archive_count': getattr(block, 'archive_count', 0),
                        'total_size': getattr(block, 'total_archive_size', 0)
                    })
                
                return jsonify({
                    'success': True,
                    'data': {
                        'blocks': blocks,
                        'pagination': {
                            'page': page,
                            'per_page': per_page,
                            'total': total_blocks,
                            'pages': (total_blocks + per_page - 1) // per_page
                        }
                    }
                })
                
            except Exception as e:
                logger.error(f"Error getting blockchain blocks: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/blockchain/metrics/realtime', methods=['GET'])
        async def get_realtime_metrics():
            """Get real-time blockchain metrics"""
            try:
                if not self.blockchain.blockchain:
                    return jsonify({
                        'success': False,
                        'error': 'Blockchain not available'
                    }), 503
                
                stats = await self.blockchain.get_blockchain_stats()
                
                # Calculate additional real-time metrics
                latest_block = self.blockchain.blockchain.get_latest_block()
                pending_tx_count = len(self.blockchain.blockchain.pending_transactions)
                
                # Node performance metrics
                node_metrics = {}
                if self.blockchain.local_node:
                    node_metrics = {
                        'storage_utilization': self.blockchain.local_node.metrics.storage_utilization,
                        'uptime_percentage': self.blockchain.local_node.metrics.uptime_percentage,
                        'total_requests_served': self.blockchain.local_node.metrics.total_requests_served,
                        'archives_stored': len(self.blockchain.local_node.stored_archives)
                    }
                
                return jsonify({
                    'success': True,
                    'data': {
                        'blockchain_stats': stats,
                        'latest_block': {
                            'height': latest_block.header.block_height,
                            'hash': latest_block.hash,
                            'timestamp': latest_block.header.timestamp
                        },
                        'pending_transactions': pending_tx_count,
                        'node_metrics': node_metrics,
                        'timestamp': datetime.now().isoformat()
                    }
                })
                
            except Exception as e:
                logger.error(f"Error getting real-time metrics: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

def add_blockchain_routes(app: Flask, blockchain_integration: BlockchainArchiveIntegration):
    """Add blockchain routes to existing Flask app"""
    
    blockchain_api = ArchiveChainAPI(blockchain_integration)
    
    # Register all blockchain routes with the main app
    for rule in blockchain_api.app.url_map.iter_rules():
        app.add_url_rule(
            rule.rule,
            endpoint=f"blockchain_{rule.endpoint}",
            view_func=blockchain_api.app.view_functions[rule.endpoint],
            methods=rule.methods
        )
    
    logger.info("ArchiveChain API routes registered")
    
    return app