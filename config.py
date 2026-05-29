"""
Configuration module for One AI Tool.
Loads environment variables and provides application settings.
"""
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Load version from VERSION file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VERSION_FILE = os.path.join(BASE_DIR, 'VERSION')
try:
    with open(VERSION_FILE, 'r') as f:
        APP_VERSION = f.read().strip()
except FileNotFoundError:
    APP_VERSION = datetime.now().strftime('%Y%m%d%H%M%S')

class Config:
    """Base configuration class."""
    
    # App Version
    VERSION = APP_VERSION
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Supabase
    SUPABASE_URL = os.getenv('SUPABASE_URL', '')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')
    
    # Gemini API (for ASR AI evaluation)
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    
    # Reddit API (optional)
    REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID', '')
    REDDIT_CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET', '')
    REDDIT_USER_AGENT = os.getenv('REDDIT_USER_AGENT', 'OneAITool/1.0')
    
    # YouTube API (optional)
    YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY', '')
    
    # File paths
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    EXPORTS_DIR = os.path.join(BASE_DIR, 'exports')
    UPLOADS_DIR = os.path.join(BASE_DIR, 'uploads')
    LOGS_DIR = os.path.join(BASE_DIR, 'logs')
    
    # Ensure directories exist
    for directory in [EXPORTS_DIR, UPLOADS_DIR, LOGS_DIR]:
        os.makedirs(directory, exist_ok=True)
    
    # ASR Aligner settings
    ASR_BATCH_SIZE = 40
    ASR_OVERLAP_CONTEXT = 3
    ASR_RETRY_DELAY = 10
    ASR_MAX_RETRIES = 5
    ASR_BATCH_DELAY = 15
    
    # Available Gemini models
    AVAILABLE_MODELS = [
        "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-pro",
        "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"
    ]
    
    MODEL_RPM_LIMITS = {
        "gemini-2.5-flash": 15, "gemini-2.5-flash-lite": 15,
        "gemini-2.5-pro": 10, "gemini-2.0-flash": 15,
        "gemini-1.5-flash": 15, "gemini-1.5-pro": 10
    }
    
    @classmethod
    def is_supabase_configured(cls):
        """Check if Supabase credentials are configured."""
        return bool(cls.SUPABASE_URL and cls.SUPABASE_KEY and 
                    'your-' not in cls.SUPABASE_URL and 
                    'your-' not in cls.SUPABASE_KEY)
    
    @classmethod
    def is_gemini_configured(cls):
        """Check if Gemini API key is configured."""
        return bool(cls.GEMINI_API_KEY and 'your-' not in cls.GEMINI_API_KEY)
