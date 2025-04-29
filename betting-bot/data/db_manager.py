# betting-bot/data/db_manager.py
import aiomysql
import logging
from typing import Optional, List, Dict, Any, Union
import os
# Import your database config
try:
    # Assumes config is a sibling directory to data/
    from ..config.database_mysql import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB, MYSQL_POOL_MIN_SIZE, MYSQL_POOL_MAX_SIZE
except ImportError:
    # Fallback if run differently or structure changes
    from config.database_mysql import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB, MYSQL_POOL_MIN_SIZE, MYSQL_POOL_MAX_SIZE

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self._pool: Optional[aiomysql.Pool] = None
        logger.info("MySQL DatabaseManager initialized.")
        if not all([MYSQL_HOST, MYSQL_USER, MYSQL_DB, MYSQL_PASSWORD is not None]):
            logger.critical("Missing one or more MySQL environment variables. DatabaseManager cannot connect.")

    async def connect(self) -> aiomysql.Pool:
        """Create or return existing MySQL connection pool."""
        if self._pool is None:
            if not all([MYSQL_HOST, MYSQL_USER, MYSQL_DB, MYSQL_PASSWORD is not None]):
                raise ConnectionError("Cannot connect: MySQL environment variables are not configured.")

            logger.info("Attempting to create MySQL connection pool...")
            try:
                self._pool = await aiomysql.create_pool(
                    host=MYSQL_HOST,
                    port=MYSQL_PORT,
                    user=MYSQL_USER,
                    password=MYSQL_PASSWORD,
                    db=MYSQL_DB,
                    minsize=MYSQL_POOL_MIN_SIZE,
                    maxsize=MYSQL_POOL_MAX_SIZE,
                    autocommit=True
                )
                # Test the connection immediately
                async with self._pool.acquire() as conn:
                    async with conn.cursor() as cursor:
                        await cursor.execute("SELECT 1")
                logger.info("MySQL connection pool created and tested successfully.")
            except Exception as e:
                logger.critical(f"FATAL: Failed to connect to MySQL: {e}", exc_info=True)
                self._pool = None
                raise ConnectionError(f"Failed to connect to MySQL: {e}") from e
        return self._pool

    async def close(self):
        """Close the MySQL connection pool."""
        if self._pool is not None:
            logger.info("Closing MySQL connection pool...")
            self._pool.close()
            await self._pool.wait_closed()
            self._pool = None
            logger.info("MySQL connection pool closed.")

    async def execute(self, query: str, *args) -> Optional[str]:
        """Execute a query that may or may not return results."""
        if not self._pool:
            logger.error("Cannot execute query: Database pool not available.")
            return None
        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(query, args)
                    await conn.commit()
                    return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error executing query: {query} with args: {args}. Error: {e}", exc_info=True)
            return None

    async def fetch_one(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Execute a query and return a single row as a dictionary."""
        if not self._pool:
            logger.error("Cannot fetch_one: Database pool not available.")
            return None
        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute(query, args)
                    return await cursor.fetchone()
        except Exception as e:
            logger.error(f"Error fetching one row: {query} with args: {args}. Error: {e}", exc_info=True)
            return None

    async def fetch_all(self, query: str, *args) -> List[Dict[str, Any]]:
        """Execute a query and return all rows as a list of dictionaries."""
        if not self._pool:
            logger.error("Cannot fetch_all: Database pool not available.")
            return []
        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute(query, args)
                    return await cursor.fetchall()
        except Exception as e:
            logger.error(f"Error fetching all rows: {query} with args: {args}. Error: {e}", exc_info=True)
            return []

    async def fetchval(self, query: str, *args) -> Optional[Any]:
        """Execute a query and return a single value from the first row."""
        if not self._pool:
            logger.error("Cannot fetchval: Database pool not available.")
            return None
        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(query, args)
                    row = await cursor.fetchone()
                    return row[0] if row else None
        except Exception as e:
            logger.error(f"Error fetching value: {query} with args: {args}. Error: {e}", exc_info=True)
            return None

    async def initialize_db(self) -> None:
        """Initialize the database with MySQL-compatible tables and indexes."""
        if not self._pool:
            logger.error("Cannot initialize DB: Database pool not available.")
            return

        logger.info("Attempting to initialize database schema...")
        # Use a transaction to ensure all tables/indexes are created atomically
        async with self._pool.acquire() as conn:
            # Check if tables exist before trying to create
            # Slightly more complex check for MySQL
            async def table_exists(conn, table_name):
                cursor = await conn.cursor()
                await cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
                result = await cursor.fetchone()
                return result is not None

            try:
                async with conn.begin():
                    # --- Bets Table ---
                    if not await table_exists(conn, 'bets'):
                        await conn.execute('''
                            CREATE TABLE bets (
                                bet_id BIGINT AUTO_INCREMENT PRIMARY KEY,
                                guild_id BIGINT NOT NULL,
                                user_id BIGINT NOT NULL,
                                game_id BIGINT,
                                bet_type TEXT NOT NULL,
                                selection TEXT NOT NULL,
                                units INTEGER NOT NULL,
                                odds REAL NOT NULL,
                                status TEXT NOT NULL,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                bet_won BOOLEAN DEFAULT FALSE,
                                bet_loss BOOLEAN DEFAULT FALSE,
                                result_value REAL,
                                result_description TEXT
                            )
                        ''')
            except Exception as e:
                logger.error(f"Error initializing database: {e}", exc_info=True)
                raise
