# betting-bot/services/data_sync_service.py

"""Service for synchronizing external data with the database."""

import logging
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import aiohttp
import json

try:
    from ..data.cache_manager import CacheManager
    from ..utils.errors import DataSyncError
    from ..config.api_settings import API_ENABLED, API_KEY, API_HOSTS
except ImportError:
    from data.cache_manager import CacheManager
    from utils.errors import DataSyncError
    from config.api_settings import API_ENABLED, API_KEY, API_HOSTS

logger = logging.getLogger(__name__)


class DataSyncService:
    def __init__(self, game_service, db_manager):
        self.game_service = game_service
        self.db = db_manager
        self.cache = CacheManager()
        self._sync_task: Optional[asyncio.Task] = None
        self.running = False

    async def start(self):
        """Start the data sync service background task."""
        if not API_ENABLED:
            logger.warning("API is disabled. DataSyncService will not run.")
            return
        if not self.running:
            if hasattr(self.cache, 'connect'):
                await self.cache.connect()
            self.running = True
            self._sync_task = asyncio.create_task(self._daily_sync_loop())
            logger.info("Data sync service started.")

    async def stop(self):
        """Stop the data sync service background task."""
        self.running = False
        logger.info("Stopping DataSyncService...")
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await asyncio.wait_for(self._sync_task, timeout=5.0)
            except asyncio.CancelledError:
                logger.info("Data sync task cancelled.")
            except asyncio.TimeoutError:
                logger.warning("Data sync task did not cancel within timeout.")
            except Exception as e:
                logger.error(f"Error awaiting data sync task cancellation: {e}")
            finally:
                self._sync_task = None

        if hasattr(self.cache, 'close'):
            await self.cache.close()
        logger.info("Data sync service stopped.")

    async def _daily_sync_loop(self):
        """Main loop for daily data synchronization."""
        await asyncio.sleep(60)
        while self.running:
            next_run_time = None
            try:
                logger.info("Starting daily data sync cycle...")
                await self._sync_all_data()
                logger.info("Daily data sync cycle finished.")

                now = datetime.now(timezone.utc)
                next_run_time = (now + timedelta(days=1)).replace(hour=3, minute=0, second=0, microsecond=0)
                sleep_duration = (next_run_time - now).total_seconds()
                sleep_duration = max(60, sleep_duration)

                logger.info(f"Next data sync scheduled at {next_run_time.isoformat()} (in {sleep_duration/3600:.2f} hours).")
                await asyncio.sleep(sleep_duration)

            except asyncio.CancelledError:
                logger.info("Data sync loop cancelled.")
                break
            except Exception as e:
                logger.exception(f"Error in daily sync loop: {e}")
                logger.info("Waiting 1 hour before retrying sync loop due to error.")
                await asyncio.sleep(3600)

    async def _sync_all_data(self):
        """Sync all relevant data (leagues, teams, schedule, standings) from APIs."""
        if not API_ENABLED:
            logger.warning("API disabled, skipping data sync.")
            return

        try:
            logger.info("Syncing core data: Leagues and Teams...")
            all_sports = list(API_HOSTS.keys())
            synced_leagues = []

            for sport in all_sports:
                if not API_HOSTS.get(sport):
                    continue
                try:
                    sport_leagues = await self._sync_leagues(sport)
                    if sport_leagues:
                        synced_leagues.extend(sport_leagues)
                    await asyncio.sleep(1.1)
                except Exception as e:
                    logger.error(f"Error syncing leagues for sport '{sport}': {e}")

            if synced_leagues:
                await self._sync_teams(synced_leagues)
            else:
                logger.warning("Skipping team sync as no leagues were synced.")
            await asyncio.sleep(1.1)

            if synced_leagues:
                logger.info("Syncing upcoming game schedules...")
                await self._sync_schedules(synced_leagues, days_ahead=7)
            else:
                logger.warning("Skipping schedule sync as no leagues were synced.")
            await asyncio.sleep(1.1)

            if synced_leagues:
                logger.info("Syncing league standings...")
                await self._sync_standings(synced_leagues)
            else:
                logger.warning("Skipping standings sync as no leagues were synced.")

            logger.info("Core data sync finished.")
        except Exception as e:
            logger.exception(f"Error during _sync_all_data: {e}")

    async def _sync_leagues(self, sport: str) -> List[Dict]:
        """Fetch and store/update leagues for a specific sport."""
        logger.debug(f"Syncing leagues for sport: {sport}")
        try:
            response_data = await self.game_service._make_request(sport, "leagues")
            leagues_api = response_data.get('response', [])
            if not leagues_api:
                return []

            processed_leagues = []
            for league_entry in leagues_api:
                league = league_entry.get('league', {})
                country = league_entry.get('country', {})
                season_info = league_entry.get('seasons', [{}])[-1]
                if not league.get('id'):
                    continue
                processed_leagues.append({
                    'id': league['id'], 'name': league.get('name'), 'type': league.get('type'),
                    'logo': league.get('logo'), 'country': country.get('name'),
                    'country_code': country.get('code'), 'country_flag': country.get('flag'),
                    'season': season_info.get('year'), 'sport': sport
                })

            if processed_leagues:
                upsert_query = """
                    INSERT INTO leagues (id, name, type, logo, country, country_code,
                                        country_flag, season, sport)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        name = VALUES(name), type = VALUES(type), logo = VALUES(logo),
                        country = VALUES(country), country_code = VALUES(country_code),
                        country_flag = VALUES(country_flag), season = VALUES(season),
                        sport = VALUES(sport)
                """
                data_tuples = [
                    (lg['id'], lg['name'], lg['type'], lg['logo'], lg['country'], lg['country_code'],
                     lg['country_flag'], lg['season'], lg['sport'])
                    for lg in processed_leagues
                ]
                count = 0
                for data_tuple in data_tuples:
                    try:
                        await self.db.execute(upsert_query, *data_tuple)
                        count += 1
                    except Exception as e:
                        logger.error(f"Error upserting league {data_tuple[0]}: {e}")
                logger.info(f"Upserted {count}/{len(processed_leagues)} leagues for sport: {sport}")
            return processed_leagues
        except Exception as e:
            logger.exception(f"Error syncing leagues for {sport}: {e}")
            return []

    async def _sync_teams(self, leagues: List[Dict]):
        """Fetch and store/update teams for the given leagues."""
        logger.debug(f"Syncing teams for {len(leagues)} leagues...")
        if not leagues:
            return

        leagues_by_sport: Dict[str, List[Dict]] = {}
        for league in leagues:
            sport = league.get('sport')
            if sport:
                leagues_by_sport.setdefault(sport, []).append(league)

        all_processed_teams = []
        for sport, sport_leagues in leagues_by_sport.items():
            logger.info(f"Syncing teams for {len(sport_leagues)} leagues in sport: {sport}")
            for league in sport_leagues:
                league_id = league.get('id')
                if not league_id:
                    continue
                try:
                    season = league.get('season') or datetime.now(timezone.utc).year
                    response_data = await self.game_service._make_request(
                        sport, "teams", params={'league': str(league_id), 'season': str(season)}
                    )
                    teams_api = response_data.get('response', [])
                    if not teams_api:
                        continue

                    processed_teams = []
                    for team_entry in teams_api:
                        team = team_entry.get('team', {})
                        venue = team_entry.get('venue', {})
                        if not team.get('id'):
                            continue
                        processed_teams.append({
                            'id': team['id'], 'name': team.get('name'), 'code': team.get('code'),
                            'country': team.get('country'), 'founded': team.get('founded'),
                            'national': team.get('national', False), 'logo': team.get('logo'),
                            'venue_id': venue.get('id'),
                            'venue_name': venue.get('name'), 'venue_address': venue.get('address'),
                            'venue_city': venue.get('city'), 'venue_capacity': venue.get('capacity'),
                            'venue_surface': venue.get('surface'), 'venue_image': venue.get('image'),
                            'sport': sport
                        })

                    if processed_teams:
                        upsert_query = """
                            INSERT INTO teams (id, name, code, country, founded, national, logo,
                                              venue_id, venue_name, venue_address, venue_city, venue_capacity,
                                              venue_surface, venue_image, sport)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE
                                name=VALUES(name), code=VALUES(code), country=VALUES(country),
                                founded=VALUES(founded), national=VALUES(national), logo=VALUES(logo),
                                venue_id=VALUES(venue_id), venue_name=VALUES(venue_name), venue_address=VALUES(venue_address),
                                venue_city=VALUES(venue_city), venue_capacity=VALUES(venue_capacity),
                                venue_surface=VALUES(venue_surface), venue_image=VALUES(venue_image), sport=VALUES(sport)
                        """
                        data_tuples = [
                            (t['id'], t['name'], t['code'], t['country'], t['founded'], t['national'], t['logo'],
                             t['venue_id'], t['venue_name'], t['venue_address'], t['venue_city'], t['venue_capacity'],
                             t['venue_surface'], t['venue_image'], t['sport'])
                            for t in processed_teams
                        ]
                        count = 0
                        for data_tuple in data_tuples:
                            try:
                                await self.db.execute(upsert_query, *data_tuple)
                                count += 1
                            except Exception as e:
                                logger.error(f"Error upserting team {data_tuple[0]}: {e}")

                        all_processed_teams.extend(processed_teams)
                        logger.debug(f"Upserted {count}/{len(processed_teams)} teams for league {league_id}")
                    await asyncio.sleep(1.1)
                except Exception as e:
                    logger.exception(f"Error syncing teams for league {league_id} ({sport}): {e}")
        logger.info(f"Finished syncing teams. Total teams processed: {len(all_processed_teams)}")

    async def _sync_schedules(self, leagues: List[Dict], days_ahead: int):
        """Fetch and store/update game schedules for the upcoming days."""
        logger.debug(f"Syncing schedules for {len(leagues)} leagues, {days_ahead} days ahead...")
        if not leagues:
            return

        start_date = datetime.now(timezone.utc)
        end_date = start_date + timedelta(days=days_ahead)
        leagues_by_sport: Dict[str, List[Dict]] = {}
        for league in leagues:
            sport = league.get('sport')
            if sport:
                leagues_by_sport.setdefault(sport, []).append(league)

        all_processed_games = []
        for sport, sport_leagues in leagues_by_sport.items():
            logger.info(f"Syncing schedules for {len(sport_leagues)} leagues in sport: {sport}")
            for league in sport_leagues:
                league_id = league.get('id')
                if not league_id:
                    continue
                try:
                    schedule_api = await self.game_service.get_league_schedule(
                        sport, str(league_id), start_date, end_date
                    )
                    if not schedule_api:
                        continue

                    await self.game_service._upsert_games_from_api(schedule_api, sport)
                    all_processed_games.extend(schedule_api)

                    await asyncio.sleep(1.1)
                except Exception as e:
                    logger.exception(f"Error syncing schedule for league {league_id} ({sport}): {e}")
        logger.info(f"Finished syncing schedules. Total games processed from API: {len(all_processed_games)}")

    async def _sync_standings(self, leagues: List[Dict]):
        """Fetch and store/update league standings."""
        logger.debug(f"Syncing standings for {len(leagues)} leagues...")
        if not leagues:
            return

        leagues_by_sport: Dict[str, List[Dict]] = {}
        for league in leagues:
            sport = league.get('sport')
            if sport:
                leagues_by_sport.setdefault(sport, []).append(league)

        all_processed_standings = []
        for sport, sport_leagues in leagues_by_sport.items():
            logger.info(f"Syncing standings for {len(sport_leagues)} leagues in sport: {sport}")
            for league in sport_leagues:
                league_id = league.get('id')
                if not league_id:
                    continue
                try:
                    season = league.get('season') or datetime.now(timezone.utc).year
                    response_data = await self.game_service._make_request(
                        sport, "standings", params={'league': str(league_id), 'season': str(season)}
                    )
                    standings_api = response_data.get('response', [])
                    if not standings_api:
                        continue

                    processed_standings = []
                    for standing_group_entry in standings_api:
                        standings_table = standing_group_entry.get('league', {}).get('standings', [[]])
                        if standings_table and isinstance(standings_table[0], list):
                            standings_table = standings_table[0]

                        for team_standing in standings_table:
                            team = team_standing.get('team', {})
                            if not team.get('id'):
                                continue
                            all_stats = team_standing.get('all', {})
                            goals_stats = all_stats.get('goals', {})
                            normalized = {
                                'league_id': league_id, 'team_id': team['id'], 'season': season,
                                'rank': team_standing.get('rank'), 'points': team_standing.get('points'),
                                'goals_diff': team_standing.get('goalsDiff'), 'form': team_standing.get('form'),
                                'status': team_standing.get('status'), 'description': team_standing.get('description'),
                                'group_name': team_standing.get('group'),
                                'played': all_stats.get('played'), 'won': all_stats.get('win'),
                                'draw': all_stats.get('draw'), 'lost': all_stats.get('lose'),
                                'goals_for': goals_stats.get('for'), 'goals_against': goals_stats.get('against'),
                                'sport': sport
                            }
                            processed_standings.append(normalized)

                    if processed_standings:
                        upsert_query = """
                            INSERT INTO standings (league_id, team_id, season, `rank`, points, goals_diff, form,
                                                  status, description, group_name, played, won, draw, lost,
                                                  goals_for, goals_against, sport, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, UTC_TIMESTAMP())
                            ON DUPLICATE KEY UPDATE
                                `rank`=VALUES(`rank`), points=VALUES(points), goals_diff=VALUES(goals_diff),
                                form=VALUES(form), status=VALUES(status), description=VALUES(description),
                                group_name=VALUES(group_name), played=VALUES(played), won=VALUES(won), draw=VALUES(draw),
                                lost=VALUES(lost), goals_for=VALUES(goals_for), goals_against=VALUES(goals_against),
                                sport=VALUES(sport), updated_at=UTC_TIMESTAMP()
                        """
                        data_tuples = [
                            (s['league_id'], s['team_id'], s['season'], s['rank'], s['points'], s['goals_diff'], s['form'],
                             s['status'], s['description'], s['group_name'], s['played'], s['won'], s['draw'], s['lost'],
                             s['goals_for'], s['goals_against'], s['sport'])
                            for s in processed_standings
                        ]
                        count = 0
                        for data_tuple in data_tuples:
                            try:
                                await self.db.execute(upsert_query, *data_tuple)
                                count += 1
                            except Exception as e:
                                logger.error(f"Error upserting standing for team {data_tuple[1]} in league {data_tuple[0]}: {e}")

                        all_processed_standings.extend(processed_standings)
                        logger.debug(f"Upserted {count}/{len(processed_standings)} standing entries for league {league_id}")
                    await asyncio.sleep(1.1)
                except Exception as e:
                    logger.exception(f"Error syncing standings for league {league_id} ({sport}): {e}")
        logger.info(f"Finished syncing standings. Total entries processed: {len(all_processed_standings)}")
