# betting-bot/data/db_manager.py

"""Database manager for MySQL using aiomysql."""

import aiomysql
import logging
from typing import Optional, List, Dict, Any, Union
import os

try:
    from ..config.database_mysql import (
        MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB,
        MYSQL_POOL_MIN_SIZE, MYSQL_POOL_MAX_SIZE
    )
except ImportError:
    from config.database_mysql import (
        MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB,
        MYSQL_POOL_MIN_SIZE, MYSQL_POOL_MAX_SIZE
    )

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.db_name = MYSQL_DB  # Store database name from config
        self._pool: Optional[aiomysql.Pool] = None
        logger.info("MySQL DatabaseManager initialized.")
        if not all([MYSQL_HOST, MYSQL_USER, MYSQL_DB, MYSQL_PASSWORD is not None]):
            logger.critical("Missing one or more MySQL environment variables. DatabaseManager cannot connect.")

    async def connect(self) -> Optional[aiomysql.Pool]:
        """Create or return existing MySQL connection pool."""
        if self._pool is None:
            if not all([MYSQL_HOST, MYSQL_USER, MYSQL_DB, MYSQL_PASSWORD is not None]):
                logger.critical("Cannot connect: MySQL environment variables are not configured.")
                return None

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
                    autocommit=True,
                    connect_timeout=10,
                    charset='utf8mb4',
                    cursorclass=aiomysql.DictCursor
                )
                async with self._pool.acquire() as conn:
                    async with conn.cursor() as cursor:
                        await cursor.execute("SELECT 1")
                logger.info("MySQL connection pool created and tested successfully.")
                await self.initialize_db()
            except aiomysql.OperationalError as op_err:
                logger.critical(f"FATAL: OperationalError connecting to MySQL: {op_err}", exc_info=True)
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

    async def execute(self, query: str, *args) -> Optional[int]:
        """Execute a query (INSERT/UPDATE/DELETE) and return the last row ID or affected rows."""
        if not self._pool:
            await self.connect()
        if not self._pool:
            logger.error("Cannot execute: DB pool unavailable.")
            raise ConnectionError("DB pool unavailable.")
        logger.debug(f"Executing DB Query: {query} Args: {args}")
        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    rowcount = await cursor.execute(query, args)
                    return cursor.lastrowid if query.strip().upper().startswith("INSERT") else rowcount
        except Exception as e:
            logger.error(f"Error executing query: {query} Args: {args}. Error: {e}", exc_info=True)
            return None

    async def fetch_one(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Execute a query and fetch one row as a dictionary."""
        if not self._pool:
            await self.connect()
        if not self._pool:
            logger.error("Cannot fetch_one: DB pool unavailable.")
            raise ConnectionError("DB pool unavailable.")
        logger.debug(f"Fetching One DB Query: {query} Args: {args}")
        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute(query, args)
                    return await cursor.fetchone()
        except Exception as e:
            logger.error(f"Error fetching one row: {query} Args: {args}. Error: {e}", exc_info=True)
            return None

    async def fetch_all(self, query: str, *args) -> List[Dict[str, Any]]:
        """Execute a query and fetch all rows as a list of dictionaries."""
        if not self._pool:
            await self.connect()
        if not self._pool:
            logger.error("Cannot fetch_all: DB pool unavailable.")
            raise ConnectionError("DB pool unavailable.")
        logger.debug(f"Fetching All DB Query: {query} Args: {args}")
        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute(query, args)
                    return await cursor.fetchall()
        except Exception as e:
            logger.error(f"Error fetching all rows: {query} Args: {args}. Error: {e}", exc_info=True)
            return []

    async def fetchval(self, query: str, *args) -> Optional[Any]:
        """Execute a query and fetch a single value."""
        if not self._pool:
            await self.connect()
        if not self._pool:
            logger.error("Cannot fetchval: DB pool unavailable.")
            raise ConnectionError("DB pool unavailable.")
        logger.debug(f"Fetching Value DB Query: {query} Args: {args}")
        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(query, args)
                    row = await cursor.fetchone()
                    return row[0] if row else None
        except Exception as e:
            logger.error(f"Error fetching value: {query} Args: {args}. Error: {e}", exc_info=True)
            return None

    async def table_exists(self, conn, table_name: str) -> bool:
        """Check if a table exists in the database."""
        try:
            result = await self.fetchval(
                """
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema = %s AND table_name = %s
                """,
                self.db_name, table_name
            )
            return result > 0 if result is not None else False
        except Exception as e:
            logger.exception(f"Error checking if table '{table_name}' exists: {e}")
            raise

    async def initialize_db(self):
        """Initialize the database schema, creating tables if they don't exist."""
        if not self._pool:
            logger.error("Cannot initialize DB: Connection pool is not available.")
            return
        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    logger.info("Attempting to initialize/verify database schema...")

                    # USERS Table
                    if not await self.table_exists(conn, 'users'):
                        await cursor.execute("""
                            CREATE TABLE users (
                                user_id BIGINT PRIMARY KEY COMMENT 'Discord User ID',
                                username VARCHAR(100) NULL COMMENT 'Last known Discord username',
                                balance DECIMAL(15,2) DEFAULT 1000.00 NOT NULL COMMENT 'Available betting units',
                                frozen_balance DECIMAL(15,2) DEFAULT 0.00 NOT NULL COMMENT 'Units tied up in pending bets',
                                join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'When user was first added',
                                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last interaction time'
                            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                        """)
                        logger.info("Table 'users' created.")
                    else:
                        logger.info("Table 'users' already exists.")

                    # GUILD_SETTINGS Table
                    if not await self.table_exists(conn, 'guild_settings'):
                        await cursor.execute("""
                            CREATE TABLE guild_settings (
                                guild_id BIGINT PRIMARY KEY,
                                is_active BOOLEAN DEFAULT TRUE,
                                subscription_level INTEGER DEFAULT 0,
                                is_paid BOOLEAN DEFAULT FALSE,
                                embed_channel_1 BIGINT NULL,
                                command_channel_1 BIGINT NULL,
                                admin_channel_1 BIGINT NULL,
                                admin_role BIGINT NULL,
                                authorized_role BIGINT NULL COMMENT 'Role ID for authorized cappers',
                                voice_channel_id BIGINT NULL COMMENT 'Monthly stats voice channel ID',
                                yearly_channel_id BIGINT NULL COMMENT 'Yearly stats voice channel ID',
                                total_units_channel_id BIGINT NULL COMMENT 'Optional: Lifetime units channel ID',
                                min_units DECIMAL(15,2) DEFAULT 0.1,
                                max_units DECIMAL(15,2) DEFAULT 10.0,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                        """)
                        logger.info("Table 'guild_settings' created.")
                    else:
                        logger.info("Table 'guild_settings' already exists.")

                    # CAPPERS Table
                    if not await self.table_exists(conn, 'cappers'):
                        await cursor.execute("""
                            CREATE TABLE cappers (
                                guild_id BIGINT NOT NULL,
                                user_id BIGINT NOT NULL,
                                display_name VARCHAR(100) NULL,
                                image_path VARCHAR(255) NULL,
                                banner_color VARCHAR(7) NULL DEFAULT '#0096FF',
                                bet_won INTEGER DEFAULT 0 NOT NULL,
                                bet_loss INTEGER DEFAULT 0 NOT NULL,
                                bet_push INTEGER DEFAULT 0 NOT NULL,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                                PRIMARY KEY (guild_id, user_id),
                                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                        """)
                        logger.info("Table 'cappers' created.")
                    else:
                        logger.info("Table 'cappers' already exists.")

                    # GAMES Table
                    if not await self.table_exists(conn, 'games'):
                        await cursor.execute("""
                            CREATE TABLE games (
                                id BIGINT PRIMARY KEY COMMENT 'API Fixture ID',
                                sport VARCHAR(50) NOT NULL COMMENT 'Sport key (e.g., soccer, basketball)',
                                league_id BIGINT NULL COMMENT 'API League ID',
                                league_name VARCHAR(150) NULL,
                                home_team_id BIGINT NULL COMMENT 'API Team ID',
                                away_team_id BIGINT NULL COMMENT 'API Team ID',
                                home_team_name VARCHAR(150) NULL,
                                away_team_name VARCHAR(150) NULL,
                                home_team_logo VARCHAR(255) NULL,
                                away_team_logo VARCHAR(255) NULL,
                                start_time TIMESTAMP NULL COMMENT 'Game start time in UTC',
                                end_time TIMESTAMP NULL COMMENT 'Game end time in UTC (if known)',
                                status VARCHAR(20) NULL COMMENT 'Game status (e.g., TBD, NS, LIVE, FT, CANC)',
                                score JSON NULL COMMENT 'JSON storing scores (e.g., {"home": 1, "away": 0})',
                                venue VARCHAR(150) NULL,
                                referee VARCHAR(100) NULL,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                        """)
                        await cursor.execute("CREATE INDEX idx_games_league_status_time ON games (league_id, status, start_time)")
                        await cursor.execute("CREATE INDEX idx_games_start_time ON games (start_time)")
                        await cursor.execute("CREATE INDEX idx_games_status ON games (status)")
                        logger.info("Table 'games' created.")
                    else:
                        logger.info("Table 'games' already exists.")

                    # BETS Table
                    if not await self.table_exists(conn, 'bets'):
                        await cursor.execute("""
                            CREATE TABLE bets (
                                bet_serial INT AUTO_INCREMENT PRIMARY KEY,
                                guild_id BIGINT NOT NULL COMMENT 'Discord Guild ID',
                                user_id BIGINT NOT NULL COMMENT 'Discord User ID of better',
                                game_id BIGINT NULL COMMENT 'FK to games.id (API Fixture ID)',
                                bet_type VARCHAR(50) NOT NULL COMMENT 'e.g., moneyline, spread, total',
                                team_name VARCHAR(255) NOT NULL COMMENT 'Team/Selection description',
                                stake DECIMAL(15,2) NOT NULL COMMENT 'Units risked',
                                odds DECIMAL(10,2) NOT NULL COMMENT 'American odds',
                                channel_id BIGINT NOT NULL COMMENT 'Discord Channel ID where bet was placed/posted',
                                message_id BIGINT NULL COMMENT 'Discord Message ID of the posted bet',
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                status VARCHAR(20) DEFAULT 'pending' NOT NULL COMMENT 'pending, won, lost, push, canceled, expired',
                                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                                expiration_time TIMESTAMP NULL COMMENT 'Optional: Time when pending bet should auto-expire',
                                result_value DECIMAL(15,2) NULL COMMENT 'Net units won/lost (+/-)',
                                result_description TEXT NULL COMMENT 'Optional description of result (e.g., who resolved)',
                                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                                FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE SET NULL
                            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                        """)
                        await cursor.execute("CREATE INDEX idx_bets_user_id ON bets(user_id)")
                        await cursor.execute("CREATE INDEX idx_bets_guild_id ON bets(guild_id)")
                        await cursor.execute("CREATE INDEX idx_bets_game_id ON bets(game_id)")
                        await cursor.execute("CREATE INDEX idx_bets_status ON bets(status)")
                        await cursor.execute("CREATE INDEX idx_bets_created_at ON bets(created_at)")
                        logger.info("Table 'bets' created.")
                    else:
                        logger.info("Table 'bets' already exists.")

                    # UNIT_RECORDS Table
                    if not await self.table_exists(conn, 'unit_records'):
                        await cursor.execute("""
                            CREATE TABLE unit_records (
                                record_id INT AUTO_INCREMENT PRIMARY KEY,
                                bet_serial INT NOT NULL COMMENT 'FK to bets.bet_serial',
                                guild_id BIGINT NOT NULL,
                                user_id BIGINT NOT NULL,
                                year INT NOT NULL COMMENT 'Year the bet resolved',
                                month INT NOT NULL COMMENT 'Month the bet resolved (1-12)',
                                units DECIMAL(15,2) NOT NULL COMMENT 'Units staked on the original bet',
                                odds DECIMAL(10,2) NOT NULL COMMENT 'Odds of the original bet',
                                result_value DECIMAL(15,2) NOT NULL COMMENT 'Net units won/lost from the bet',
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Timestamp when record was created (bet resolved)',
                                FOREIGN KEY (bet_serial) REFERENCES bets(bet_serial) ON DELETE CASCADE,
                                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                        """)
                        await cursor.execute("CREATE INDEX idx_unit_records_guild_user_ym ON unit_records(guild_id, user_id, year, month)")
                        await cursor.execute("CREATE INDEX idx_unit_records_year_month ON unit_records(year, month)")
                        await cursor.execute("CREATE INDEX idx_unit_records_user_id ON unit_records(user_id)")
                        await cursor.execute("CREATE INDEX idx_unit_records_guild_id ON unit_records(guild_id)")
                        logger.info("Table 'unit_records' created.")
                    else:
                        logger.info("Table 'unit_records' already exists.")
                        await cursor.execute("SHOW COLUMNS FROM unit_records LIKE 'year'")
                        if not await cursor.fetchone():
                            await cursor.execute("""
                                ALTER TABLE unit_records
                                ADD COLUMN year INT NOT NULL COMMENT 'Year the bet resolved' AFTER user_id
                            """)
                            logger.info("Added 'year' column to existing 'unit_records' table.")
                        await cursor.execute("SHOW COLUMNS FROM unit_records LIKE 'month'")
                        if not await cursor.fetchone():
                            await cursor.execute("""
                                ALTER TABLE unit_records
                                ADD COLUMN month INT NOT NULL COMMENT 'Month the bet resolved (1-12)' AFTER year
                            """)
                            logger.info("Added 'month' column to existing 'unit_records' table.")

                    # LEAGUES Table
                    if not await self.table_exists(conn, 'leagues'):
                        await cursor.execute("""
                            CREATE TABLE leagues (
                                id BIGINT PRIMARY KEY COMMENT 'API League ID',
                                name VARCHAR(150) NULL,
                                sport VARCHAR(50) NOT NULL,
                                type VARCHAR(50) NULL,
                                logo VARCHAR(255) NULL,
                                country VARCHAR(100) NULL,
                                country_code CHAR(3) NULL,
                                country_flag VARCHAR(255) NULL,
                                season INTEGER NULL COMMENT 'Typically the starting year of the season'
                            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                        """)
                        await cursor.execute("CREATE INDEX idx_leagues_sport_country ON leagues (sport, country)")
                        logger.info("Table 'leagues' created.")
                    else:
                        logger.info("Table 'leagues' already exists.")

                    # TEAMS Table
                    if not await self.table_exists(conn, 'teams'):
                        await cursor.execute("""
                            CREATE TABLE teams (
                                id BIGINT PRIMARY KEY COMMENT 'API Team ID',
                                name VARCHAR(150) NULL,
                                sport VARCHAR(50) NOT NULL,
                                code VARCHAR(10) NULL COMMENT 'Short code (e.g., LAL)',
                                country VARCHAR(100) NULL,
                                founded INTEGER NULL,
                                national BOOLEAN DEFAULT FALSE,
                                logo VARCHAR(255) NULL,
                                venue_id BIGINT NULL COMMENT 'API Venue ID',
                                venue_name VARCHAR(150) NULL,
                                venue_address VARCHAR(255) NULL,
                                venue_city VARCHAR(100) NULL,
                                venue_capacity INTEGER NULL,
                                venue_surface VARCHAR(50) NULL,
                                venue_image VARCHAR(255) NULL
                            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                        """)
                        await cursor.execute("CREATE INDEX idx_teams_sport_country ON teams (sport, country)")
                        await cursor.execute("CREATE INDEX idx_teams_name ON teams (name)")
                        logger.info("Table 'teams' created.")
                    else:
                        logger.info("Table 'teams' already exists.")

                    # STANDINGS Table
                    if not await self.table_exists(conn, 'standings'):
                        await cursor.execute("""
                            CREATE TABLE standings (
                                league_id BIGINT NOT NULL COMMENT 'API League ID',
                                team_id BIGINT NOT NULL COMMENT 'API Team ID',
                                season INT NOT NULL COMMENT 'Season year',
                                sport VARCHAR(50) NOT NULL,
                                `rank` INTEGER NULL COMMENT 'Team rank in group/league',
                                points INTEGER NULL,
                                goals_diff INTEGER NULL,
                                form VARCHAR(20) NULL COMMENT 'e.g., WWLDW',
                                status VARCHAR(50) NULL COMMENT 'e.g., same',
                                description VARCHAR(100) NULL COMMENT 'Promotion/relegation zone etc.',
                                group_name VARCHAR(100) NULL COMMENT 'League group/conference name',
                                played INTEGER DEFAULT 0,
                                won INTEGER DEFAULT 0,
                                draw INTEGER DEFAULT 0,
                                lost INTEGER DEFAULT 0,
                                goals_for INTEGER DEFAULT 0,
                                goals_against INTEGER DEFAULT 0,
                                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                                PRIMARY KEY (league_id, team_id, season) COMMENT 'Composite primary key'
                            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                        """)
                        await cursor.execute("CREATE INDEX idx_standings_league_season_rank ON standings (league_id, season, `rank`)")
                        logger.info("Table 'standings' created.")
                    else:
                        logger.info("Table 'standings' already exists.")

                    # GAME_EVENTS Table
                    if not await self.table_exists(conn, 'game_events'):
                        await cursor.execute("""
                            CREATE TABLE game_events (
                                event_id BIGINT AUTO_INCREMENT PRIMARY KEY,
                                game_id BIGINT NOT NULL COMMENT 'FK to games.id',
                                guild_id BIGINT NULL COMMENT 'Optional: Guild context if event is guild-specific',
                                event_type VARCHAR(50) NOT NULL COMMENT 'e.g., game_start, score_change, game_end',
                                details TEXT NULL COMMENT 'JSON or text details about the event',
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
                            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                        """)
                        await cursor.execute("CREATE INDEX idx_game_events_game_time ON game_events (game_id, created_at)")
                        logger.info("Table 'game_events' created.")
                    else:
                        logger.info("Table 'game_events' already exists.")

                    logger.info("Database schema initialization/verification complete.")

        except Exception as e:
            logger.error(f"Error initializing/verifying database schema: {e}", exc_info=True)
            raise
