# betting-bot/data/db_manager.py

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

if not MYSQL_DB:
    print("CRITICAL ERROR: MYSQL_DB environment variable is not set.")

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages the connection pool and executes queries against the MySQL DB."""

    def __init__(self):
        """Initializes the DatabaseManager."""
        self._pool: Optional[aiomysql.Pool] = None
        self.db_name = MYSQL_DB
        logger.info("MySQL DatabaseManager initialized.")
        if not all([MYSQL_HOST, MYSQL_USER, self.db_name, MYSQL_PASSWORD is not None]):
            logger.critical(
                "Missing one or more MySQL environment variables "
                "(HOST, USER, PASSWORD, DB). DatabaseManager cannot connect."
            )

    async def connect(self) -> Optional[aiomysql.Pool]:
        """Create or return existing MySQL connection pool."""
        if self._pool is None:
            if not all([MYSQL_HOST, MYSQL_USER, self.db_name, MYSQL_PASSWORD is not None]):
                logger.critical(
                    "Cannot connect: MySQL environment variables are not "
                    "configured."
                )
                return None

            logger.info("Attempting to create MySQL connection pool...")
            try:
                self._pool = await aiomysql.create_pool(
                    host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER,
                    password=MYSQL_PASSWORD, db=self.db_name,
                    minsize=MYSQL_POOL_MIN_SIZE, maxsize=MYSQL_POOL_MAX_SIZE,
                    autocommit=True, connect_timeout=10,
                    charset='utf8mb4'
                )
                async with self._pool.acquire() as conn:
                    async with conn.cursor() as cursor:
                        await cursor.execute("SELECT 1")
                logger.info(
                    "MySQL connection pool created and tested successfully."
                )
                await self.initialize_db()
            except aiomysql.OperationalError as op_err:
                logger.critical(f"FATAL: OpError connecting to MySQL: {op_err}", exc_info=True)
                self._pool = None
                raise ConnectionError(f"Failed to connect (OperationalError): {op_err}") from op_err
            except Exception as e:
                logger.critical(f"FATAL: Failed to connect to MySQL: {e}", exc_info=True)
                self._pool = None
                raise ConnectionError(f"Failed to connect: {e}") from e
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
        """Execute INSERT, UPDATE, DELETE. Returns rowcount."""
        if not self._pool:
            await self.connect()
        if not self._pool:
            logger.error("Cannot execute: DB pool unavailable.")
            raise ConnectionError("DB pool unavailable.")

        # Flatten nested tuple/list if only one argument is a tuple/list
        if len(args) == 1 and isinstance(args[0], (tuple, list)):
            args = tuple(args[0])

        logger.debug(f"Executing DB Query: {query} Args: {args}")
        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cursor:  # Default tuple cursor
                    rowcount = await cursor.execute(query, args)
                    return rowcount  # Return rowcount, not lastrowid
        except Exception as e:
            logger.error(f"Error executing query: {query} Args: {args}. Error: {e}", exc_info=True)
            return None

    async def fetch_one(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Fetch one row as a dictionary."""
        if not self._pool:
            await self.connect()
        if not self._pool:
            logger.error("Cannot fetch_one: DB pool unavailable.")
            raise ConnectionError("DB pool unavailable.")

        if len(args) == 1 and isinstance(args[0], (tuple, list)):
            args = tuple(args[0])

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
        """Fetch all rows as a list of dictionaries."""
        if not self._pool:
            await self.connect()
        if not self._pool:
            logger.error("Cannot fetch_all: DB pool unavailable.")
            raise ConnectionError("DB pool unavailable.")

        if len(args) == 1 and isinstance(args[0], (tuple, list)):
            args = tuple(args[0])

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
        """Fetch a single value from the first row."""
        if not self._pool:
            await self.connect()
        if not self._pool:
            logger.error("Cannot fetchval: DB pool unavailable.")
            raise ConnectionError("DB pool unavailable.")

        if len(args) == 1 and isinstance(args[0], (tuple, list)):
            args = tuple(args[0])

        logger.debug(f"Fetching Value DB Query: {query} Args: {args}")
        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor(aiomysql.Cursor) as cursor:
                    await cursor.execute(query, args)
                    row = await cursor.fetchone()
                    return row[0] if row else None
        except Exception as e:
            logger.error(f"Error fetching value: {query} Args: {args}. Error: {e}", exc_info=True)
            return None

    async def table_exists(self, conn, table_name: str) -> bool:
        """Check if a table exists in the database."""
        async with conn.cursor(aiomysql.Cursor) as cursor:
            try:
                await cursor.execute(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = %s AND table_name = %s",
                    (self.db_name, table_name)
                )
                result = await cursor.fetchone()
                return result[0] > 0 if result else False
            except Exception as e:
                logger.error(f"Error checking if table '{table_name}' exists: {e}", exc_info=True)
                raise

    async def _check_and_add_column(self, cursor, table_name, column_name, column_definition):
        """Checks if a column exists and adds it if not."""
        async with cursor.connection.cursor(aiomysql.DictCursor) as dict_cursor:
            await dict_cursor.execute(f"SHOW COLUMNS FROM `{table_name}` LIKE %s", (column_name,))
            exists = await dict_cursor.fetchone()

        if not exists:
            logger.info(f"Adding column '{column_name}' to table '{table_name}'...")
            alter_statement = f"ALTER TABLE `{table_name}` ADD COLUMN `{column_name}` {column_definition}"
            await cursor.execute(alter_statement)
            logger.info(f"Successfully added column '{column_name}'.")
        else:
            logger.debug(f"Column '{column_name}' already exists in '{table_name}'.")

    async def initialize_db(self):
        """Initializes the database schema."""
        if not self._pool:
            logger.error("Cannot initialize DB: Connection pool unavailable.")
            return
        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor(aiomysql.Cursor) as cursor:
                    logger.info("Attempting to initialize/verify database schema...")

                    if not await self.table_exists(conn, 'users'):
                        await cursor.execute('''
                            CREATE TABLE users (
                                user_id BIGINT PRIMARY KEY COMMENT 'Discord User ID',
                                username VARCHAR(100) NULL COMMENT 'Last known Discord username',
                                balance DECIMAL(15, 2) DEFAULT 1000.00 NOT NULL,
                                frozen_balance DECIMAL(15, 2) DEFAULT 0.00 NOT NULL,
                                join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                        ''')
                        logger.info("Table 'users' created.")
                    else:
                        logger.info("Table 'users' already exists.")

                    if not await self.table_exists(conn, 'games'):
                        await cursor.execute('''
                            CREATE TABLE games (
                                id BIGINT PRIMARY KEY COMMENT 'API Fixture ID',
                                sport VARCHAR(50) NOT NULL,
                                league_id BIGINT NULL, league_name VARCHAR(150) NULL,
                                home_team_id BIGINT NULL, away_team_id BIGINT NULL,
                                home_team_name VARCHAR(150) NULL, away_team_name VARCHAR(150) NULL,
                                home_team_logo VARCHAR(255) NULL, away_team_logo VARCHAR(255) NULL,
                                start_time TIMESTAMP NULL COMMENT 'Game start time in UTC',
                                end_time TIMESTAMP NULL COMMENT 'Game end time in UTC (if known)',
                                status VARCHAR(20) NULL COMMENT 'Game status (e.g., NS, LIVE, FT)',
                                score JSON NULL COMMENT 'JSON storing scores',
                                venue VARCHAR(150) NULL, referee VARCHAR(100) NULL,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                        ''')
                        await cursor.execute('CREATE INDEX idx_games_league_status_time ON games (league_id, status, start_time)')
                        await cursor.execute('CREATE INDEX idx_games_start_time ON games (start_time)')
                        await cursor.execute('CREATE INDEX idx_games_status ON games (status)')
                        logger.info("Table 'games' created.")
                    else:
                        logger.info("Table 'games' already exists.")
                        await self._check_and_add_column(cursor, 'games', 'sport', "VARCHAR(50) NOT NULL COMMENT 'Sport key' AFTER id")
                        await self._check_and_add_column(cursor, 'games', 'league_name', "VARCHAR(150) NULL AFTER league_id")
                        await self._check_and_add_column(cursor, 'games', 'home_team_name', "VARCHAR(150) NULL AFTER away_team_id")
                        await self._check_and_add_column(cursor, 'games', 'away_team_name', "VARCHAR(150) NULL AFTER home_team_name")
                        await self._check_and_add_column(cursor, 'games', 'home_team_logo', "VARCHAR(255) NULL AFTER away_team_name")
                        await self._check_and_add_column(cursor, 'games', 'away_team_logo', "VARCHAR(255) NULL AFTER home_team_logo")
                        await self._check_and_add_column(cursor, 'games', 'end_time', "TIMESTAMP NULL COMMENT 'Game end time' AFTER start_time")
                        await self._check_and_add_column(cursor, 'games', 'status', "VARCHAR(20) NULL COMMENT 'Game status' AFTER end_time")
                        await self._check_and_add_column(cursor, 'games', 'score', "JSON NULL COMMENT 'JSON scores' AFTER status")
                        await self._check_and_add_column(cursor, 'games', 'venue', "VARCHAR(150) NULL AFTER score")
                        await self._check_and_add_column(cursor, 'games', 'referee', "VARCHAR(100) NULL AFTER venue")

                    if not await self.table_exists(conn, 'bets'):
                        await cursor.execute('''
                            CREATE TABLE bets (
                                bet_serial BIGINT PRIMARY KEY,
                                event_id VARCHAR(255) DEFAULT NULL,
                                guild_id BIGINT NOT NULL,
                                message_id BIGINT DEFAULT NULL,
                                status VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT 'pending, won, lost, push, canceled, expired',
                                user_id BIGINT NOT NULL,
                                game_id BIGINT DEFAULT NULL,
                                bet_type VARCHAR(50) DEFAULT NULL,
                                player_prop VARCHAR(255) DEFAULT NULL,
                                player_id VARCHAR(50) DEFAULT NULL,
                                league VARCHAR(50) NOT NULL,
                                team VARCHAR(100) NOT NULL,
                                opponent VARCHAR(50) DEFAULT NULL,
                                line VARCHAR(255) DEFAULT NULL,
                                odds DECIMAL(10,2) DEFAULT NULL,
                                units DECIMAL(10,2) NOT NULL,
                                legs INT DEFAULT NULL,
                                bet_won TINYINT DEFAULT 0,
                                bet_loss TINYINT DEFAULT 0,
                                created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
                                game_start DATETIME DEFAULT NULL,
                                result_value DECIMAL(15,2) DEFAULT NULL,
                                result_description TEXT DEFAULT NULL,
                                expiration_time TIMESTAMP NULL DEFAULT NULL,
                                updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                                channel_id BIGINT DEFAULT NULL,
                                PRIMARY KEY (bet_serial),
                                KEY idx_user_guild (user_id,guild_id),
                                KEY idx_bets_game_id (game_id),
                                KEY idx_bets_user_id (user_id),
                                KEY idx_bets_guild_id (guild_id),
                                KEY idx_bets_created_at (created_at),
                                CONSTRAINT fk_bets_game_id FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE SET NULL
                            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                        ''')
                        logger.info("Table 'bets' created.")
                    else:
                        logger.info("Table 'bets' already exists.")
                        async with conn.cursor(aiomysql.DictCursor) as dict_cursor:
                            await dict_cursor.execute("SHOW COLUMNS FROM bets LIKE 'game_id'")
                            col_info = await dict_cursor.fetchone()
                            if col_info and 'bigint' not in col_info.get('Type', '').lower():
                                logger.warning("Column 'bets.game_id' is not BIGINT. Manual alteration might be needed.")

                    if not await self.table_exists(conn, 'unit_records'):
                        await cursor.execute('''
                            CREATE TABLE unit_records (
                                record_id INT AUTO_INCREMENT PRIMARY KEY,
                                bet_serial BIGINT NOT NULL COMMENT 'FK to bets.bet_serial',
                                guild_id BIGINT NOT NULL, user_id BIGINT NOT NULL,
                                year INT NOT NULL COMMENT 'Year bet resolved',
                                month INT NOT NULL COMMENT 'Month bet resolved (1-12)',
                                units DECIMAL(15, 2) NOT NULL COMMENT 'Original stake',
                                odds DECIMAL(10, 2) NOT NULL COMMENT 'Original odds',
                                result_value DECIMAL(15, 2) NOT NULL COMMENT 'Net units won/lost',
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Timestamp bet resolved',
                                FOREIGN KEY (bet_serial) REFERENCES bets(bet_serial) ON DELETE CASCADE
                            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                        ''')
                        await cursor.execute('CREATE INDEX idx_unit_records_guild_user_ym ON unit_records(guild_id, user_id, year, month)')
                        await cursor.execute('CREATE INDEX idx_unit_records_year_month ON unit_records(year, month)')
                        await cursor.execute('CREATE INDEX idx_unit_records_user_id ON unit_records(user_id)')
                        await cursor.execute('CREATE INDEX idx_unit_records_guild_id ON unit_records(guild_id)')
                        logger.info("Table 'unit_records' created.")
                    else:
                        logger.info("Table 'unit_records' already exists.")
                        await self._check_and_add_column(cursor, 'unit_records', 'year', "INT NOT NULL COMMENT 'Year bet resolved' AFTER user_id")
                        await self._check_and_add_column(cursor, 'unit_records', 'month', "INT NOT NULL COMMENT 'Month bet resolved (1-12)' AFTER year")

                    if not await self.table_exists(conn, 'guild_settings'):
                        await cursor.execute('''
                            CREATE TABLE guild_settings (
                                guild_id BIGINT PRIMARY KEY,
                                is_active BOOLEAN DEFAULT TRUE, subscription_level INTEGER DEFAULT 0,
                                is_paid BOOLEAN DEFAULT FALSE, embed_channel_1 BIGINT NULL,
                                command_channel_1 BIGINT NULL, admin_channel_1 BIGINT NULL,
                                admin_role BIGINT NULL, authorized_role BIGINT NULL,
                                voice_channel_id BIGINT NULL, yearly_channel_id BIGINT NULL,
                                total_units_channel_id BIGINT NULL,
                                min_units DECIMAL(15, 2) DEFAULT 0.1, max_units DECIMAL(15, 2) DEFAULT 10.0,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                        ''')
                        logger.info("Table 'guild_settings' created.")
                    else:
                        logger.info("Table 'guild_settings' already exists.")

                    if not await self.table_exists(conn, 'cappers'):
                        await cursor.execute('''
                            CREATE TABLE cappers (
                                guild_id BIGINT NOT NULL, user_id BIGINT NOT NULL,
                                display_name VARCHAR(100) NULL, image_path VARCHAR(255) NULL,
                                banner_color VARCHAR(7) NULL DEFAULT '#0096FF',
                                bet_won INTEGER DEFAULT 0 NOT NULL, bet_loss INTEGER DEFAULT 0 NOT NULL,
                                bet_push INTEGER DEFAULT 0 NOT NULL,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                                PRIMARY KEY (guild_id, user_id)
                            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                        ''')
                        logger.info("Table 'cappers' created.")
                    else:
                        logger.info("Table 'cappers' already exists.")
                        await self._check_and_add_column(cursor, 'cappers', 'bet_push', "INTEGER DEFAULT 0 NOT NULL COMMENT 'Count of pushed bets' AFTER bet_loss")

                    if not await self.table_exists(conn, 'leagues'):
                        await cursor.execute('''
                            CREATE TABLE leagues (
                                id BIGINT PRIMARY KEY COMMENT 'API League ID', name VARCHAR(150) NULL,
                                sport VARCHAR(50) NOT NULL, type VARCHAR(50) NULL, logo VARCHAR(255) NULL,
                                country VARCHAR(100) NULL, country_code CHAR(3) NULL,
                                country_flag VARCHAR(255) NULL, season INTEGER NULL
                            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                        ''')
                        await cursor.execute('CREATE INDEX idx_leagues_sport_country ON leagues (sport, country)')
                        logger.info("Table 'leagues' created.")
                    else:
                        logger.info("Table 'leagues' already exists.")

                    if not await self.table_exists(conn, 'teams'):
                        await cursor.execute('''
                            CREATE TABLE teams (
                                id BIGINT PRIMARY KEY COMMENT 'API Team ID', name VARCHAR(150) NULL,
                                sport VARCHAR(50) NOT NULL, code VARCHAR(10) NULL, country VARCHAR(100) NULL,
                                founded INTEGER NULL, national BOOLEAN DEFAULT FALSE, logo VARCHAR(255) NULL,
                                venue_id BIGINT NULL, venue_name VARCHAR(150) NULL, venue_address VARCHAR(255) NULL,
                                venue_city VARCHAR(100) NULL, venue_capacity INTEGER NULL,
                                venue_surface VARCHAR(50) NULL, venue_image VARCHAR(255) NULL
                            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                        ''')
                        await cursor.execute('CREATE INDEX idx_teams_sport_country ON teams (sport, country)')
                        await cursor.execute('CREATE INDEX idx_teams_name ON teams (name)')
                        logger.info("Table 'teams' created.")
                    else:
                        logger.info("Table 'teams' already exists.")

                    if not await self.table_exists(conn, 'standings'):
                        await cursor.execute('''
                            CREATE TABLE standings (
                                league_id BIGINT NOT NULL, team_id BIGINT NOT NULL, season INT NOT NULL,
                                sport VARCHAR(50) NOT NULL, `rank` INTEGER NULL, points INTEGER NULL,
                                goals_diff INTEGER NULL, form VARCHAR(20) NULL, status VARCHAR(50) NULL,
                                description VARCHAR(100) NULL, group_name VARCHAR(100) NULL,
                                played INTEGER DEFAULT 0, won INTEGER DEFAULT 0, draw INTEGER DEFAULT 0, lost INTEGER DEFAULT 0,
                                goals_for INTEGER DEFAULT 0, goals_against INTEGER DEFAULT 0,
                                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                                PRIMARY KEY (league_id, team_id, season)
                            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                        ''')
                        await cursor.execute('CREATE INDEX idx_standings_league_season_rank ON standings (league_id, season, `rank`)')
                        logger.info("Table 'standings' created.")
                    else:
                        logger.info("Table 'standings' already exists.")
                        async with conn.cursor(aiomysql.DictCursor) as dict_cursor:
                            await dict_cursor.execute("SHOW COLUMNS FROM standings LIKE 'season'")
                            if not await dict_cursor.fetchone():
                                logger.warning("Attempting to add 'season' column and modify PK for 'standings'. BACKUP RECOMMENDED.")
                                try:
                                    await cursor.execute("ALTER TABLE standings DROP PRIMARY KEY")
                                    await cursor.execute("ALTER TABLE standings ADD COLUMN season INT NOT NULL COMMENT 'Season year' AFTER team_id")
                                    await cursor.execute("ALTER TABLE standings ADD PRIMARY KEY (league_id, team_id, season)")
                                    logger.info("Added 'season' column and updated PK for 'standings'.")
                                except Exception as alter_err:
                                    logger.error(f"Failed to alter 'standings' table: {alter_err}. Manual intervention needed.")

                    if not await self.table_exists(conn, 'game_events'):
                        await cursor.execute('''
                            CREATE TABLE game_events (
                                event_id BIGINT AUTO_INCREMENT PRIMARY KEY, game_id BIGINT NOT NULL,
                                guild_id BIGINT NULL, event_type VARCHAR(50) NOT NULL,
                                details TEXT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
                            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                        ''')
                        await cursor.execute('CREATE INDEX idx_game_events_game_time ON game_events (game_id, created_at)')
                        logger.info("Table 'game_events' created.")
                    else:
                        logger.info("Table 'game_events' already exists.")

                    logger.info("Database schema initialization/verification complete.")
        except Exception as e:
            logger.error(f"Error initializing/verifying database schema: {e}", exc_info=True)
            raise
