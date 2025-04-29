from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging
from decimal import Decimal
from ..data.db_manager import DatabaseManager
from ..config.settings import Settings
import asyncio
import numpy as np
from ..data.cache_manager import CacheManager

logger = logging.getLogger(__name__)

class AnalyticsServiceError(Exception):
    """Base exception for analytics service errors."""
    pass

class AnalyticsService:
    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseManager()
        self.cache = CacheManager()
        self.running = False
        self._update_task: Optional[asyncio.Task] = None
        self.settings = Settings()

    async def start(self) -> None:
        """Start the analytics service."""
        try:
            self.running = True
            self._update_task = asyncio.create_task(self._update_analytics())
            logger.info("Analytics service started successfully")
        except Exception as e:
            logger.error(f"Error starting analytics service: {str(e)}")
            raise AnalyticsServiceError(f"Failed to start analytics service: {str(e)}")

    async def stop(self) -> None:
        """Stop the analytics service."""
        try:
            self.running = False
            if self._update_task:
                self._update_task.cancel()
            logger.info("Analytics service stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping analytics service: {str(e)}")

    async def get_user_betting_stats(self, user_id: int, days: int = 30) -> Dict:
        """Get user's betting statistics for the specified period."""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            stats = await self.db.fetchrow(
                """
                SELECT 
                    COUNT(*) as total_bets,
                    SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN outcome = 'loss' THEN 1 ELSE 0 END) as losses,
                    SUM(amount) as total_amount_bet,
                    SUM(CASE WHEN outcome = 'win' THEN amount * odds ELSE 0 END) as total_winnings,
                    AVG(odds) as average_odds
                FROM bets
                WHERE user_id = $1 AND created_at >= $2
                """,
                user_id, start_date
            )

            if not stats:
                return {
                    "total_bets": 0,
                    "wins": 0,
                    "losses": 0,
                    "total_amount_bet": Decimal('0'),
                    "total_winnings": Decimal('0'),
                    "average_odds": Decimal('0'),
                    "win_rate": 0.0
                }

            stats_dict = dict(stats)
            total_bets = stats_dict['total_bets']
            stats_dict['win_rate'] = (stats_dict['wins'] / total_bets * 100) if total_bets > 0 else 0.0
            return stats_dict

        except Exception as e:
            logger.error(f"Error getting user betting stats: {str(e)}")
            raise

    async def get_popular_bets(self, limit: int = 10) -> List[Dict]:
        """Get most popular betting options."""
        try:
            popular_bets = await self.db.fetch(
                """
                SELECT 
                    b.game_type,
                    b.bet_type,
                    COUNT(*) as bet_count,
                    SUM(b.amount) as total_amount,
                    AVG(b.odds) as average_odds
                FROM bets b
                GROUP BY b.game_type, b.bet_type
                ORDER BY bet_count DESC
                LIMIT $1
                """,
                limit
            )
            return [dict(bet) for bet in popular_bets]
        except Exception as e:
            logger.error(f"Error getting popular bets: {str(e)}")
            raise

    async def get_daily_revenue(self, days: int = 7) -> List[Dict]:
        """Get daily revenue statistics."""
        try:
            revenue = await self.db.fetch(
                """
                SELECT 
                    DATE(created_at) as date,
                    SUM(CASE WHEN outcome = 'win' THEN -amount * (odds - 1) ELSE amount END) as revenue
                FROM bets
                WHERE created_at >= NOW() - INTERVAL '$1 days'
                GROUP BY DATE(created_at)
                ORDER BY date DESC
                """,
                days
            )
            return [dict(day) for day in revenue]
        except Exception as e:
            logger.error(f"Error getting daily revenue: {str(e)}")
            raise

    async def get_user_activity_trends(self, user_id: int, days: int = 30) -> List[Dict]:
        """Get user's betting activity trends."""
        try:
            trends = await self.db.fetch(
                """
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as bet_count,
                    SUM(amount) as total_amount,
                    SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) as wins
                FROM bets
                WHERE user_id = $1 AND created_at >= NOW() - INTERVAL '$2 days'
                GROUP BY DATE(created_at)
                ORDER BY date DESC
                """,
                user_id, days
            )
            return [dict(trend) for trend in trends]
        except Exception as e:
            logger.error(f"Error getting user activity trends: {str(e)}")
            raise

    async def get_risk_analysis(self, user_id: int) -> Dict:
        """Analyze user's betting risk profile."""
        try:
            analysis = await self.db.fetchrow(
                """
                SELECT 
                    AVG(amount) as average_bet_amount,
                    MAX(amount) as max_bet_amount,
                    STDDEV(amount) as bet_amount_stddev,
                    COUNT(DISTINCT game_type) as unique_games_played,
                    COUNT(*) as total_bets
                FROM bets
                WHERE user_id = $1
                """,
                user_id
            )

            if not analysis:
                return {
                    "risk_level": "unknown",
                    "average_bet_amount": Decimal('0'),
                    "max_bet_amount": Decimal('0'),
                    "bet_amount_stddev": Decimal('0'),
                    "unique_games_played": 0,
                    "total_bets": 0
                }

            analysis_dict = dict(analysis)
            
            # Calculate risk level based on betting patterns
            avg_bet = float(analysis_dict['average_bet_amount'])
            max_bet = float(analysis_dict['max_bet_amount'])
            stddev = float(analysis_dict['bet_amount_stddev'])
            
            if max_bet > avg_bet * 5 or stddev > avg_bet * 2:
                risk_level = "high"
            elif max_bet > avg_bet * 3 or stddev > avg_bet:
                risk_level = "medium"
            else:
                risk_level = "low"
            
            analysis_dict['risk_level'] = risk_level
            return analysis_dict

        except Exception as e:
            logger.error(f"Error getting risk analysis: {str(e)}")
            raise

    async def get_user_stats(self, guild_id: int, user_id: int) -> Dict:
        """Get detailed statistics for a user."""
        try:
            # Get basic stats
            stats = await self.db.fetch_one(
                """
                SELECT
                    COUNT(*) as total_bets,
                    SUM(CASE WHEN result = 'won' THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN result = 'lost' THEN 1 ELSE 0 END) as losses,
                    SUM(CASE WHEN result = 'push' THEN 1 ELSE 0 END) as pushes,
                    SUM(units) as total_units,
                    SUM(CASE WHEN result = 'won' THEN units ELSE -units END) as net_units
                FROM bets
                WHERE guild_id = $1 AND user_id = $2
                """,
                guild_id, user_id
            )

            if not stats:
                return {}

            # Calculate win percentage
            total_bets = stats['total_bets']
            if total_bets > 0:
                win_percentage = (stats['wins'] / total_bets) * 100
            else:
                win_percentage = 0

            # Get recent performance
            recent_stats = await self.db.fetch_one(
                """
                SELECT
                    COUNT(*) as total_bets,
                    SUM(CASE WHEN result = 'won' THEN units ELSE -units END) as net_units
                FROM bets
                WHERE guild_id = $1 AND user_id = $2
                AND created_at >= $3
                """,
                guild_id, user_id, datetime.utcnow() - timedelta(days=30)
            )

            return {
                "total_bets": stats['total_bets'],
                "wins": stats['wins'],
                "losses": stats['losses'],
                "pushes": stats['pushes'],
                "win_percentage": round(win_percentage, 2),
                "total_units": round(stats['total_units'], 2),
                "net_units": round(stats['net_units'], 2),
                "roi": round((stats['net_units'] / stats['total_units'] * 100) if stats['total_units'] > 0 else 0, 2),
                "recent_bets": recent_stats['total_bets'],
                "recent_net_units": round(recent_stats['net_units'], 2)
            }
        except Exception as e:
            logger.error(f"Error getting user stats: {str(e)}")
            return {}

    async def get_league_stats(self, guild_id: int, league: str) -> Dict:
        """Get statistics for a specific league."""
        try:
            # Get league stats
            stats = await self.db.fetch_one(
                """
                SELECT
                    COUNT(*) as total_bets,
                    SUM(CASE WHEN result = 'won' THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN result = 'lost' THEN 1 ELSE 0 END) as losses,
                    SUM(CASE WHEN result = 'push' THEN 1 ELSE 0 END) as pushes,
                    SUM(units) as total_units,
                    SUM(CASE WHEN result = 'won' THEN units ELSE -units END) as net_units
                FROM bets
                WHERE guild_id = $1 AND league = $2
                """,
                guild_id, league
            )

            if not stats:
                return {}

            # Calculate win percentage
            total_bets = stats['total_bets']
            if total_bets > 0:
                win_percentage = (stats['wins'] / total_bets) * 100
            else:
                win_percentage = 0

            # Get most successful bet types
            bet_types = await self.db.fetch(
                """
                SELECT
                    bet_type,
                    COUNT(*) as total_bets,
                    SUM(CASE WHEN result = 'won' THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN result = 'won' THEN units ELSE -units END) as net_units
                FROM bets
                WHERE guild_id = $1 AND league = $2
                GROUP BY bet_type
                ORDER BY net_units DESC
                LIMIT 5
                """,
                guild_id, league
            )

            return {
                "total_bets": stats['total_bets'],
                "wins": stats['wins'],
                "losses": stats['losses'],
                "pushes": stats['pushes'],
                "win_percentage": round(win_percentage, 2),
                "total_units": round(stats['total_units'], 2),
                "net_units": round(stats['net_units'], 2),
                "roi": round((stats['net_units'] / stats['total_units'] * 100) if stats['total_units'] > 0 else 0, 2),
                "best_bet_types": [
                    {
                        "type": bt['bet_type'],
                        "total_bets": bt['total_bets'],
                        "wins": bt['wins'],
                        "net_units": round(bt['net_units'], 2)
                    }
                    for bt in bet_types
                ]
            }
        except Exception as e:
            logger.error(f"Error getting league stats: {str(e)}")
            return {}

    async def get_guild_stats(self, guild_id: int) -> Dict:
        """Get overall statistics for a guild."""
        try:
            # Get guild stats
            stats = await self.db.fetch_one(
                """
                SELECT
                    COUNT(*) as total_bets,
                    SUM(CASE WHEN result = 'won' THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN result = 'lost' THEN 1 ELSE 0 END) as losses,
                    SUM(CASE WHEN result = 'push' THEN 1 ELSE 0 END) as pushes,
                    SUM(units) as total_units,
                    SUM(CASE WHEN result = 'won' THEN units ELSE -units END) as net_units
                FROM bets
                WHERE guild_id = $1
                """,
                guild_id
            )

            if not stats:
                return {}

            # Calculate win percentage
            total_bets = stats['total_bets']
            if total_bets > 0:
                win_percentage = (stats['wins'] / total_bets) * 100
            else:
                win_percentage = 0

            # Get top performers
            top_performers = await self.db.fetch(
                """
                SELECT
                    user_id,
                    COUNT(*) as total_bets,
                    SUM(CASE WHEN result = 'won' THEN units ELSE -units END) as net_units
                FROM bets
                WHERE guild_id = $1
                GROUP BY user_id
                ORDER BY net_units DESC
                LIMIT 5
                """,
                guild_id
            )

            # Get league performance
            league_stats = await self.db.fetch(
                """
                SELECT
                    league,
                    COUNT(*) as total_bets,
                    SUM(CASE WHEN result = 'won' THEN units ELSE -units END) as net_units
                FROM bets
                WHERE guild_id = $1
                GROUP BY league
                ORDER BY net_units DESC
                """,
                guild_id
            )

            return {
                "total_bets": stats['total_bets'],
                "wins": stats['wins'],
                "losses": stats['losses'],
                "pushes": stats['pushes'],
                "win_percentage": round(win_percentage, 2),
                "total_units": round(stats['total_units'], 2),
                "net_units": round(stats['net_units'], 2),
                "roi": round((stats['net_units'] / stats['total_units'] * 100) if stats['total_units'] > 0 else 0, 2),
                "top_performers": [
                    {
                        "user_id": tp['user_id'],
                        "total_bets": tp['total_bets'],
                        "net_units": round(tp['net_units'], 2)
                    }
                    for tp in top_performers
                ],
                "league_performance": [
                    {
                        "league": ls['league'],
                        "total_bets": ls['total_bets'],
                        "net_units": round(ls['net_units'], 2)
                    }
                    for ls in league_stats
                ]
            }
        except Exception as e:
            logger.error(f"Error getting guild stats: {str(e)}")
            return {}

    async def get_trend_analysis(self, guild_id: int, days: int = 30) -> Dict:
        """Get trend analysis for a guild."""
        try:
            # Get daily performance
            daily_stats = await self.db.fetch(
                """
                SELECT
                    DATE(created_at) as date,
                    COUNT(*) as total_bets,
                    SUM(CASE WHEN result = 'won' THEN units ELSE -units END) as net_units
                FROM bets
                WHERE guild_id = $1
                AND created_at >= $2
                GROUP BY DATE(created_at)
                ORDER BY DATE(created_at)
                """,
                guild_id, datetime.utcnow() - timedelta(days=days)
            )

            if not daily_stats:
                return {}

            # Calculate cumulative performance
            dates = []
            daily_net_units = []
            cumulative_net_units = []
            current_cumulative = 0

            for stat in daily_stats:
                dates.append(stat['date'])
                daily_net_units.append(stat['net_units'])
                current_cumulative += stat['net_units']
                cumulative_net_units.append(current_cumulative)

            # Calculate moving average
            window_size = 7
            moving_avg = []
            for i in range(len(daily_net_units)):
                if i < window_size - 1:
                    moving_avg.append(None)
                else:
                    avg = sum(daily_net_units[i-window_size+1:i+1]) / window_size
                    moving_avg.append(avg)

            return {
                "dates": [d.isoformat() for d in dates],
                "daily_net_units": [round(u, 2) for u in daily_net_units],
                "cumulative_net_units": [round(u, 2) for u in cumulative_net_units],
                "moving_average": [round(u, 2) if u is not None else None for u in moving_avg],
                "total_period_units": round(sum(daily_net_units), 2),
                "average_daily_units": round(sum(daily_net_units) / len(daily_net_units), 2)
            }
        except Exception as e:
            logger.error(f"Error getting trend analysis: {str(e)}")
            return {}

    async def _update_analytics(self) -> None:
        """Periodically update analytics data."""
        while self.running:
            try:
                # Get all active guilds
                guilds = await self.db.fetch(
                    "SELECT guild_id FROM guild_settings WHERE is_active = true"
                )

                for guild in guilds:
                    guild_id = guild['guild_id']
                    
                    # Update user stats
                    users = await self.db.fetch(
                        """
                        SELECT DISTINCT user_id FROM bets
                        WHERE guild_id = $1
                        """,
                        guild_id
                    )

                    for user in users:
                        user_id = user['user_id']
                        stats = await self.get_user_stats(guild_id, user_id)
                        await self.cache.set(
                            f"analytics:user:{guild_id}:{user_id}",
                            stats,
                            ttl=3600  # Cache for 1 hour
                        )

                    # Update league stats
                    leagues = await self.db.fetch(
                        """
                        SELECT DISTINCT league FROM bets
                        WHERE guild_id = $1
                        """,
                        guild_id
                    )

                    for league in leagues:
                        league_name = league['league']
                        stats = await self.get_league_stats(guild_id, league_name)
                        await self.cache.set(
                            f"analytics:league:{guild_id}:{league_name}",
                            stats,
                            ttl=3600
                        )

                    # Update guild stats
                    stats = await self.get_guild_stats(guild_id)
                    await self.cache.set(
                        f"analytics:guild:{guild_id}",
                        stats,
                        ttl=3600
                    )

                    # Update trend analysis
                    trends = await self.get_trend_analysis(guild_id)
                    await self.cache.set(
                        f"analytics:trends:{guild_id}",
                        trends,
                        ttl=3600
                    )

                await asyncio.sleep(3600)  # Update every hour
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in analytics update loop: {str(e)}")
                await asyncio.sleep(3600) 