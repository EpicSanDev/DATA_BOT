"""
Gestionnaire Cryptographique Sécurisé pour ArchiveChain

Ce module corrige les vulnérabilités critiques de sécurité cryptographique :
- Génération sécurisée de nombres aléatoires
- Gestion des sels cryptographiques
- Fonctions de hachage sécurisées
- Validation cryptographique
"""

import secrets
import hashlib
import hmac
from typing import Optional, Dict, Any, Tuple
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64
import time


class SecureCryptoManager:
    """Gestionnaire cryptographique sécurisé utilisant les meilleures pratiques"""
    
    # Constantes de sécurité
    SALT_LENGTH = 32  # 256 bits
    CHALLENGE_LENGTH = 32  # 256 bits  
    PBKDF2_ITERATIONS = 100000  # Recommandation OWASP 2023
    
    def __init__(self):
        """Initialise le gestionnaire cryptographique"""
        self._backend = default_backend()
        self._salt_cache: Dict[str, bytes] = {}
        self._challenge_cache: Dict[str, Dict[str, Any]] = {}
    
    def generate_secure_salt(self, identifier: Optional[str] = None) -> bytes:
        """
        Génère un sel cryptographiquement sûr
        
        Args:
            identifier: Identifiant optionnel pour la mise en cache
            
        Returns:
            Sel de 32 bytes cryptographiquement sûr
        """
        salt = secrets.token_bytes(self.SALT_LENGTH)
        
        if identifier:
            self._salt_cache[identifier] = salt
            
        return salt
    
    def get_or_create_salt(self, identifier: str) -> bytes:
        """
        Récupère un sel existant ou en crée un nouveau
        
        Args:
            identifier: Identifiant unique pour le sel
            
        Returns:
            Sel associé à l'identifiant
        """
        if identifier not in self._salt_cache:
            self._salt_cache[identifier] = self.generate_secure_salt()
        
        return self._salt_cache[identifier]
    
    def generate_secure_challenge(self, node_id: str, archive_id: str) -> str:
        """
        Génère un challenge cryptographiquement sûr pour le consensus PoA
        
        Corrige la vulnérabilité critique : consensus.py:113-114
        Remplace random.random() par secrets.randbits()
        
        Args:
            node_id: ID du nœud
            archive_id: ID de l'archive
            
        Returns:
            Challenge hexadécimal sécurisé
        """
        # Utilise secrets pour la génération cryptographiquement sûre
        timestamp = str(time.time())
        random_bytes = secrets.token_bytes(self.CHALLENGE_LENGTH)
        
        # Combine les données de manière déterministe
        combined_data = f"{node_id}{archive_id}{timestamp}".encode() + random_bytes
        
        # Génère le challenge avec SHA-256
        challenge = hashlib.sha256(combined_data).hexdigest()[:self.CHALLENGE_LENGTH]
        
        # Stocke le challenge avec métadonnées
        challenge_key = f"{node_id}_{archive_id}"
        self._challenge_cache[challenge_key] = {
            "challenge": challenge,
            "timestamp": time.time(),
            "node_id": node_id,
            "archive_id": archive_id,
            "random_component": random_bytes.hex()
        }
        
        return challenge
    
    def verify_challenge_response(self, node_id: str, archive_id: str, 
                                 response: str, expected_checksum: str) -> bool:
        """
        Vérifie la réponse à un challenge de stockage
        
        Args:
            node_id: ID du nœud
            archive_id: ID de l'archive
            response: Réponse du nœud
            expected_checksum: Checksum attendu
            
        Returns:
            True si la réponse est valide
        """
        challenge_key = f"{node_id}_{archive_id}"
        
        if challenge_key not in self._challenge_cache:
            return False
        
        challenge_data = self._challenge_cache[challenge_key]
        challenge = challenge_data["challenge"]
        
        # Vérifie l'expiration (1 heure max)
        if time.time() - challenge_data["timestamp"] > 3600:
            del self._challenge_cache[challenge_key]
            return False
        
        # Calcule la réponse attendue
        expected_response = self.secure_hash_with_salt(
            f"{expected_checksum}{challenge}".encode(),
            challenge_data["random_component"].encode()
        )
        
        # Compare de manière sécurisée
        is_valid = hmac.compare_digest(response, expected_response)
        
        if is_valid:
            # Nettoie le challenge utilisé
            del self._challenge_cache[challenge_key]
            
        return is_valid
    
    def secure_hash_with_salt(self, data: bytes, salt: bytes) -> str:
        """
        Génère un hash sécurisé avec sel
        
        Corrige la vulnérabilité critique : archive_data.py:86
        Remplace le sel hardcodé par un sel dynamique sécurisé
        
        Args:
            data: Données à hasher
            salt: Sel cryptographique
            
        Returns:
            Hash hexadécimal avec préfixe d'algorithme
        """
        # Utilise PBKDF2 pour le renforcement cryptographique
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.PBKDF2_ITERATIONS,
            backend=self._backend
        )
        
        key = kdf.derive(data)
        return f"pbkdf2_sha256_{key.hex()}"
    
    def calculate_secure_checksum(self, content: bytes, salt_id: str) -> str:
        """
        Calcule un checksum sécurisé pour l'intégrité des archives
        
        Args:
            content: Contenu à vérifier
            salt_id: Identifiant pour le sel
            
        Returns:
            Checksum sécurisé avec préfixe
        """
        salt = self.get_or_create_salt(salt_id)
        return self.secure_hash_with_salt(content, salt)
    
    def generate_secure_random_int(self, min_val: int, max_val: int) -> int:
        """
        Génère un entier aléatoire cryptographiquement sûr
        
        Args:
            min_val: Valeur minimale
            max_val: Valeur maximale
            
        Returns:
            Entier aléatoire sécurisé
        """
        return secrets.randbelow(max_val - min_val + 1) + min_val
    
    def generate_secure_random_float(self) -> float:
        """
        Génère un float aléatoire cryptographiquement sûr entre 0 et 1
        
        Returns:
            Float aléatoire sécurisé
        """
        # Génère 32 bits aléatoires et normalise
        random_bits = secrets.randbits(32)
        return random_bits / (2**32 - 1)
    
    def constant_time_compare(self, a: str, b: str) -> bool:
        """
        Compare deux chaînes en temps constant pour éviter les timing attacks
        
        Args:
            a: Première chaîne
            b: Deuxième chaîne
            
        Returns:
            True si les chaînes sont identiques
        """
        return hmac.compare_digest(a.encode(), b.encode())
    
    def secure_token_generation(self, length: int = 32) -> str:
        """
        Génère un token sécurisé pour les identifiants
        
        Args:
            length: Longueur du token en bytes
            
        Returns:
            Token hexadécimal sécurisé
        """
        return secrets.token_hex(length)
    
    def derive_key_from_password(self, password: str, salt: bytes) -> bytes:
        """
        Dérive une clé à partir d'un mot de passe avec PBKDF2
        
        Args:
            password: Mot de passe
            salt: Sel cryptographique
            
        Returns:
            Clé dérivée de 32 bytes
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.PBKDF2_ITERATIONS,
            backend=self._backend
        )
        
        return kdf.derive(password.encode('utf-8'))
    
    def cleanup_expired_challenges(self, max_age: int = 3600):
        """
        Nettoie les challenges expirés pour éviter l'accumulation mémoire
        
        Args:
            max_age: Âge maximal en secondes
        """
        current_time = time.time()
        expired_keys = []
        
        for key, data in self._challenge_cache.items():
            if current_time - data["timestamp"] > max_age:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._challenge_cache[key]
    
    def get_crypto_stats(self) -> Dict[str, Any]:
        """
        Retourne les statistiques du gestionnaire cryptographique
        
        Returns:
            Dictionnaire avec les statistiques
        """
        return {
            "cached_salts": len(self._salt_cache),
            "active_challenges": len(self._challenge_cache),
            "pbkdf2_iterations": self.PBKDF2_ITERATIONS,
            "salt_length_bits": self.SALT_LENGTH * 8,
            "challenge_length_bits": self.CHALLENGE_LENGTH * 8
        }


# Instance globale du gestionnaire cryptographique
crypto_manager = SecureCryptoManager()