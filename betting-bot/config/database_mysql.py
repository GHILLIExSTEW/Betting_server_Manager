# betting-bot/config/database_mysql.py
import os
from dotenv import load_dotenv

# Load .env file from the betting-bot directory
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
    print(f"Loaded environment variables from: {dotenv_path}")
else:
    print(f"WARNING: .env file not found at: {dotenv_path}")

# --- MySQL Configuration from Environment Variables ---
MYSQL_HOST = os.getenv('MYSQL_HOST')
MYSQL_PORT = int(os.getenv('MYSQL_PORT', '3306')) # Default MySQL port
MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_DB = os.getenv('MYSQL_DB')

# Optional: Pool size settings from environment variables
MYSQL_POOL_MIN_SIZE = int(os.getenv('MYSQL_POOL_MIN_SIZE', '1'))
MYSQL_POOL_MAX_SIZE = int(os.getenv('MYSQL_POOL_MAX_SIZE', '10'))

# Basic check for essential config
required_vars = {
    'MYSQL_HOST': MYSQL_HOST,
    'MYSQL_PORT': MYSQL_PORT,
    'MYSQL_USER': MYSQL_USER,
    'MYSQL_PASSWORD': MYSQL_PASSWORD,
    'MYSQL_DB': MYSQL_DB
}

missing_vars = [var for var, value in required_vars.items() if value is None]
if missing_vars:
    print(f"WARNING: Missing required MySQL environment variables: {', '.join(missing_vars)}")
    # Log the actual values (without password) for debugging
    debug_info = {k: v if k != 'MYSQL_PASSWORD' else '***' for k, v in required_vars.items()}
    print(f"Current configuration: {debug_info}")
