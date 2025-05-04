import asyncio
import aiosqlite
import logging
from datetime import datetime

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def check_guild_settings():
    async with aiosqlite.connect('betting-bot/data/betting.db') as db:
        # Get column names
        async with db.execute("PRAGMA table_info(guild_settings)") as cursor:
            columns = await cursor.fetchall()
            column_names = [col[1] for col in columns]
            logger.info("Guild Settings Table Columns:")
            for col in columns:
                logger.info(f"  {col[1]} ({col[2]})")
            logger.info("-" * 50)

        # Check guild settings with all columns
        async with db.execute("SELECT * FROM guild_settings") as cursor:
            rows = await cursor.fetchall()
            if not rows:
                logger.info("No guild settings found")
                return
            
            for row in rows:
                logger.info(f"\nGuild Settings Row:")
                for col_name, value in zip(column_names, row):
                    # Format timestamp if it's the created_at column
                    if col_name == 'created_at' and value:
                        try:
                            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                            value = dt.strftime('%Y-%m-%d %H:%M:%S UTC')
                        except:
                            pass
                    logger.info(f"  {col_name}: {value}")

        # Check unit records
        async with db.execute("""
            SELECT guild_id, COUNT(*) as record_count
            FROM unit_records
            WHERE guild_id IN (1328116926903353398, 1328126227013439601)
            GROUP BY guild_id
        """) as cursor:
            rows = await cursor.fetchall()
            if not rows:
                logger.info("No unit records found for either guild")
                return
            
            for row in rows:
                guild_id, count = row
                logger.info(f"Guild {guild_id} has {count} unit records")

if __name__ == "__main__":
    asyncio.run(check_guild_settings()) 