from typing import Dict, Optional, List, Tuple
import logging
import hashlib
import secrets
from datetime import datetime, timedelta
from ..data.db_manager import DatabaseManager
from ..config.settings import Settings
import asyncio
import numpy as np
from ..data.cache_manager import CacheManager

logger = logging.getLogger(__name__)

class SecurityServiceError(Exception):
    """Base exception for security service errors."""
    pass

class SecurityService:
    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseManager()
        self.cache = CacheManager()
        self.running = False
        self._monitoring_task: Optional[asyncio.Task] = None
        self._suspicious_activities: Dict[int, List[Dict]] = {}  # guild_id -> activities
        self.settings = Settings()
        self.failed_attempts = {}  # Track failed login attempts
        self.lockout_duration = timedelta(minutes=15)  # Lockout duration after too many failed attempts

    async def start(self) -> None:
        """Start the security service."""
        try:
            self.running = True
            self._monitoring_task = asyncio.create_task(self._monitor_activities())
            logger.info("Security service started successfully")
        except Exception as e:
            logger.error(f"Error starting security service: {str(e)}")
            raise SecurityServiceError(f"Failed to start security service: {str(e)}")

    async def stop(self) -> None:
        """Stop the security service."""
        try:
            self.running = False
            if self._monitoring_task:
                self._monitoring_task.cancel()
            self._suspicious_activities.clear()
            logger.info("Security service stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping security service: {str(e)}")

    async def verify_bet_integrity(self, user_id: int, game_id: int, bet_amount: float, bet_type: str) -> bool:
        """Verify the integrity of a bet before it's placed."""
        try:
            # Check if user exists and is active
            user = await self.db.fetchrow(
                "SELECT is_active FROM users WHERE user_id = $1",
                user_id
            )
            if not user or not user['is_active']:
                return False

            # Check if game exists and is active
            game = await self.db.fetchrow(
                "SELECT is_active FROM games WHERE game_id = $1",
                game_id
            )
            if not game or not game['is_active']:
                return False

            # Check if bet type is valid
            valid_bet_types = await self.db.fetch(
                "SELECT bet_type FROM valid_bet_types WHERE game_id = $1",
                game_id
            )
            valid_types = [row['bet_type'] for row in valid_bet_types]
            if bet_type not in valid_types:
                return False

            return True

        except Exception as e:
            logger.error(f"Error verifying bet integrity: {str(e)}")
            return False

    async def detect_suspicious_activity(self, user_id: int) -> Dict:
        """Detect suspicious betting patterns."""
        try:
            # Get recent betting activity
            recent_bets = await self.db.fetch(
                """
                SELECT amount, created_at, outcome
                FROM bets
                WHERE user_id = $1
                AND created_at >= NOW() - INTERVAL '1 hour'
                ORDER BY created_at DESC
                """,
                user_id
            )

            if not recent_bets:
                return {"is_suspicious": False, "reason": None}

            # Check for rapid betting
            if len(recent_bets) > 20:  # More than 20 bets in an hour
                return {
                    "is_suspicious": True,
                    "reason": "excessive_betting_frequency"
                }

            # Check for unusual bet amounts
            amounts = [float(bet['amount']) for bet in recent_bets]
            avg_amount = sum(amounts) / len(amounts)
            if any(amount > avg_amount * 5 for amount in amounts):
                return {
                    "is_suspicious": True,
                    "reason": "unusual_bet_amounts"
                }

            return {"is_suspicious": False, "reason": None}

        except Exception as e:
            logger.error(f"Error detecting suspicious activity: {str(e)}")
            return {"is_suspicious": False, "reason": None}

    async def validate_game_result(self, game_id: int, result: str) -> bool:
        """Validate the integrity of a game result."""
        try:
            # Check if result matches valid outcomes
            valid_outcomes = await self.db.fetch(
                "SELECT outcome FROM valid_game_outcomes WHERE game_id = $1",
                game_id
            )
            valid_outcome_list = [row['outcome'] for row in valid_outcomes]
            
            if result not in valid_outcome_list:
                return False

            # Check if result hasn't been tampered with
            game = await self.db.fetchrow(
                """
                SELECT result_hash, result_timestamp
                FROM game_results
                WHERE game_id = $1
                """,
                game_id
            )

            if not game:
                return False

            # Verify result hash
            expected_hash = hashlib.sha256(
                f"{result}{game['result_timestamp']}".encode()
            ).hexdigest()

            return expected_hash == game['result_hash']

        except Exception as e:
            logger.error(f"Error validating game result: {str(e)}")
            return False

    async def log_security_event(self, user_id: int, event_type: str, details: str) -> None:
        """Log security-related events."""
        try:
            await self.db.execute(
                """
                INSERT INTO security_logs 
                (user_id, event_type, details, created_at)
                VALUES ($1, $2, $3, $4)
                """,
                user_id, event_type, details, datetime.utcnow()
            )
        except Exception as e:
            logger.error(f"Error logging security event: {str(e)}")

    async def check_user_restrictions(self, user_id: int) -> Dict:
        """Check if user has any active restrictions."""
        try:
            restrictions = await self.db.fetchrow(
                """
                SELECT restriction_type, reason, expires_at
                FROM user_restrictions
                WHERE user_id = $1
                AND expires_at > NOW()
                """,
                user_id
            )

            if not restrictions:
                return {"has_restrictions": False}

            return {
                "has_restrictions": True,
                "restriction_type": restrictions['restriction_type'],
                "reason": restrictions['reason'],
                "expires_at": restrictions['expires_at']
            }

        except Exception as e:
            logger.error(f"Error checking user restrictions: {str(e)}")
            return {"has_restrictions": False}

    async def check_bet_fraud(
        self,
        guild_id: int,
        user_id: int,
        bet_details: Dict
    ) -> Tuple[bool, Optional[str]]:
        """Check if a bet might be fraudulent."""
        try:
            # Get user's recent betting history
            recent_bets = await self.db.fetch(
                """
                SELECT * FROM bets
                WHERE guild_id = $1 AND user_id = $2
                AND created_at >= $3
                ORDER BY created_at DESC
                LIMIT 10
                """,
                guild_id, user_id, datetime.utcnow() - timedelta(hours=24)
            )

            if not recent_bets:
                return True, None

            # Check for rapid betting
            if len(recent_bets) >= 10:
                time_diff = recent_bets[0]['created_at'] - recent_bets[-1]['created_at']
                if time_diff.total_seconds() < 3600:  # 10 bets in less than an hour
                    return False, "Too many bets in a short period"

            # Check for unusual bet amounts
            avg_units = np.mean([bet['units'] for bet in recent_bets])
            std_units = np.std([bet['units'] for bet in recent_bets])
            if bet_details['units'] > avg_units + (3 * std_units):
                return False, "Unusually large bet amount"

            # Check for pattern betting
            if len(recent_bets) >= 5:
                same_league = all(bet['league'] == bet_details['league'] for bet in recent_bets[:5])
                same_type = all(bet['bet_type'] == bet_details['bet_type'] for bet in recent_bets[:5])
                if same_league and same_type:
                    return False, "Suspicious betting pattern detected"

            return True, None
        except Exception as e:
            logger.error(f"Error checking bet fraud: {str(e)}")
            return True, None

    async def check_user_activity(
        self,
        guild_id: int,
        user_id: int
    ) -> Tuple[bool, Optional[str]]:
        """Check if a user's activity is suspicious."""
        try:
            # Get user's recent activity
            recent_activity = await self.db.fetch(
                """
                SELECT * FROM user_activity
                WHERE guild_id = $1 AND user_id = $2
                AND created_at >= $3
                ORDER BY created_at DESC
                LIMIT 100
                """,
                guild_id, user_id, datetime.utcnow() - timedelta(days=7)
            )

            if not recent_activity:
                return True, None

            # Check for rapid command usage
            command_counts = {}
            for activity in recent_activity:
                command = activity['command']
                command_counts[command] = command_counts.get(command, 0) + 1

            for command, count in command_counts.items():
                if count > 50:  # More than 50 uses of a single command in 7 days
                    return False, f"Excessive use of command: {command}"

            # Check for unusual time patterns
            hours = [activity['created_at'].hour for activity in recent_activity]
            if len(set(hours)) > 20:  # Activity spread across too many hours
                return False, "Unusual activity pattern detected"

            return True, None
        except Exception as e:
            logger.error(f"Error checking user activity: {str(e)}")
            return True, None

    async def check_guild_activity(self, guild_id: int) -> Tuple[bool, Optional[str]]:
        """Check if a guild's activity is suspicious."""
        try:
            # Get guild's recent activity
            recent_activity = await self.db.fetch(
                """
                SELECT * FROM guild_activity
                WHERE guild_id = $1
                AND created_at >= $2
                ORDER BY created_at DESC
                LIMIT 1000
                """,
                guild_id, datetime.utcnow() - timedelta(days=7)
            )

            if not recent_activity:
                return True, None

            # Check for rapid user growth
            unique_users = len(set(activity['user_id'] for activity in recent_activity))
            if unique_users > 100:  # More than 100 unique users in 7 days
                return False, "Unusual user growth detected"

            # Check for command distribution
            command_counts = {}
            for activity in recent_activity:
                command = activity['command']
                command_counts[command] = command_counts.get(command, 0) + 1

            # Check if any command is used excessively
            total_commands = sum(command_counts.values())
            for command, count in command_counts.items():
                if count / total_commands > 0.5:  # More than 50% of all commands
                    return False, f"Excessive use of command: {command}"

            return True, None
        except Exception as e:
            logger.error(f"Error checking guild activity: {str(e)}")
            return True, None

    async def log_suspicious_activity(
        self,
        guild_id: int,
        user_id: int,
        activity_type: str,
        details: str
    ) -> None:
        """Log suspicious activity."""
        try:
            await self.db.execute(
                """
                INSERT INTO security_logs (
                    guild_id, user_id, activity_type, details, created_at
                )
                VALUES ($1, $2, $3, $4, $5)
                """,
                guild_id, user_id, activity_type, details, datetime.utcnow()
            )

            # Add to in-memory cache
            if guild_id not in self._suspicious_activities:
                self._suspicious_activities[guild_id] = []
            self._suspicious_activities[guild_id].append({
                "user_id": user_id,
                "activity_type": activity_type,
                "details": details,
                "timestamp": datetime.utcnow()
            })
        except Exception as e:
            logger.error(f"Error logging suspicious activity: {str(e)}")

    async def get_suspicious_activities(
        self,
        guild_id: int,
        limit: int = 10
    ) -> List[Dict]:
        """Get recent suspicious activities for a guild."""
        try:
            return await self.db.fetch(
                """
                SELECT * FROM security_logs
                WHERE guild_id = $1
                ORDER BY created_at DESC
                LIMIT $2
                """,
                guild_id, limit
            )
        except Exception as e:
            logger.error(f"Error getting suspicious activities: {str(e)}")
            return []

    async def _monitor_activities(self) -> None:
        """Monitor activities for suspicious patterns."""
        while self.running:
            try:
                # Get all active guilds
                guilds = await self.db.fetch(
                    "SELECT guild_id FROM guild_settings WHERE is_active = true"
                )

                for guild in guilds:
                    guild_id = guild['guild_id']

                    # Check guild activity
                    is_valid, reason = await self.check_guild_activity(guild_id)
                    if not is_valid:
                        await self.log_suspicious_activity(
                            guild_id,
                            0,  # System user
                            "guild_activity",
                            f"Suspicious guild activity: {reason}"
                        )

                    # Get recent users
                    users = await self.db.fetch(
                        """
                        SELECT DISTINCT user_id FROM user_activity
                        WHERE guild_id = $1
                        AND created_at >= $2
                        """,
                        guild_id, datetime.utcnow() - timedelta(hours=24)
                    )

                    for user in users:
                        user_id = user['user_id']

                        # Check user activity
                        is_valid, reason = await self.check_user_activity(guild_id, user_id)
                        if not is_valid:
                            await self.log_suspicious_activity(
                                guild_id,
                                user_id,
                                "user_activity",
                                f"Suspicious user activity: {reason}"
                            )

                await asyncio.sleep(300)  # Check every 5 minutes
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                await asyncio.sleep(300) 