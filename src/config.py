import os
import logging
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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
