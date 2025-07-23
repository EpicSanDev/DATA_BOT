"""
Validateurs robustes pour ArchiveChain

Ce module fournit des validateurs complets et sécurisés pour tous les types
de données dans le système blockchain, avec sanitisation automatique.

SÉCURITÉ: Tous les validateurs incluent une protection contre les injections
et la sanitisation automatique des données d'entrée.
"""

import re
import json
import hashlib
import time
from typing import Dict, Any, List, Optional, Union, Tuple
from urllib.parse import urlparse, urlunparse
from datetime import datetime
from decimal import Decimal, InvalidOperation
import ipaddress

from .exceptions import ValidationError
from .error_handler import RobustnessLogger


class URLValidator:
    """Validateur robuste pour les URLs avec sanitisation"""
    
    # Patterns de sécurité
    ALLOWED_SCHEMES = {'http', 'https', 'ftp', 'ftps'}
    BLOCKED_DOMAINS = {
        'localhost', '127.0.0.1', '0.0.0.0', '::1',
        'metadata.google.internal',  # Google Cloud metadata
        '169.254.169.254',           # AWS metadata
        'kubernetes.default.svc',     # Kubernetes internal
    }
    
    DANGEROUS_PATTERNS = [
        r'javascript:',
        r'data:',
        r'vbscript:',
        r'file:',
        r'jar:',
        r'@',  # Potentiel bypass d'auth
        r'\.\.',  # Directory traversal
        r'%2e%2e',  # Encoded directory traversal
        r'%252e',   # Double-encoded
    ]
    
    def __init__(self):
        self.logger = RobustnessLogger("url_validator")
    
    def validate_and_sanitize(self, url: str, context: str = "general") -> str:
        """
        Valide et sanitise une URL de manière sécurisée
        
        Args:
            url: URL à valider
            context: Contexte de validation (archive, metadata, etc.)
            
        Returns:
            URL sanitisée et validée
            
        Raises:
            ValidationError: Si l'URL est invalide ou dangereuse
        """
        
        if not url or not isinstance(url, str):
            raise ValidationError(
                "URL must be a non-empty string",
                field_name="url",
                expected_format="valid_url_string",
                actual_value=str(url)[:100]
            )
        
        # Nettoyer l'URL
        cleaned_url = self._clean_url(url)
        
        # Valider la longueur
        if len(cleaned_url) > 2048:  # RFC limite raisonnable
            raise ValidationError(
                "URL too long (max 2048 characters)",
                field_name="url",
                expected_format="url_length_<=_2048",
                actual_value=f"length_{len(cleaned_url)}"
            )
        
        # Parser l'URL
        try:
            parsed = urlparse(cleaned_url)
        except Exception as e:
            raise ValidationError(
                f"Invalid URL format: {str(e)}",
                field_name="url",
                expected_format="valid_url_format"
            )
        
        # Valider le schéma
        if parsed.scheme.lower() not in self.ALLOWED_SCHEMES:
            raise ValidationError(
                f"URL scheme '{parsed.scheme}' not allowed",
                field_name="url_scheme",
                expected_format=f"one_of_{list(self.ALLOWED_SCHEMES)}",
                actual_value=parsed.scheme
            )
        
        # Valider le hostname
        self._validate_hostname(parsed.hostname or '', context)
        
        # Vérifier les patterns dangereux
        self._check_dangerous_patterns(cleaned_url)
        
        # Valider spécifiquement selon le contexte
        self._validate_context_specific(parsed, context)
        
        # Construire l'URL finale sanitisée
        sanitized_url = urlunparse(parsed)
        
        self.logger.debug(
            f"URL validated and sanitized",
            context={
                "original_url": url[:100],
                "sanitized_url": sanitized_url[:100],
                "context": context,
                "scheme": parsed.scheme,
                "hostname": parsed.hostname
            }
        )
        
        return sanitized_url
    
    def _clean_url(self, url: str) -> str:
        """Nettoie l'URL des caractères dangereux"""
        # Supprimer les espaces
        url = url.strip()
        
        # Supprimer les caractères de contrôle
        url = ''.join(char for char in url if ord(char) >= 32)
        
        # Normaliser les encodages
        url = url.replace('%20', ' ').replace(' ', '%20')
        
        return url
    
    def _validate_hostname(self, hostname: str, context: str):
        """Valide le hostname de manière sécurisée"""
        if not hostname:
            raise ValidationError(
                "URL must have a valid hostname",
                field_name="hostname",
                expected_format="valid_hostname"
            )
        
        hostname_lower = hostname.lower()
        
        # Vérifier les domaines bloqués
        if hostname_lower in self.BLOCKED_DOMAINS:
            raise ValidationError(
                f"Hostname '{hostname}' is blocked for security reasons",
                field_name="hostname",
                expected_format="allowed_hostname",
                actual_value=hostname
            )
        
        # Vérifier les adresses IP privées
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_multicast:
                raise ValidationError(
                    f"Private/internal IP address not allowed: {hostname}",
                    field_name="hostname",
                    expected_format="public_ip_or_domain",
                    actual_value=hostname
                )
        except ValueError:
            # Pas une IP, c'est un domaine - continuer
            pass
        
        # Valider le format du domaine
        domain_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
        if not re.match(domain_pattern, hostname):
            raise ValidationError(
                f"Invalid domain format: {hostname}",
                field_name="hostname",
                expected_format="valid_domain_name",
                actual_value=hostname
            )
    
    def _check_dangerous_patterns(self, url: str):
        """Vérifie les patterns dangereux dans l'URL"""
        url_lower = url.lower()
        
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, url_lower):
                raise ValidationError(
                    f"URL contains dangerous pattern: {pattern}",
                    field_name="url",
                    expected_format="safe_url_pattern",
                    actual_value="***BLOCKED_PATTERN***"
                )
    
    def _validate_context_specific(self, parsed, context: str):
        """Validation spécifique au contexte"""
        if context == "archive":
            # Pour les archives, vérifier les extensions suspectes
            path = parsed.path.lower()
            suspicious_extensions = ['.exe', '.bat', '.cmd', '.scr', '.com']
            
            if any(path.endswith(ext) for ext in suspicious_extensions):
                raise ValidationError(
                    f"Suspicious file extension in archive URL",
                    field_name="url_path",
                    expected_format="safe_file_extension",
                    actual_value=parsed.path
                )


