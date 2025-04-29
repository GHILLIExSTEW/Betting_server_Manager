import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import aiosqlite
from ..data.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

class AnalyticsService:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    async def get_capper_stats(self, guild_id: int, user_id: int) -> Dict:
        """Get statistics for a specific capper."""
        try:
            # Get total bets
            total_bets = await self.db.fetch_one(
                """
                SELECT COUNT(*) as count FROM bets
                WHERE guild_id = ? AND user_id = ?
                """,
                guild_id, user_id
            )

            # Get won bets
            won_bets = await self.db.fetch_one(
                """
                SELECT COUNT(*) as count FROM bets
                WHERE guild_id = ? AND user_id = ? AND status = 'won'
                """,
                guild_id, user_id
            )

            # Get lost bets
            lost_bets = await self.db.fetch_one(
                """
                SELECT COUNT(*) as count FROM bets
                WHERE guild_id = ? AND user_id = ? AND status = 'lost'
                """,
                guild_id, user_id
            )

            # Get total units
            total_units = await self.db.fetch_one(
                """
                SELECT SUM(units) as total FROM bets
                WHERE guild_id = ? AND user_id = ?
                """,
                guild_id, user_id
            )

            # Get net units
            net_units = await self.db.fetch_one(
                """
                SELECT SUM(result_value) as net FROM bets
                WHERE guild_id = ? AND user_id = ? AND status IN ('won', 'lost')
                """,
                guild_id, user_id
            )

            return {
                'total_bets': total_bets['count'] if total_bets else 0,
                'won_bets': won_bets['count'] if won_bets else 0,
                'lost_bets': lost_bets['count'] if lost_bets else 0,
                'total_units': total_units['total'] if total_units else 0,
                'net_units': net_units['net'] if net_units else 0,
                'win_percentage': (won_bets['count'] / total_bets['count'] * 100) if total_bets and total_bets['count'] > 0 else 0
            }
        except Exception as e:
            logger.error(f"Error getting capper stats: {str(e)}")
            return {}

    async def get_guild_stats(self, guild_id: int) -> Dict:
        """Get statistics for the entire guild."""
        try:
            # Get total bets
            total_bets = await self.db.fetch_one(
                """
                SELECT COUNT(*) as count FROM bets
                WHERE guild_id = ?
                """,
                guild_id
            )

            # Get total cappers
            total_cappers = await self.db.fetch_one(
                """
                SELECT COUNT(DISTINCT user_id) as count FROM bets
                WHERE guild_id = ?
                """,
                guild_id
            )

            # Get total units wagered
            total_units = await self.db.fetch_one(
                """
                SELECT SUM(units) as total FROM bets
                WHERE guild_id = ?
                """,
                guild_id
            )

            # Get net units
            net_units = await self.db.fetch_one(
                """
                SELECT SUM(result_value) as net FROM bets
                WHERE guild_id = ? AND status IN ('won', 'lost')
                """,
                guild_id
            )

            return {
                'total_bets': total_bets['count'] if total_bets else 0,
                'total_cappers': total_cappers['count'] if total_cappers else 0,
                'total_units': total_units['total'] if total_units else 0,
                'net_units': net_units['net'] if net_units else 0
            }
        except Exception as e:
            logger.error(f"Error getting guild stats: {str(e)}")
            return {}

    async def get_top_cappers(self, guild_id: int, limit: int = 5) -> List[Dict]:
        """Get top performing cappers in the guild."""
        try:
            return await self.db.fetch(
                """
                SELECT 
                    user_id,
                    COUNT(*) as total_bets,
                    SUM(CASE WHEN status = 'won' THEN 1 ELSE 0 END) as won_bets,
                    SUM(units) as total_units,
                    SUM(result_value) as net_units
                FROM bets
                WHERE guild_id = ?
                GROUP BY user_id
                ORDER BY net_units DESC
                LIMIT ?
                """,
                guild_id, limit
            )
        except Exception as e:
            logger.error(f"Error getting top cappers: {str(e)}")
            return []

    async def get_recent_bets(self, guild_id: int, limit: int = 10) -> List[Dict]:
        """Get recent bets in the guild."""
        try:
            return await self.db.fetch(
                """
                SELECT * FROM bets
                WHERE guild_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                guild_id, limit
            )
        except Exception as e:
            logger.error(f"Error getting recent bets: {str(e)}")
            return [] 