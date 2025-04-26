import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Discord Configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
TEST_GUILD_ID = int(os.getenv('TEST_GUILD_ID', 0))

# Database Configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', ''),
    'db': os.getenv('DB_NAME', 'betting_bot')
}

# Redis Configuration
REDIS_CONFIG = {
    'host': os.getenv('CACHE_HOST', 'localhost'),
    'port': int(os.getenv('CACHE_PORT', 6379)),
    'db': int(os.getenv('REDIS_DB', 0)),
    'password': os.getenv('CACHE_PASSWORD', '')
}

# API Configuration
API_KEY = os.getenv('API_KEY')
API_BASE_URL = os.getenv('API_BASE_URL', 'https://api.example.com')
WEBSOCKET_API_KEY = os.getenv('WEBSOCKET_API_KEY')

# Security
FERNET_KEY = os.getenv('FERNET_KEY')

# File Paths
BASE_DIR = Path(__file__).parent.parent
STATIC_DIR = BASE_DIR / 'static'
LOGO_BASE_URL = os.getenv('LOGO_BASE_URL', 'https://example.com/logos')

# Default Images
DEFAULT_AVATAR_URL = os.getenv('DEFAULT_AVATAR_URL', 'https://example.com/default.png')
BOT_DEFAULT_IMAGE = os.getenv('BOT_DEFAULT_IMAGE', 'https://example.com/bot.png')
BOT_DEFAULT_THUMBNAIL = os.getenv('BOT_DEFAULT_THUMBNAIL', 'https://example.com/thumbnail.png')

# Supported Leagues
SUPPORTED_LEAGUES = [
    'nfl',
    'nba',
    'mlb',
    'nhl',
    'ncaaf',
    'ncaab',
    'pga',
    'ufc',
    'tennis',
    'esports'
]

# Rate Limiting
API_RATE_LIMIT = int(os.getenv('API_RATE_LIMIT', 100))  # requests per minute
DISCORD_RATE_LIMIT = int(os.getenv('DISCORD_RATE_LIMIT', 50))  # requests per minute

# Cache TTLs (in seconds)
GAME_CACHE_TTL = 300  # 5 minutes
LEAGUE_CACHE_TTL = int(os.getenv('LEAGUE_CACHE_TTL', 3600))  # 1 hour
TEAM_CACHE_TTL = int(os.getenv('TEAM_CACHE_TTL', 86400))  # 24 hours
USER_CACHE_TTL = 3600  # 1 hour
BET_CACHE_TTL = 1800  # 30 minutes

# Web Server Configuration
WEB_HOST = os.getenv('WEB_HOST', '0.0.0.0')
WEB_PORT = int(os.getenv('WEB_PORT', 25594))

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
LOG_FILE = os.getenv('LOG_FILE', 'bot.log')

# Betting Configuration
MIN_UNITS = 1.0
MAX_UNITS = 100.0
DEFAULT_UNITS = 10.0

# Voice Channel Configuration
VOICE_UPDATE_INTERVAL = int(os.getenv('VOICE_UPDATE_INTERVAL', 60))  # seconds
VOICE_CHANNEL_PREFIX = os.getenv('VOICE_CHANNEL_PREFIX', '💰')

# Subscription Configuration
SUBSCRIPTION_PRICES = {
    'monthly': float(os.getenv('SUBSCRIPTION_MONTHLY_PRICE', 9.99)),
    'yearly': float(os.getenv('SUBSCRIPTION_YEARLY_PRICE', 99.99))
}

# Feature Flags
ENABLE_VOICE_CHANNELS = os.getenv('ENABLE_VOICE_CHANNELS', 'true').lower() == 'true'
ENABLE_WEB_DASHBOARD = os.getenv('ENABLE_WEB_DASHBOARD', 'true').lower() == 'true'
ENABLE_IMAGE_GENERATION = os.getenv('ENABLE_IMAGE_GENERATION', 'true').lower() == 'true'

# Error messages
ERROR_MESSAGES = {
    'INSUFFICIENT_BALANCE': 'Insufficient balance to place bet',
    'INVALID_BET': 'Invalid bet amount or type',
    'API_ERROR': 'Error connecting to game data API',
    'DB_ERROR': 'Database error occurred',
    'CACHE_ERROR': 'Cache error occurred',
    'GENERAL_ERROR': 'An error occurred while processing your request'
} 