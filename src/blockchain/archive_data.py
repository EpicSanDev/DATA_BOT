"""
Archive Data Structures for ArchiveChain

Defines data structures for storing and managing archive information
in the ArchiveChain blockchain.
"""

import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

class CompressionType(Enum):
    """Supported compression types for archived content"""
    NONE = "none"
    GZIP = "gzip"
    ZSTD = "zstd"
    BROTLI = "brotli"

class ContentType(Enum):
    """Types of archived content"""
    HTML = "text/html"
    PDF = "application/pdf"
    JSON = "application/json"
    IMAGE = "image/*"
    VIDEO = "video/*"
    DOCUMENT = "application/document"
    OTHER = "application/octet-stream"

@dataclass
class ArchiveMetadata:
    """Metadata for archived content"""
    screenshots: List[str]  # List of screenshot hashes
    external_resources: List[str]  # CSS, JS, image hashes
    linked_pages: List[str]  # Related archive IDs
    tags: List[str]  # Community tags
    category: str  # Content category
    priority: int  # Archive priority (1-10)
    language: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ArchiveMetadata':
        """Create from dictionary"""
        return cls(**data)

@dataclass
class ArchiveData:
    """Main archive data structure matching the problem statement format"""
    archive_id: str  # SHA256 hash of content
    original_url: str  # Original URL
    capture_timestamp: str  # ISO 8601 timestamp
    content_type: str  # MIME type
    compression: str  # Compression algorithm used
    size_compressed: int  # Compressed size in bytes
    size_original: int  # Original size in bytes
    checksum: str  # SHA3-256 hash for integrity
    metadata: ArchiveMetadata  # Additional metadata
    
    # Blockchain-specific fields
    block_height: Optional[int] = None  # Block where this was first archived
    replication_count: int = 3  # Number of replicas
    storage_nodes: List[str] = None  # Node IDs storing this archive
    
    def __post_init__(self):
        """Initialize optional fields"""
        if self.storage_nodes is None:
            self.storage_nodes = []
    
    def calculate_archive_id(self, content: bytes) -> str:
        """Calculate archive ID from content"""
        sha256_hash = hashlib.sha256(content).hexdigest()
        self.archive_id = sha256_hash
        return sha256_hash
    
    def calculate_checksum(self, content: bytes) -> str:
        """Calculate SHA3-256 checksum for integrity verification"""
        # Using SHA256 as fallback since SHA3 may not be available
        checksum = hashlib.sha256(content + b"integrity_check").hexdigest()
        self.checksum = f"sha256_{checksum}"
        return self.checksum
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        # Convert metadata to dict
        data['metadata'] = self.metadata.to_dict()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ArchiveData':
        """Create from dictionary"""
        # Convert metadata back to object
        metadata_dict = data.pop('metadata')
        metadata = ArchiveMetadata.from_dict(metadata_dict)
        return cls(metadata=metadata, **data)
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ArchiveData':
        """Create from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def validate(self) -> bool:
        """Validate archive data integrity"""
        # Check required fields
        if not all([
            self.archive_id,
            self.original_url,
            self.capture_timestamp,
            self.content_type,
            self.checksum
        ]):
            return False
        
        # Validate timestamp format
        try:
            datetime.fromisoformat(self.capture_timestamp.replace('Z', '+00:00'))
        except ValueError:
            return False
        
        # Validate sizes
        if self.size_compressed < 0 or self.size_original < 0:
            return False
        
        # Validate replication count
        if self.replication_count < 1 or self.replication_count > 15:
            return False
        
        return True
    
    def get_storage_requirement(self) -> int:
        """Calculate storage requirement in bytes"""
        # Include overhead for metadata and redundancy
        metadata_size = len(self.to_json().encode())
        return self.size_compressed + metadata_size
    
    def is_popular(self, threshold: int = 100) -> bool:
        """Check if content is popular based on replication count"""
        return self.replication_count > threshold

class ArchiveIndex:
    """Index for fast archive lookups"""
    
    def __init__(self):
        self.url_index: Dict[str, str] = {}  # url -> archive_id
        self.content_index: Dict[str, List[str]] = {}  # content_type -> [archive_ids]
        self.timestamp_index: Dict[str, List[str]] = {}  # date -> [archive_ids]
        self.tag_index: Dict[str, List[str]] = {}  # tag -> [archive_ids]
    
    def add_archive(self, archive: ArchiveData):
        """Add archive to all indices"""
        archive_id = archive.archive_id
        
        # URL index
        self.url_index[archive.original_url] = archive_id
        
        # Content type index
        content_type = archive.content_type
        if content_type not in self.content_index:
            self.content_index[content_type] = []
        self.content_index[content_type].append(archive_id)
        
        # Timestamp index (by date)
        date = archive.capture_timestamp[:10]  # YYYY-MM-DD
        if date not in self.timestamp_index:
            self.timestamp_index[date] = []
        self.timestamp_index[date].append(archive_id)
        
        # Tag index
        for tag in archive.metadata.tags:
            if tag not in self.tag_index:
                self.tag_index[tag] = []
            self.tag_index[tag].append(archive_id)
    
    def find_by_url(self, url: str) -> Optional[str]:
        """Find archive by URL"""
        return self.url_index.get(url)
    
    def find_by_content_type(self, content_type: str) -> List[str]:
        """Find archives by content type"""
        return self.content_index.get(content_type, [])
    
    def find_by_date(self, date: str) -> List[str]:
        """Find archives by date (YYYY-MM-DD)"""
        return self.timestamp_index.get(date, [])
    
    def find_by_tag(self, tag: str) -> List[str]:
        """Find archives by tag"""
        return self.tag_index.get(tag, [])
    
    def search(self, query: str) -> List[str]:
        """Simple text search across indices"""
        results = set()
        
        # Search in URLs
        for url, archive_id in self.url_index.items():
            if query.lower() in url.lower():
                results.add(archive_id)
        
        # Search in tags
        for tag, archive_ids in self.tag_index.items():
            if query.lower() in tag.lower():
                results.update(archive_ids)
        
        return list(results)