# betting-bot/services/bet_service.py

"""Service for managing bets and handling bet-related reactions."""

import logging
from typing import Dict, List, Optional, Union
from datetime import datetime, timezone
import uuid
import discord
import json

try:
    from utils.errors import BetServiceError, ValidationError
except ImportError:
    from utils.errors import BetServiceError, ValidationError

logger = logging.getLogger(__name__)

class BetService:
    def __init__(self, bot, db_manager):
        """
        Initialize the BetService.

        Args:
            bot: The Discord bot instance.
            db_manager: The database manager instance.
        """
        self.bot = bot
        self.db_manager = db_manager
        self.pending_reactions: Dict[int, Dict[str, Union[str, int, List]]] = {}
        logger.info("BetService initialized")

    async def start(self):
        """Start the BetService and perform any necessary setup."""
        logger.info("Starting BetService")
        try:
            # Example: Check for expired pending bets
            await self.cleanup_expired_bets()
            logger.info("BetService started successfully")
        except Exception as e:
            logger.error(f"Failed to start BetService: {e}", exc_info=True)
            raise BetServiceError(f"Could not start BetService: {str(e)}")

    async def stop(self):
        """Stop the BetService and perform any necessary cleanup."""
        logger.info("Stopping BetService")
        try:
            self.pending_reactions.clear()
            logger.info("BetService stopped successfully")
        except Exception as e:
            logger.error(f"Failed to stop BetService: {e}", exc_info=True)
            raise BetServiceError(f"Could not stop BetService: {str(e)}")

    async def cleanup_expired_bets(self):
        """Remove expired pending bets from the database."""
        logger.debug("Checking for expired pending bets")
        try:
            # Convert timestamp to MySQL DATETIME最好的格式
            expiration_time = datetime.now(timezone.utc).timestamp() - (24 * 3600)  # 24 hours ago
            expiration_datetime = datetime.fromtimestamp(expiration_time, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            query = """
                DELETE FROM bets
                WHERE status = 'pending' AND created_at < %s
            """
            await self.db_manager.execute(query, (expiration_datetime,))
            logger.debug("Expired pending bets cleaned up")
        except Exception as e:
            logger.error(f"Failed to clean up expired bets: {e}", exc_info=True)
            raise BetServiceError(f"Could not clean up expired bets: {str(e)}")

    async def cleanup_unconfirmed_bets(self):
        """Delete unconfirmed bets that are older than 5 minutes."""
        logger.info("Starting cleanup of unconfirmed bets")
        try:
            # First get the bets that need to be cleaned up
            query = """
                SELECT bet_serial, guild_id, user_id 
                FROM bets 
                WHERE confirmed = 0 
                AND created_at < NOW() - INTERVAL '5 minutes'
            """
            expired_bets = await self.db_manager.fetch_all(query)
            
            if not expired_bets:
                logger.debug("No unconfirmed bets to clean up")
                return
                
            logger.info(f"Found {len(expired_bets)} unconfirmed bets to clean up")
            
            for bet in expired_bets:
                try:
                    # Clean up related records in a transaction
                    async with self.db_manager.transaction():
                        # Delete bet legs
                        await self.db_manager.execute(
                            "DELETE FROM bet_legs WHERE bet_serial = %s",
                            (bet['bet_serial'],)
                        )
                        # Delete bet images
                        await self.db_manager.execute(
                            "DELETE FROM bet_images WHERE bet_serial = %s",
                            (bet['bet_serial'],)
                        )
                        # Delete the bet itself
                        await self.db_manager.execute(
                            "DELETE FROM bets WHERE bet_serial = %s",
                            (bet['bet_serial'],)
                        )
                    logger.info(f"Successfully cleaned up bet {bet['bet_serial']} for user {bet['user_id']} in guild {bet['guild_id']}")
                except Exception as e:
                    logger.error(f"Failed to clean up bet {bet['bet_serial']}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error in cleanup_unconfirmed_bets: {e}", exc_info=True)
            raise BetServiceError(f"Failed to clean up unconfirmed bets: {str(e)}")

    async def confirm_bet(self, bet_serial: int, channel_id: int) -> bool:
        """Mark a bet as confirmed when the image is sent to a channel."""
        try:
            query = """
                UPDATE bets 
                SET confirmed = 1, 
                    channel_id = %s 
                WHERE bet_serial = %s
            """
            result = await self.db_manager.execute(query, (channel_id, bet_serial))
            return result is not None
        except Exception as e:
            logger.error(f"Error confirming bet {bet_serial}: {e}")
            return False

    async def create_straight_bet(
        self, guild_id: int, user_id: int, game_id: Optional[str],
        bet_type: str, team: str, opponent: str, line: str,
        units: float, odds: float, channel_id: Optional[int],
        league: str
    ) -> Optional[int]:
        """Create a straight bet."""
        try:
            bet_details = {
                'game_id': game_id,
                'bet_type': bet_type,
                'team': team,
                'opponent': opponent,
                'line': line
            }
            
            query = """
                INSERT INTO bets (
                    guild_id, user_id, league, bet_type,
                    bet_details, units, odds, channel_id,
                    confirmed
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """
            
            result = await self.db_manager.execute(
                query,
                (
                    guild_id, user_id, league, bet_type,
                    json.dumps(bet_details), units, odds,
                    channel_id, 1 if channel_id else 0
                )
            )
            
            if result is not None:
                # Get the last inserted ID
                id_result = await self.db_manager.fetchval("SELECT LAST_INSERT_ID()")
                return id_result
            return None
            
        except Exception as e:
            logger.error(f"Error creating straight bet: {e}")
            return None

    async def create_parlay_bet(
        self, guild_id: int, user_id: int, legs: List[Dict],
        channel_id: Optional[int], league: str
    ) -> Optional[int]:
        """Create a parlay bet."""
        try:
            bet_details = {
                'legs': legs,
                'total_odds': self._calculate_parlay_odds(legs)
            }
            
            query = """
                INSERT INTO bets (
                    guild_id, user_id, league, bet_type,
                    bet_details, units, odds, channel_id,
                    confirmed
                ) VALUES (
                    %s, %s, %s, 'parlay', %s, %s, %s, %s, %s
                )
            """
            
            total_units = sum(float(leg.get('units', 1.0)) for leg in legs)
            
            result = await self.db_manager.execute(
                query,
                (
                    guild_id, user_id, league,
                    json.dumps(bet_details), total_units,
                    bet_details['total_odds'], channel_id,
                    1 if channel_id else 0
                )
            )
            
            if result is not None:
                # Get the last inserted ID
                id_result = await self.db_manager.fetchval("SELECT LAST_INSERT_ID()")
                return id_result
            return None
            
        except Exception as e:
            logger.error(f"Error creating parlay bet: {e}")
            return None

    def _calculate_parlay_odds(self, legs: List[Dict]) -> float:
        """Calculate total odds for a parlay bet."""
        total_odds = 1.0
        for leg in legs:
            odds = float(leg.get('odds', 0))
            if odds > 0:
                total_odds *= (odds / 100.0 + 1)
            else:
                total_odds *= (100.0 / abs(odds) + 1)
        return round((total_odds - 1) * 100)

    async def update_straight_bet_channel(self, bet_serial: str, channel_id: int):
        """
        Update the channel ID for a straight bet.

        Args:
            bet_serial (str): Unique bet serial number.
            channel_id (int): ID of the channel to associate with the bet.

        Raises:
            BetServiceError: If the update fails.
        """
        logger.debug(f"Updating channel_id for straight bet {bet_serial} to {channel_id}")
        try:
            query = """
                UPDATE bets
                SET channel_id = %s
                WHERE bet_serial = %s AND bet_type = 'straight'
            """
            await self.db_manager.execute(query, (channel_id, bet_serial))
            logger.debug(f"Straight bet {bet_serial} channel updated to {channel_id}")
        except Exception as e:
            logger.error(f"Failed to update channel for bet {bet_serial}: {e}", exc_info=True)
            raise BetServiceError(f"Could not update channel for bet {bet_serial}: {str(e)}")

    async def update_parlay_bet_channel(self, bet_serial: str, channel_id: int):
        """
        Update the channel ID for a parlay bet.

        Args:
            bet_serial (str): Unique bet serial number.
            channel_id (int): ID of the channel to associate with the bet.

        Raises:
            BetServiceError: If the update fails.
        """
        logger.debug(f"Updating channel_id for parlay bet {bet_serial} to {channel_id}")
        try:
            query = """
                UPDATE bets
                SET channel_id = %s
                WHERE bet_serial = %s AND bet_type = 'parlay'
            """
            await self.db_manager.execute(query, (channel_id, bet_serial))
            logger.debug(f"Parlay bet {bet_serial} channel updated to {channel_id}")
        except Exception as e:
            logger.error(f"Failed to update channel for bet {bet_serial}: {e}", exc_info=True)
            raise BetServiceError(f"Could not update channel for bet {bet_serial}: {str(e)}")

    async def delete_bet(self, bet_serial: str):
        """
        Delete a bet and its associated legs from the database.

        Args:
            bet_serial (str): Unique bet serial number.

        Raises:
            BetServiceError: If the deletion fails.
        """
        logger.debug(f"Deleting bet {bet_serial}")
        try:
            # Delete legs (for parlay bets)
            leg_query = "DELETE FROM bet_legs WHERE bet_serial = %s"
            await self.db_manager.execute(leg_query, (bet_serial,))

            # Delete bet
            bet_query = "DELETE FROM bets WHERE bet_serial = %s"
            await self.db_manager.execute(bet_query, (bet_serial,))

            # Remove from pending reactions
            self.pending_reactions = {
                msg_id: data for msg_id, data in self.pending_reactions.items()
                if data.get('bet_serial') != bet_serial
            }
            logger.debug(f"Bet {bet_serial} deleted successfully")
        except Exception as e:
            logger.error(f"Failed to delete bet {bet_serial}: {e}", exc_info=True)
            raise BetServiceError(f"Could not delete bet {bet_serial}: {str(e)}")

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """
        Handle a reaction added to a bet slip message.

        Args:
            payload: The raw reaction event payload.
        """
        logger.debug(f"Handling reaction add for message {payload.message_id} by user {payload.user_id}")
        try:
            if payload.message_id not in self.pending_reactions:
                logger.debug(f"No pending reaction data for message {payload.message_id}")
                return

            reaction_data = self.pending_reactions[payload.message_id]
            bet_serial = reaction_data.get('bet_serial')
            user_id = reaction_data.get('user_id')
            guild_id = reaction_data.get('guild_id')
            channel_id = reaction_data.get('channel_id')

            # Example: Log the reaction (customize based on your needs)
            logger.info(
                f"Reaction {payload.emoji} added to bet {bet_serial} by user {payload.user_id} "
                f"in channel {channel_id} (guild {guild_id})"
            )

            # Optional: Update database or perform actions based on reaction
            # Example: Record reaction in a reactions table
            query = """
                INSERT INTO bet_reactions (
                    bet_serial, user_id, emoji, channel_id, message_id, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """
            params = (
                bet_serial, payload.user_id, str(payload.emoji), channel_id,
                payload.message_id, datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            )
            await self.db_manager.execute(query, params)

            # Update unit records if the reaction is a win/loss
            if str(payload.emoji) in ['✅', '❌']:  # Check for win/loss emojis
                # Get bet details
                bet_query = """
                    SELECT guild_id, user_id, units, odds, status
                    FROM bets
                    WHERE bet_serial = %s
                """
                bet_result = await self.db_manager.fetch_one(bet_query, (bet_serial,))
                
                if bet_result:
                    guild_id = bet_result['guild_id']
                    user_id = bet_result['user_id']
                    units = bet_result['units']
                    odds = bet_result['odds']
                    
                    # Calculate result value based on emoji
                    result_value = units * (1 + odds/100) if str(payload.emoji) == '✅' else -units
                    
                    # Get current year and month
                    now = datetime.now(timezone.utc)
                    year = now.year
                    month = now.month
                    
                    # Update unit records
                    unit_query = """
                        INSERT INTO unit_records (
                            bet_serial, guild_id, user_id, year, month, units, odds, result_value, created_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            result_value = VALUES(result_value),
                            created_at = VALUES(created_at)
                    """
                    unit_params = (
                        bet_serial, guild_id, user_id, year, month, units, odds, result_value,
                        datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                    )
                    await self.db_manager.execute(unit_query, unit_params)
                    
                    # Update bet status
                    status_query = """
                        UPDATE bets
                        SET status = %s
                        WHERE bet_serial = %s
                    """
                    status = 'won' if str(payload.emoji) == '✅' else 'lost'
                    await self.db_manager.execute(status_query, (status, bet_serial))

        except Exception as e:
            logger.error(f"Failed to handle reaction add for message {payload.message_id}: {e}", exc_info=True)

    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        """
        Handle a reaction removed from a bet slip message.

        Args:
            payload: The raw reaction event payload.
        """
        logger.debug(f"Handling reaction remove for message {payload.message_id} by user {payload.user_id}")
        try:
            if payload.message_id not in self.pending_reactions:
                logger.debug(f"No pending reaction data for message {payload.message_id}")
                return

            reaction_data = self.pending_reactions[payload.message_id]
            bet_serial = reaction_data.get('bet_serial')
            user_id = reaction_data.get('user_id')
            guild_id = reaction_data.get('guild_id')
            channel_id = reaction_data.get('channel_id')

            # Example: Log the reaction removal
            logger.info(
                f"Reaction {payload.emoji} removed from bet {bet_serial} by user {payload.user_id} "
                f"in channel {channel_id} (guild {guild_id})"
            )

            # Optional: Update database (e.g., remove reaction record)
            query = """
                DELETE FROM bet_reactions
                WHERE bet_serial = %s AND user_id = %s AND emoji = %s AND message_id = %s
            """
            params = (bet_serial, payload.user_id, str(payload.emoji), payload.message_id)
            await self.db_manager.execute(query, params)

        except Exception as e:
            logger.error(f"Failed to handle reaction remove for message {payload.message_id}: {e}", exc_info=True)
