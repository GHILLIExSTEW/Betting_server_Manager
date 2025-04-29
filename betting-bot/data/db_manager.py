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
                # Initialize database schema
                await self.initialize_db()
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
        async with self._pool.acquire() as conn:
            # Check if tables exist before trying to create
            async def table_exists(conn, table_name):
                cursor = await conn.cursor()
                await cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
                result = await cursor.fetchone()
                return result is not None

            try:
                # Start transaction
                await conn.begin()
                
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
                    await conn.execute('CREATE INDEX idx_bets_guild_user ON bets (guild_id, user_id)')
                    await conn.execute('CREATE INDEX idx_bets_status ON bets (status)')
                    await conn.execute('CREATE INDEX idx_bets_created_at ON bets (created_at)')
                    logger.info("Table 'bets' created.")

                # --- Guild Settings Table ---
                if not await table_exists(conn, 'guild_settings'):
                    await conn.execute('''
                        CREATE TABLE guild_settings (
                            guild_id BIGINT PRIMARY KEY,
                            is_active BOOLEAN DEFAULT TRUE,
                            subscription_level INTEGER DEFAULT 0,
                            is_paid BOOLEAN DEFAULT FALSE,
                            embed_channel_1 BIGINT,
                            command_channel_1 BIGINT,
                            admin_channel_1 BIGINT,
                            admin_role BIGINT,
                            authorized_role BIGINT,
                            voice_channel_id BIGINT,
                            yearly_channel_id BIGINT,
                            total_units_channel_id BIGINT
                        )
                    ''')
                    await conn.execute('CREATE INDEX idx_guild_settings_active ON guild_settings (is_active)')
                    logger.info("Table 'guild_settings' created.")

                # --- Guild Users Table ---
                if not await table_exists(conn, 'guild_users'):
                    await conn.execute('''
                        CREATE TABLE guild_users (
                            guild_id BIGINT,
                            user_id BIGINT,
                            units_balance REAL DEFAULT 0,
                            lifetime_units REAL DEFAULT 0,
                            PRIMARY KEY (guild_id, user_id)
                        )
                    ''')
                    await conn.execute('CREATE INDEX idx_guild_users_balance ON guild_users (guild_id, units_balance DESC)')
                    logger.info("Table 'guild_users' created.")

                # --- Unit Records Table ---
                if not await table_exists(conn, 'unit_records'):
                    await conn.execute('''
                        CREATE TABLE unit_records (
                            record_id BIGINT AUTO_INCREMENT PRIMARY KEY,
                            bet_id BIGINT NULL,
                            guild_id BIGINT,
                            user_id BIGINT,
                            year INTEGER,
                            month INTEGER,
                            units INTEGER NOT NULL,
                            odds REAL NOT NULL,
                            result_value REAL NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')
                    await conn.execute('CREATE INDEX idx_unit_records_guild_user_time ON unit_records (guild_id, user_id, year, month)')
                    await conn.execute('CREATE INDEX idx_unit_records_guild_time ON unit_records (guild_id, created_at)')
                    await conn.execute('CREATE INDEX idx_unit_records_bet_id ON unit_records (bet_id)')
                    logger.info("Table 'unit_records' created.")

                # --- Monthly Totals Table ---
                if not await table_exists(conn, 'monthly_totals'):
                    await conn.execute('''
                        CREATE TABLE monthly_totals (
                            guild_id BIGINT NOT NULL,
                            year INTEGER NOT NULL,
                            month INTEGER NOT NULL,
                            total REAL DEFAULT 0,
                            PRIMARY KEY (guild_id, year, month)
                        )
                    ''')
                    logger.info("Table 'monthly_totals' created.")

                # --- Yearly Totals Table ---
                if not await table_exists(conn, 'yearly_totals'):
                    await conn.execute('''
                        CREATE TABLE yearly_totals (
                            guild_id BIGINT NOT NULL,
                            year INTEGER NOT NULL,
                            total REAL DEFAULT 0,
                            PRIMARY KEY (guild_id, year)
                        )
                    ''')
                    logger.info("Table 'yearly_totals' created.")

                # Commit transaction
                await conn.commit()
                logger.info("Database schema initialization complete.")
            except Exception as e:
                # Rollback transaction on error
                await conn.rollback()
                logger.error(f"Error initializing database: {e}", exc_info=True)
                raise
