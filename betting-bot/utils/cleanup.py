import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

class CleanupTasks:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.cleanup_task: Optional[asyncio.Task] = None

    async def start_cleanup_tasks(self):
        """Start the cleanup tasks."""
        if self.cleanup_task is None or self.cleanup_task.done():
            self.cleanup_task = asyncio.create_task(self._run_cleanup_loop())
            logger.info("Cleanup tasks started")

    async def stop_cleanup_tasks(self):
        """Stop the cleanup tasks."""
        if self.cleanup_task and not self.cleanup_task.done():
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("Cleanup tasks stopped")

    async def _run_cleanup_loop(self):
        """Run the cleanup loop."""
        while True:
            try:
                await self._cleanup_unconfirmed_bets()
                await asyncio.sleep(60)  # Check every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying

    async def _cleanup_unconfirmed_bets(self):
        """Delete unconfirmed bets older than 5 minutes."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(minutes=5)
            query = """
                DELETE FROM bets 
                WHERE confirmed = 0 
                AND created_at < %s
            """
            result = await self.db_manager.execute(query, (cutoff_time,))
            if result.rowcount > 0:
                logger.info(f"Deleted {result.rowcount} unconfirmed bets older than 5 minutes")
        except Exception as e:
            logger.error(f"Error cleaning up unconfirmed bets: {e}") 