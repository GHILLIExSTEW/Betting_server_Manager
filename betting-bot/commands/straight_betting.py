# betting-bot/services/bet_service.py

"""Service for managing bets and handling bet-related reactions."""

import logging
from typing import Dict, List, Optional, Union
from datetime import datetime, timezone
import uuid
import discord

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

    async def create_straight_bet(
        self,
        guild_id: int,
        user_id: int,
        game_id: Optional[str],
        bet_type: str,
        team: str,
        opponent: Optional[str],
        line: str,
        units: float,
        odds: float,
        channel_id: Optional[int],
        league: str
    ) -> str:
        """
        Create a new straight bet in the database.

        Args:
            guild_id (int): ID of the guild.
            user_id (int): ID of the user placing the bet.
            game_id (Optional[str]): ID of the game (None for manual entries).
            bet_type (str): Type of bet ('game_line' or 'player_prop').
            team (str): Team or entity bet on.
            opponent (Optional[str]): Opponent team or player (if applicable).
            line (str): Betting line (e.g., ML, O/U 5.5).
            units (float): Units wagered.
            odds (float): Odds for the bet.
            channel_id (Optional[int]): ID of the channel where the bet is posted.
            league (str): League of the bet (e.g., NHL, NBA).

        Returns:
            str: Unique bet serial number.

        Raises:
            ValidationError: If input validation fails.
            BetServiceError: If database operation fails.
        """
        logger.debug(f"Creating straight bet for user {user_id} in guild {guild_id}, league: {league}")
        try:
            # Validate inputs
            if not team or not line:
                raise ValidationError("Team and line are required")
            if units <= 0:
                raise ValidationError("Units must be positive")
            if not (-10000 <= odds <= 10000):
                raise ValidationError("Odds must be between -10000 and +10000")
            if -100 < odds < 100:
                raise ValidationError("Odds cannot be between -99 and +99")

            # Generate unique bet serial
            bet_serial = str(uuid.uuid4())

            # Insert bet into database
            query = """
                INSERT INTO bets (
                    bet_serial, guild_id, user_id, game_id, bet_type, team, opponent,
                    line, units, odds, channel_id, league, status, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (
                bet_serial, guild_id, user_id, game_id, bet_type, team, opponent,
                line, units, odds, channel_id, league, 'pending',
                datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            )
            await self.db_manager.execute(query, params)

            logger.info(f"Straight bet created: serial={bet_serial}, user={user_id}, guild={guild_id}")
            return bet_serial

        except ValidationError as ve:
            logger.error(f"Validation error creating straight bet for user {user_id}: {ve}")
            raise
        except Exception as e:
            logger.error(f"Failed to create straight bet for user {user_id}: {e}", exc_info=True)
            raise BetServiceError(f"Could not create straight bet: {str(e)}")

    async def create_parlay_bet(
        self,
        guild_id: int,
        user_id: int,
        legs: List[Dict[str, Union[str, float, Optional[str]]]],
        channel_id: Optional[int],
        league: str
    ) -> str:
        """
        Create a new parlay bet in the database.

        Args:
            guild_id (int): ID of the guild.
            user_id (int): ID of the user placing the bet.
            legs (List[Dict]): List of bet legs, each with game_id, bet_type, team, opponent, line, units, odds.
            channel_id (Optional[int]): ID of the channel where the bet is posted.
            league (str): League of the bet (e.g., NHL, NBA).

        Returns:
            str: Unique bet serial number.

        Raises:
            ValidationError: If input validation fails.
            BetServiceError: If database operation fails.
        """
        logger.debug(f"Creating parlay bet for user {user_id} in guild {guild_id}, league: {league}, legs: {len(legs)}")
        try:
            # Validate inputs
            if len(legs) < 2:
                raise ValidationError("Parlay bets require at least two legs")
            for leg in legs:
                if not leg.get('team') or not leg.get('line'):
                    raise ValidationError("Each leg must have a team and line")
                units = leg.get('units', 0.0)
                odds = leg.get('odds', 0.0)
                if units <= 0:
                    raise ValidationError("Units must be positive for each leg")
                if not (-10000 <= odds <= 10000):
                    raise ValidationError("Odds must be between -10000 and +10000 for each leg")
                if -100 < odds < 100:
                    raise ValidationError("Odds cannot be between -99 and +99 for each leg")

            # Generate unique bet serial
            bet_serial = str(uuid.uuid4())

            # Insert parlay bet into database
            query = """
                INSERT INTO bets (
                    bet_serial, guild_id, user_id, bet_type, channel_id, league, status, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (
                bet_serial, guild_id, user_id, 'parlay', channel_id, league, 'pending',
                datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            )
            await self.db_manager.execute(query, params)

            # Insert each leg into a legs table
            leg_query = """
                INSERT INTO bet_legs (
                    bet_serial, game_id, bet_type, team, opponent, line, units, odds
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            for leg in legs:
                leg_params = (
                    bet_serial, leg.get('game_id'), leg.get('bet_type'), leg.get('team'),
                    leg.get('opponent'), leg.get('line'), leg.get('units'), leg.get('odds')
                )
                await self.db_manager.execute(leg_query, leg_params)

            logger.info(f"Parlay bet created: serial={bet_serial}, user={user_id}, guild={guild_id}, legs={len(legs)}")
            return bet_serial

        except ValidationError as ve:
            logger.error(f"Validation error creating parlay bet for user {user_id}: {ve}")
            raise
        except Exception as e:
            logger.error(f"Failed to create parlay bet for user {user_id}: {e}", exc_info=True)
            raise BetServiceError(f"Could not create parlay bet: {str(e)}")

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
