import aiomysql  # Keep aiomysql for MySQL
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

    async def connect(self) -> Optional[aiomysql.Pool]:  # Return Optional Pool
        """Create or return existing MySQL connection pool."""
        if self._pool is None:
            if not all([MYSQL_HOST, MYSQL_USER, MYSQL_DB, MYSQL_PASSWORD is not None]):
                # Log critical error and prevent further operation without connection
                logger.critical("Cannot connect: MySQL environment variables are not configured.")
                return None  # Indicate connection failure

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
                    autocommit=True,  # Keep autocommit True for simplicity unless transactions needed often
                    connect_timeout=10  # Add a connection timeout
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

    async def execute(self, query: str, *args) -> Optional[int]:  # Return Optional[int] for lastrowid or rowcount
        """Execute a query (INSERT, UPDATE, DELETE). Returns lastrowid for INSERT or rowcount."""
        if not self._pool:
            await self.connect()  # Attempt to reconnect if pool is lost
            if not self._pool:  # Check again after attempting reconnect
                logger.error("Cannot execute query: Database pool not available.")
                raise ConnectionError("Database pool not available for execute.")  # Raise error

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
                        return rowcount  # Return number of affected rows for UPDATE/DELETE
        except Exception as e:
            logger.error(f"Error executing query: {query} with args: {args}. Error: {e}", exc_info=True)
            return None  # Keep returning None for now based on original structure

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
            return None

    async def table_exists(self, conn, table_name: str) -> bool:
        """Check if a table exists in the database."""
        async with conn.cursor() as cursor:
            await cursor.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s AND table_name = %s",
                (MYSQL_DB, table_name)
            )
            return (await cursor.fetchone())[0] > 0

    async def initialize_db(self):
        """Initializes the database schema, creating tables if they don't exist."""
        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    logger.info("Attempting to initialize/verify database schema...")

                    # Create users table
                    await cursor.execute('''
                        CREATE TABLE IF NOT EXISTS users (
                            user_id BIGINT PRIMARY KEY,
                            username VARCHAR(100) NULL,
                            balance DECIMAL(15, 2) DEFAULT 1000.00,
                            frozen_balance DECIMAL(15, 2) DEFAULT 0.00,
                            join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                    ''')
                    logger.info("Checked/created 'users' table.")

                    # Create games table
                    await cursor.execute('''
                        CREATE TABLE IF NOT EXISTS games (
                            game_id VARCHAR(255) PRIMARY KEY,
                            sport_key VARCHAR(100),
                            sport_title VARCHAR(255),
                            commence_time DATETIME,
                            home_team VARCHAR(255),
                            away_team VARCHAR(255),
                            bookmaker VARCHAR(100),
                            last_update DATETIME,
                            completed BOOLEAN DEFAULT FALSE,
                            home_score INT,
                            away_score INT
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                    ''')
                    logger.info("Checked/created 'games' table.")

                    # Create bets table
                    await cursor.execute('''
                        CREATE TABLE IF NOT EXISTS bets (
                            bet_id INT AUTO_INCREMENT PRIMARY KEY,
                            user_id BIGINT NOT NULL,
                            game_id VARCHAR(255),
                            bet_type VARCHAR(50) NOT NULL,
                            team_name VARCHAR(255),
                            odds DECIMAL(10, 3) NOT NULL,
                            stake DECIMAL(15, 2) NOT NULL,
                            potential_payout DECIMAL(15, 2) NOT NULL,
                            status VARCHAR(20) DEFAULT 'pending',
                            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            parlay_id INT DEFAULT NULL,
                            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                            FOREIGN KEY (game_id) REFERENCES games(game_id) ON DELETE SET NULL,
                            INDEX(parlay_id)
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                    ''')
                    logger.info("Checked/created 'bets' table.")

                    # Guild Settings Table
                    if not await self.table_exists(conn, 'guild_settings'):
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
                                voice_channel_id BIGINT NULL,
                                yearly_channel_id BIGINT NULL,
                                total_units_channel_id BIGINT NULL
                            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                        ''')
                        await cursor.execute('CREATE INDEX idx_guild_settings_active ON guild_settings (is_active)')
                        logger.info("Table 'guild_settings' created.")

                    # Cappers Table
                    if not await self.table_exists(conn, 'cappers'):
                        await cursor.execute('''
                            CREATE TABLE cappers (
                                guild_id BIGINT NOT NULL,
                                user_id BIGINT NOT NULL,
                                display_name VARCHAR(100) NULL,
                                image_path VARCHAR(255) NULL,
                                banner_color VARCHAR(7) NULL DEFAULT '#0096FF',
                                bet_won INTEGER DEFAULT 0,
                                bet_loss INTEGER DEFAULT 0,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                                PRIMARY KEY (guild_id, user_id)
                            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                        ''')
                        logger.info("Table 'cappers' created.")

                    # Unit Records Table
                    if not await self.table_exists(conn, 'unit_records'):
                        await cursor.execute('''
                            CREATE TABLE unit_records (
                                record_id BIGINT AUTO_INCREMENT PRIMARY KEY,
                                bet_id INT NULL,
                                guild_id BIGINT NOT NULL,
                                user_id BIGINT NOT NULL,
                                year INTEGER NOT NULL,
                                month INTEGER NOT NULL,
                                units FLOAT NOT NULL,
                                odds FLOAT NOT NULL,
                                result_value FLOAT NOT NULL,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                FOREIGN KEY (bet_id) REFERENCES bets(bet_id) ON DELETE SET NULL
                            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                        ''')
                        await cursor.execute('CREATE INDEX idx_unit_records_guild_user_time ON unit_records (guild_id, user_id, year, month)')
                        await cursor.execute('CREATE INDEX idx_unit_records_guild_time ON unit_records (guild_id, created_at)')
                        await cursor.execute('CREATE INDEX idx_unit_records_bet_id ON unit_records (bet_id)')
                        logger.info("Table 'unit_records' created.")

                    # Games Table (API-based, renamed to api_games)
                    if not await self.table_exists(conn, 'api_games'):
                        await cursor.execute('''
                            CREATE TABLE api_games (
                                id BIGINT PRIMARY KEY,
                                sport VARCHAR(50) NOT NULL,
                                league_id BIGINT NULL,
                                league_name VARCHAR(150) NULL,
                                home_team_id BIGINT NULL,
                                away_team_id BIGINT NULL,
                                home_team_name VARCHAR(150) NULL,
                                away_team_name VARCHAR(150) NULL,
                                home_team_logo VARCHAR(255) NULL,
                                away_team_logo VARCHAR(255) NULL,
                                start_time TIMESTAMP NULL,
                                end_time TIMESTAMP NULL,
                                status VARCHAR(20) NULL,
                                score JSON NULL,
                                venue VARCHAR(150) NULL,
                                referee VARCHAR(100) NULL,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                        ''')
                        await cursor.execute('CREATE INDEX idx_api_games_league_status_time ON api_games (league_id, status, start_time)')
                        await cursor.execute('CREATE INDEX idx_api_games_start_time ON api_games (start_time)')
                        await cursor.execute('CREATE INDEX idx_api_games_status ON api_games (status)')
                        logger.info("Table 'api_games' created.")

                    # Leagues Table
                    if not await self.table_exists(conn, 'leagues'):
                        await cursor.execute('''
                            CREATE TABLE leagues (
                                id BIGINT PRIMARY KEY,
                                name VARCHAR(150) NULL,
                                sport VARCHAR(50) NOT NULL,
                                type VARCHAR(50) NULL,
                                logo VARCHAR(255) NULL,
                                country VARCHAR(100) NULL,
                                country_code CHAR(3) NULL,
                                country_flag VARCHAR(255) NULL,
                                season INTEGER NULL
                            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                        ''')
                        await cursor.execute('CREATE INDEX idx_leagues_sport_country ON leagues (sport, country)')
                        logger.info("Table 'leagues' created.")

                    # Teams Table
                    if not await self.table_exists(conn, 'teams'):
                        await cursor.execute('''
                            CREATE TABLE teams (
                                id BIGINT PRIMARY KEY,
                                name VARCHAR(150) NULL,
                                sport VARCHAR(50) NOT NULL,
                                code VARCHAR(10) NULL,
                                country VARCHAR(100) NULL,
                                founded INTEGER NULL,
                                national BOOLEAN DEFAULT FALSE,
                                logo VARCHAR(255) NULL,
                                venue_id BIGINT NULL,
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

                    # Standings Table
                    if not await self.table_exists(conn, 'standings'):
                        await cursor.execute('''
                            CREATE TABLE standings (
                                league_id BIGINT NOT NULL,
                                team_id BIGINT NOT NULL,
                                sport VARCHAR(50) NOT NULL,
                                season INTEGER NOT NULL,
                                `rank` INTEGER NULL,
                                points INTEGER NULL,
                                goals_diff INTEGER NULL,
                                form VARCHAR(20) NULL,
                                status VARCHAR(50) NULL,
                                description VARCHAR(100) NULL,
                                group_name VARCHAR(100) NULL,
                                played INTEGER DEFAULT 0,
                                won INTEGER DEFAULT 0,
                                draw INTEGER DEFAULT 0,
                                lost INTEGER DEFAULT 0,
                                goals_for INTEGER DEFAULT 0,
                                goals_against INTEGER DEFAULT 0,
                                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                                PRIMARY KEY (league_id, team_id, season)
                            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                        ''')
                        await cursor.execute('CREATE INDEX idx_standings_league_season_rank ON standings (league_id, season, `rank`)')
                        logger.info("Table 'standings' created.")

                    # Game Events Table
                    if not await self.table_exists(conn, 'game_events'):
                        await cursor.execute('''
                            CREATE TABLE game_events (
                                event_id BIGINT AUTO_INCREMENT PRIMARY KEY,
                                game_id BIGINT NOT NULL,
                                guild_id BIGINT NULL,
                                event_type VARCHAR(50) NOT NULL,
                                details TEXT NULL,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                FOREIGN KEY (game_id) REFERENCES api_games(id) ON DELETE CASCADE
                            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                        ''')
                        await cursor.execute('CREATE INDEX idx_game_events_game_time ON game_events (game_id, created_at)')
                        logger.info("Table 'game_events' created.")

                    logger.info("Database schema initialization/verification complete.")
        except Exception as e:
            # Rollback is implicit with aiomysql connection context manager on error
            logger.error(f"Error initializing/verifying database schema: {e}", exc_info=True)
            raise  # Re-raise the exception to signal failure
