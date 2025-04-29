# betting-bot/data/db_manager.py
import asyncpg # Use asyncpg
import logging
from typing import Optional, List, Dict, Any, Union
import os
# Import your database config
try:
    # Assumes config is a sibling directory to data/
    from ..config.database import DATABASE_URL, PG_POOL_MIN_SIZE, PG_POOL_MAX_SIZE
except ImportError:
     # Fallback if run differently or structure changes
     from config.database import DATABASE_URL, PG_POOL_MIN_SIZE, PG_POOL_MAX_SIZE


logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self._pool: Optional[asyncpg.Pool] = None
        logger.info("PostgreSQL DatabaseManager initialized.")
        if not DATABASE_URL:
             logger.critical("DATABASE_URL is not configured. DatabaseManager cannot connect.")


    async def connect(self) -> asyncpg.Pool:
        """Create or return existing PostgreSQL connection pool."""
        if self._pool is None:
            if not DATABASE_URL: # Check if config failed
                 raise ConnectionError("Cannot connect: DATABASE_URL is not configured.")

            logger.info("Attempting to create PostgreSQL connection pool...")
            try:
                self._pool = await asyncpg.create_pool(
                    dsn=DATABASE_URL,
                    min_size=PG_POOL_MIN_SIZE,
                    max_size=PG_POOL_MAX_SIZE,
                    command_timeout=60 # Example timeout
                )
                # --- Test the connection immediately ---
                async with self._pool.acquire() as test_conn:
                     await test_conn.execute("SELECT 1")
                # --- End Test ---
                logger.info("PostgreSQL connection pool created and tested successfully.")
                # initialize_db should be called explicitly after connect in setup_hook
            except (asyncpg.exceptions.InvalidPasswordError, asyncpg.exceptions.CannotConnectNowError, OSError, Exception) as e:
                logger.critical(f"FATAL: Failed to connect to PostgreSQL: {e}", exc_info=True) # Log full error
                self._pool = None
                raise ConnectionError(f"Failed to connect to PostgreSQL: {e}") from e # Raise specific error
        return self._pool

    async def close(self):
        """Close the PostgreSQL connection pool."""
        if self._pool is not None:
            logger.info("Closing PostgreSQL connection pool...")
            await self._pool.close()
            self._pool = None
            logger.info("PostgreSQL connection pool closed.")

    async def execute(self, query: str, *args) -> Optional[str]:
        """Execute a query that may or may not return results (like INSERT, UPDATE, DELETE).
           Returns the status command tag (e.g., 'INSERT 1') or None on error."""
        if not self._pool: # Check if pool exists
            logger.error("Cannot execute query: Database pool not available.")
            return None
        # Use acquire() for potentially shorter operations or simple scripts
        # Use transaction() for operations needing atomicity (all succeed or all fail)
        try:
             async with self._pool.acquire() as connection:
                # Parameters use $1, $2, ... syntax in asyncpg
                status = await connection.execute(query, *args)
                logger.debug(f"Executed query: {query[:100]}... Status: {status}")
                return status # e.g., "INSERT 0 1", "UPDATE 5"
        except Exception as e:
             logger.error(f"Error executing query: {query} with args: {args}. Error: {e}", exc_info=True)
             return None # Return None on failure

    async def fetch_one(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Execute a query and return a single row as a dictionary."""
        if not self._pool:
            logger.error("Cannot fetch_one: Database pool not available.")
            return None
        try:
             async with self._pool.acquire() as connection:
                # Parameters use $1, $2, ... syntax in asyncpg
                row: Optional[asyncpg.Record] = await connection.fetchrow(query, *args)
                # asyncpg.Record can be accessed like a dict
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error fetching one row: {query} with args: {args}. Error: {e}", exc_info=True)
            return None

    async def fetch_all(self, query: str, *args) -> List[Dict[str, Any]]:
        """Execute a query and return all rows as a list of dictionaries."""
        if not self._pool:
            logger.error("Cannot fetch_all: Database pool not available.")
            return []
        try:
             async with self._pool.acquire() as connection:
                # Parameters use $1, $2, ... syntax in asyncpg
                rows: List[asyncpg.Record] = await connection.fetch(query, *args)
                # Convert list of asyncpg.Record to list of dicts
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching all rows: {query} with args: {args}. Error: {e}", exc_info=True)
            return []

    async def fetchval(self, query: str, *args) -> Optional[Any]:
        """Execute a query and return a single value from the first row."""
        if not self._pool:
            logger.error("Cannot fetchval: Database pool not available.")
            return None
        try:
             async with self._pool.acquire() as connection:
                 # Parameters use $1, $2, ... syntax in asyncpg
                value = await connection.fetchval(query, *args)
                return value
        except Exception as e:
            logger.error(f"Error fetching value: {query} with args: {args}. Error: {e}", exc_info=True)
            return None

    async def initialize_db(self) -> None:
        """Initialize the database with PostgreSQL-compatible tables and indexes."""
        if not self._pool:
            logger.error("Cannot initialize DB: Database pool not available.")
            raise ConnectionError("Database pool not available for schema initialization.")

        logger.info("Attempting to initialize database schema...")
        # Use a transaction to ensure all tables/indexes are created atomically
        async with self._pool.acquire() as connection:
            # Check if tables exist before trying to create
            # Slightly more complex check for PostgreSQL
            async def table_exists(conn, table_name):
                exists = await conn.fetchval("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_schema = 'public' AND table_name = $1
                    );
                """, table_name)
                return exists

            try:
                 async with connection.transaction():
                    # --- Bets Table ---
                    if not await table_exists(connection, 'bets'):
                         await connection.execute('''
                             CREATE TABLE bets (
                                 bet_id BIGSERIAL PRIMARY KEY,
                                 guild_id BIGINT NOT NULL,
                                 user_id BIGINT NOT NULL,
                                 game_id BIGINT,
                                 bet_type TEXT NOT NULL,
                                 selection TEXT NOT NULL,
                                 units INTEGER NOT NULL,
                                 odds REAL NOT NULL,
                                 status TEXT NOT NULL,
                                 created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                                 updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                                 bet_won BOOLEAN DEFAULT FALSE,
                                 bet_loss BOOLEAN DEFAULT FALSE,
                                 result_value REAL,
                                 result_description TEXT, -- Added from update_bet_status
                                 expiration_time TIMESTAMPTZ,
                                 channel_id BIGINT
                             )
                         ''')
                         await connection.execute('CREATE INDEX idx_bets_guild_user ON bets (guild_id, user_id)')
                         await connection.execute('CREATE INDEX idx_bets_status ON bets (status)')
                         await connection.execute('CREATE INDEX idx_bets_created_at ON bets (created_at)')
                         await connection.execute('CREATE INDEX idx_bets_expiration ON bets (status, expiration_time)')
                         logger.info("Table 'bets' created.")

                    # --- Unit Records Table ---
                    if not await table_exists(connection, 'unit_records'):
                         await connection.execute('''
                             CREATE TABLE unit_records (
                                 record_id BIGSERIAL PRIMARY KEY,
                                 bet_id BIGINT NULL, -- REFERENCES bets(bet_id) ON DELETE SET NULL, -- Add FK later if needed
                                 guild_id BIGINT,
                                 user_id BIGINT,
                                 year INTEGER,
                                 month INTEGER,
                                 units INTEGER NOT NULL,
                                 odds REAL NOT NULL,
                                 result_value REAL NOT NULL,
                                 created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                             );
                         ''')
                         # Add FK constraint separately if needed, ensures bets table exists first
                         # await connection.execute('ALTER TABLE unit_records ADD CONSTRAINT fk_unit_records_bet FOREIGN KEY (bet_id) REFERENCES bets(bet_id) ON DELETE SET NULL;')
                         await connection.execute('CREATE INDEX idx_unit_records_guild_user_time ON unit_records (guild_id, user_id, year, month);')
                         await connection.execute('CREATE INDEX idx_unit_records_guild_time ON unit_records (guild_id, created_at);')
                         await connection.execute('CREATE INDEX idx_unit_records_bet_id ON unit_records (bet_id);')
                         logger.info("Table 'unit_records' created.")

                    # --- Guild Settings Table ---
                    if not await table_exists(connection, 'guild_settings'):
                         await connection.execute('''
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
                                 voice_channel_id BIGINT, -- Monthly
                                 yearly_channel_id BIGINT, -- Yearly
                                 total_units_channel_id BIGINT
                             )
                         ''')
                         await connection.execute('CREATE INDEX idx_guild_settings_active ON guild_settings (is_active);')
                         logger.info("Table 'guild_settings' created.")

                    # --- Guild Users Table ---
                    if not await table_exists(connection, 'guild_users'):
                         await connection.execute('''
                             CREATE TABLE guild_users (
                                 guild_id BIGINT,
                                 user_id BIGINT,
                                 units_balance REAL DEFAULT 0,
                                 lifetime_units REAL DEFAULT 0,
                                 PRIMARY KEY (guild_id, user_id)
                             )
                         ''')
                         await connection.execute('CREATE INDEX idx_guild_users_balance ON guild_users (guild_id, units_balance DESC);')
                         logger.info("Table 'guild_users' created.")

                    # --- Cappers Table ---
                    if not await table_exists(connection, 'cappers'):
                         await connection.execute('''
                              CREATE TABLE cappers (
                                  guild_id BIGINT NOT NULL,
                                  user_id BIGINT NOT NULL,
                                  display_name TEXT,
                                  banner_color TEXT,
                                  image_path TEXT,
                                  bet_won INTEGER DEFAULT 0,
                                  bet_loss INTEGER DEFAULT 0,
                                  updated_at TIMESTAMPTZ,
                                  PRIMARY KEY (guild_id, user_id)
                              )
                          ''')
                         logger.info("Table 'cappers' created.")

                    # --- Leagues Table ---
                    if not await table_exists(connection, 'leagues'):
                         await connection.execute('''
                             CREATE TABLE leagues (
                                 id BIGINT PRIMARY KEY,
                                 name TEXT,
                                 type TEXT,
                                 logo TEXT,
                                 country TEXT,
                                 country_code TEXT,
                                 country_flag TEXT,
                                 season INTEGER,
                                 sport TEXT NOT NULL
                             );
                         ''')
                         await connection.execute('CREATE INDEX idx_leagues_sport ON leagues (sport);')
                         logger.info("Table 'leagues' created.")

                    # --- Teams Table ---
                    if not await table_exists(connection, 'teams'):
                         await connection.execute('''
                              CREATE TABLE teams (
                                  id BIGINT PRIMARY KEY,
                                  name TEXT,
                                  code TEXT,
                                  country TEXT,
                                  founded INTEGER,
                                  national BOOLEAN,
                                  logo TEXT,
                                  venue_name TEXT,
                                  venue_address TEXT,
                                  venue_city TEXT,
                                  venue_capacity INTEGER,
                                  venue_surface TEXT,
                                  venue_image TEXT,
                                  sport TEXT NOT NULL
                              );
                          ''')
                         await connection.execute('CREATE INDEX idx_teams_sport ON teams (sport);')
                         await connection.execute('CREATE INDEX idx_teams_name ON teams (name);')
                         logger.info("Table 'teams' created.")

                    # --- Games Table ---
                    if not await table_exists(connection, 'games'):
                         await connection.execute('''
                             CREATE TABLE games (
                                 id BIGINT PRIMARY KEY,
                                 league_id BIGINT, -- REFERENCES leagues(id) ON DELETE CASCADE,
                                 home_team_id BIGINT, -- REFERENCES teams(id) ON DELETE SET NULL,
                                 away_team_id BIGINT, -- REFERENCES teams(id) ON DELETE SET NULL,
                                 home_team_name TEXT,
                                 away_team_name TEXT,
                                 home_team_logo TEXT,
                                 away_team_logo TEXT,
                                 start_time TIMESTAMPTZ,
                                 end_time TIMESTAMPTZ,
                                 status TEXT,
                                 score JSONB, -- Use JSONB for efficient JSON storage/querying
                                 venue TEXT,
                                 referee TEXT,
                                 sport TEXT,
                                 guild_id BIGINT, -- Added based on GameService logic
                                 updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                             );
                         ''')
                         # Add FKs separately if needed
                         await connection.execute('CREATE INDEX idx_games_league_start ON games (league_id, start_time);')
                         await connection.execute('CREATE INDEX idx_games_status_time ON games (status, start_time);')
                         await connection.execute('CREATE INDEX idx_games_start_time ON games (start_time);')
                         await connection.execute('CREATE INDEX idx_games_guild_status ON games (guild_id, status);')
                         logger.info("Table 'games' created.")

                    # --- Standings Table ---
                    if not await table_exists(connection, 'standings'):
                         await connection.execute('''
                             CREATE TABLE standings (
                                 league_id BIGINT, -- REFERENCES leagues(id) ON DELETE CASCADE,
                                 team_id BIGINT, -- REFERENCES teams(id) ON DELETE CASCADE,
                                 rank INTEGER,
                                 points INTEGER,
                                 goals_diff INTEGER,
                                 form TEXT,
                                 played INTEGER,
                                 won INTEGER,
                                 draw INTEGER,
                                 lost INTEGER,
                                 goals_for INTEGER,
                                 goals_against INTEGER,
                                 sport TEXT NOT NULL,
                                 PRIMARY KEY (league_id, team_id)
                             );
                         ''')
                         await connection.execute('CREATE INDEX idx_standings_sport ON standings (sport);')
                         logger.info("Table 'standings' created.")

                    # --- Game Events Table ---
                    if not await table_exists(connection, 'game_events'):
                         await connection.execute('''
                             CREATE TABLE game_events (
                                  event_id BIGSERIAL PRIMARY KEY,
                                  guild_id BIGINT NOT NULL,
                                  game_id BIGINT, -- REFERENCES games(id) ON DELETE CASCADE,
                                  event_type TEXT NOT NULL,
                                  details TEXT,
                                  created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                              )
                         ''')
                         await connection.execute('CREATE INDEX idx_game_events_game ON game_events (game_id, created_at DESC);')
                         logger.info("Table 'game_events' created.")

                    # --- Monthly Totals Table ---
                    if not await table_exists(connection, 'monthly_totals'):
                         await connection.execute('''
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
                    if not await table_exists(connection, 'yearly_totals'):
                         await connection.execute('''
                              CREATE TABLE yearly_totals (
                                  guild_id BIGINT NOT NULL,
                                  year INTEGER NOT NULL,
                                  total REAL DEFAULT 0,
                                  PRIMARY KEY (guild_id, year)
                              )
                         ''')
                         logger.info("Table 'yearly_totals' created.")

                    # --- Users Table ---
                    if not await table_exists(connection, 'users'):
                         await connection.execute('''
                              CREATE TABLE users (
                                  id BIGINT PRIMARY KEY, -- Assuming Discord User ID
                                  username TEXT NOT NULL,
                                  balance REAL DEFAULT 0,
                                  created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                              )
                          ''')
                         logger.info("Table 'users' created.")

                    # --- Transactions Table ---
                    if not await table_exists(connection, 'transactions'):
                         await connection.execute('''
                             CREATE TABLE transactions (
                                 transaction_id BIGSERIAL PRIMARY KEY,
                                 user_id BIGINT, -- REFERENCES users(id) ON DELETE CASCADE,
                                 type TEXT NOT NULL,
                                 amount REAL NOT NULL,
                                 created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                             )
                         ''')
                         await connection.execute('CREATE INDEX idx_transactions_user_time ON transactions (user_id, created_at);')
                         logger.info("Table 'transactions' created.")

                    logger.info("Database schema initialization check complete.")
            except Exception as e:
                 logger.error(f"Error during database schema initialization transaction: {e}", exc_info=True)
                 # Transaction will be rolled back automatically by asyncpg
                 raise # Re-raise to indicate failure
