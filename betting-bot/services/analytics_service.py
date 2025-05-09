# betting-bot/services/analytics_service.py

import discord
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone

try:
    from ..utils.errors import AnalyticsServiceError
except ImportError:
    from utils.errors import AnalyticsServiceError

logger = logging.getLogger(__name__)


class AnalyticsService:
    def __init__(self, bot, db_manager):
        self.bot = bot
        self.db = db_manager
        logger.info("AnalyticsService initialized") # Added log for consistency

    async def start(self): # ### ADDED THIS METHOD ###
        """Start the AnalyticsService and perform any necessary setup."""
        logger.info("AnalyticsService started successfully.")
        # Add any specific startup logic for analytics here if needed

    async def stop(self): # ### ADDED THIS METHOD ###
        """Stop the AnalyticsService and perform any necessary cleanup."""
        logger.info("AnalyticsService stopped.")
        # Add any specific cleanup logic here if needed

    async def get_user_stats(self, guild_id: int, user_id: int) -> Dict[str, Any]:
        # ... (rest of your existing method)
        try:
            stats = await self.db.fetch_one("""
                SELECT
                    COUNT(b.bet_serial) as total_bets,
                    SUM(CASE WHEN b.status = 'won' THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN b.status = 'lost' THEN 1 ELSE 0 END) as losses,
                    SUM(CASE WHEN b.status = 'push' THEN 1 ELSE 0 END) as pushes,
                    COALESCE(SUM(ur.result_value), 0.0) as net_units
                FROM bets b
                LEFT JOIN unit_records ur ON b.bet_serial = ur.bet_serial
                WHERE b.guild_id = %s AND b.user_id = %s
                AND b.status IN ('won', 'lost', 'push')
            """, guild_id, user_id)

            if not stats or (stats.get('total_bets') or 0) == 0:
                return {'total_bets': 0, 'wins': 0, 'losses': 0, 'pushes': 0, 'win_rate': 0.0, 'net_units': 0.0, 'roi': 0.0}

            wins = stats.get('wins') or 0
            losses = stats.get('losses') or 0
            total_bets = stats.get('total_bets') or 0
            net_units = stats.get('net_units') or 0.0

            total_resolved_for_winrate = wins + losses
            win_rate = (wins / total_resolved_for_winrate * 100) if total_resolved_for_winrate > 0 else 0.0

            # Assuming 'stake' is the column name for units risked in the 'bets' table.
            # The original query in your files used 'units' for stake, and 'result_value' for payout in unit_records.
            # For ROI, we need total units risked (staked).
            total_risked_result = await self.db.fetch_one("""
                SELECT COALESCE(SUM(units), 0) as total_risked 
                FROM bets
                WHERE guild_id = %s AND user_id = %s
                AND status IN ('won', 'lost', 'push')
            """, guild_id, user_id)
            total_risked = total_risked_result.get('total_risked') or 0 if total_risked_result else 0

            roi = (net_units / total_risked * 100.0) if total_risked > 0 else 0.0

            return {
                'total_bets': total_bets, 'wins': wins, 'losses': losses,
                'pushes': stats.get('pushes') or 0,
                'win_rate': win_rate, 'net_units': net_units, 'roi': roi
            }
        except Exception as e:
            logger.exception(f"Error getting user stats for user {user_id} in guild {guild_id}: {e}")
            raise AnalyticsServiceError(f"Failed to get user stats: {str(e)}")

    async def get_guild_stats(self, guild_id: int) -> Dict[str, Any]:
        # ... (rest of your existing method)
        try:
            stats = await self.db.fetch_one("""
                SELECT
                    COUNT(b.bet_serial) as total_bets,
                    SUM(CASE WHEN b.status = 'won' THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN b.status = 'lost' THEN 1 ELSE 0 END) as losses,
                    SUM(CASE WHEN b.status = 'push' THEN 1 ELSE 0 END) as pushes,
                    COALESCE(SUM(ur.result_value), 0.0) as net_units,
                    COUNT(DISTINCT b.user_id) as total_cappers
                FROM bets b
                LEFT JOIN unit_records ur ON b.bet_serial = ur.bet_serial
                WHERE b.guild_id = %s
                AND b.status IN ('won', 'lost', 'push')
            """, guild_id)

            if not stats or (stats.get('total_bets') or 0) == 0:
                return {'total_bets': 0, 'wins': 0, 'losses': 0, 'pushes': 0, 'win_rate': 0.0, 'net_units': 0.0, 'total_cappers': 0, 'roi': 0.0}

            wins = stats.get('wins') or 0
            losses = stats.get('losses') or 0
            total_bets = stats.get('total_bets') or 0
            net_units = stats.get('net_units') or 0.0

            total_resolved_for_winrate = wins + losses
            win_rate = (wins / total_resolved_for_winrate * 100.0) if total_resolved_for_winrate > 0 else 0.0

            total_risked_result = await self.db.fetch_one("""
                SELECT COALESCE(SUM(units), 0) as total_risked
                FROM bets
                WHERE guild_id = %s AND status IN ('won', 'lost', 'push')
            """, guild_id)
            total_risked = total_risked_result.get('total_risked') or 0 if total_risked_result else 0
            roi = (net_units / total_risked * 100.0) if total_risked > 0 else 0.0

            return {
                'total_bets': total_bets, 'wins': wins, 'losses': losses,
                'pushes': stats.get('pushes') or 0, 'win_rate': win_rate,
                'net_units': net_units, 'total_cappers': stats.get('total_cappers') or 0, 'roi': roi
            }
        except Exception as e:
            logger.exception(f"Error getting guild stats for guild {guild_id}: {e}")
            raise AnalyticsServiceError(f"Failed to get guild stats: {str(e)}")

    async def get_leaderboard(
        self,
        guild_id: int,
        timeframe: str = 'weekly',
        limit: int = 10,
        metric: str = 'net_units'
    ) -> List[Dict[str, Any]]:
        # ... (rest of your existing method)
        try:
            now = datetime.now(timezone.utc)
            start_date = None
            if timeframe == 'daily':
                start_date = now - timedelta(days=1)
            elif timeframe == 'weekly':
                start_date = now - timedelta(weeks=1)
            elif timeframe == 'monthly':
                start_date = now - timedelta(days=30) # Approx month
            elif timeframe == 'yearly':
                start_date = datetime(now.year, 1, 1, tzinfo=timezone.utc)
            # Add 'all_time' if needed, where start_date would be None

            query_parts = [
                """
                SELECT
                    b.user_id,
                    COALESCE(u.username, CONCAT('User ', b.user_id)) as username,
                    SUM(CASE WHEN b.status IN ('won', 'lost', 'push') THEN 1 ELSE 0 END) as total_resolved_bets,
                    SUM(CASE WHEN b.status = 'won' THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN b.status = 'lost' THEN 1 ELSE 0 END) as losses,
                    COALESCE(SUM(ur.result_value), 0.0) as net_units,
                    COALESCE(SUM(CASE WHEN b.status IN ('won', 'lost', 'push') THEN b.units ELSE 0 END), 0) as total_risked 
                FROM bets b
                LEFT JOIN unit_records ur ON b.bet_serial = ur.bet_serial
                LEFT JOIN users u ON b.user_id = u.user_id
                WHERE b.guild_id = %s AND b.status IN ('won', 'lost', 'push')
                """
            ]
            params: List[Any] = [guild_id]

            if start_date:
                # Assuming 'created_at' in 'bets' table marks when bet was placed/resolved for timeframe filtering.
                # If 'unit_records.created_at' is when it was resolved, adjust accordingly.
                query_parts.append("AND b.updated_at >= %s") # Filter by when bet was last updated (likely resolved time)
                params.append(start_date)

            query_parts.append("GROUP BY b.user_id, u.username")

            # Construct the main query part
            main_query = " ".join(query_parts)

            # Define order by logic
            order_by_clause = ""
            if metric == 'net_units':
                order_by_clause = "ORDER BY net_units DESC"
            elif metric == 'roi':
                # Ensure total_risked is not zero to avoid division by zero for ROI calculation
                order_by_clause = "ORDER BY CASE WHEN total_risked > 0 THEN (net_units / total_risked) ELSE -999999 END DESC, net_units DESC"
            elif metric == 'win_rate':
                order_by_clause = "ORDER BY CASE WHEN (wins + losses) > 0 THEN (wins * 1.0 / (wins + losses)) ELSE -1 END DESC, wins DESC"
            elif metric == 'wins':
                order_by_clause = "ORDER BY wins DESC"
            else: # Default to net_units
                order_by_clause = "ORDER BY net_units DESC"
                logger.warning("Invalid leaderboard metric '%s', defaulting to net_units.", metric)

            final_query = f"""
                WITH UserAggregatedStats AS (
                    {main_query}
                )
                SELECT
                    us.user_id,
                    us.username,
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
                FROM UserAggregatedStats us
                WHERE us.total_resolved_bets > 0 
                {order_by_clause}
                LIMIT %s
            """
            params.append(limit)

            leaderboard_data = await self.db.fetch_all(final_query, *params)
            return leaderboard_data

        except Exception as e:
            logger.exception(f"Error getting leaderboard for guild {guild_id}, timeframe {timeframe}, metric {metric}: {e}")
            raise AnalyticsServiceError(f"Failed to get leaderboard: {str(e)}")
