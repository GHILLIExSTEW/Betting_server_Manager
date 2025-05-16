# services/api_service.py
# Service module for handling TheSportsDB API calls

from typing import List, Dict, Optional
import thesportsdb
from config.leagues import LEAGUE_IDS
from utils.helpers import (
    get_league_teams,
    is_valid_ncaa_team,
    is_valid_darts_player,
    get_team_logo_path,
    get_league_logo_path,
)


class ApiService:
    """Service for fetching sports data from TheSportsDB API."""

    @staticmethod
    async def get_upcoming_events(league_key: str) -> List[Dict]:
        """Fetch upcoming events for a league."""
        league = LEAGUE_IDS.get(league_key, {})
        league_id = league.get("id")
        events = []

        if league_id:
            try:
                events_data = thesportsdb.events.nextLeagueEvents(league_id)
                if events_data and "events" in events_data:
                    for event in events_data["events"]:
                        home_team = event.get("strHomeTeam", "")
                        away_team = event.get("strAwayTeam", "")
                        # Validate NCAA teams if applicable
                        if league_key == "NCAA":
                            if is_valid_ncaa_team(home_team) and is_valid_ncaa_team(away_team):
                                events.append(event)
                        else:
                            events.append(event)
            except Exception:
                pass
        elif league_key in ["CFL", "AFL"]:
            # Mock events for unsupported leagues
            teams = get_league_teams(league_key)
            if len(teams) >= 2:
                events.append({
                    "idEvent": f"mock_{league_key}_{teams[0]}_vs_{teams[1]}",
                    "strHomeTeam": teams[0],
                    "strAwayTeam": teams[1],
                    "strEvent": f"{teams[0]} vs {teams[1]}",
                    "dateEvent": "2025-05-16"
                })
        elif league_key == "Darts":
            # Mock Darts event with players
            players = get_league_teams(league_key)[:2]  # First two players
            if len(players) >= 2 and is_valid_darts_player(players[0]) and is_valid_darts_player(players[1]):
                events.append({
                    "idEvent": f"mock_Darts_{players[0]}_vs_{players[1]}",
                    "strHomeTeam": players[0],
                    "strAwayTeam": players[1],
                    "strEvent": f"{players[0]} vs {players[1]}",
                    "dateEvent": "2025-05-16"
                })

        return events

    @staticmethod
    async def get_event_details(event_id: str) -> Optional[Dict]:
        """Fetch details for a specific event."""
        try:
            event_data = thesportsdb.events.eventInfo(event_id)
            if event_data and "events" in event_data:
                return event_data["events"][0]
        except Exception:
            pass
        return None

    @staticmethod
    async def get_league_standings(league_key: str, season: str = "2024-2025") -> List[Dict]:
        """Fetch standings for a league."""
        league = LEAGUE_IDS.get(league_key, {})
        league_id = league.get("id")
        standings = []

        if league_id:
            try:
                standings_data = thesportsdb.leagues.leagueSeasonTable(league_id, season)
                if standings_data and "table" in standings_data:
                    standings = standings_data["table"]
            except Exception:
                pass
        return standings

    @staticmethod
    async def get_teams(league_key: str) -> List[str]:
        """Fetch teams for a league."""
        return get_league_teams(league_key)

    @staticmethod
    async def get_team_logo(team_name: str, league_key: str) -> Optional[str]:
        """Get the file path for a team’s logo."""
        return get_team_logo_path(team_name, league_key)

    @staticmethod
    async def get_league_logo(league_key: str) -> Optional[str]:
        """Get the file path for a league’s logo."""
        return get_league_logo_path(league_key)

    @staticmethod
    async def get_player_details(player_name: str, league_key: str) -> Optional[Dict]:
        """Fetch details for a player (e.g., Darts, Tennis, UFC/MMA)."""
        if league_key == "Darts" and is_valid_darts_player(player_name):
            try:
                player_data = thesportsdb.players.playerInfo(player_name)
                if player_data and "players" in player_data:
                    return player_data["players"][0]
            except Exception:
                pass
        return None
