import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
API_ENABLED = os.getenv('API_ENABLED', 'false').lower() == 'true'

# API Hosts
API_HOSTS = {
    'football': os.getenv('FOOTBALL_API_HOST'),
    'basketball': os.getenv('BASKETBALL_API_HOST'),
    'hockey': os.getenv('HOCKEY_API_HOST'),
    'baseball': os.getenv('BASEBALL_API_HOST'),
    'american-football': os.getenv('AMERICAN_FOOTBALL_API_HOST'),
    'rugby': os.getenv('RUGBY_API_HOST'),
    'handball': os.getenv('HANDBALL_API_HOST'),
    'volleyball': os.getenv('VOLLEYBALL_API_HOST'),
    'cricket': os.getenv('CRICKET_API_HOST'),
    'formula1': os.getenv('FORMULA1_API_HOST'),
    'mma': os.getenv('MMA_API_HOST'),
    'tennis': os.getenv('TENNIS_API_HOST'),
    'golf': os.getenv('GOLF_API_HOST'),
    'cycling': os.getenv('CYCLING_API_HOST'),
    'soccer': os.getenv('SOCCER_API_HOST')
}

# API Key
API_KEY = os.getenv('API_KEY')

# API Timeouts and Retries
API_TIMEOUT = int(os.getenv('API_TIMEOUT', '30'))
API_RETRY_ATTEMPTS = int(os.getenv('API_RETRY_ATTEMPTS', '3'))
API_RETRY_DELAY = int(os.getenv('API_RETRY_DELAY', '5')) 