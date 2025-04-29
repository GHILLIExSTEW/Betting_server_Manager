"""Analytics service for tracking and analyzing betting statistics."""

import discord
import logging
import aiosqlite
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from utils.errors import AnalyticsServiceError

logger = logging.getLogger(__name__)

class AnalyticsService:
    def __init__(self, bot):
        self.bot = bot
        self.db_path = 'betting-bot/data/betting.db'

    async def get_user_stats(self, guild_id: int, user_id: int) -> Dict[str, Any]:
        """Get betting statistics for a user."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Get total bets
                async with db.execute("""
                    SELECT COUNT(*) as total_bets,
                           SUM(CASE WHEN status = 'won' THEN 1 ELSE 0 END) as wins,
                           SUM(CASE WHEN status = 'lost' THEN 1 ELSE 0 END) as losses,
                           SUM(CASE WHEN status = 'won' THEN units * odds ELSE 0 END) as profit,
                           SUM(CASE WHEN status = 'lost' THEN units ELSE 0 END) as losses_units
                    FROM bets
                    WHERE guild_id = ? AND user_id = ?
                """, (guild_id, user_id)) as cursor:
                    row = await cursor.fetchone()
                    if not row:
                        return {
                            'total_bets': 0,
                            'wins': 0,
                            'losses': 0,
                            'profit': 0,
                            'win_rate': 0
                        }

                    total_bets = row[0] or 0
                    wins = row[1] or 0
                    losses = row[2] or 0
                    profit = row[3] or 0
                    losses_units = row[4] or 0

                    return {
                        'total_bets': total_bets,
                        'wins': wins,
                        'losses': losses,
                        'profit': profit - losses_units,
                        'win_rate': (wins / total_bets * 100) if total_bets > 0 else 0
                    }
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            raise AnalyticsServiceError(f"Failed to get user stats: {str(e)}")

    async def get_guild_stats(self, guild_id: int) -> Dict[str, Any]:
        """Get betting statistics for a guild."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Get total bets
                async with db.execute("""
                    SELECT COUNT(*) as total_bets,
                           SUM(CASE WHEN status = 'won' THEN 1 ELSE 0 END) as wins,
                           SUM(CASE WHEN status = 'lost' THEN 1 ELSE 0 END) as losses,
                           SUM(CASE WHEN status = 'won' THEN units * odds ELSE 0 END) as profit,
                           SUM(CASE WHEN status = 'lost' THEN units ELSE 0 END) as losses_units,
                           COUNT(DISTINCT user_id) as total_cappers
                    FROM bets
                    WHERE guild_id = ?
                """, (guild_id,)) as cursor:
                    row = await cursor.fetchone()
                    if not row:
                        return {
                            'total_bets': 0,
                            'wins': 0,
                            'losses': 0,
                            'profit': 0,
                            'win_rate': 0,
                            'total_cappers': 0
                        }

                    total_bets = row[0] or 0
                    wins = row[1] or 0
                    losses = row[2] or 0
                    profit = row[3] or 0
                    losses_units = row[4] or 0
                    total_cappers = row[5] or 0

                    return {
                        'total_bets': total_bets,
                        'wins': wins,
                        'losses': losses,
                        'profit': profit - losses_units,
                        'win_rate': (wins / total_bets * 100) if total_bets > 0 else 0,
                        'total_cappers': total_cappers
                    }
        except Exception as e:
            logger.error(f"Error getting guild stats: {e}")
            raise AnalyticsServiceError(f"Failed to get guild stats: {str(e)}")

    async def get_leaderboard(
        self,
        guild_id: int,
        timeframe: str = 'weekly',
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get the betting leaderboard for a guild."""
        try:
            # Calculate date range
            now = datetime.utcnow()
            if timeframe == 'daily':
                start_date = now - timedelta(days=1)
            elif timeframe == 'weekly':
                start_date = now - timedelta(weeks=1)
            elif timeframe == 'monthly':
                start_date = now - timedelta(days=30)
            else:
                raise ValueError(f"Invalid timeframe: {timeframe}")

            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT user_id,
                           COUNT(*) as total_bets,
                           SUM(CASE WHEN status = 'won' THEN 1 ELSE 0 END) as wins,
                           SUM(CASE WHEN status = 'won' THEN units * odds ELSE 0 END) as profit,
                           SUM(CASE WHEN status = 'lost' THEN units ELSE 0 END) as losses_units
                    FROM bets
                    WHERE guild_id = ? AND created_at >= ?
                    GROUP BY user_id
                    ORDER BY (profit - losses_units) DESC
                    LIMIT ?
                """, (guild_id, start_date, limit)) as cursor:
                    rows = await cursor.fetchall()
                    return [{
                        'user_id': row[0],
                        'total_bets': row[1],
                        'wins': row[2],
                        'profit': row[3] - row[4]
                    } for row in rows]
        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}")
            raise AnalyticsServiceError(f"Failed to get leaderboard: {str(e)}") 