# betting-bot/data/db_manager.py
import aiomysql # Keep aiomysql for MySQL
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

    async def connect(self) -> Optional[aiomysql.Pool]: # Return Optional Pool
        """Create or return existing MySQL connection pool."""
        if self._pool is None:
            if not all([MYSQL_HOST, MYSQL_USER, MYSQL_DB, MYSQL_PASSWORD is not None]):
                # Log critical error and prevent further operation without connection
                logger.critical("Cannot connect: MySQL environment variables are not configured.")
                # Optionally raise an error or handle appropriately depending on desired bot behavior
                # raise ConnectionError("Cannot connect: MySQL environment variables are not configured.")
                return None # Indicate connection failure

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
                    autocommit=True, # Keep autocommit True for simplicity unless transactions needed often
                    connect_timeout=10 # Add a connection timeout
                )
                # Test the connection immediately
                async with self._pool.acquire() as conn:
                    async with conn.cursor() as cursor:
                        await cursor.execute("SELECT 1")
                logger.info("MySQL connection pool created and tested successfully.")
                # Initialize database schema AFTER successful pool creation
                await self.initialize_db()
            except aiomysql.OperationalError as op_err:
                 logger.critical(f"FATAL: OperationalError connecting to MySQL (check host, port, credentials, db existence): {op_err}", exc_info=True)
                 self._pool = None
                 raise ConnectionError(f"Failed to connect to MySQL (OperationalError): {op_err}") from op_err
            except Exception as e:
                logger.critical(f"FATAL: Failed to connect to MySQL: {e}", exc_info=True)
                self._pool = None
                # Re-raise a more specific or generic connection error
                raise ConnectionError(f"Failed to connect to MySQL: {e}") from e
        return self._pool

    async def close(self):
        """Close the MySQL connection pool."""
        if self._pool is not None:
            logger.info("Closing MySQL connection pool...")
            try:
                 self._pool.close()
                 await self._pool.wait_closed()
                 self._pool = None
                 logger.info("MySQL connection pool closed.")
            except Exception as e:
                 logger.error(f"Error closing MySQL pool: {e}")

    async def execute(self, query: str, *args) -> Optional[int]: # Return Optional[int] for lastrowid or rowcount
        """Execute a query (INSERT, UPDATE, DELETE). Returns lastrowid for INSERT or rowcount."""
        if not self._pool:
            await self.connect() # Attempt to reconnect if pool is lost
            if not self._pool: # Check again after attempting reconnect
                logger.error("Cannot execute query: Database pool not available.")
                raise ConnectionError("Database pool not available for execute.") # Raise error

        logger.debug(f"Executing DB Query: {query} Args: {args}")
        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    rowcount = await cursor.execute(query, args)
                    # For INSERT with AUTO_INCREMENT, lastrowid is useful
                    # For UPDATE/DELETE, rowcount is useful
                    if query.strip().upper().startswith("INSERT"):
                        return cursor.lastrowid
                    else:
                        return rowcount # Return number of affected rows for UPDATE/DELETE
        except Exception as e:
            logger.error(f"Error executing query: {query} with args: {args}. Error: {e}", exc_info=True)
            # Consider raising a custom DatabaseError here instead of returning None
            # raise DatabaseError(f"Failed to execute query: {e}") from e
            return None # Keep returning None for now based on original structure

    async def fetch_one(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Execute a query and return a single row as a dictionary."""
        if not self._pool:
             await self.connect()
             if not self._pool:
                logger.error("Cannot fetch_one: Database pool not available.")
                raise ConnectionError("Database pool not available for fetch_one.")

        logger.debug(f"Fetching One DB Query: {query} Args: {args}")
        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute(query, args)
                    return await cursor.fetchone()
        except Exception as e:
            logger.error(f"Error fetching one row: {query} with args: {args}. Error: {e}", exc_info=True)
            # raise DatabaseError(f"Failed to fetch one row: {e}") from e
            return None

    async def fetch_all(self, query: str, *args) -> List[Dict[str, Any]]:
        """Execute a query and return all rows as a list of dictionaries."""
        if not self._pool:
             await self.connect()
             if not self._pool:
                logger.error("Cannot fetch_all: Database pool not available.")
                raise ConnectionError("Database pool not available for fetch_all.")

        logger.debug(f"Fetching All DB Query: {query} Args: {args}")
        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute(query, args)
                    return await cursor.fetchall()
        except Exception as e:
            logger.error(f"Error fetching all rows: {query} with args: {args}. Error: {e}", exc_info=True)
            # raise DatabaseError(f"Failed to fetch all rows: {e}") from e
            return []

    async def fetchval(self, query: str, *args) -> Optional[Any]:
        """Execute a query and return a single value from the first row."""
        if not self._pool:
             await self.connect()
             if not self._pool:
                logger.error("Cannot fetchval: Database pool not available.")
                raise ConnectionError("Database pool not available for fetchval.")

        logger.debug(f"Fetching Value DB Query: {query} Args: {args}")
        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(query, args)
                    row = await cursor.fetchone()
                    return row[0] if row else None
        except Exception as e:
            logger.error(f"Error fetching value: {query} with args: {args}. Error: {e}", exc_info=True)
            # raise DatabaseError(f"Failed to fetch value: {e}") from e
            return None

    async def initialize_db(self) -> None:
        """Initialize the database with MySQL-compatible tables and indexes."""
        if not self._pool:
            logger.error("Cannot initialize DB: Database pool not available.")
            return

        logger.info("Attempting to initialize/verify database schema...")
        async with self._pool.acquire() as conn:
            # Check if tables exist before trying to create
            async def table_exists(conn, table_name):
                async with conn.cursor() as cursor:
                    # Use information_schema for a more standard check
                    await cursor.execute("""
                        SELECT COUNT(*)
                        FROM information_schema.tables
                        WHERE table_schema = DATABASE() AND table_name = %s
                    """, (table_name,))
                    result = await cursor.fetchone()
                    return result[0] > 0 if result else False

            try:
                # Use aiomysql transaction context manager
                async with conn.cursor() as cursor: # Get a cursor for checks first

                    # --- Bets Table ---
                    if not await table_exists(conn, 'bets'):
                        await cursor.execute('''
                            CREATE TABLE bets (
                                bet_id BIGINT AUTO_INCREMENT PRIMARY KEY,
                                guild_id BIGINT NOT NULL,
                                user_id BIGINT NOT NULL,
                                game_id BIGINT NULL, -- Added game_id column
                                bet_type VARCHAR(50) NOT NULL, -- Use VARCHAR instead of TEXT if max length known
                                selection TEXT NOT NULL,
                                units FLOAT NOT NULL, -- Use FLOAT for units
                                odds FLOAT NOT NULL, -- Use FLOAT for odds
                                status VARCHAR(20) NOT NULL DEFAULT 'pending', -- Use VARCHAR, add default
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, -- Auto update timestamp
                                result_value FLOAT NULL, -- Use FLOAT
                                result_description TEXT NULL,
                                expiration_time TIMESTAMP NULL, -- Added expiration_time
                                channel_id BIGINT NULL -- Added channel_id
                                -- Removed bet_won/bet_loss, use status
                            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                        ''')
                        await cursor.execute('CREATE INDEX idx_bets_guild_user ON bets (guild_id, user_id)')
                        await cursor.execute('CREATE INDEX idx_bets_status ON bets (status)')
                        await cursor.execute('CREATE INDEX idx_bets_created_at ON bets (created_at)')
                        await cursor.execute('CREATE INDEX idx_bets_game_id ON bets (game_id)') # Index for game_id
                        logger.info("Table 'bets' created.")
                    else:
                        # Check if game_id column exists and add if missing (Example ALTER)
                        await cursor.execute("""
                            SELECT COUNT(*) FROM information_schema.columns
                            WHERE table_schema=DATABASE() AND table_name='bets' AND column_name='game_id'
                        """)
                        if (await cursor.fetchone())[0] == 0:
                            await cursor.execute("ALTER TABLE bets ADD COLUMN game_id BIGINT NULL AFTER user_id;")
                            await cursor.execute("CREATE INDEX idx_bets_game_id ON bets (game_id)")
                            logger.info("Added 'game_id' column to 'bets' table.")
                        # Add similar checks/ALTER statements for other potentially missing columns like expiration_time, channel_id

                    # --- Guild Settings Table ---
                    if not await table_exists(conn, 'guild_settings'):
                        await cursor.execute('''
                            CREATE TABLE guild_settings (
                                guild_id BIGINT PRIMARY KEY,
                                is_active BOOLEAN DEFAULT TRUE,
                                subscription_level INTEGER DEFAULT 0,
                                is_paid BOOLEAN DEFAULT FALSE,
                                embed_channel_1 BIGINT NULL,
                                command_channel_1 BIGINT NULL,
                                admin_channel_1 BIGINT NULL,
                                admin_role BIGINT NULL,
                                authorized_role BIGINT NULL,
                                voice_channel_id BIGINT NULL, -- Monthly
                                yearly_channel_id BIGINT NULL, -- Yearly
                                total_units_channel_id BIGINT NULL -- Optional total? Might be same as yearly
                            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                        ''')
                        await cursor.execute('CREATE INDEX idx_guild_settings_active ON guild_settings (is_active)')
                        logger.info("Table 'guild_settings' created.")
                    # Add ALTER TABLE checks for columns if needed

                    # --- Cappers Table (Replaces guild_users?) ---
                    # This table seems more relevant based on setid command
                    if not await table_exists(conn, 'cappers'):
                         await cursor.execute('''
                              CREATE TABLE cappers (
                                   guild_id BIGINT NOT NULL,
                                   user_id BIGINT NOT NULL,
                                   display_name VARCHAR(100) NULL, -- Store display name
                                   image_path VARCHAR(255) NULL,   -- Store relative path to logo
                                   banner_color VARCHAR(7) NULL DEFAULT '#0096FF', -- Store hex color
                                   bet_won INTEGER DEFAULT 0,      -- Track wins directly?
                                   bet_loss INTEGER DEFAULT 0,     -- Track losses directly?
                                   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                   updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                                   PRIMARY KEY (guild_id, user_id)
                              ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                         ''')
                         logger.info("Table 'cappers' created.")
                    # Add ALTER TABLE checks if needed

                    # --- Users Table (For balance, separate from cappers) ---
                    if not await table_exists(conn, 'users'):
                         await cursor.execute('''
                              CREATE TABLE users (
                                   id BIGINT PRIMARY KEY, -- Discord User ID
                                   username VARCHAR(100) NULL,
                                   balance FLOAT DEFAULT 0.0, -- Renamed from units_balance for clarity
                                   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                   updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                                   -- lifetime_units could be calculated or stored in another table if needed
                              ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                         ''')
                         logger.info("Table 'users' created.")
                     # Add ALTER TABLE checks if needed

                    # --- Transactions Table (For tracking balance changes) ---
                    if not await table_exists(conn, 'transactions'):
                         await cursor.execute('''
                              CREATE TABLE transactions (
                                   transaction_id BIGINT AUTO_INCREMENT PRIMARY KEY,
                                   user_id BIGINT NOT NULL,
                                   type VARCHAR(50) NOT NULL, -- e.g., 'bet_win', 'bet_loss', 'deposit', 'withdrawal'
                                   amount FLOAT NOT NULL, -- Can be positive or negative
                                   bet_id BIGINT NULL, -- Link to bet if applicable
                                   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                   description TEXT NULL,
                                   FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE, -- Link to users table
                                   FOREIGN KEY (bet_id) REFERENCES bets(bet_id) ON DELETE SET NULL -- Link to bets table
                              ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                         ''')
                         await cursor.execute('CREATE INDEX idx_transactions_user_time ON transactions (user_id, created_at)')
                         logger.info("Table 'transactions' created.")
                    # Add ALTER TABLE checks if needed


                    # --- Unit Records Table (For historical/analytical unit tracking per bet) ---
                    if not await table_exists(conn, 'unit_records'):
                        await cursor.execute('''
                            CREATE TABLE unit_records (
                                record_id BIGINT AUTO_INCREMENT PRIMARY KEY,
                                bet_id BIGINT NULL, -- Link to the bet table
                                guild_id BIGINT NOT NULL,
                                user_id BIGINT NOT NULL,
                                year INTEGER NOT NULL,
                                month INTEGER NOT NULL,
                                units FLOAT NOT NULL, -- Units risked on the bet
                                odds FLOAT NOT NULL, -- Odds of the bet
                                result_value FLOAT NOT NULL, -- Calculated +/- units from the bet
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- When the record was created (bet resolved)
                                FOREIGN KEY (bet_id) REFERENCES bets(bet_id) ON DELETE SET NULL -- Link to bets
                                -- Removed FOREIGN KEY constraints to guild/user if users can leave guilds but records should persist
                                -- Consider adding FKs back if desired behavior is different
                            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                        ''')
                        await cursor.execute('CREATE INDEX idx_unit_records_guild_user_time ON unit_records (guild_id, user_id, year, month)')
                        await cursor.execute('CREATE INDEX idx_unit_records_guild_time ON unit_records (guild_id, created_at)')
                        await cursor.execute('CREATE INDEX idx_unit_records_bet_id ON unit_records (bet_id)')
                        logger.info("Table 'unit_records' created.")
                    # Add ALTER TABLE checks if needed

                    # --- Games Table (Store game info fetched from API) ---
                    if not await table_exists(conn, 'games'):
                         await cursor.execute('''
                              CREATE TABLE games (
                                   id BIGINT PRIMARY KEY, -- Use API's fixture/game ID as primary key
                                   sport VARCHAR(50) NOT NULL,
                                   league_id BIGINT NULL,
                                   league_name VARCHAR(150) NULL, -- Store name for easier display
                                   home_team_id BIGINT NULL,
                                   away_team_id BIGINT NULL,
                                   home_team_name VARCHAR(150) NULL,
                                   away_team_name VARCHAR(150) NULL,
                                   home_team_logo VARCHAR(255) NULL,
                                   away_team_logo VARCHAR(255) NULL,
                                   start_time TIMESTAMP NULL, -- Game start time (UTC)
                                   end_time TIMESTAMP NULL, -- Calculated/Estimated end time (Optional)
                                   status VARCHAR(20) NULL, -- e.g., 'NS', 'LIVE', 'FT', 'PST', 'CANC'
                                   score JSON NULL, -- Store score details as JSON
                                   venue VARCHAR(150) NULL,
                                   referee VARCHAR(100) NULL,
                                   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                   updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                              ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                         ''')
                         await cursor.execute('CREATE INDEX idx_games_league_status_time ON games (league_id, status, start_time)')
                         await cursor.execute('CREATE INDEX idx_games_start_time ON games (start_time)')
                         await cursor.execute('CREATE INDEX idx_games_status ON games (status)')
                         logger.info("Table 'games' created.")
                    # Add ALTER TABLE checks if needed


                    # --- Leagues Table ---
                    if not await table_exists(conn, 'leagues'):
                         await cursor.execute('''
                              CREATE TABLE leagues (
                                   id BIGINT PRIMARY KEY, -- API League ID
                                   name VARCHAR(150) NULL,
                                   sport VARCHAR(50) NOT NULL,
                                   type VARCHAR(50) NULL, -- e.g., League, Cup
                                   logo VARCHAR(255) NULL,
                                   country VARCHAR(100) NULL,
                                   country_code CHAR(3) NULL,
                                   country_flag VARCHAR(255) NULL,
                                   season INTEGER NULL -- Current/last known season year
                              ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                         ''')
                         await cursor.execute('CREATE INDEX idx_leagues_sport_country ON leagues (sport, country)')
                         logger.info("Table 'leagues' created.")
                     # Add ALTER TABLE checks if needed

                     # --- Teams Table ---
                    if not await table_exists(conn, 'teams'):
                         await cursor.execute('''
                              CREATE TABLE teams (
                                   id BIGINT PRIMARY KEY, -- API Team ID
                                   name VARCHAR(150) NULL,
                                   sport VARCHAR(50) NOT NULL,
                                   code VARCHAR(10) NULL, -- 3-letter code if available
                                   country VARCHAR(100) NULL,
                                   founded INTEGER NULL,
                                   national BOOLEAN DEFAULT FALSE,
                                   logo VARCHAR(255) NULL,
                                   venue_id BIGINT NULL, -- API Venue ID (if available separately)
                                   venue_name VARCHAR(150) NULL,
                                   venue_address VARCHAR(255) NULL,
                                   venue_city VARCHAR(100) NULL,
                                   venue_capacity INTEGER NULL,
                                   venue_surface VARCHAR(50) NULL,
                                   venue_image VARCHAR(255) NULL
                              ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                         ''')
                         await cursor.execute('CREATE INDEX idx_teams_sport_country ON teams (sport, country)')
                         await cursor.execute('CREATE INDEX idx_teams_name ON teams (name)')
                         logger.info("Table 'teams' created.")
                     # Add ALTER TABLE checks if needed

                     # --- Standings Table ---
                    if not await table_exists(conn, 'standings'):
                         await cursor.execute('''
                              CREATE TABLE standings (
                                   league_id BIGINT NOT NULL,
                                   team_id BIGINT NOT NULL,
                                   sport VARCHAR(50) NOT NULL,
                                   season INTEGER NOT NULL, -- Season year the standing is for
                                   `rank` INTEGER NULL, -- Use backticks as rank is a keyword
                                   points INTEGER NULL,
                                   goals_diff INTEGER NULL,
                                   form VARCHAR(20) NULL, -- e.g., 'WWLDW'
                                   status VARCHAR(50) NULL, -- e.g., 'same', 'up', 'down' (optional)
                                   description VARCHAR(100) NULL, -- e.g., 'Promotion', 'Relegation zone'
                                   group_name VARCHAR(100) NULL, -- For leagues with groups/conferences
                                   played INTEGER DEFAULT 0,
                                   won INTEGER DEFAULT 0,
                                   draw INTEGER DEFAULT 0,
                                   lost INTEGER DEFAULT 0,
                                   goals_for INTEGER DEFAULT 0,
                                   goals_against INTEGER DEFAULT 0,
                                   updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                                   PRIMARY KEY (league_id, team_id, season) -- Composite key for unique entry per season
                              ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                         ''')
                         await cursor.execute('CREATE INDEX idx_standings_league_season_rank ON standings (league_id, season, `rank`)')
                         logger.info("Table 'standings' created.")
                    # Add ALTER TABLE checks if needed


                     # --- Game Events Table (Optional: for detailed logging) ---
                    if not await table_exists(conn, 'game_events'):
                         await cursor.execute('''
                              CREATE TABLE game_events (
                                   event_id BIGINT AUTO_INCREMENT PRIMARY KEY,
                                   game_id BIGINT NOT NULL,
                                   guild_id BIGINT NULL, -- If events are guild-specific? Or link to bet?
                                   event_type VARCHAR(50) NOT NULL, -- e.g., 'score_change', 'game_start', 'game_end', 'bet_placed'
                                   details TEXT NULL, -- JSON or text description
                                   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                   FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE -- Link events to games
                              ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                         ''')
                         await cursor.execute('CREATE INDEX idx_game_events_game_time ON game_events (game_id, created_at)')
                         logger.info("Table 'game_events' created.")
                    # Add ALTER TABLE checks if needed


                    # --- Remove Deprecated Tables (Example) ---
                    # Drop guild_users, monthly_totals, yearly_totals if replaced by new structure
                    # Use IF EXISTS for safety
                    # await cursor.execute("DROP TABLE IF EXISTS guild_users;")
                    # logger.info("Dropped deprecated table 'guild_users'.")
                    # await cursor.execute("DROP TABLE IF EXISTS monthly_totals;")
                    # logger.info("Dropped deprecated table 'monthly_totals'.")
                    # await cursor.execute("DROP TABLE IF EXISTS yearly_totals;")
                    # logger.info("Dropped deprecated table 'yearly_totals'.")

                logger.info("Database schema initialization/verification complete.")
            except Exception as e:
                # Rollback is implicit with aiomysql connection context manager on error
                logger.error(f"Error initializing/verifying database schema: {e}", exc_info=True)
                raise # Re-raise the exception to signal failure
