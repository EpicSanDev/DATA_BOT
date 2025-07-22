from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class ContentType(Enum):
    WEB_PAGE = "web_page"
    DOCUMENT = "document"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    APPLICATION = "application"
    UNKNOWN = "unknown"

class ArchiveStatus(Enum):
    PENDING = "pending"
    DOWNLOADED = "downloaded"
    SCREENSHOT = "screenshot"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class WebResource:
    url: str
    title: Optional[str] = None
    content_type: ContentType = ContentType.UNKNOWN
    file_path: Optional[str] = None
    screenshot_path: Optional[str] = None
    content_length: Optional[int] = None
    status: ArchiveStatus = ArchiveStatus.PENDING
    discovered_at: datetime = None
    archived_at: Optional[datetime] = None
    parent_url: Optional[str] = None
    depth: int = 0
    tags: List[str] = None
    metadata: Dict[str, Any] = None
    error_message: Optional[str] = None

    def __post_init__(self):
        if self.discovered_at is None:
            self.discovered_at = datetime.now()
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}

@dataclass
class SearchQuery:
    query: str
    category: str
    priority: int = 1
    generated_by: str = "ollama"
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class ArchiveStats:
    total_discovered: int = 0
    total_downloaded: int = 0
    total_screenshots: int = 0
    total_failed: int = 0
    total_size_mb: float = 0.0
    domains_discovered: int = 0
    start_time: datetime = None
    last_update: datetime = None

    def __post_init__(self):
        if self.start_time is None:
            self.start_time = datetime.now()
        if self.last_update is None:
            self.last_update = datetime.now()
