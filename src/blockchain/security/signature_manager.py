"""
Gestionnaire de Signatures ECDSA pour ArchiveChain

Ce module implémente un système complet de signatures ECDSA pour corriger
les vulnérabilités critiques de sécurité :
- Signatures cryptographiques manquantes dans block.py:53 et tokens.py:38
- Validation obligatoire des signatures pour toutes les transactions
- Gestion sécurisée des clés publiques/privées
"""

import hashlib
import json
import time
from typing import Dict, Any, Optional, Tuple, List
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature
from dataclasses import dataclass
import base64


@dataclass
class KeyPair:
    """Paire de clés ECDSA"""
    private_key: ec.EllipticCurvePrivateKey
    public_key: ec.EllipticCurvePublicKey
    address: str  # Adresse dérivée de la clé publique
    
    def get_public_key_pem(self) -> str:
        """Retourne la clé publique au format PEM"""
        pem = self.public_key.public_key_pem()
        return pem.decode('utf-8')
    
    def get_private_key_pem(self) -> str:
        """Retourne la clé privée au format PEM (à utiliser avec précaution)"""
        pem = self.private_key.private_key_pem(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        return pem.decode('utf-8')


class SignatureManager:
    """Gestionnaire de signatures ECDSA sécurisé"""
    
    def __init__(self):
        """Initialise le gestionnaire de signatures"""
        self._backend = default_backend()
        self._key_registry: Dict[str, ec.EllipticCurvePublicKey] = {}
        self._signature_cache: Dict[str, Dict[str, Any]] = {}
    
    def generate_key_pair(self) -> KeyPair:
        """
        Génère une nouvelle paire de clés ECDSA
        
        Returns:
            Nouvelle paire de clés avec adresse dérivée
        """
        # Utilise la courbe secp256k1 (utilisée par Bitcoin)
        private_key = ec.generate_private_key(ec.SECP256K1(), self._backend)
        public_key = private_key.public_key()
        
        # Dérive l'adresse de la clé publique
        address = self._derive_address_from_public_key(public_key)
        
        return KeyPair(private_key, public_key, address)
    
    def _derive_address_from_public_key(self, public_key: ec.EllipticCurvePublicKey) -> str:
        """
        Dérive une adresse à partir d'une clé publique
        
        Args:
            public_key: Clé publique ECDSA
            
        Returns:
            Adresse hexadécimale dérivée
        """
        # Sérialise la clé publique
        public_key_bytes = public_key.public_key_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint
        )
        
        # Hash SHA-256 puis RIPEMD-160 (style Bitcoin)
        sha256_hash = hashlib.sha256(public_key_bytes).digest()
        
        # Utilise SHA-256 à nouveau car RIPEMD-160 n'est pas toujours disponible
        address_hash = hashlib.sha256(sha256_hash).digest()
        
        # Prend les 20 premiers bytes et encode en hex avec préfixe
        return "arc" + address_hash[:20].hex()
    
    def register_public_key(self, address: str, public_key_pem: str) -> bool:
        """
        Enregistre une clé publique pour une adresse
        
        Args:
            address: Adresse de l'utilisateur
            public_key_pem: Clé publique au format PEM
            
        Returns:
            True si l'enregistrement a réussi
        """
        try:
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode('utf-8'),
                backend=self._backend
            )
            
            # Vérifie que l'adresse correspond à la clé publique
            derived_address = self._derive_address_from_public_key(public_key)
            if derived_address != address:
                return False
            
            self._key_registry[address] = public_key
            return True
            
        except Exception:
            return False
    
    def sign_transaction(self, transaction_data: Dict[str, Any], 
                        private_key: ec.EllipticCurvePrivateKey) -> str:
        """
        Signe une transaction avec une clé privée ECDSA
        
        Corrige la vulnérabilité critique : block.py:53 et tokens.py:38
        Implémente un système complet de signatures ECDSA
        
        Args:
            transaction_data: Données de la transaction
            private_key: Clé privée pour la signature
            
        Returns:
            Signature encodée en base64
        """
        # Normalise les données de transaction
        normalized_data = self._normalize_transaction_data(transaction_data)
        
        # Crée le hash des données
        message_hash = hashlib.sha256(normalized_data.encode('utf-8')).digest()
        
        # Signe avec ECDSA
        signature = private_key.sign(message_hash, ec.ECDSA(hashes.SHA256()))
        
        # Encode en base64 pour le stockage
        signature_b64 = base64.b64encode(signature).decode('utf-8')
        
        # Cache la signature pour éviter les re-calculs
        tx_id = transaction_data.get('tx_id', '')
        if tx_id:
            self._signature_cache[tx_id] = {
                'signature': signature_b64,
                'timestamp': time.time(),
                'data_hash': hashlib.sha256(normalized_data.encode()).hexdigest()
            }
        
        return signature_b64
    
    def verify_transaction_signature(self, transaction_data: Dict[str, Any], 
                                   signature: str, sender_address: str) -> bool:
        """
        Vérifie la signature d'une transaction
        
        Args:
            transaction_data: Données de la transaction
            signature: Signature à vérifier
            sender_address: Adresse de l'expéditeur
            
        Returns:
            True si la signature est valide
        """
        # Vérifie que la clé publique est enregistrée
        if sender_address not in self._key_registry:
            return False
        
        public_key = self._key_registry[sender_address]
        
        try:
            # Normalise les données de transaction
            normalized_data = self._normalize_transaction_data(transaction_data)
            message_hash = hashlib.sha256(normalized_data.encode('utf-8')).digest()
            
            # Décode la signature
            signature_bytes = base64.b64decode(signature.encode('utf-8'))
            
            # Vérifie la signature ECDSA
            public_key.verify(signature_bytes, message_hash, ec.ECDSA(hashes.SHA256()))
            
            return True
            
        except (InvalidSignature, Exception):
            return False
    
    def _normalize_transaction_data(self, transaction_data: Dict[str, Any]) -> str:
        """
        Normalise les données de transaction pour un hachage déterministe
        
        Args:
            transaction_data: Données de la transaction
            
        Returns:
            Chaîne JSON normalisée
        """
        # Crée une copie sans la signature
        data_copy = transaction_data.copy()
        data_copy.pop('signature', None)
        
        # Trie les clés pour un ordre déterministe
        return json.dumps(data_copy, sort_keys=True, separators=(',', ':'))
    
    def sign_block(self, block_data: Dict[str, Any], 
                   validator_private_key: ec.EllipticCurvePrivateKey) -> str:
        """
        Signe un bloc avec la clé privée d'un validateur
        
        Args:
            block_data: Données du bloc
            validator_private_key: Clé privée du validateur
            
        Returns:
            Signature du bloc encodée en base64
        """
        # Normalise les données du bloc
        normalized_data = json.dumps(block_data, sort_keys=True, separators=(',', ':'))
        
        # Hash des données
        block_hash = hashlib.sha256(normalized_data.encode('utf-8')).digest()
        
        # Signe le hash
        signature = validator_private_key.sign(block_hash, ec.ECDSA(hashes.SHA256()))
        
        return base64.b64encode(signature).decode('utf-8')
    
    def verify_block_signature(self, block_data: Dict[str, Any], 
                              signature: str, validator_address: str) -> bool:
        """
        Vérifie la signature d'un bloc
        
        Args:
            block_data: Données du bloc
            signature: Signature à vérifier
            validator_address: Adresse du validateur
            
        Returns:
            True si la signature est valide
        """
        if validator_address not in self._key_registry:
            return False
        
        public_key = self._key_registry[validator_address]
        
        try:
            # Normalise les données
            normalized_data = json.dumps(block_data, sort_keys=True, separators=(',', ':'))
            block_hash = hashlib.sha256(normalized_data.encode('utf-8')).digest()
            
            # Décode et vérifie la signature
            signature_bytes = base64.b64decode(signature.encode('utf-8'))
            public_key.verify(signature_bytes, block_hash, ec.ECDSA(hashes.SHA256()))
            
            return True
            
        except (InvalidSignature, Exception):
            return False
    
    def create_multi_signature(self, transaction_data: Dict[str, Any], 
                              private_keys: List[ec.EllipticCurvePrivateKey]) -> List[str]:
        """
        Crée des signatures multiples pour une transaction
        
        Args:
            transaction_data: Données de la transaction
            private_keys: Liste des clés privées
            
        Returns:
            Liste des signatures
        """
        signatures = []
        for private_key in private_keys:
            signature = self.sign_transaction(transaction_data, private_key)
            signatures.append(signature)
        
        return signatures
    
    def verify_multi_signature(self, transaction_data: Dict[str, Any], 
                              signatures: List[str], addresses: List[str],
                              required_signatures: int) -> bool:
        """
        Vérifie des signatures multiples
        
        Args:
            transaction_data: Données de la transaction
            signatures: Liste des signatures
            addresses: Liste des adresses correspondantes
            required_signatures: Nombre minimum de signatures requises
            
        Returns:
            True si suffisamment de signatures sont valides
        """
        if len(signatures) != len(addresses):
            return False
        
        valid_signatures = 0
        
        for signature, address in zip(signatures, addresses):
            if self.verify_transaction_signature(transaction_data, signature, address):
                valid_signatures += 1
        
        return valid_signatures >= required_signatures
    
    def get_signature_info(self, tx_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère les informations de signature pour une transaction
        
        Args:
            tx_id: ID de la transaction
            
        Returns:
            Informations de signature ou None
        """
        return self._signature_cache.get(tx_id)
    
    def cleanup_signature_cache(self, max_age: int = 86400):
        """
        Nettoie le cache des signatures anciennes
        
        Args:
            max_age: Âge maximal en secondes (défaut: 24h)
        """
        current_time = time.time()
        expired_keys = []
        
        for tx_id, info in self._signature_cache.items():
            if current_time - info['timestamp'] > max_age:
                expired_keys.append(tx_id)
        
        for key in expired_keys:
            del self._signature_cache[key]
    
    def get_registered_addresses(self) -> List[str]:
        """
        Retourne la liste des adresses enregistrées
        
        Returns:
            Liste des adresses avec clés publiques enregistrées
        """
        return list(self._key_registry.keys())
    
    def export_public_key(self, address: str) -> Optional[str]:
        """
        Exporte la clé publique d'une adresse
        
        Args:
            address: Adresse de l'utilisateur
            
        Returns:
            Clé publique au format PEM ou None
        """
        if address not in self._key_registry:
            return None
        
        public_key = self._key_registry[address]
        pem = public_key.public_key_pem()
        return pem.decode('utf-8')
    
    def get_signature_stats(self) -> Dict[str, Any]:
        """
        Retourne les statistiques du gestionnaire de signatures
        
        Returns:
            Dictionnaire avec les statistiques
        """
        return {
            "registered_keys": len(self._key_registry),
            "cached_signatures": len(self._signature_cache),
            "curve_used": "secp256k1",
            "hash_algorithm": "SHA-256"
        }


# Instance globale du gestionnaire de signatures
signature_manager = SignatureManager()