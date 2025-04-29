import logging
import aiohttp
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class SportsAPI:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.api_key = os.getenv('API_KEY')
        self.api_hosts = {
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
            if not self.session:
                await self.start()

            # Determine the sport from the league
            sport = self._get_sport_from_league(league)
            if not sport:
                raise ValueError(f"Unknown league: {league}")

            headers = {
                'x-rapidapi-key': self.api_key,
                'x-rapidapi-host': self.api_hosts[sport].split('//')[1]
            }

            async with self.session.get(
                f"{self.api_hosts[sport]}/fixtures",
                params={'league': league, 'season': datetime.now().year},
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('response', [])
                else:
                    logger.error(f"API request failed with status {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Error getting live fixtures: {str(e)}")
            return []

    def _get_sport_from_league(self, league: str) -> Optional[str]:
        """Determine the sport from the league code."""
        # This is a simple mapping - you might need to expand this based on your needs
        league_mappings = {
            'nfl': 'american-football',
            'nba': 'basketball',
            'mlb': 'baseball',
            'nhl': 'hockey',
            'premier-league': 'football',
            'la-liga': 'football',
            'bundesliga': 'football',
            'serie-a': 'football',
            'ligue-1': 'football'
        }
        return league_mappings.get(league.lower()) 