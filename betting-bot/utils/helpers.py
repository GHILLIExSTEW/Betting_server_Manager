# utils/helpers.py
# Utility functions for NCAA validation, logo processing, and Darts players

from typing import List, Optional
from PIL import Image
import io
import requests
import thesportsdb
from config.leagues import LEAGUE_IDS, CFL_TEAMS, AFL_TEAMS


# NCAA teams list (661 Division I and II teams, abridged for brevity)
NCAA_TEAMS = [
    "Abilene Christian University",
    "Air Force (United States Air Force Academy)",
    "Akron (University of Akron)",
    "Alabama A&M University",
    "Alabama State University",
    # ... include all 661 teams from your provided list ...
    "Young Harris College",
]

# PDC Darts players (128 Tour Card holders for 2025)
DARTS_PLAYERS = [
    "Adam Gawlas",
    "Adam Hunt",
    "Adam Smith-Neale",
    "Adam Warner",
    "Alan Soutar",
    "Alexander Merkx",
    "Andrew Gilding",
    "Andy Baetens",
    "Arron Monk",
    "Barry van Peer",
    "Ben Robb",
    "Berry van Peer",
    "Boris Krčmar",
    "Bradley Brooks",
    "Brendan Dolan",
    "Brett Claydon",
    "Callan Rydz",
    "Cameron Menzies",
    "Chris Dobey",
    "Chris Landman",
    "Christian Kist",
    "Christian Perez",
    "Christopher Toonders",
    "Connor Scutt",
    "Damon Heta",
    "Daniel Klose",
    "Daniel Larsson",
    "Danny Jansen",
    "Danny Lauby",
    "Danny Noppert",
    "Danny van Trijp",
    "Darius Labanauskas",
    "Daryl Gurney",
    "Dave Chisnall",
    "David Cameron",
    "Dennis Nilsson",
    "Devon Petersen",
    "Dimitri Van den Bergh",
    "Dirk van Duijvenbode",
    "Dom Taylor",
    "Dominic Hogan",
    "Dylan Slevin",
    "Florian Hempel",
    "Gabriel Clemens",
    "Gary Anderson",
    "George Killington",
    "Gerwyn Price",
    "Gian van Veen",
    "Graham Hall",
    "Graham Usher",
    "Haupai Puha",
    "Ian White",
    "Jacek Krupka",
    "Jack Main",
    "James Hurrell",
    "James Wade",
    "Jamie Hughes",
    "Jeffrey de Graaf",
    "Jeffrey de Zwaan",
    "Jeffrey Sparidaans",
    "Jermaine Wattimena",
    "Jim Williams",
    "Joe Cullen",
    "John Henderson",
    "Jonny Clayton",
    "José de Sousa",
    "Josh Payne",
    "Josh Rock",
    "Jules van Dongen",
    "Jurjen van der Velde",
    "Justin Hood",
    "Karel Sedláček",
    "Keane Barry",
    "Kevin Doets",
    "Kevin Troppmann",
    "Krzysztof Ratajski",
    "Lee Evans",
    "Leonard Gates",
    "Lewy Williams",
    "Lourence Ilagan",
    "Luc Peters",
    "Luke Humphries",
    "Luke Littler",
    "Luke Woodhouse",
    "Maik Kuivenhoven",
    "Mario Vandenbogaerde",
    "Martin Lukeman",
    "Martin Schindler",
    "Matt Campbell",
    "Mensur Suljović",
    "Michael Mansell",
    "Michael Smith",
    "Michael van Gerwen",
    "Mickey Mansell",
    "Mike De Decker",
    "Mindaugas Barauskas",
    "Nathan Aspinall",
    "Nathan Rafferty",
    "Nick Kenny",
    "Niels Zonneveld",
    "Noa-Lynn van Leuven",
    "Owen Bates",
    "Patrick Geeraets",
    "Peter Wright",
    "Raymond van Barneveld",
    "Ricardo Pietreczko",
    "Richard Veenstra",
    "Ricky Evans",
    "Ritchie Edhouse",
    "Rob Cross",
    "Robert Owen",
    "Ross Smith",
    "Rowby-John Rodriguez",
    "Ryan Joyce",
    "Ryan Meikle",
    "Ryan Searle",
    "Scott Williams",
    "Sebastian Białecki",
    "Simon Whitlock",
    "Stephen Bunting",
    "Stephen Burton",
    "Steve Beaton",
    "Steve Lennon",
    "Thibault Tricole",
    "Tim Wolters",
    "Tomoya Goto",
    "Vincent van der Voort",
    "Wesley Plaisier",
    "Wessel Nijman",
    "William O’Connor",
]


def is_valid_ncaa_team(team_name: str) -> bool:
    """Check if a team name is in the NCAA teams list."""
    return any(team_name.lower() in ncaa_team.lower() for ncaa_team in NCAA_TEAMS)


def is_valid_darts_player(player_name: str) -> bool:
    """Check if a player name is in the PDC Darts players list."""
    return player_name in DARTS_PLAYERS


def get_league_teams(league_key: str) -> List[str]:
    """Get list of teams for a given league."""
    league = LEAGUE_IDS.get(league_key, {})
    league_id = league.get("id")

    if league_id:
        try:
            teams_data = thesportsdb.teams.leagueTeams(league_id)
            if teams_data and "teams" in teams_data:
                return [team["strTeam"] for team in teams_data["teams"]]
        except Exception:
            pass
    elif league_key == "CFL":
        return CFL_TEAMS
    elif league_key == "AFL":
        return AFL_TEAMS
    elif league_key == "Darts":
        return DARTS_PLAYERS  # Return players for Darts
    return []


def download_logo(url: str, save_path: str) -> bool:
    """Download and save a logo from a URL."""
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            img = Image.open(io.BytesIO(response.content))
            img.save(save_path)
            return True
    except Exception:
        pass
    return False


def get_team_logo_path(team_name: str, league_key: str) -> Optional[str]:
    """Get the file path for a team’s logo, downloading if necessary."""
    league = LEAGUE_IDS.get(league_key, {})
    league_id = league.get("id")
    save_path = f"assets/logos/{team_name.replace('/', '_')}.png"

    if not os.path.exists(save_path) and league_id:
        try:
            teams_data = thesportsdb.teams.leagueTeams(league_id)
            if teams_data and "teams" in teams_data:
                for team in teams_data["teams"]:
                    if team["strTeam"].lower() == team_name.lower():
                        logo_url = team.get("strTeamBadge")
                        if logo_url and download_logo(logo_url, save_path):
                            return save_path
        except Exception:
            pass
    elif os.path.exists(save_path):
        return save_path
    return None


def get_league_logo_path(league_key: str) -> Optional[str]:
    """Get the file path for a league’s logo, downloading if necessary."""
    league = LEAGUE_IDS.get(league_key, {})
    league_id = league.get("id")
    save_path = f"assets/leagues/{league_key}.png"

    if not os.path.exists(save_path) and league_id:
        try:
            league_data = thesportsdb.leagues.leagueInfo(league_id)
            if league_data and "leagues" in league_data:
                logo_url = league_data["leagues"][0].get("strBadge")
                if logo_url and download_logo(logo_url, save_path):
                    return save_path
        except Exception:
            pass
    elif os.path.exists(save_path):
        return save_path
    return None
