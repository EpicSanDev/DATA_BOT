"""
Gestionnaire P2P pour ArchiveChain
Gère la découverte de nœuds, les connexions et la communication peer-to-peer
"""

import asyncio
import json
import time
import logging
from typing import Dict, List, Optional, Set, Callable, Any
from dataclasses import dataclass, asdict
import socket
import threading
from concurrent.futures import ThreadPoolExecutor

# Import des modules ArchiveChain
import sys
sys.path.append('../..')
from src.blockchain.node import ArchiveNode, NodeType, NodeNetwork

@dataclass
class PeerInfo:
    """Informations sur un peer du réseau"""
    node_id: str
    address: str
    port: int
    node_type: NodeType
    capabilities: List[str]
    last_seen: float
    reputation: float = 1.0
    latency: float = 0.0
    version: str = "1.0.0"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PeerInfo':
        data['node_type'] = NodeType(data['node_type'])
        return cls(**data)

@dataclass
class NetworkMessage:
    """Message réseau P2P"""
    message_type: str
    sender_id: str
    receiver_id: str
    payload: Dict[str, Any]
    timestamp: float
    signature: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class P2PManager:
    """
    Gestionnaire principal du réseau P2P ArchiveChain
    Gère la découverte, connexion et communication entre nœuds
    """
    
    # Types de messages P2P
    MSG_HANDSHAKE = "handshake"
    MSG_PEER_LIST = "peer_list"
    MSG_BLOCK_ANNOUNCE = "block_announce"
    MSG_TX_ANNOUNCE = "tx_announce"
    MSG_ARCHIVE_REQUEST = "archive_request"
    MSG_ARCHIVE_RESPONSE = "archive_response"
    MSG_SYNC_REQUEST = "sync_request"
    MSG_SYNC_RESPONSE = "sync_response"
    MSG_PING = "ping"
    MSG_PONG = "pong"
    
    def __init__(self, node: ArchiveNode, port: int = 8333):
        self.node = node
        self.port = port
        self.peers: Dict[str, PeerInfo] = {}
        self.connections: Dict[str, socket.socket] = {}
        self.message_handlers: Dict[str, Callable] = {}
        self.running = False
        self.server_socket: Optional[socket.socket] = None
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.logger = self._setup_logger()
        
        # Configuration réseau
        self.max_peers = 50
        self.peer_timeout = 300  # 5 minutes
        self.heartbeat_interval = 30  # 30 secondes
        self.bootstrap_nodes = [
            ("bootstrap1.archivechain.io", 8333),
            ("bootstrap2.archivechain.io", 8333),
            ("bootstrap3.archivechain.io", 8333)
        ]
        
        # Statistiques réseau
        self.stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "connections_established": 0,
            "connections_failed": 0,
            "bytes_sent": 0,
            "bytes_received": 0,
            "start_time": time.time()
        }
        
        self._register_message_handlers()
    
    def _setup_logger(self) -> logging.Logger:
        """Configure le logger P2P"""
        logger = logging.getLogger(f'P2PManager-{self.node.node_id}')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.FileHandler(f'blockchain/network/p2p_{self.node.node_id}.log')
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
    
    def _register_message_handlers(self):
        """Enregistre les gestionnaires de messages"""
        self.message_handlers = {
            self.MSG_HANDSHAKE: self._handle_handshake,
            self.MSG_PEER_LIST: self._handle_peer_list,
            self.MSG_BLOCK_ANNOUNCE: self._handle_block_announce,
            self.MSG_TX_ANNOUNCE: self._handle_tx_announce,
            self.MSG_ARCHIVE_REQUEST: self._handle_archive_request,
            self.MSG_ARCHIVE_RESPONSE: self._handle_archive_response,
            self.MSG_SYNC_REQUEST: self._handle_sync_request,
            self.MSG_SYNC_RESPONSE: self._handle_sync_response,
            self.MSG_PING: self._handle_ping,
            self.MSG_PONG: self._handle_pong
        }
    
    async def start(self):
        """Démarre le gestionnaire P2P"""
        self.logger.info(f"Démarrage du gestionnaire P2P sur le port {self.port}")
        self.running = True
        
        # Démarrer le serveur pour accepter les connexions entrantes
        await self._start_server()
        
        # Se connecter aux nœuds bootstrap
        await self._connect_to_bootstrap_nodes()
        
        # Démarrer les tâches de maintenance
        asyncio.create_task(self._heartbeat_loop())
        asyncio.create_task(self._peer_maintenance_loop())
        
        self.logger.info("Gestionnaire P2P démarré avec succès")
    
    async def stop(self):
        """Arrête le gestionnaire P2P"""
        self.logger.info("Arrêt du gestionnaire P2P")
        self.running = False
        
        # Fermer toutes les connexions
        for peer_id, connection in self.connections.items():
            try:
                connection.close()
            except Exception as e:
                self.logger.warning(f"Erreur lors de la fermeture de la connexion {peer_id}: {e}")
        
        # Fermer le serveur
        if self.server_socket:
            self.server_socket.close()
        
        # Arrêter l'executor
        self.executor.shutdown(wait=True)
        
        self.logger.info("Gestionnaire P2P arrêté")
    
    async def _start_server(self):
        """Démarre le serveur pour accepter les connexions entrantes"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('0.0.0.0', self.port))
            self.server_socket.listen(10)
            self.server_socket.setblocking(False)
            
            self.logger.info(f"Serveur P2P en écoute sur le port {self.port}")
            
            # Boucle d'acceptation des connexions
            asyncio.create_task(self._accept_connections())
            
        except Exception as e:
            self.logger.error(f"Erreur lors du démarrage du serveur: {e}")
            raise
    
    async def _accept_connections(self):
        """Accepte les connexions entrantes"""
        while self.running:
            try:
                # Utiliser un timeout pour éviter de bloquer
                self.server_socket.settimeout(1.0)
                client_socket, address = self.server_socket.accept()
                
                self.logger.info(f"Nouvelle connexion entrante de {address}")
                
                # Traiter la connexion dans un thread séparé
                self.executor.submit(self._handle_incoming_connection, client_socket, address)
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    self.logger.error(f"Erreur lors de l'acceptation d'une connexion: {e}")
                await asyncio.sleep(0.1)
    
    def _handle_incoming_connection(self, client_socket: socket.socket, address):
        """Gère une connexion entrante"""
        try:
            # Recevoir le handshake
            data = client_socket.recv(4096)
            if not data:
                client_socket.close()
                return
            
            message = json.loads(data.decode('utf-8'))
            
            if message.get('message_type') == self.MSG_HANDSHAKE:
                peer_info = self._process_handshake(message)
                if peer_info:
                    # Enregistrer le peer et la connexion
                    self.peers[peer_info.node_id] = peer_info
                    self.connections[peer_info.node_id] = client_socket
                    self.stats["connections_established"] += 1
                    
                    # Envoyer notre handshake en réponse
                    response = self._create_handshake_message()
                    self._send_message_to_socket(client_socket, response)
                    
                    self.logger.info(f"Connexion établie avec {peer_info.node_id}")
                else:
                    client_socket.close()
            else:
                client_socket.close()
                
        except Exception as e:
            self.logger.error(f"Erreur lors du traitement de la connexion entrante: {e}")
            client_socket.close()
    
    async def connect_to_peer(self, address: str, port: int) -> bool:
        """Se connecte à un peer spécifique"""
        try:
            self.logger.info(f"Tentative de connexion à {address}:{port}")
            
            # Créer la socket
            peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_socket.settimeout(10.0)  # Timeout de 10 secondes
            
            # Se connecter
            peer_socket.connect((address, port))
            
            # Envoyer le handshake
            handshake = self._create_handshake_message()
            self._send_message_to_socket(peer_socket, handshake)
            
            # Recevoir la réponse
            response_data = peer_socket.recv(4096)
            response = json.loads(response_data.decode('utf-8'))
            
            if response.get('message_type') == self.MSG_HANDSHAKE:
                peer_info = self._process_handshake(response)
                if peer_info:
                    # Enregistrer le peer
                    self.peers[peer_info.node_id] = peer_info
                    self.connections[peer_info.node_id] = peer_socket
                    self.stats["connections_established"] += 1
                    
                    self.logger.info(f"Connexion réussie avec {peer_info.node_id}")
                    return True
            
            peer_socket.close()
            self.stats["connections_failed"] += 1
            return False
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la connexion à {address}:{port}: {e}")
            self.stats["connections_failed"] += 1
            return False
    
    async def _connect_to_bootstrap_nodes(self):
        """Se connecte aux nœuds bootstrap"""
        for address, port in self.bootstrap_nodes:
            try:
                # Résoudre l'adresse (simulation - dans la réalité, utiliser DNS)
                if address.endswith('.archivechain.io'):
                    # Simuler des adresses IP pour les bootstrap nodes
                    bootstrap_ips = {
                        'bootstrap1.archivechain.io': '192.168.1.100',
                        'bootstrap2.archivechain.io': '192.168.1.101',
                        'bootstrap3.archivechain.io': '192.168.1.102'
                    }
                    real_address = bootstrap_ips.get(address, '127.0.0.1')
                else:
                    real_address = address
                
                success = await self.connect_to_peer(real_address, port)
                if success:
                    self.logger.info(f"Connecté au bootstrap node {address}")
                else:
                    self.logger.warning(f"Échec de connexion au bootstrap node {address}")
                    
            except Exception as e:
                self.logger.warning(f"Erreur avec le bootstrap node {address}: {e}")
    
    def _create_handshake_message(self) -> Dict[str, Any]:
        """Crée un message de handshake"""
        return {
            "message_type": self.MSG_HANDSHAKE,
            "sender_id": self.node.node_id,
            "payload": {
                "node_type": self.node.node_type.value,
                "capabilities": self.node.capabilities,
                "version": "1.0.0",
                "port": self.port,
                "timestamp": time.time()
            }
        }
    
    def _process_handshake(self, message: Dict[str, Any]) -> Optional[PeerInfo]:
        """Traite un message de handshake"""
        try:
            payload = message.get('payload', {})
            
            peer_info = PeerInfo(
                node_id=message['sender_id'],
                address="", # Sera rempli par l'appelant
                port=payload.get('port', 8333),
                node_type=NodeType(payload['node_type']),
                capabilities=payload.get('capabilities', []),
                last_seen=time.time(),
                version=payload.get('version', '1.0.0')
            )
            
            return peer_info
            
        except Exception as e:
            self.logger.error(f"Erreur lors du traitement du handshake: {e}")
            return None
    
    async def broadcast_message(self, message_type: str, payload: Dict[str, Any]):
        """Diffuse un message à tous les peers connectés"""
        message = NetworkMessage(
            message_type=message_type,
            sender_id=self.node.node_id,
            receiver_id="broadcast",
            payload=payload,
            timestamp=time.time()
        )
        
        # Envoyer à tous les peers connectés
        for peer_id in list(self.connections.keys()):
            await self.send_message_to_peer(peer_id, message)
    
    async def send_message_to_peer(self, peer_id: str, message: NetworkMessage) -> bool:
        """Envoie un message à un peer spécifique"""
        if peer_id not in self.connections:
            self.logger.warning(f"Pas de connexion avec le peer {peer_id}")
            return False
        
        try:
            connection = self.connections[peer_id]
            self._send_message_to_socket(connection, message.to_dict())
            self.stats["messages_sent"] += 1
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'envoi du message à {peer_id}: {e}")
            # Retirer la connexion défaillante
            self._remove_peer(peer_id)
            return False
    
    def _send_message_to_socket(self, sock: socket.socket, message: Dict[str, Any]):
        """Envoie un message via une socket"""
        data = json.dumps(message).encode('utf-8')
        sock.sendall(data)
        self.stats["bytes_sent"] += len(data)
    
    async def _heartbeat_loop(self):
        """Boucle de heartbeat pour maintenir les connexions"""
        while self.running:
            try:
                # Envoyer un ping à tous les peers
                for peer_id in list(self.peers.keys()):
                    ping_message = NetworkMessage(
                        message_type=self.MSG_PING,
                        sender_id=self.node.node_id,
                        receiver_id=peer_id,
                        payload={"timestamp": time.time()},
                        timestamp=time.time()
                    )
                    await self.send_message_to_peer(peer_id, ping_message)
                
                await asyncio.sleep(self.heartbeat_interval)
                
            except Exception as e:
                self.logger.error(f"Erreur dans la boucle heartbeat: {e}")
                await asyncio.sleep(5)
    
    async def _peer_maintenance_loop(self):
        """Boucle de maintenance des peers"""
        while self.running:
            try:
                current_time = time.time()
                peers_to_remove = []
                
                # Identifier les peers inactifs
                for peer_id, peer_info in self.peers.items():
                    if current_time - peer_info.last_seen > self.peer_timeout:
                        peers_to_remove.append(peer_id)
                
                # Retirer les peers inactifs
                for peer_id in peers_to_remove:
                    self._remove_peer(peer_id)
                    self.logger.info(f"Peer retiré pour inactivité: {peer_id}")
                
                # Découvrir de nouveaux peers si nécessaire
                if len(self.peers) < self.max_peers // 2:
                    await self._discover_new_peers()
                
                await asyncio.sleep(60)  # Maintenance toutes les minutes
                
            except Exception as e:
                self.logger.error(f"Erreur dans la maintenance des peers: {e}")
                await asyncio.sleep(10)
    
    def _remove_peer(self, peer_id: str):
        """Retire un peer du réseau"""
        if peer_id in self.peers:
            del self.peers[peer_id]
        
        if peer_id in self.connections:
            try:
                self.connections[peer_id].close()
            except:
                pass
            del self.connections[peer_id]
    
    async def _discover_new_peers(self):
        """Découvre de nouveaux peers via les peers existants"""
        # Demander la liste des peers à nos peers connectés
        for peer_id in list(self.peers.keys()):
            request_message = NetworkMessage(
                message_type=self.MSG_PEER_LIST,
                sender_id=self.node.node_id,
                receiver_id=peer_id,
                payload={"request": "peer_list"},
                timestamp=time.time()
            )
            await self.send_message_to_peer(peer_id, request_message)
    
    # Gestionnaires de messages
    def _handle_handshake(self, message: Dict[str, Any]):
        """Gère les messages de handshake"""
        # Déjà traité dans les méthodes de connexion
        pass
    
    def _handle_peer_list(self, message: Dict[str, Any]):
        """Gère les demandes/réponses de liste de peers"""
        payload = message.get('payload', {})
        
        if payload.get('request') == 'peer_list':
            # Envoyer notre liste de peers
            peer_list = [peer.to_dict() for peer in self.peers.values()]
            response = NetworkMessage(
                message_type=self.MSG_PEER_LIST,
                sender_id=self.node.node_id,
                receiver_id=message['sender_id'],
                payload={"peers": peer_list},
                timestamp=time.time()
            )
            asyncio.create_task(self.send_message_to_peer(message['sender_id'], response))
        
        elif 'peers' in payload:
            # Traiter la liste de peers reçue
            for peer_data in payload['peers']:
                if peer_data['node_id'] not in self.peers:
                    # Tentative de connexion au nouveau peer
                    asyncio.create_task(
                        self.connect_to_peer(peer_data['address'], peer_data['port'])
                    )
    
    def _handle_block_announce(self, message: Dict[str, Any]):
        """Gère les annonces de nouveaux blocs"""
        # À implémenter selon les besoins de synchronisation
        self.logger.info(f"Bloc annoncé par {message['sender_id']}")
    
    def _handle_tx_announce(self, message: Dict[str, Any]):
        """Gère les annonces de nouvelles transactions"""
        # À implémenter selon les besoins de synchronisation
        self.logger.info(f"Transaction annoncée par {message['sender_id']}")
    
    def _handle_archive_request(self, message: Dict[str, Any]):
        """Gère les demandes d'archives"""
        # À implémenter selon les besoins d'archivage
        self.logger.info(f"Demande d'archive de {message['sender_id']}")
    
    def _handle_archive_response(self, message: Dict[str, Any]):
        """Gère les réponses d'archives"""
        # À implémenter selon les besoins d'archivage
        self.logger.info(f"Réponse d'archive de {message['sender_id']}")
    
    def _handle_sync_request(self, message: Dict[str, Any]):
        """Gère les demandes de synchronisation"""
        # À implémenter selon les besoins de synchronisation
        self.logger.info(f"Demande de sync de {message['sender_id']}")
    
    def _handle_sync_response(self, message: Dict[str, Any]):
        """Gère les réponses de synchronisation"""
        # À implémenter selon les besoins de synchronisation
        self.logger.info(f"Réponse de sync de {message['sender_id']}")
    
    def _handle_ping(self, message: Dict[str, Any]):
        """Gère les messages ping"""
        # Répondre avec un pong
        pong_message = NetworkMessage(
            message_type=self.MSG_PONG,
            sender_id=self.node.node_id,
            receiver_id=message['sender_id'],
            payload={"timestamp": time.time()},
            timestamp=time.time()
        )
        asyncio.create_task(self.send_message_to_peer(message['sender_id'], pong_message))
    
    def _handle_pong(self, message: Dict[str, Any]):
        """Gère les messages pong"""
        # Mettre à jour le last_seen du peer
        sender_id = message['sender_id']
        if sender_id in self.peers:
            self.peers[sender_id].last_seen = time.time()
            # Calculer la latence
            ping_time = message.get('payload', {}).get('timestamp', 0)
            if ping_time:
                self.peers[sender_id].latency = time.time() - ping_time
    
    def get_network_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du réseau"""
        return {
            **self.stats,
            "connected_peers": len(self.peers),
            "active_connections": len(self.connections),
            "uptime": time.time() - self.stats["start_time"]
        }
    
    def get_peer_list(self) -> List[PeerInfo]:
        """Retourne la liste des peers connectés"""
        return list(self.peers.values())