# config/leagues.py
# Mapping of allowed leagues to TheSportsDB league IDs and metadata

# League mappings with TheSportsDB IDs
LEAGUE_IDS = {
    "NFL": {"id": "4391", "sport": "American Football", "name": "NFL"},
    "EPL": {"id": "4328", "sport": "Soccer", "name": "English Premier League"},
    "NBA": {"id": "4387", "sport": "Basketball", "name": "NBA"},
    "MLB": {"id": "4424", "sport": "Baseball", "name": "MLB"},
    "NHL": {"id": "4380", "sport": "Ice Hockey", "name": "NHL"},
    "La Liga": {"id": "4335", "sport": "Soccer", "name": "La Liga"},
    "NCAA": {"id": "4329", "sport": "American Football", "name": "NCAA Football"},  # Also 4330 for Basketball
    "Bundesliga": {"id": "4332", "sport": "Soccer", "name": "Bundesliga"},
    "Serie A": {"id": "4331", "sport": "Soccer", "name": "Serie A"},
    "Ligue 1": {"id": "4334", "sport": "Soccer", "name": "Ligue 1"},
    "MLS": {"id": "4346", "sport": "Soccer", "name": "MLS"},
    "Formula 1": {"id": "4358", "sport": "Motorsport", "name": "Formula 1"},
    "Tennis": {"id": "4359", "sport": "Tennis", "name": "Tennis"},
    "UFC/MMA": {"id": "4360", "sport": "Fighting", "name": "UFC"},
    "WNBA": {"id": "4410", "sport": "Basketball", "name": "WNBA"},
    "CFL": {"id": None, "sport": "American Football", "name": "CFL"},  # Unsupported by TheSportsDB
    "AFL": {"id": None, "sport": "Australian Football", "name": "AFL"},  # Unsupported
    "Darts": {"id": None, "sport": "Darts", "name": "PDC Darts"},  # Player-based
    "EuroLeague": {"id": "4356", "sport": "Basketball", "name": "EuroLeague"},
    "NPB": {"id": "4412", "sport": "Baseball", "name": "NPB"},
    "KBO": {"id": "4413", "sport": "Baseball", "name": "KBO"},
    "KHL": {"id": "4378", "sport": "Ice Hockey", "name": "KHL"}
}

# Static team lists for unsupported leagues
CFL_TEAMS = [
    "BC Lions",
    "Calgary Stampeders",
    "Edmonton Elks",
    "Saskatchewan Roughriders",
    "Winnipeg Blue Bombers",
    "Hamilton Tiger-Cats",
    "Toronto Argonauts",
    "Ottawa Redblacks",
    "Montreal Alouettes"
]

AFL_TEAMS = [
    "Adelaide Crows",
    "Brisbane Lions",
    "Carlton Blues",
    "Collingwood Magpies",
    "Essendon Bombers",
    "Fremantle Dockers",
    "Geelong Cats",
    "Gold Coast Suns",
    "Greater Western Sydney Giants",
    "Hawthorn Hawks",
    "Melbourne Demons",
    "North Melbourne Kangaroos",
    "Port Adelaide Power",
    "Richmond Tigers",
    "St Kilda Saints",
    "Sydney Swans",
    "West Coast Eagles",
    "Western Bulldogs"
]

# Note: Darts players are stored separately in utils/helpers.py due to player-based nature
