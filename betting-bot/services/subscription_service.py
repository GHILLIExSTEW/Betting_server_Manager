import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SubscriptionService:
    def __init__(self, db_manager):
        self.db_manager = db_manager

    async def create_subscription(self, guild_id: int, user_id: int, plan_type: str = 'premium') -> bool:
        """Create a new subscription for a guild."""
        try:
            # Calculate subscription end date (30 days from now)
            end_date = datetime.utcnow() + timedelta(days=30)
            
            await self.db_manager.execute(
                """
                INSERT INTO subscriptions (
                    guild_id, user_id, plan_type, start_date, end_date, is_active
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """,
                guild_id, user_id, plan_type, datetime.utcnow(), end_date, True
            )

            # Update guild settings to mark as paid
            await self.db_manager.execute(
                "UPDATE guild_settings SET is_paid = TRUE WHERE guild_id = %s",
                guild_id
            )

            return True
        except Exception as e:
            logger.error(f"Error creating subscription for guild {guild_id}: {e}")
            return False

    async def get_subscription(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """Get the current subscription for a guild."""
        try:
            return await self.db_manager.fetch_one(
                """
                SELECT * FROM subscriptions 
                WHERE guild_id = %s AND is_active = TRUE 
                ORDER BY end_date DESC LIMIT 1
                """,
                guild_id
            )
        except Exception as e:
            logger.error(f"Error getting subscription for guild {guild_id}: {e}")
            return None

    async def cancel_subscription(self, guild_id: int) -> bool:
        """Cancel a guild's subscription."""
        try:
            # Mark current subscription as inactive
            await self.db_manager.execute(
                """
                UPDATE subscriptions 
                SET is_active = FALSE 
                WHERE guild_id = %s AND is_active = TRUE
                """,
                guild_id
            )

            # Update guild settings to mark as unpaid
            await self.db_manager.execute(
                "UPDATE guild_settings SET is_paid = FALSE WHERE guild_id = %s",
                guild_id
            )

            return True
        except Exception as e:
            logger.error(f"Error canceling subscription for guild {guild_id}: {e}")
            return False

    async def check_subscription_status(self, guild_id: int) -> bool:
        """Check if a guild has an active subscription."""
        try:
            subscription = await self.get_subscription(guild_id)
            if not subscription:
                return False

            # Check if subscription has expired
            if subscription['end_date'] < datetime.utcnow():
                await self.cancel_subscription(guild_id)
                return False

            return True
        except Exception as e:
            logger.error(f"Error checking subscription status for guild {guild_id}: {e}")
            return False

    async def renew_subscription(self, guild_id: int) -> bool:
        """Renew a guild's subscription."""
        try:
            subscription = await self.get_subscription(guild_id)
            if not subscription:
                return False

            # Calculate new end date (30 days from current end date)
            new_end_date = subscription['end_date'] + timedelta(days=30)
            
            await self.db_manager.execute(
                """
                UPDATE subscriptions 
                SET end_date = %s 
                WHERE guild_id = %s AND is_active = TRUE
                """,
                new_end_date, guild_id
            )

            return True
        except Exception as e:
            logger.error(f"Error renewing subscription for guild {guild_id}: {e}")
            return False

    async def get_subscription_details(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed subscription information for a guild."""
        try:
            subscription = await self.get_subscription(guild_id)
            if not subscription:
                return None

            # Calculate days remaining
            days_remaining = (subscription['end_date'] - datetime.utcnow()).days

            return {
                'plan_type': subscription['plan_type'],
                'start_date': subscription['start_date'],
                'end_date': subscription['end_date'],
                'days_remaining': max(0, days_remaining),
                'is_active': subscription['is_active']
            }
        except Exception as e:
            logger.error(f"Error getting subscription details for guild {guild_id}: {e}")
            return None 