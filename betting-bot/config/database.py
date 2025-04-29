# betting-bot/config/database.py
import os
from dotenv import load_dotenv

# Ensure dotenv() is called somewhere before this is imported,
# usually in the main entry point (main.py).
# Or call it here if this module might be imported before main.py loads it.
# load_dotenv() # Consider placement carefully

# --- PostgreSQL Configuration (for AWS RDS or other hosted PG) ---
PG_USER = os.getenv('PG_USER') # Get user from .env
PG_PASSWORD = os.getenv('PG_PASSWORD') # Get password from .env
PG_HOST = os.getenv('PG_HOST') # Get RDS endpoint/server address from .env
PG_PORT = os.getenv('PG_PORT', '5432') # Default PostgreSQL port
PG_DATABASE = os.getenv('PG_DATABASE') # Get database name from .env

# Construct the DSN (Data Source Name) for asyncpg
# Add error checking to ensure variables are loaded
if not all([PG_USER, PG_PASSWORD, PG_HOST, PG_DATABASE]):
    # Log this error prominently if possible, or raise early
    print("FATAL ERROR: Missing one or more PostgreSQL environment variables (PG_USER, PG_PASSWORD, PG_HOST, PG_DATABASE) in .env")
    # raise ValueError("Missing PostgreSQL environment variables") # Option to halt execution
    DATABASE_URL = None # Set to None to indicate configuration failure
else:
    DATABASE_URL = f"postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DATABASE}"

# Optional: Pool size settings from environment variables
PG_POOL_MIN_SIZE = int(os.getenv('PG_POOL_MIN_SIZE', '1'))
PG_POOL_MAX_SIZE = int(os.getenv('PG_POOL_MAX_SIZE', '10'))
