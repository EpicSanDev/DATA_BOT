import os
import logging
from typing import Optional
# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv is optional
    pass

class Config:
    # Ollama settings
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama2")
    
    # Base settings
    MAX_DEPTH = int(os.getenv("MAX_DEPTH", "3"))
    MAX_PAGES_PER_DOMAIN = int(os.getenv("MAX_PAGES_PER_DOMAIN", "50"))
    CONCURRENT_DOWNLOADS = int(os.getenv("CONCURRENT_DOWNLOADS", "5"))
    SCREENSHOT_TIMEOUT = int(os.getenv("SCREENSHOT_TIMEOUT", "30"))
    DOWNLOAD_TIMEOUT = int(os.getenv("DOWNLOAD_TIMEOUT", "60"))
    
    # Paths
    ARCHIVE_PATH = os.getenv("ARCHIVE_PATH", "./archive")
    SCREENSHOTS_PATH = os.getenv("SCREENSHOTS_PATH", "./screenshots")
    LOGS_PATH = os.getenv("LOGS_PATH", "./logs")
    DATABASE_PATH = os.getenv("DATABASE_PATH", "./data/archive.db")
    
    # User agent
    USER_AGENT = os.getenv("USER_AGENT", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
    
    # Chrome options
    HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
    WINDOW_SIZE = os.getenv("WINDOW_SIZE", "1920,1080")
    
    # Classification
    MIN_CONTENT_LENGTH = int(os.getenv("MIN_CONTENT_LENGTH", "100"))
    SUPPORTED_FORMATS = os.getenv("SUPPORTED_FORMATS", "html,pdf,doc,docx,txt,md,json,xml").split(",")
    
    # Rate limiting
    DELAY_BETWEEN_REQUESTS = float(os.getenv("DELAY_BETWEEN_REQUESTS", "1"))
    RESPECT_ROBOTS_TXT = os.getenv("RESPECT_ROBOTS_TXT", "true").lower() == "true"
    
    # ArchiveChain Blockchain settings
    BLOCKCHAIN_ENABLED = os.getenv("BLOCKCHAIN_ENABLED", "true").lower() == "true"
    BLOCKCHAIN_DATA_PATH = os.getenv("BLOCKCHAIN_DATA_PATH", "./data/blockchain.json")
    BLOCKCHAIN_NODE_TYPE = os.getenv("BLOCKCHAIN_NODE_TYPE", "full_archive")
    BLOCKCHAIN_LISTEN_PORT = int(os.getenv("BLOCKCHAIN_LISTEN_PORT", "8334"))
    BLOCKCHAIN_MINING_ENABLED = os.getenv("BLOCKCHAIN_MINING_ENABLED", "true").lower() == "true"
    
    # Node configuration
    NODE_STORAGE_CAPACITY = int(os.getenv("NODE_STORAGE_CAPACITY", str(100 * 1024 * 1024 * 1024)))  # 100GB
    NODE_GEOGRAPHIC_REGION = os.getenv("NODE_GEOGRAPHIC_REGION", "us-east-1")
    NODE_CONTENT_SPECIALIZATIONS = os.getenv("NODE_CONTENT_SPECIALIZATIONS", "text/html,application/pdf").split(",")
    
    # Consensus settings
    POA_STORAGE_WEIGHT = float(os.getenv("POA_STORAGE_WEIGHT", "0.5"))
    POA_BANDWIDTH_WEIGHT = float(os.getenv("POA_BANDWIDTH_WEIGHT", "0.3"))
    POA_LONGEVITY_WEIGHT = float(os.getenv("POA_LONGEVITY_WEIGHT", "0.2"))
    
    # Token settings
    ARC_GENESIS_ADDRESS = os.getenv("ARC_GENESIS_ADDRESS", "genesis_wallet")
    ARC_MINING_REWARD = float(os.getenv("ARC_MINING_REWARD", "50.0"))
    
    # Smart contract settings
    BOUNTY_DEFAULT_DURATION = int(os.getenv("BOUNTY_DEFAULT_DURATION", str(7 * 24 * 3600)))  # 7 days
    PRESERVATION_POOL_MIN_FUNDING = float(os.getenv("PRESERVATION_POOL_MIN_FUNDING", "1000.0"))
    
    @classmethod
    def setup_directories(cls):
        """Créer les répertoires nécessaires"""
        directories = [
            cls.ARCHIVE_PATH,
            cls.SCREENSHOTS_PATH,
            cls.LOGS_PATH,
            os.path.dirname(cls.DATABASE_PATH),
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    @classmethod
    def setup_logging(cls, level: str = "INFO") -> None:
        """Configuration du logging"""
        cls.setup_directories()
        
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        logging.basicConfig(
            level=getattr(logging, level.upper()),
            format=log_format,
            handlers=[
                logging.FileHandler(os.path.join(cls.LOGS_PATH, "archive_bot.log")),
                logging.StreamHandler()
            ]
        )
