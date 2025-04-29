import asyncio
import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import stripe
from ..data.db_manager import DatabaseManager
from ..data.cache_manager import CacheManager

logger = logging.getLogger(__name__)

class PaymentServiceError(Exception):
    """Base exception for payment service errors."""
    pass

class PaymentService:
    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseManager()
        self.cache = CacheManager()
        self.running = False
        self._subscription_check_task: Optional[asyncio.Task] = None
        self._payment_processing_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the payment service."""
        try:
            self.running = True
            self._subscription_check_task = asyncio.create_task(self._check_subscriptions())
            self._payment_processing_task = asyncio.create_task(self._process_payments())
            logger.info("Payment service started successfully")
        except Exception as e:
            logger.error(f"Error starting payment service: {str(e)}")
            raise PaymentServiceError(f"Failed to start payment service: {str(e)}")

    async def stop(self) -> None:
        """Stop the payment service."""
        try:
            self.running = False
            if self._subscription_check_task:
                self._subscription_check_task.cancel()
            if self._payment_processing_task:
                self._payment_processing_task.cancel()
            logger.info("Payment service stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping payment service: {str(e)}")

    async def create_subscription(
        self,
        guild_id: int,
        user_id: int,
        plan_id: str,
        payment_method_id: str
    ) -> Dict:
        """Create a new subscription."""
        try:
            # Create Stripe customer if not exists
            customer = await self._get_or_create_customer(guild_id, user_id)

            # Create subscription
            subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[{"price": plan_id}],
                payment_behavior="default_incomplete",
                payment_settings={"save_default_payment_method": "on_subscription"},
                expand=["latest_invoice.payment_intent"]
            )

            # Store subscription in database
            await self.db.execute(
                """
                INSERT INTO subscriptions (
                    guild_id, user_id, stripe_customer_id, stripe_subscription_id,
                    plan_id, status, current_period_start, current_period_end
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                guild_id,
                user_id,
                customer.id,
                subscription.id,
                plan_id,
                subscription.status,
                datetime.fromtimestamp(subscription.current_period_start),
                datetime.fromtimestamp(subscription.current_period_end)
            )

            return {
                "subscription_id": subscription.id,
                "client_secret": subscription.latest_invoice.payment_intent.client_secret
            }
        except Exception as e:
            logger.error(f"Error creating subscription: {str(e)}")
            raise PaymentServiceError(f"Failed to create subscription: {str(e)}")

    async def cancel_subscription(self, subscription_id: str) -> bool:
        """Cancel a subscription."""
        try:
            # Cancel in Stripe
            stripe.Subscription.delete(subscription_id)

            # Update database
            await self.db.execute(
                """
                UPDATE subscriptions
                SET status = 'canceled', canceled_at = $1
                WHERE stripe_subscription_id = $2
                """,
                datetime.utcnow(),
                subscription_id
            )

            return True
        except Exception as e:
            logger.error(f"Error canceling subscription: {str(e)}")
            return False

    async def update_payment_method(
        self,
        guild_id: int,
        user_id: int,
        payment_method_id: str
    ) -> bool:
        """Update the payment method for a subscription."""
        try:
            # Get customer
            customer = await self._get_customer(guild_id, user_id)
            if not customer:
                return False

            # Attach payment method to customer
            stripe.PaymentMethod.attach(payment_method_id, customer=customer.id)

            # Set as default payment method
            stripe.Customer.modify(
                customer.id,
                invoice_settings={"default_payment_method": payment_method_id}
            )

            return True
        except Exception as e:
            logger.error(f"Error updating payment method: {str(e)}")
            return False

    async def get_subscription(self, guild_id: int) -> Optional[Dict]:
        """Get subscription details for a guild."""
        try:
            subscription = await self.db.fetch_one(
                """
                SELECT * FROM subscriptions
                WHERE guild_id = $1 AND status = 'active'
                ORDER BY created_at DESC
                LIMIT 1
                """,
                guild_id
            )
            return dict(subscription) if subscription else None
        except Exception as e:
            logger.error(f"Error getting subscription: {str(e)}")
            return None

    async def _get_or_create_customer(self, guild_id: int, user_id: int) -> stripe.Customer:
        """Get or create a Stripe customer."""
        try:
            # Check if customer exists
            customer = await self._get_customer(guild_id, user_id)
            if customer:
                return customer

            # Create new customer
            customer = stripe.Customer.create(
                metadata={
                    "guild_id": str(guild_id),
                    "user_id": str(user_id)
                }
            )

            # Store in database
            await self.db.execute(
                """
                INSERT INTO stripe_customers (guild_id, user_id, stripe_customer_id)
                VALUES ($1, $2, $3)
                """,
                guild_id, user_id, customer.id
            )

            return customer
        except Exception as e:
            logger.error(f"Error getting/creating customer: {str(e)}")
            raise PaymentServiceError(f"Failed to get/create customer: {str(e)}")

    async def _get_customer(self, guild_id: int, user_id: int) -> Optional[stripe.Customer]:
        """Get a Stripe customer."""
        try:
            customer_id = await self.db.fetchval(
                """
                SELECT stripe_customer_id FROM stripe_customers
                WHERE guild_id = $1 AND user_id = $2
                """,
                guild_id, user_id
            )
            if customer_id:
                return stripe.Customer.retrieve(customer_id)
            return None
        except Exception as e:
            logger.error(f"Error getting customer: {str(e)}")
            return None

    async def _check_subscriptions(self) -> None:
        """Periodically check subscription status."""
        while self.running:
            try:
                # Get subscriptions expiring soon
                expiring_soon = await self.db.fetch(
                    """
                    SELECT * FROM subscriptions
                    WHERE status = 'active'
                    AND current_period_end <= $1
                    """,
                    datetime.utcnow() + timedelta(days=7)
                )

                for sub in expiring_soon:
                    # Check Stripe status
                    stripe_sub = stripe.Subscription.retrieve(sub['stripe_subscription_id'])
                    if stripe_sub.status != sub['status']:
                        # Update database
                        await self.db.execute(
                            """
                            UPDATE subscriptions
                            SET status = $1, current_period_end = $2
                            WHERE stripe_subscription_id = $3
                            """,
                            stripe_sub.status,
                            datetime.fromtimestamp(stripe_sub.current_period_end),
                            stripe_sub.id
                        )

                        # Update guild premium status
                        await self.db.execute(
                            """
                            UPDATE guild_settings
                            SET is_premium = $1
                            WHERE guild_id = $2
                            """,
                            stripe_sub.status == 'active',
                            sub['guild_id']
                        )

                await asyncio.sleep(3600)  # Check every hour
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error checking subscriptions: {str(e)}")
                await asyncio.sleep(3600)

    async def _process_payments(self) -> None:
        """Process pending payments."""
        while self.running:
            try:
                # Get pending payments
                pending_payments = await self.db.fetch(
                    """
                    SELECT * FROM payments
                    WHERE status = 'pending'
                    ORDER BY created_at ASC
                    LIMIT 10
                    """
                )

                for payment in pending_payments:
                    try:
                        # Process payment in Stripe
                        intent = stripe.PaymentIntent.retrieve(payment['stripe_payment_intent_id'])
                        if intent.status == 'succeeded':
                            # Update payment status
                            await self.db.execute(
                                """
                                UPDATE payments
                                SET status = 'completed', completed_at = $1
                                WHERE payment_id = $2
                                """,
                                datetime.utcnow(),
                                payment['payment_id']
                            )

                            # Update subscription if applicable
                            if payment['subscription_id']:
                                await self.db.execute(
                                    """
                                    UPDATE subscriptions
                                    SET status = 'active'
                                    WHERE subscription_id = $1
                                    """,
                                    payment['subscription_id']
                                )
                    except Exception as e:
                        logger.error(f"Error processing payment {payment['payment_id']}: {str(e)}")
                        # Mark payment as failed
                        await self.db.execute(
                            """
                            UPDATE payments
                            SET status = 'failed', failed_at = $1
                            WHERE payment_id = $2
                            """,
                            datetime.utcnow(),
                            payment['payment_id']
                        )

                await asyncio.sleep(300)  # Process every 5 minutes
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in payment processing loop: {str(e)}")
                await asyncio.sleep(300) 