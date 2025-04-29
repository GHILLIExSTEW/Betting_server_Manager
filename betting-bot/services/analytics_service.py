# betting-bot/services/analytics_service.py

"""Analytics service for tracking and analyzing betting statistics."""

import discord # Keep discord import if bot instance is used for anything
import logging
# import aiosqlite # Remove direct DB driver import
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone # Add timezone

# Use relative imports assuming services/ is sibling to utils/
try:
    from ..utils.errors import AnalyticsServiceError
    # Import DatabaseManager only for type hinting if needed
    # from ..data.db_manager import DatabaseManager
except ImportError:
    from utils.errors import AnalyticsServiceError
    # from data.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

class AnalyticsService:
    # Corrected __init__
    def __init__(self, bot, db_manager): # Accept bot and db_manager
        """Initializes the Analytics Service.

        Args:
            bot: The discord bot instance.
            db_manager: The shared DatabaseManager instance.
        """
        self.bot = bot # Store bot instance (might be useful later)
        self.db = db_manager # Use the passed-in db_manager instance
        # self.db_path = '...' # No longer needed

    async def get_user_stats(self, guild_id: int, user_id: int) -> Dict[str, Any]:
        """Get betting statistics for a user using the shared db_manager."""
        try:
            # Use self.db and PostgreSQL syntax ($ placeholders)
            # Ensure 'result_value' column exists and is populated correctly in 'unit_records' or 'bets'
            stats = await self.db.fetch_one("""
                SELECT
                    COUNT(b.bet_id) as total_bets,
                    SUM(CASE WHEN b.status = 'won' THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN b.status = 'lost' THEN 1 ELSE 0 END) as losses,
                    SUM(CASE WHEN b.status = 'push' THEN 1 ELSE 0 END) as pushes,
                    COALESCE(SUM(ur.result_value), 0.0) as net_units -- Sum calculated profit/loss from unit_records
                FROM bets b
                LEFT JOIN unit_records ur ON b.bet_id = ur.bet_id -- Join to get calculated result
                WHERE b.guild_id = $1 AND b.user_id = $2
                AND b.status IN ('won', 'lost', 'push') -- Only count resolved bets
            """, guild_id, user_id)

            if not stats or (stats.get('total_bets') or 0) == 0:
                # Return default zeroed stats if no bets found or division by zero would occur
                return {
                    'total_bets': 0, 'wins': 0, 'losses': 0, 'pushes': 0,
                    'win_rate': 0.0, 'net_units': 0.0, 'roi': 0.0
                }

            # Ensure values are treated as numbers, defaulting to 0 if None
            wins = stats.get('wins') or 0
            losses = stats.get('losses') or 0
            pushes = stats.get('pushes') or 0
            total_bets = stats.get('total_bets') or 0
            net_units = stats.get('net_units') or 0.0

            total_resolved_for_winrate = wins + losses # Don't include pushes in win rate denominator
            win_rate = (wins / total_resolved_for_winrate * 100) if total_resolved_for_winrate > 0 else 0.0

            # Calculate ROI (Return on Investment) -> (Net Units / Total Units Risked) * 100
            # Need total units risked from bets table
            total_risked_result = await self.db.fetch_one("""
                 SELECT COALESCE(SUM(units), 0) as total_risked
                 FROM bets
                 WHERE guild_id = $1 AND user_id = $2
                 AND status IN ('won', 'lost', 'push')
            """, guild_id, user_id)
            total_risked = total_risked_result.get('total_risked') or 0 if total_risked_result else 0

            roi = (net_units / total_risked * 100.0) if total_risked > 0 else 0.0

            return {
                'total_bets': total_bets,
                'wins': wins,
                'losses': losses,
                'pushes': pushes,
                'win_rate': win_rate,
                'net_units': net_units,
                'roi': roi
            }
        except Exception as e:
            logger.exception(f"Error getting user stats for user {user_id} in guild {guild_id}: {e}")
            raise AnalyticsServiceError(f"Failed to get user stats: {str(e)}")

    async def get_guild_stats(self, guild_id: int) -> Dict[str, Any]:
        """Get betting statistics for the entire guild using the shared db_manager."""
        try:
            # Combined query for efficiency
            stats = await self.db.fetch_one("""
                SELECT
                    COUNT(b.bet_id) as total_bets,
                    SUM(CASE WHEN b.status = 'won' THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN b.status = 'lost' THEN 1 ELSE 0 END) as losses,
                    SUM(CASE WHEN b.status = 'push' THEN 1 ELSE 0 END) as pushes,
                    COALESCE(SUM(ur.result_value), 0.0) as net_units,
                    COUNT(DISTINCT b.user_id) as total_cappers -- Count distinct users who placed resolved bets
                FROM bets b
                LEFT JOIN unit_records ur ON b.bet_id = ur.bet_id
                WHERE b.guild_id = $1
                AND b.status IN ('won', 'lost', 'push')
            """, guild_id)

            if not stats or (stats.get('total_bets') or 0) == 0:
                 return {
                    'total_bets': 0, 'wins': 0, 'losses': 0, 'pushes': 0,
                    'win_rate': 0.0, 'net_units': 0.0, 'total_cappers': 0, 'roi': 0.0
                }

            wins = stats.get('wins') or 0
            losses = stats.get('losses') or 0
            pushes = stats.get('pushes') or 0
            total_bets = stats.get('total_bets') or 0
            net_units = stats.get('net_units') or 0.0
            total_cappers = stats.get('total_cappers') or 0

            total_resolved_for_winrate = wins + losses
            win_rate = (wins / total_resolved_for_winrate * 100.0) if total_resolved_for_winrate > 0 else 0.0

            # Calculate ROI
            total_risked_result = await self.db.fetch_one("""
                 SELECT COALESCE(SUM(units), 0) as total_risked
                 FROM bets
                 WHERE guild_id = $1 AND status IN ('won', 'lost', 'push')
            """, guild_id)
            total_risked = total_risked_result.get('total_risked') or 0 if total_risked_result else 0
            roi = (net_units / total_risked * 100.0) if total_risked > 0 else 0.0

            return {
                'total_bets': total_bets,
                'wins': wins,
                'losses': losses,
                'pushes': pushes,
                'win_rate': win_rate,
                'net_units': net_units,
                'total_cappers': total_cappers,
                'roi': roi
            }
        except Exception as e:
            logger.exception(f"Error getting guild stats for guild {guild_id}: {e}")
            raise AnalyticsServiceError(f"Failed to get guild stats: {str(e)}")

    async def get_leaderboard(
        self,
        guild_id: int,
        timeframe: str = 'weekly', # 'daily', 'weekly', 'monthly', 'yearly', 'alltime'
        limit: int = 10,
        metric: str = 'net_units' # 'net_units', 'roi', 'win_rate', 'wins'
    ) -> List[Dict[str, Any]]:
        """Get the betting leaderboard for a guild based on a metric and timeframe."""
        try:
            # Calculate date range based on timeframe
            now = datetime.now(timezone.utc)
            start_date = None
            if timeframe == 'daily':
                start_date = now - timedelta(days=1)
            elif timeframe == 'weekly':
                start_date = now - timedelta(weeks=1)
            elif timeframe == 'monthly':
                # Be careful with months - days=30 is an approximation
                start_date = now - timedelta(days=30)
            elif timeframe == 'yearly':
                 start_date = datetime(now.year, 1, 1, tzinfo=timezone.utc)
            # 'alltime' means start_date remains None

            # Build the core query for metrics
            # Ensure created_at column exists in bets table
            query = """
                SELECT
                    b.user_id,
                    COUNT(b.bet_id) FILTER (WHERE b.status IN ('won', 'lost', 'push')) as total_resolved_bets, -- Count only resolved
                    SUM(CASE WHEN b.status = 'won' THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN b.status = 'lost' THEN 1 ELSE 0 END) as losses,
                    COALESCE(SUM(ur.result_value), 0.0) as net_units,
                    COALESCE(SUM(CASE WHEN b.status IN ('won', 'lost', 'push') THEN b.units ELSE 0 END), 0) as total_risked -- Sum units only for resolved bets
                FROM bets b
                LEFT JOIN unit_records ur ON b.bet_id = ur.bet_id
                WHERE b.guild_id = $1
            """
            params: List[Any] = [guild_id]
            param_index = 2

            if start_date:
                # Filter by bet creation time OR resolution time? Using created_at for now.
                query += f" AND b.created_at >= ${param_index}"
                params.append(start_date)
                param_index += 1

            query += " GROUP BY b.user_id"

            # Determine ordering based on metric
            order_by_clause = ""
            # Use aliases defined in the outer query's SELECT list
            if metric == 'net_units':
                order_by_clause = "ORDER BY net_units DESC"
            elif metric == 'roi':
                 order_by_clause = "ORDER BY CASE WHEN total_risked > 0 THEN (net_units / total_risked) ELSE -99999 END DESC" # Put 0 risked at bottom, handle division by zero
            elif metric == 'win_rate':
                 order_by_clause = "ORDER BY CASE WHEN (wins + losses) > 0 THEN (wins * 1.0 / (wins + losses)) ELSE -1 END DESC, wins DESC" # Break ties by wins
            elif metric == 'wins':
                 order_by_clause = "ORDER BY wins DESC"
            else: # Default to net_units if metric is invalid
                 order_by_clause = "ORDER BY net_units DESC"
                 logger.warning(f"Invalid leaderboard metric '{metric}', defaulting to net_units.")

            # Wrap the aggregation in a CTE to use calculated columns in ORDER BY
            final_query = f"""
                WITH UserStats AS (
                    {query}
                )
                SELECT
                    us.user_id,
                    -- Optionally join with users table here to get username if needed
                    -- u.username,
                    us.total_resolved_bets,
                    us.wins,
                    us.losses,
                    us.net_units,
                    us.total_risked,
                    CASE
                        WHEN (us.wins + us.losses) > 0 THEN (us.wins * 100.0 / (us.wins + us.losses))
                        ELSE 0.0
                    END as win_rate,
                    CASE
                        WHEN us.total_risked > 0 THEN (us.net_units / us.total_risked * 100.0)
                        ELSE 0.0
                    END as roi
                FROM UserStats us
                -- Optional JOIN: LEFT JOIN users u ON us.user_id = u.id
                WHERE us.total_resolved_bets > 0 -- Only show users with resolved bets? Optional filter.
                {order_by_clause} -- Apply ordering here
                LIMIT ${param_index}; -- Apply limit
            """
            params.append(limit)

            leaderboard_data = await self.db.fetch_all(final_query, *params)

            return leaderboard_data

        except Exception as e:
            logger.exception(f"Error getting leaderboard for guild {guild_id}: {e}")
            raise AnalyticsServiceError(f"Failed to get leaderboard: {str(e)}")
