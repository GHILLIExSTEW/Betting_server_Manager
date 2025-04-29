import aiosqlite
import logging
from typing import Optional, List, Dict, Any
import os

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: str = 'data/betting.db'):
        self.db_path = db_path
        self._ensure_db_directory()

    def _ensure_db_directory(self):
        """Ensure the database directory exists."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    async def connect(self):
        """Create a database connection."""
        return await aiosqlite.connect(self.db_path)

    async def execute(self, query: str, *args) -> None:
        """Execute a query that doesn't return results."""
        async with await self.connect() as db:
            await db.execute(query, args)
            await db.commit()

    async def fetch_one(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Execute a query and return a single row."""
        async with await self.connect() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, args)
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def fetch_all(self, query: str, *args) -> List[Dict[str, Any]]:
        """Execute a query and return all rows."""
        async with await self.connect() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, args)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def initialize_db(self) -> None:
        """Initialize the database with required tables."""
        try:
            async with await self.connect() as db:
                # Create bets table
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS bets (
                        bet_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        game_id INTEGER,
                        bet_type TEXT NOT NULL,
                        selection TEXT NOT NULL,
                        units INTEGER NOT NULL,
                        odds REAL NOT NULL,
                        status TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        bet_won INTEGER DEFAULT 0,
                        bet_loss INTEGER DEFAULT 0
                    )
                ''')

                # Create unit_records table
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS unit_records (
                        record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        bet_id INTEGER,
                        units INTEGER NOT NULL,
                        odds REAL NOT NULL,
                        result_value REAL NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (bet_id) REFERENCES bets(bet_id)
                    )
                ''')

                # Create guild_settings table
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS guild_settings (
                        guild_id INTEGER PRIMARY KEY,
                        is_active BOOLEAN DEFAULT 1,
                        voice_channel_id INTEGER,
                        yearly_channel_id INTEGER
                    )
                ''')

                # Create guild_users table
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS guild_users (
                        guild_id INTEGER,
                        user_id INTEGER,
                        units_balance REAL DEFAULT 0,
                        lifetime_units REAL DEFAULT 0,
                        PRIMARY KEY (guild_id, user_id)
                    )
                ''')

                await db.commit()
                logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            raise 