import asyncpg
import logging
from typing import List, Dict, Optional, Any
from bot.config.settings import (
    DB_HOST,
    DB_PORT,
    DB_NAME,
    DB_USER,
    DB_PASSWORD
)

logger = logging.getLogger(__name__)

class DatabaseManager:
    _pool = None

    @classmethod
    async def get_pool(cls):
        """Get or create database connection pool"""
        if cls._pool is None:
            try:
                cls._pool = await asyncpg.create_pool(
                    host=DB_HOST,
                    port=DB_PORT,
                    database=DB_NAME,
                    user=DB_USER,
                    password=DB_PASSWORD
                )
                logger.info("Database connection pool created successfully")
            except Exception as e:
                logger.error(f"Failed to create database pool: {e}")
                raise
        return cls._pool

    @classmethod
    async def close_pool(cls):
        """Close database connection pool"""
        if cls._pool:
            await cls._pool.close()
            cls._pool = None
            logger.info("Database connection pool closed")

    @classmethod
    async def execute(cls, query: str, *args) -> None:
        """Execute a query that doesn't return results"""
        try:
            pool = await cls.get_pool()
            async with pool.acquire() as conn:
                await conn.execute(query, *args)
        except Exception as e:
            logger.error(f"Database execute error: {e}")
            raise

    @classmethod
    async def fetch(cls, query: str, *args) -> List[Dict[str, Any]]:
        """Execute a query and return all results"""
        try:
            pool = await cls.get_pool()
            async with pool.acquire() as conn:
                records = await conn.fetch(query, *args)
                return [dict(record) for record in records]
        except Exception as e:
            logger.error(f"Database fetch error: {e}")
            raise

    @classmethod
    async def fetch_one(cls, query: str, *args) -> Optional[Dict[str, Any]]:
        """Execute a query and return first result"""
        try:
            pool = await cls.get_pool()
            async with pool.acquire() as conn:
                record = await conn.fetchrow(query, *args)
                return dict(record) if record else None
        except Exception as e:
            logger.error(f"Database fetch_one error: {e}")
            raise

    @classmethod
    async def execute_many(cls, query: str, args_list: List[tuple]) -> None:
        """Execute a query multiple times with different parameters"""
        try:
            pool = await cls.get_pool()
            async with pool.acquire() as conn:
                await conn.executemany(query, args_list)
        except Exception as e:
            logger.error(f"Database execute_many error: {e}")
            raise

    @classmethod
    async def transaction(cls, queries: List[tuple]) -> None:
        """Execute multiple queries in a transaction"""
        try:
            pool = await cls.get_pool()
            async with pool.acquire() as conn:
                async with conn.transaction():
                    for query, args in queries:
                        await conn.execute(query, *args)
        except Exception as e:
            logger.error(f"Database transaction error: {e}")
            raise

# Create a singleton instance
db_manager = DatabaseManager() 