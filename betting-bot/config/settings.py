# Betting Configuration
MIN_UNITS = 1
MAX_UNITS = 3
DEFAULT_UNITS = 1

# Database Configuration
DB_PATH = 'data/betting.db'
CACHE_DIR = 'data/cache'

# Logging Configuration
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_FILE = 'logs/betting_bot.log'

# API Configuration
API_KEY = ''  # Set this in environment variables
API_TIMEOUT = 30  # seconds
API_RETRY_ATTEMPTS = 3
API_RETRY_DELAY = 5  # seconds

# Cache Configuration
CACHE_TTL = 3600  # 1 hour in seconds
CACHE_MAX_SIZE = 1000  # Maximum number of items in cache
GAME_CACHE_TTL = 300  # 5 minutes in seconds
LEAGUE_CACHE_TTL = 86400  # 24 hours in seconds
TEAM_CACHE_TTL = 86400  # 24 hours in seconds
USER_CACHE_TTL = 86400 # 24 hours in seconds

# Betting Rules
MIN_ODDS = -1000
MAX_ODDS = 1000
ALLOWED_BET_TYPES = ['moneyline', 'spread', 'total']
ALLOWED_LEAGUES = ['NBA', 'NFL', 'MLB', 'NHL', 'MLS', 'Other']

# Voice Channel Configuration
VOICE_CHANNEL_CHECK_INTERVAL = 300  # 5 minutes in seconds
VOICE_CHANNEL_GRACE_PERIOD = 3600  # 1 hour in seconds

# Analytics Configuration
ANALYTICS_UPDATE_INTERVAL = 3600  # 1 hour in seconds
ANALYTICS_RETENTION_DAYS = 30  # Number of days to keep analytics data 
