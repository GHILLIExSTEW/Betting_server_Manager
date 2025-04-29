import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import aiohttp
from data.db_manager import DatabaseManager
from data.cache_manager import CacheManager
from utils.errors import DataSyncError
import os
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class DataSyncService:
    def __init__(self, game_service):
        self.game_service = game_service
        self.db = DatabaseManager()
        self.cache = CacheManager()
        self._sync_task: Optional[asyncio.Task] = None
        self.running = False
        self.api_key = os.getenv('API_KEY')

    async def start(self):
        """Start the data sync service."""
        if not self.running:
            self.running = True
            self._sync_task = asyncio.create_task(self._daily_sync_loop())
            logger.info("Data sync service started")

    async def stop(self):
        """Stop the data sync service."""
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
        self.running = False
        logger.info("Data sync service stopped")

    async def _daily_sync_loop(self):
        """Main loop for daily data synchronization."""
        while self.running:
            try:
                # Calculate time until next sync (midnight UTC)
                now = datetime.utcnow()
                next_sync = (now + timedelta(days=1)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                time_until_next = (next_sync - now).total_seconds()

                # Wait until next sync time
                await asyncio.sleep(time_until_next)

                # Perform daily sync
                await self._sync_all_data()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in daily sync loop: {str(e)}")
                # If error occurs, wait 1 hour before retrying
                await asyncio.sleep(3600)

    async def _sync_all_data(self):
        """Sync all data from the API and normalize it."""
        try:
            logger.info("Starting daily data sync")
            
            # Get all supported sports from environment variables
            sports = {
                'football': os.getenv('FOOTBALL_API_HOST'),
                'basketball': os.getenv('BASKETBALL_API_HOST'),
                'hockey': os.getenv('HOCKEY_API_HOST'),
                'baseball': os.getenv('BASEBALL_API_HOST'),
                'american-football': os.getenv('AMERICAN_FOOTBALL_API_HOST'),
                'rugby': os.getenv('RUGBY_API_HOST'),
                'handball': os.getenv('HANDBALL_API_HOST'),
                'volleyball': os.getenv('VOLLEYBALL_API_HOST'),
                'cricket': os.getenv('CRICKET_API_HOST'),
                'formula1': os.getenv('FORMULA1_API_HOST'),
                'mma': os.getenv('MMA_API_HOST'),
                'tennis': os.getenv('TENNIS_API_HOST'),
                'golf': os.getenv('GOLF_API_HOST'),
                'cycling': os.getenv('CYCLING_API_HOST'),
                'soccer': os.getenv('SOCCER_API_HOST')
            }

            for sport, api_host in sports.items():
                if not api_host:
                    continue
                
                try:
                    # Fetch leagues for the sport
                    leagues = await self._fetch_leagues(sport)
                    
                    # Fetch and normalize games for each league
                    for league in leagues:
                        await self._sync_league_games(sport, league)
                        
                    # Fetch and normalize standings
                    await self._sync_standings(sport)
                    
                    # Fetch and normalize teams
                    await self._sync_teams(sport)
                    
                    logger.info(f"Successfully synced data for {sport}")
                    
                except Exception as e:
                    logger.error(f"Error syncing data for {sport}: {str(e)}")
                    continue

            logger.info("Daily data sync completed")
            
        except Exception as e:
            logger.error(f"Error in daily data sync: {str(e)}")
            raise DataSyncError(f"Failed to sync data: {str(e)}")

    async def _fetch_leagues(self, sport: str) -> List[Dict]:
        """Fetch leagues for a specific sport."""
        try:
            response = await self.game_service._make_request(sport, "leagues")
            if not isinstance(response, dict) or 'response' not in response:
                raise DataSyncError(f"Invalid response format for {sport} leagues")
            
            leagues = response['response']
            normalized_leagues = []
            
            for league in leagues:
                normalized_league = {
                    'id': league.get('league', {}).get('id'),
                    'name': league.get('league', {}).get('name'),
                    'type': league.get('league', {}).get('type'),
                    'logo': league.get('league', {}).get('logo'),
                    'country': league.get('country', {}).get('name'),
                    'country_code': league.get('country', {}).get('code'),
                    'country_flag': league.get('country', {}).get('flag'),
                    'season': league.get('seasons', [{}])[0].get('year'),
                    'sport': sport
                }
                normalized_leagues.append(normalized_league)
            
            # Store in database
            await self.db.execute(
                """
                INSERT INTO leagues (id, name, type, logo, country, country_code, 
                                    country_flag, season, sport)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (id) DO UPDATE
                SET name = $2, type = $3, logo = $4, country = $5,
                    country_code = $6, country_flag = $7, season = $8, sport = $9
                """,
                *normalized_league.values()
            )
            
            return normalized_leagues
            
        except Exception as e:
            logger.error(f"Error fetching leagues for {sport}: {str(e)}")
            raise

    async def _sync_league_games(self, sport: str, league: Dict):
        """Sync and normalize games for a specific league."""
        try:
            # Get games for the next 7 days
            start_date = datetime.utcnow()
            end_date = start_date + timedelta(days=7)
            
            games = await self.game_service.get_league_schedule(
                sport, 
                str(league['id']), 
                start_date, 
                end_date
            )
            
            normalized_games = []
            for game in games:
                normalized_game = {
                    'id': game.get('fixture', {}).get('id'),
                    'league_id': league['id'],
                    'home_team_id': game.get('teams', {}).get('home', {}).get('id'),
                    'away_team_id': game.get('teams', {}).get('away', {}).get('id'),
                    'home_team_name': game.get('teams', {}).get('home', {}).get('name'),
                    'away_team_name': game.get('teams', {}).get('away', {}).get('name'),
                    'home_team_logo': game.get('teams', {}).get('home', {}).get('logo'),
                    'away_team_logo': game.get('teams', {}).get('away', {}).get('logo'),
                    'start_time': game.get('fixture', {}).get('date'),
                    'status': game.get('fixture', {}).get('status', {}).get('long'),
                    'score': game.get('goals', {}),
                    'venue': game.get('fixture', {}).get('venue', {}).get('name'),
                    'referee': game.get('fixture', {}).get('referee'),
                    'sport': sport
                }
                normalized_games.append(normalized_game)
            
            # Store in database
            for game in normalized_games:
                await self.db.execute(
                    """
                    INSERT INTO games (id, league_id, home_team_id, away_team_id,
                                     home_team_name, away_team_name, home_team_logo,
                                     away_team_logo, start_time, status, score,
                                     venue, referee, sport)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                    ON CONFLICT (id) DO UPDATE
                    SET league_id = $2, home_team_id = $3, away_team_id = $4,
                        home_team_name = $5, away_team_name = $6, home_team_logo = $7,
                        away_team_logo = $8, start_time = $9, status = $10,
                        score = $11, venue = $12, referee = $13, sport = $14
                    """,
                    *game.values()
                )
            
        except Exception as e:
            logger.error(f"Error syncing games for league {league['id']}: {str(e)}")
            raise

    async def _sync_standings(self, sport: str):
        """Sync and normalize standings for a sport."""
        try:
            # Get all leagues for the sport
            leagues = await self.db.fetch(
                "SELECT id FROM leagues WHERE sport = $1",
                sport
            )
            
            for league in leagues:
                response = await self.game_service._make_request(
                    sport, 
                    f"standings?league={league['id']}&season={datetime.utcnow().year}"
                )
                
                if not isinstance(response, dict) or 'response' not in response:
                    continue
                
                standings = response['response']
                normalized_standings = []
                
                for standing in standings:
                    for team_standing in standing.get('league', {}).get('standings', [[]])[0]:
                        normalized_standing = {
                            'league_id': league['id'],
                            'team_id': team_standing.get('team', {}).get('id'),
                            'rank': team_standing.get('rank'),
                            'points': team_standing.get('points'),
                            'goals_diff': team_standing.get('goalsDiff'),
                            'form': team_standing.get('form'),
                            'played': team_standing.get('all', {}).get('played'),
                            'won': team_standing.get('all', {}).get('win'),
                            'draw': team_standing.get('all', {}).get('draw'),
                            'lost': team_standing.get('all', {}).get('lose'),
                            'goals_for': team_standing.get('all', {}).get('goals', {}).get('for'),
                            'goals_against': team_standing.get('all', {}).get('goals', {}).get('against'),
                            'sport': sport
                        }
                        normalized_standings.append(normalized_standing)
                
                # Store in database
                for standing in normalized_standings:
                    await self.db.execute(
                        """
                        INSERT INTO standings (league_id, team_id, rank, points,
                                            goals_diff, form, played, won, draw,
                                            lost, goals_for, goals_against, sport)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                        ON CONFLICT (league_id, team_id) DO UPDATE
                        SET rank = $3, points = $4, goals_diff = $5, form = $6,
                            played = $7, won = $8, draw = $9, lost = $10,
                            goals_for = $11, goals_against = $12, sport = $13
                        """,
                        *standing.values()
                    )
            
        except Exception as e:
            logger.error(f"Error syncing standings for {sport}: {str(e)}")
            raise

    async def _sync_teams(self, sport: str):
        """Sync and normalize team data for a sport."""
        try:
            # Get all leagues for the sport
            leagues = await self.db.fetch(
                "SELECT id FROM leagues WHERE sport = $1",
                sport
            )
            
            for league in leagues:
                response = await self.game_service._make_request(
                    sport, 
                    f"teams?league={league['id']}&season={datetime.utcnow().year}"
                )
                
                if not isinstance(response, dict) or 'response' not in response:
                    continue
                
                teams = response['response']
                normalized_teams = []
                
                for team in teams:
                    team_data = team.get('team', {})
                    venue_data = team.get('venue', {})
                    
                    normalized_team = {
                        'id': team_data.get('id'),
                        'name': team_data.get('name'),
                        'code': team_data.get('code'),
                        'country': team_data.get('country'),
                        'founded': team_data.get('founded'),
                        'national': team_data.get('national'),
                        'logo': team_data.get('logo'),
                        'venue_name': venue_data.get('name'),
                        'venue_address': venue_data.get('address'),
                        'venue_city': venue_data.get('city'),
                        'venue_capacity': venue_data.get('capacity'),
                        'venue_surface': venue_data.get('surface'),
                        'venue_image': venue_data.get('image'),
                        'sport': sport
                    }
                    normalized_teams.append(normalized_team)
                
                # Store in database
                for team in normalized_teams:
                    await self.db.execute(
                        """
                        INSERT INTO teams (id, name, code, country, founded,
                                         national, logo, venue_name, venue_address,
                                         venue_city, venue_capacity, venue_surface,
                                         venue_image, sport)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                        ON CONFLICT (id) DO UPDATE
                        SET name = $2, code = $3, country = $4, founded = $5,
                            national = $6, logo = $7, venue_name = $8,
                            venue_address = $9, venue_city = $10,
                            venue_capacity = $11, venue_surface = $12,
                            venue_image = $13, sport = $14
                        """,
                        *team.values()
                    )
            
        except Exception as e:
            logger.error(f"Error syncing teams for {sport}: {str(e)}")
            raise 