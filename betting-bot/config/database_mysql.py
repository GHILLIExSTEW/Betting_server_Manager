# betting-bot/config/database_mysql.py
import os
from dotenv import load_dotenv

# Load .env file from the parent directory relative to this config file
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

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
if not all([MYSQL_USER, MYSQL_HOST, MYSQL_DB, MYSQL_PASSWORD is not None]): # Check password exists even if empty
     # You might want to raise an error or log a critical warning here
     print("WARNING: Missing one or more required MySQL environment variables (MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB)")
     # raise ValueError("Missing required MySQL environment variables")
