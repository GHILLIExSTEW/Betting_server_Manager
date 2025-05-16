# api/sports_api.py
# Service for fetching sports data from TheSportsDB API

import logging
import aiohttp
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta, timezone
import json
import os
from dotenv import load_dotenv
import thesportsdb  # For thesportsdb API
import aiosqlite  # For database operations

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class SportsAPI:
    def __init__(self, db_path: str = "data/betting.db"):
        self.session: Optional[aiohttp.ClientSession] = None
        self.api_key = os.getenv('API_KEY')
        self.db_path = db_path
        # Set TheSportsDB API key
        if self.api_key:
            os.environ["THESPORTSDB_API_KEY"] = self.api_key

    async def start(self):
        """Initialize the API client session."""
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def close(self):
        """Close the API client session."""
        if self.session:
            await self.session.close()
            self.session = None

    async def get_live_fixtures(self, league: str) -> List[Dict]:
        """Get live fixtures for a specific league."""
        try:
            # Map league to TheSportsDB league ID
            league_id = self._get_sport_from_league(league)
            if not league_id:
                logger.error(f"Unknown league: {league}")
                return []

            # Fetch upcoming events using thesportsdb
            events_data = thesportsdb.events.nextLeagueEvents(league_id)
            if not events_data or "events" not in events_data:
                logger.error(f"No events found for league {league} (ID: {league_id})")
                return []

            # Map thesportsdb events to expected fixture format
            fixtures = [
                {
                    "id": event.get("idEvent", ""),
                    "home_team_name": event.get("strHomeTeam", "Unknown"),
                    "away_team_name": event.get("strAwayTeam", "Unknown"),
                    "start_time": event.get("dateEvent", "Time N/A")
                }
                for event in events_data["events"][:25]  # Limit to 25 as per original
            ]
            return fixtures

        except Exception as e:
            logger.error(f"Error getting live fixtures: {str(e)}")
            return []

    async def fetch_and_save_daily_games(self):
        """Fetch scheduled games for all leagues and save raw JSON."""
        try:
            # Ensure API session is started
            await self.start()

            # Create directory for raw JSON
            raw_data_dir = "data/raw_games"
            os.makedirs(raw_data_dir, exist_ok=True)

            # Get current date for file naming
            current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            saved_files = []

            # Iterate through all supported leagues
            for league, league_id in self._get_league_mappings().items():
                if not league_id:
                    logger.info(f"Skipping unsupported league: {league}")
                    continue

                try:
                    # Fetch upcoming events
                    events_data = thesportsdb.events.nextLeagueEvents(league_id)
                    if not events_data or "events" not in events_data:
                        logger.warning(f"No events found for league {league} (ID: {league_id})")
                        continue

                    # Save raw JSON
                    file_path = os.path.join(raw_data_dir, f"{current_date}_{league}.json")
                    with open(file_path, "w") as f:
                        json.dump(events_data, f, indent=2)
                    saved_files.append(file_path)
                    logger.info(f"Saved raw JSON for {league} to {file_path}")

                except Exception as e:
                    logger.error(f"Error fetching games for {league}: {str(e)}")

            return saved_files

        except Exception as e:
            logger.error(f"Error in fetch_and_save_daily_games: {str(e)}")
            return []

    async def process_raw_games_to_db(self, json_file_path: str):
        """Process raw JSON game data and insert into api_games table."""
        try:
            # Extract league from file name
            file_name = os.path.basename(json_file_path)
            league = file_name.split("_")[-1].replace(".json", "")
            league_id = self._get_sport_from_league(league)
            if not league_id:
                logger.error(f"Unknown league in file: {league}")
                return

            # Load raw JSON
            with open(json_file_path, "r") as f:
                events_data = json.load(f)

            if not events_data or "events" not in events_data:
                logger.warning(f"No events in JSON file: {json_file_path}")
                return

            # Map league to sport
            league_info = self._get_league_info(league)
            sport = league_info.get("sport", "Unknown")
            league_name = league_info.get("name", league)

            # Connect to database
            async with aiosqlite.connect(self.db_path) as db:
                for event in events_data["events"]:
                    try:
                        # Map thesportsdb fields to api_games schema
                        game_data = {
                            "id": int(event.get("idEvent", 0)) or None,
                            "sport": sport,
                            "league_id": int(league_id) if league_id else None,
                            "league_name": league_name,
                            "home_team_id": int(event.get("idHomeTeam", 0)) or None,
                            "away_team_id": int(event.get("idAwayTeam", 0)) or None,
                            "start_time": event.get("dateEvent", None),
                            "end_time": None,  # Not available in nextLeagueEvents
                            "status": "scheduled",
                            "score": None,
                            "venue": event.get("strVenue", None),
                            "referee": None,
                        }

                        # Validate and format start_time
                        if game_data["start_time"]:
                            try:
                                # Convert dateEvent (YYYY-MM-DD) to timestamp
                                dt = datetime.strptime(game_data["start_time"], "%Y-%m-%d")
                                game_data["start_time"] = dt.replace(tzinfo=timezone.utc).isoformat()
                            except ValueError:
                                logger.warning(f"Invalid start_time for event {game_data['id']}: {game_data['start_time']}")
                                game_data["start_time"] = None

                        # Skip if critical fields are missing
                        if not game_data["id"] or not game_data["sport"]:
                            logger.warning(f"Skipping event with missing id or sport: {event}")
                            continue

                        # Insert into api_games table
                        await db.execute(
                            """
                            INSERT INTO api_games (
                                id, sport, league_id, league_name, home_team_id, away_team_id,
                                start_time, end_time, status, score, venue, referee
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(id) DO UPDATE SET
                                sport=excluded.sport,
                                league_id=excluded.league_id,
                                league_name=excluded.league_name,
                                home_team_id=excluded.home_team_id,
                                away_team_id=excluded.away_team_id,
                                start_time=excluded.start_time,
                                end_time=excluded.end_time,
                                status=excluded.status,
                                score=excluded.score,
                                venue=excluded.venue,
                                referee=excluded.referee,
                                updated_at=CURRENT_TIMESTAMP
                            """,
                            (
                                game_data["id"],
                                game_data["sport"],
                                game_data["league_id"],
                                game_data["league_name"],
                                game_data["home_team_id"],
                                game_data["away_team_id"],
                                game_data["start_time"],
                                game_data["end_time"],
                                game_data["status"],
                                game_data["score"],
                                game_data["venue"],
                                game_data["referee"],
                            )
                        )
                        await db.commit()
                        logger.debug(f"Inserted/updated game {game_data['id']} for {league}")

                    except Exception as e:
                        logger.error(f"Error processing event {event.get('idEvent', 'unknown')} for {league}: {str(e)}")

        except Exception as e:
            logger.error(f"Error processing JSON file {json_file_path}: {str(e)}")

    async def run_daily_fetch(self):
        """Run daily game fetch at 03:00 AM UTC."""
        while True:
            try:
                now = datetime.now(timezone.utc)
                # Calculate time until next 03:00 AM UTC
                next_run = now.replace(hour=3, minute=0, second=0, microsecond=0)
                if now.hour >= 3:
                    next_run += timedelta(days=1)
                seconds_until_run = (next_run - now).total_seconds()

                logger.info(f"Scheduling next game fetch at {next_run} UTC")
                await asyncio.sleep(seconds_until_run)

                # Fetch and process games
                saved_files = await self.fetch_and_save_daily_games()
                for file_path in saved_files:
                    await self.process_raw_games_to_db(file_path)

            except Exception as e:
                logger.error(f"Error in daily fetch loop: {str(e)}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

    def _get_sport_from_league(self, league: str) -> Optional[str]:
        """Map league to TheSportsDB league ID."""
        return self._get_league_mappings().get(league, None)

    def _get_league_mappings(self) -> Dict[str, Optional[str]]:
        """Return mapping of leagues to TheSportsDB league IDs."""
        return {
            "NFL": "4391",  # American Football
            "EPL": "4328",  # Soccer
            "NBA": "4387",  # Basketball
            "MLB": "4424",  # Baseball
            "NHL": "4380",  # Hockey
            "La Liga": "4335",  # Soccer
            "NCAA": "4329",  # American Football (also 4330 for Basketball)
            "Bundesliga": "4332",  # Soccer
            "Serie A": "4331",  # Soccer
            "Ligue 1": "4334",  # Soccer
            "MLS": "4346",  # Soccer
            "Formula 1": "4358",  # Motorsport
            "Tennis": "4359",  # Tennis
            "UFC/MMA": "4360",  # Fighting
            "WNBA": "4410",  # Basketball
            "CFL": None,  # Unsupported
            "AFL": None,  # Unsupported
            "Darts": None,  # Unsupported
            "EuroLeague": "4356",  # Basketball
            "NPB": "4412",  # Baseball
            "KBO": "4413",  # Baseball
            "KHL": "4378"  # Hockey
        }

    def _get_league_info(self, league: str) -> Dict[str, str]:
        """Return sport and name for a league."""
        league_info = {
            "NFL": {"sport": "American Football", "name": "NFL"},
            "EPL": {"sport": "Soccer", "name": "English Premier League"},
            "NBA": {"sport": "Basketball", "name": "NBA"},
            "MLB": {"sport": "Baseball", "name": "MLB"},
            "NHL": {"sport": "Ice Hockey", "name": "NHL"},
            "La Liga": {"sport": "Soccer", "name": "La Liga"},
            "NCAA": {"sport": "American Football", "name": "NCAA"},
            "Bundesliga": {"sport": "Soccer", "name": "Bundesliga"},
            "Serie A": {"sport": "Soccer", "name": "Serie A"},
            "Ligue 1": {"sport": "Soccer", "name": "Ligue 1"},
            "MLS": {"sport": "Soccer", "name": "MLS"},
            "Formula 1": {"sport": "Motorsport", "name": "Formula 1"},
            "Tennis": {"sport": "Tennis", "name": "Tennis"},
            "UFC/MMA": {"sport": "Fighting", "name": "UFC"},
            "WNBA": {"sport": "Basketball", "name": "WNBA"},
            "CFL": {"sport": "American Football", "name": "CFL"},
            "AFL": {"sport": "Australian Football", "name": "AFL"},
            "Darts": {"sport": "Darts", "name": "PDC Darts"},
            "EuroLeague": {"sport": "Basketball", "name": "EuroLeague"},
            "NPB": {"sport": "Baseball", "name": "NPB"},
            "KBO": {"sport": "Baseball", "name": "KBO"},
            "KHL": {"sport": "Ice Hockey", "name": "KHL"}
        }
        return league_info.get(league, {"sport": "Unknown", "name": league})

# Example usage for standalone execution
if __name__ == "__main__":
    async def main():
        api = SportsAPI()
        try:
            await api.run_daily_fetch()
        finally:
            await api.close()

    asyncio.run(main())
