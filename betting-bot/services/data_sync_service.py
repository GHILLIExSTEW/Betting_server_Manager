# betting-bot/services/data_sync_service.py

import logging
import asyncio
from datetime import datetime, timedelta, timezone # Add timezone
from typing import Dict, List, Optional
import aiohttp # Keep aiohttp if used directly here
import json # Import json for potential data processing

# Use relative imports
try:
    # from ..data.db_manager import DatabaseManager # Not needed if passed in
    from ..data.cache_manager import CacheManager
    from ..utils.errors import DataSyncError
    # Import GameService only for type hinting if needed, or access via self.bot
    # from .game_service import GameService
    from ..config.api_settings import API_ENABLED, API_KEY, API_HOSTS # Import config
except ImportError:
    # from data.db_manager import DatabaseManager
    from data.cache_manager import CacheManager
    from utils.errors import DataSyncError
    # from services.game_service import GameService # Fallback
    from config.api_settings import API_ENABLED, API_KEY, API_HOSTS

# from dotenv import load_dotenv # Loaded in main.py

logger = logging.getLogger(__name__)

class DataSyncService:
    # Corrected __init__
    def __init__(self, game_service, db_manager): # Accept game_service and db_manager
        """Initializes the Data Sync Service.

        Args:
            game_service: The shared GameService instance (used for _make_request).
            db_manager: The shared DatabaseManager instance.
        """
        self.game_service = game_service # Store game_service instance
        self.db = db_manager # Use shared db_manager instance
        # Instantiate cache here, or pass if managed centrally
        self.cache = CacheManager()
        self._sync_task: Optional[asyncio.Task] = None
        self.running = False
        # API Key/Hosts are likely needed by game_service._make_request, not directly here
        # self.api_key = API_KEY
        # self.api_hosts = API_HOSTS

    async def start(self):
        """Start the data sync service background task."""
        if not API_ENABLED:
             logger.warning("API is disabled. DataSyncService will not run.")
             return

        if not self.running:
            # Connect cache if needed
            if hasattr(self.cache, 'connect'): await self.cache.connect()

            self.running = True
            # Run initial sync immediately? Or wait for loop? Let's wait.
            self._sync_task = asyncio.create_task(self._daily_sync_loop())
            logger.info("Data sync service started.")

    async def stop(self):
        """Stop the data sync service background task."""
        self.running = False
        logger.info("Stopping DataSyncService...")
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                logger.info("Data sync task cancelled.")
            except Exception as e:
                 logger.error(f"Error awaiting data sync task cancellation: {e}")
            self._sync_task = None

        if hasattr(self.cache, 'close'): await self.cache.close()
        logger.info("Data sync service stopped.")


    async def _daily_sync_loop(self):
        """Main loop for daily data synchronization."""
        await asyncio.sleep(10) # Initial delay before first run
        while self.running:
            try:
                logger.info("Starting daily data sync cycle...")
                await self._sync_all_data()
                logger.info("Daily data sync cycle finished.")

                # Calculate time until next sync (e.g., 3 AM UTC)
                now = datetime.now(timezone.utc)
                next_run_time = (now + timedelta(days=1)).replace(
                    hour=3, minute=0, second=0, microsecond=0 # Example: Run at 3 AM UTC
                )
                # If it's already past 3 AM today, schedule for tomorrow
                if now >= next_run_time:
                     next_run_time += timedelta(days=1)

                sleep_duration = (next_run_time - now).total_seconds()
                logger.info(f"Next data sync scheduled in {sleep_duration/3600:.2f} hours.")
                await asyncio.sleep(sleep_duration)

            except asyncio.CancelledError:
                logger.info("Data sync loop cancelled.")
                break
            except Exception as e:
                logger.exception(f"Error in daily sync loop: {e}")
                # Wait longer after an error before retrying
                await asyncio.sleep(3600) # Wait 1 hour after error

    async def _sync_all_data(self):
        """Sync all relevant data (leagues, teams, schedule, standings) from APIs."""
        if not API_ENABLED:
             logger.warning("API disabled, skipping data sync.")
             return

        try:
            logger.info("Syncing core data: Leagues and Teams...")
            # Sync Leagues first, as other syncs might depend on league IDs/sports
            # Use API_HOSTS keys directly as sport identifiers
            all_sports = list(API_HOSTS.keys())
            synced_leagues = []

            for sport in all_sports:
                 if not API_HOSTS.get(sport): # Skip if host not configured
                      continue
                 try:
                      sport_leagues = await self._sync_leagues(sport)
                      if sport_leagues:
                          synced_leagues.extend(sport_leagues)
                      await asyncio.sleep(1) # Small delay between sports
                 except Exception as e:
                      logger.error(f"Error syncing leagues for sport '{sport}': {e}")

            # Sync Teams (requires leagues to exist)
            await self._sync_teams(synced_leagues)

            # Sync Schedules (e.g., next N days)
            logger.info("Syncing upcoming game schedules...")
            await self._sync_schedules(synced_leagues, days_ahead=7) # Sync next 7 days

            # Sync Standings
            logger.info("Syncing league standings...")
            await self._sync_standings(synced_leagues)

            logger.info("Core data sync finished.")

        except Exception as e:
            logger.exception(f"Error during _sync_all_data: {e}")
            # Don't raise, allow loop to continue later


    async def _sync_leagues(self, sport: str) -> List[Dict]:
        """Fetch and store/update leagues for a specific sport."""
        logger.debug(f"Syncing leagues for sport: {sport}")
        try:
            # Use game_service's helper to make the API call
            response_data = await self.game_service._make_request(sport, "leagues")
            leagues_api = response_data.get('response', [])
            if not leagues_api:
                 logger.warning(f"No leagues returned from API for sport: {sport}")
                 return []

            processed_leagues = []
            for league_entry in leagues_api:
                league = league_entry.get('league', {})
                country = league_entry.get('country', {})
                # Assuming seasons is a list, take the latest/current one if possible
                season_info = league_entry.get('seasons', [{}])[-1] # Get last season as approximation

                if not league.get('id'): continue # Skip if no league ID

                normalized_league = {
                    'id': league['id'],
                    'name': league.get('name'),
                    'type': league.get('type'),
                    'logo': league.get('logo'),
                    'country': country.get('name'),
                    'country_code': country.get('code'),
                    'country_flag': country.get('flag'),
                    'season': season_info.get('year'), # Current season year
                    'sport': sport
                }
                processed_leagues.append(normalized_league)

            # Use self.db (DatabaseManager) for upsert
            # Assumes PostgreSQL syntax for ON CONFLICT
            for league in processed_leagues:
                 await self.db.execute(
                     """
                     INSERT INTO leagues (id, name, type, logo, country, country_code,
                                          country_flag, season, sport)
                     VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                     ON CONFLICT (id) DO UPDATE SET
                         name = EXCLUDED.name, type = EXCLUDED.type, logo = EXCLUDED.logo,
                         country = EXCLUDED.country, country_code = EXCLUDED.country_code,
                         country_flag = EXCLUDED.country_flag, season = EXCLUDED.season,
                         sport = EXCLUDED.sport
                     """,
                     league['id'], league['name'], league['type'], league['logo'],
                     league['country'], league['country_code'], league['country_flag'],
                     league['season'], league['sport']
                 )
            logger.info(f"Upserted {len(processed_leagues)} leagues for sport: {sport}")
            return processed_leagues

        except Exception as e:
            logger.exception(f"Error syncing leagues for {sport}: {e}")
            # Re-raise specific error? Or just return empty list?
            return [] # Return empty on error to avoid stopping full sync


    async def _sync_teams(self, leagues: List[Dict]):
         """Fetch and store/update teams for the given leagues."""
         logger.debug(f"Syncing teams for {len(leagues)} leagues...")
         if not leagues: return

         # Group leagues by sport to use the correct API host
         leagues_by_sport: Dict[str, List[Dict]] = {}
         for league in leagues:
              sport = league['sport']
              if sport not in leagues_by_sport:
                   leagues_by_sport[sport] = []
              leagues_by_sport[sport].append(league)

         all_processed_teams = []
         for sport, sport_leagues in leagues_by_sport.items():
              logger.info(f"Syncing teams for {len(sport_leagues)} leagues in sport: {sport}")
              for league in sport_leagues:
                   try:
                        season = league.get('season') or datetime.now(timezone.utc).year # Need season year
                        # Make API call using game_service helper
                        response_data = await self.game_service._make_request(
                             sport,
                             "teams",
                             params={'league': str(league['id']), 'season': str(season)}
                        )
                        teams_api = response_data.get('response', [])
                        if not teams_api: continue

                        processed_teams = []
                        for team_entry in teams_api:
                             team = team_entry.get('team', {})
                             venue = team_entry.get('venue', {})
                             if not team.get('id'): continue # Skip if no ID

                             normalized_team = {
                                  'id': team['id'],
                                  'name': team.get('name'),
                                  'code': team.get('code'),
                                  'country': team.get('country'),
                                  'founded': team.get('founded'),
                                  'national': team.get('national', False), # Default to False if missing
                                  'logo': team.get('logo'),
                                  'venue_name': venue.get('name'),
                                  'venue_address': venue.get('address'),
                                  'venue_city': venue.get('city'),
                                  'venue_capacity': venue.get('capacity'),
                                  'venue_surface': venue.get('surface'),
                                  'venue_image': venue.get('image'),
                                  'sport': sport
                             }
                             processed_teams.append(normalized_team)

                        # Upsert teams into DB
                        for team in processed_teams:
                            await self.db.execute(
                               """
                               INSERT INTO teams (id, name, code, country, founded, national, logo,
                                                 venue_name, venue_address, venue_city, venue_capacity,
                                                 venue_surface, venue_image, sport)
                               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                               ON CONFLICT (id) DO UPDATE SET
                                   name=EXCLUDED.name, code=EXCLUDED.code, country=EXCLUDED.country,
                                    founded=EXCLUDED.founded, national=EXCLUDED.national, logo=EXCLUDED.logo,
                                   venue_name=EXCLUDED.venue_name, venue_address=EXCLUDED.venue_address,
                                   venue_city=EXCLUDED.venue_city, venue_capacity=EXCLUDED.venue_capacity,
                                   venue_surface=EXCLUDED.venue_surface, venue_image=EXCLUDED.venue_image,
                                   sport=EXCLUDED.sport
                               """,
                               team['id'], team['name'], team['code'], team['country'], team['founded'],
                               team['national'], team['logo'], team['venue_name'], team['venue_address'],
                               team['venue_city'], team['venue_capacity'], team['venue_surface'],
                               team['venue_image'], team['sport']
                            )
                        all_processed_teams.extend(processed_teams)
                     logger.debug(f"Upserted {len(processed_teams)} teams for league {league['id']}")
                     await asyncio.sleep(0.5) # Small delay between leagues
                  
                except Exception as e:
                    logger.exception(f"Error syncing teams for league {league.get('id', 'N/A')} in sport {sport}: {e}")
        logger.info(f"Finished syncing teams. Total teams processed: {len(all_processed_teams)}")


    async def _sync_schedules(self, leagues: List[Dict], days_ahead: int):
         """Fetch and store/update game schedules for the upcoming days."""
         logger.debug(f"Syncing schedules for {len(leagues)} leagues, {days_ahead} days ahead...")
         if not leagues: return

         start_date = datetime.now(timezone.utc)
         end_date = start_date + timedelta(days=days_ahead)

         leagues_by_sport: Dict[str, List[Dict]] = {}
         for league in leagues:
              sport = league['sport']
              if sport not in leagues_by_sport: leagues_by_sport[sport] = []
              leagues_by_sport[sport].append(league)

         all_processed_games = []
         for sport, sport_leagues in leagues_by_sport.items():
             logger.info(f"Syncing schedules for {len(sport_leagues)} leagues in sport: {sport}")
             for league in sport_leagues:
                 try:
                      # Use game_service method which includes caching logic
                      schedule_api = await self.game_service.get_league_schedule(
                           sport, str(league['id']), start_date, end_date
                      )
                      if not schedule_api: continue

                      processed_games = []
                      for game_entry in schedule_api:
                          fixture = game_entry.get('fixture', {})
                          league_data = game_entry.get('league', {}) # API might repeat league info
                          teams_data = game_entry.get('teams', {})
                          goals_data = game_entry.get('goals', {}) # Score info
                          score_full = game_entry.get('score', {}) # More score info (halftime, etc.)

                          if not fixture.get('id'): continue

                          # Parse timestamp correctly - ensure it's UTC
                          game_timestamp_str = fixture.get('date')
                          game_start_time = None
                          if game_timestamp_str:
                               try:
                                    # Assume ISO 8601 format from API
                                    game_start_time = datetime.fromisoformat(game_timestamp_str.replace('Z', '+00:00'))
                                    if game_start_time.tzinfo is None: # Add UTC if missing
                                         game_start_time = game_start_time.replace(tzinfo=timezone.utc)
                               except ValueError:
                                    logger.warning(f"Could not parse timestamp {game_timestamp_str} for game {fixture['id']}")

                          normalized_game = {
                              'id': fixture['id'],
                              'league_id': league_data.get('id', league['id']), # Use league_id from loop if missing
                              'home_team_id': teams_data.get('home', {}).get('id'),
                              'away_team_id': teams_data.get('away', {}).get('id'),
                              'home_team_name': teams_data.get('home', {}).get('name'),
                              'away_team_name': teams_data.get('away', {}).get('name'),
                              'home_team_logo': teams_data.get('home', {}).get('logo'), # Get logos if needed
                              'away_team_logo': teams_data.get('away', {}).get('logo'),
                              'start_time': game_start_time,
                              'status': fixture.get('status', {}).get('short', 'TBD'), # Use short status code
                              # Combine score data into a JSONB compatible dict
                              'score': json.dumps({
                                   'home': goals_data.get('home'),
                                   'away': goals_data.get('away'),
                                   'halftime': score_full.get('halftime'),
                                   'fulltime': score_full.get('fulltime'),
                                   'extratime': score_full.get('extratime'),
                                   'penalty': score_full.get('penalty')
                              }),
                              'venue': fixture.get('venue', {}).get('name'),
                              'referee': fixture.get('referee'),
                              'sport': sport,
                              'updated_at': datetime.now(timezone.utc) # Track sync time
                          }
                          processed_games.append(normalized_game)

                      # Upsert games into DB
                      for game in processed_games:
                          # Need to handle score potentially being None/empty for INSERT/UPDATE
                          score_json = game['score'] if game['score'] != 'null' else None

                          await self.db.execute(
                              """
                              INSERT INTO games (id, league_id, home_team_id, away_team_id, home_team_name,
                                                 away_team_name, home_team_logo, away_team_logo, start_time,
                                                 status, score, venue, referee, sport, updated_at)
                              VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11::jsonb, $12, $13, $14, $15)
                              ON CONFLICT (id) DO UPDATE SET
                                  league_id=EXCLUDED.league_id, home_team_id=EXCLUDED.home_team_id,
                                  away_team_id=EXCLUDED.away_team_id, home_team_name=EXCLUDED.home_team_name,
                                  away_team_name=EXCLUDED.away_team_name, start_time=EXCLUDED.start_time,
                                  status=EXCLUDED.status, score=EXCLUDED.score, venue=EXCLUDED.venue,
                                  referee=EXCLUDED.referee, sport=EXCLUDED.sport, updated_at=EXCLUDED.updated_at
                                  -- Add logos if updating them here
                              """,
                              game['id'], game['league_id'], game['home_team_id'], game['away_team_id'],
                              game['home_team_name'], game['away_team_name'], game['home_team_logo'],
                              game['away_team_logo'], game['start_time'], game['status'], score_json,
                              game['venue'], game['referee'], game['sport'], game['updated_at']
                          )
                      all_processed_games.extend(processed_games)
                      logger.debug(f"Upserted {len(processed_games)} schedule games for league {league['id']}")
                      await asyncio.sleep(0.5) # Small delay

                 except Exception as e:
                      logger.exception(f"Error syncing schedule for league {league.get('id', 'N/A')} in sport {sport}: {e}")
         logger.info(f"Finished syncing schedules. Total games processed: {len(all_processed_games)}")


    async def _sync_standings(self, leagues: List[Dict]):
         """Fetch and store/update league standings."""
         logger.debug(f"Syncing standings for {len(leagues)} leagues...")
         if not leagues: return

         leagues_by_sport: Dict[str, List[Dict]] = {}
         for league in leagues:
              sport = league['sport']
              if sport not in leagues_by_sport: leagues_by_sport[sport] = []
              leagues_by_sport[sport].append(league)

         all_processed_standings = []
         for sport, sport_leagues in leagues_by_sport.items():
              logger.info(f"Syncing standings for {len(sport_leagues)} leagues in sport: {sport}")
              for league in sport_leagues:
                   try:
                        season = league.get('season') or datetime.now(timezone.utc).year
                        # Make API call
                        response_data = await self.game_service._make_request(
                             sport,
                             "standings",
                             params={'league': str(league['id']), 'season': str(season)}
                        )
                        standings_api = response_data.get('response', [])
                        if not standings_api: continue

                        # API often wraps standings inside league->standings array of arrays
                        processed_standings = []
                        for standing_group_entry in standings_api:
                             # The actual standings table is usually nested
                             standings_table = standing_group_entry.get('league', {}).get('standings', [[]])[0]
                             for team_standing in standings_table:
                                 team = team_standing.get('team', {})
                                 if not team.get('id'): continue

                                 all_stats = team_standing.get('all', {})
                                 goals_stats = all_stats.get('goals', {})

                                 normalized = {
                                     'league_id': league['id'],
                                     'team_id': team['id'],
                                     'rank': team_standing.get('rank'),
                                     'points': team_standing.get('points'),
                                     'goals_diff': team_standing.get('goalsDiff'),
                                     'form': team_standing.get('form'), # String like 'WWLDW'
                                     'played': all_stats.get('played'),
                                     'won': all_stats.get('win'),
                                     'draw': all_stats.get('draw'),
                                     'lost': all_stats.get('lose'),
                                     'goals_for': goals_stats.get('for'),
                                     'goals_against': goals_stats.get('against'),
                                     'sport': sport
                                 }
                                 processed_standings.append(normalized)

                        # Upsert standings into DB (PK is league_id, team_id)
                        for standing in processed_standings:
                             await self.db.execute(
                                 """
                                 INSERT INTO standings (league_id, team_id, rank, points, goals_diff, form,
                                                        played, won, draw, lost, goals_for, goals_against, sport)
                                 VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                                 ON CONFLICT (league_id, team_id) DO UPDATE SET
                                     rank=EXCLUDED.rank, points=EXCLUDED.points, goals_diff=EXCLUDED.goals_diff,
                                     form=EXCLUDED.form, played=EXCLUDED.played, won=EXCLUDED.won, draw=EXCLUDED.draw,
                                     lost=EXCLUDED.lost, goals_for=EXCLUDED.goals_for,
                                     goals_against=EXCLUDED.goals_against, sport=EXCLUDED.sport
                                 """,
                                 standing['league_id'], standing['team_id'], standing['rank'], standing['points'],
                                 standing['goals_diff'], standing['form'], standing['played'], standing['won'],
                                 standing['draw'], standing['lost'], standing['goals_for'],
                                 standing['goals_against'], standing['sport']
                             )
                        all_processed_standings.extend(processed_standings)
                        logger.debug(f"Upserted {len(processed_standings)} standing entries for league {league['id']}")
                        await asyncio.sleep(0.5) # Small delay

                   except Exception as e:
                        logger.exception(f"Error syncing standings for league {league.get('id', 'N/A')} in sport {sport}: {e}")
         logger.info(f"Finished syncing standings. Total entries processed: {len(all_processed_standings)}")
