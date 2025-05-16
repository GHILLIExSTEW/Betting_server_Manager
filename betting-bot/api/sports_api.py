```python
import logging
import aiohttp
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json
import os
from dotenv import load_dotenv
import thesportsdb  # Added for thesportsdb

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class SportsAPI:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.api_key = os.getenv('API_KEY')
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

    def _get_sport_from_league(self, league: str) -> Optional[str]:
        """Map league to TheSportsDB league ID."""
        league_mappings = {
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
        return league_mappings.get(league, None)
```