class MetadataValidator:
    """Validateur pour les métadonnées d'archives"""
    
    def __init__(self):
        self.logger = RobustnessLogger("metadata_validator")
        self.url_validator = URLValidator()
    
    def validate_archive_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valide et sanitise les métadonnées d'archive
        
        Args:
            metadata: Métadonnées à valider
            
        Returns:
            Métadonnées validées et sanitisées
        """
        
        if not isinstance(metadata, dict):
            raise ValidationError(
                "Metadata must be a dictionary",
                field_name="metadata",
                expected_format="dictionary",
                actual_value=type(metadata).__name__
            )
        
        validated = {}
        
        # Valider chaque champ
        validated['screenshots'] = self._validate_screenshots(
            metadata.get('screenshots', [])
        )
        
        validated['external_resources'] = self._validate_external_resources(
            metadata.get('external_resources', [])
        )
        
        validated['linked_pages'] = self._validate_linked_pages(
            metadata.get('linked_pages', [])
        )
        
        validated['tags'] = self._validate_tags(
            metadata.get('tags', [])
        )
        
        validated['category'] = self._validate_category(
            metadata.get('category', 'general')
        )
        
        validated['priority'] = self._validate_priority(
            metadata.get('priority', 5)
        )
        
        validated['language'] = self._validate_language(
            metadata.get('language')
        )
        
        validated['title'] = self._validate_title(
            metadata.get('title')
        )
        
        validated['description'] = self._validate_description(
            metadata.get('description')
        )
        
        self.logger.debug(
            "Metadata validated successfully",
            context={
                "original_fields": len(metadata),
                "validated_fields": len(validated),
                "category": validated['category'],
                "priority": validated['priority']
            }
        )
        
        return validated
    
    def _validate_screenshots(self, screenshots: List[str]) -> List[str]:
        """Valide les hashes de screenshots"""
        if not isinstance(screenshots, list):
            raise ValidationError(
                "Screenshots must be a list",
                field_name="screenshots",
                expected_format="list_of_hashes"
            )
        
        validated = []
        for i, screenshot in enumerate(screenshots):
            if not isinstance(screenshot, str):
                continue
            
            # Valider le format de hash
            if re.match(r'^[a-fA-F0-9]{64}$', screenshot):
                validated.append(screenshot.lower())
            else:
                self.logger.warning(
                    f"Invalid screenshot hash format at index {i}",
                    context={"hash": screenshot[:16]}
                )
        
        return validated[:10]  # Limiter à 10 screenshots max
    
    def _validate_external_resources(self, resources: List[str]) -> List[str]:
        """Valide les ressources externes"""
        if not isinstance(resources, list):
            return []
        
        validated = []
        for resource in resources:
            if isinstance(resource, str) and len(resource) <= 1000:
                # Soit un hash, soit une URL
                if re.match(r'^[a-fA-F0-9]{32,64}$', resource):
                    validated.append(resource.lower())
                else:
                    try:
                        clean_url = self.url_validator.validate_and_sanitize(
                            resource, "external_resource"
                        )
                        validated.append(clean_url)
                    except ValidationError:
                        continue  # Ignorer les URLs invalides
        
        return validated[:50]  # Limiter à 50 ressources max
    
    def _validate_linked_pages(self, linked_pages: List[str]) -> List[str]:
        """Valide les pages liées (archive IDs)"""
        if not isinstance(linked_pages, list):
            return []
        
        validated = []
        for page_id in linked_pages:
            if isinstance(page_id, str) and re.match(r'^[a-fA-F0-9]{64}$', page_id):
                validated.append(page_id.lower())
        
        return validated[:20]  # Limiter à 20 liens max
    
    def _validate_tags(self, tags: List[str]) -> List[str]:
        """Valide les tags"""
        if not isinstance(tags, list):
            return []
        
        validated = []
        tag_pattern = re.compile(r'^[a-zA-Z0-9_\-]{1,50}$')
        
        for tag in tags:
            if isinstance(tag, str):
                # Nettoyer le tag
                clean_tag = re.sub(r'[^\w\-]', '', tag.strip().lower())
                
                if tag_pattern.match(clean_tag) and clean_tag not in validated:
                    validated.append(clean_tag)
        
        return validated[:20]  # Limiter à 20 tags max
    
    def _validate_category(self, category: str) -> str:
        """Valide la catégorie"""
        allowed_categories = {
            'general', 'news', 'education', 'entertainment', 'technology',
            'science', 'health', 'finance', 'government', 'legal',
            'social', 'art', 'history', 'reference', 'other'
        }
        
        if not isinstance(category, str):
            return 'general'
        
        clean_category = category.strip().lower()
        return clean_category if clean_category in allowed_categories else 'general'
    
    def _validate_priority(self, priority: Union[int, str]) -> int:
        """Valide la priorité (1-10)"""
        try:
            priority_int = int(priority)
            return max(1, min(10, priority_int))
        except (ValueError, TypeError):
            return 5  # Priorité par défaut
    
    def _validate_language(self, language: Optional[str]) -> Optional[str]:
        """Valide le code de langue (ISO 639-1)"""
        if not language or not isinstance(language, str):
            return None
        
        # Pattern simple pour les codes de langue ISO 639-1
        lang_pattern = re.compile(r'^[a-z]{2}(-[A-Z]{2})?$')
        clean_lang = language.strip()
        
        return clean_lang if lang_pattern.match(clean_lang) else None
    
    def _validate_title(self, title: Optional[str]) -> Optional[str]:
        """Valide le titre"""
        if not title or not isinstance(title, str):
            return None
        
        # Nettoyer et limiter la taille
        clean_title = title.strip()[:200]
        
        # Supprimer les caractères de contrôle
        clean_title = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', clean_title)
        
        return clean_title if clean_title else None
    
    def _validate_description(self, description: Optional[str]) -> Optional[str]:
        """Valide la description"""
        if not description or not isinstance(description, str):
            return None
        
        # Nettoyer et limiter la taille
        clean_desc = description.strip()[:1000]
        
        # Supprimer les caractères de contrôle
        clean_desc = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', clean_desc)
        
        return clean_desc if clean_desc else None


class DataValidator:
    """Validateur général pour tous les types de données"""
    
    def __init__(self):
        self.logger = RobustnessLogger("data_validator")
        self.url_validator = URLValidator()
        self.metadata_validator = MetadataValidator()
    
    def validate_transaction_data(self, tx_data: Dict[str, Any]) -> Dict[str, Any]:
        """Valide les données de transaction"""
        required_fields = ['tx_id', 'tx_type', 'sender', 'timestamp']
        
        for field in required_fields:
            if field not in tx_data:
                raise ValidationError(
                    f"Missing required field: {field}",
                    field_name=field,
                    expected_format="required_field"
                )
        
        validated = {}
        
        # Valider l'ID de transaction
        validated['tx_id'] = self._validate_tx_id(tx_data['tx_id'])
        
        # Valider le type de transaction
        validated['tx_type'] = self._validate_tx_type(tx_data['tx_type'])
        
        # Valider l'adresse expéditeur
        validated['sender'] = self._validate_address(tx_data['sender'])
        
        # Valider le timestamp
        validated['timestamp'] = self._validate_timestamp(tx_data['timestamp'])
        
        # Champs optionnels
        if 'receiver' in tx_data:
            validated['receiver'] = self._validate_address(tx_data['receiver'])
        
        if 'amount' in tx_data:
            validated['amount'] = self._validate_amount(tx_data['amount'])
        
        if 'fee' in tx_data:
            validated['fee'] = self._validate_amount(tx_data['fee'])
        
        return validated
    
    def _validate_tx_id(self, tx_id: str) -> str:
        """Valide l'ID de transaction"""
        if not isinstance(tx_id, str):
            raise ValidationError(
                "Transaction ID must be a string",
                field_name="tx_id",
                expected_format="string"
            )
        
        # Doit être un hash hexadécimal
        if not re.match(r'^[a-fA-F0-9]{16,64}$', tx_id):
            raise ValidationError(
                "Invalid transaction ID format",
                field_name="tx_id",
                expected_format="hex_string_16_to_64_chars",
                actual_value=tx_id[:20]
            )
        
        return tx_id.lower()
    
    def _validate_tx_type(self, tx_type: str) -> str:
        """Valide le type de transaction"""
        allowed_types = {
            'genesis', 'archive', 'verify', 'reward', 'transfer',
            'mint', 'burn', 'stake', 'unstake', 'fee'
        }
        
        if not isinstance(tx_type, str):
            raise ValidationError(
                "Transaction type must be a string",
                field_name="tx_type",
                expected_format="string"
            )
        
        clean_type = tx_type.strip().lower()
        
        if clean_type not in allowed_types:
            raise ValidationError(
                f"Invalid transaction type: {tx_type}",
                field_name="tx_type",
                expected_format=f"one_of_{list(allowed_types)}",
                actual_value=clean_type
            )
        
        return clean_type
    
    def _validate_address(self, address: str) -> str:
        """Valide une adresse blockchain"""
        if not isinstance(address, str):
            raise ValidationError(
                "Address must be a string",
                field_name="address",
                expected_format="string"
            )
        
        clean_address = address.strip()
        
        # Adresses spéciales
        special_addresses = {
            '0x0', 'genesis', 'burn_pool', 'mining_pool', 
            'stake_pool', 'archive_pool', 'archiving_rewards_pool'
        }
        
        if clean_address in special_addresses:
            return clean_address
        
        # Format adresse normale (hex ou nom)
        if re.match(r'^0x[a-fA-F0-9]{40}$', clean_address):
            return clean_address.lower()
        elif re.match(r'^[a-zA-Z0-9_]{3,50}$', clean_address):
            return clean_address
        else:
            raise ValidationError(
                f"Invalid address format: {address}",
                field_name="address",
                expected_format="0x_hex_40_chars_or_alphanumeric_3_to_50",
                actual_value=clean_address[:20]
            )
    
    def _validate_timestamp(self, timestamp: Union[float, int, str]) -> float:
        """Valide un timestamp"""
        try:
            ts = float(timestamp)
        except (ValueError, TypeError):
            raise ValidationError(
                "Timestamp must be a number",
                field_name="timestamp",
                expected_format="float_or_int",
                actual_value=str(timestamp)[:20]
            )
        
        # Vérifier que c'est raisonnable (entre 2020 et 2050)
        min_ts = 1577836800  # 2020-01-01
        max_ts = 2524608000  # 2050-01-01
        
        if ts < min_ts or ts > max_ts:
            raise ValidationError(
                f"Timestamp out of reasonable range: {ts}",
                field_name="timestamp",
                expected_format=f"between_{min_ts}_and_{max_ts}",
                actual_value=str(ts)
            )
        
        return ts
    
    def _validate_amount(self, amount: Union[int, float, str, Decimal]) -> int:
        """Valide un montant (converti en entier)"""
        try:
            if isinstance(amount, Decimal):
                amount_int = int(amount)
            else:
                amount_int = int(float(amount))
        except (ValueError, TypeError, InvalidOperation):
            raise ValidationError(
                "Amount must be a valid number",
                field_name="amount",
                expected_format="number",
                actual_value=str(amount)[:20]
            )
        
        if amount_int < 0:
            raise ValidationError(
                "Amount cannot be negative",
                field_name="amount",
                expected_format="non_negative_integer",
                actual_value=str(amount_int)
            )
        
        # Limite raisonnable pour éviter les overflow
        max_amount = 10**18  # 1 trillion de base units
        if amount_int > max_amount:
            raise ValidationError(
                f"Amount too large: {amount_int}",
                field_name="amount",
                expected_format=f"max_{max_amount}",
                actual_value=str(amount_int)
            )
        
        return amount_int
    
    def validate_archive_data(self, archive_data: Dict[str, Any]) -> Dict[str, Any]:
        """Valide les données d'archive complètes"""
        required_fields = [
            'archive_id', 'original_url', 'capture_timestamp',
            'content_type', 'size_compressed', 'size_original', 'checksum'
        ]
        
        for field in required_fields:
            if field not in archive_data:
                raise ValidationError(
                    f"Missing required field: {field}",
                    field_name=field,
                    expected_format="required_field"
                )
        
        validated = {}
        
        # Valider l'URL originale
        validated['original_url'] = self.url_validator.validate_and_sanitize(
            archive_data['original_url'], "archive"
        )
        
        # Valider les métadonnées si présentes
        if 'metadata' in archive_data:
            validated['metadata'] = self.metadata_validator.validate_archive_metadata(
                archive_data['metadata']
            )
        
        # Autres validations...
        validated['archive_id'] = self._validate_tx_id(archive_data['archive_id'])
        validated['content_type'] = self._validate_content_type(archive_data['content_type'])
        validated['size_compressed'] = self._validate_size(archive_data['size_compressed'])
        validated['size_original'] = self._validate_size(archive_data['size_original'])
        validated['checksum'] = self._validate_checksum(archive_data['checksum'])
        
        return validated
    
    def _validate_content_type(self, content_type: str) -> str:
        """Valide le type de contenu MIME"""
        if not isinstance(content_type, str):
            raise ValidationError(
                "Content type must be a string",
                field_name="content_type"
            )
        
        # Pattern MIME basique
        mime_pattern = r'^[a-zA-Z0-9][a-zA-Z0-9!#$&\-\^_]*\/[a-zA-Z0-9][a-zA-Z0-9!#$&\-\^_]*$'
        clean_type = content_type.strip().lower()
        
        if not re.match(mime_pattern, clean_type):
            raise ValidationError(
                f"Invalid MIME type format: {content_type}",
                field_name="content_type",
                expected_format="valid_mime_type",
                actual_value=clean_type
            )
        
        return clean_type
    
    def _validate_size(self, size: Union[int, str]) -> int:
        """Valide une taille de fichier"""
        try:
            size_int = int(size)
        except (ValueError, TypeError):
            raise ValidationError(
                "Size must be an integer",
                field_name="size",
                expected_format="integer"
            )
        
        if size_int < 0:
            raise ValidationError(
                "Size cannot be negative",
                field_name="size",
                expected_format="non_negative_integer"
            )
        
        # Limite raisonnable (10GB)
        max_size = 10 * 1024 * 1024 * 1024
        if size_int > max_size:
            raise ValidationError(
                f"Size too large: {size_int}",
                field_name="size",
                expected_format=f"max_{max_size}",
                actual_value=str(size_int)
            )
        
        return size_int
    
    def _validate_checksum(self, checksum: str) -> str:
        """Valide un checksum"""
        if not isinstance(checksum, str):
            raise ValidationError(
                "Checksum must be a string",
                field_name="checksum"
            )
        
        # SHA256 ou SHA3-256
        if not re.match(r'^[a-fA-F0-9]{64}$', checksum):
            raise ValidationError(
                "Invalid checksum format (must be 64-char hex)",
                field_name="checksum",
                expected_format="64_char_hex_string",
                actual_value=checksum[:20]
            )
        
        return checksum.lower()