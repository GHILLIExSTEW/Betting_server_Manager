"""Configuration for team name mappings."""

# Team name mappings for logo file naming
TEAM_MAPPINGS = {
    # NHL Teams
    "Oilers": "edmonton_oilers",
    "Flames": "calgary_flames",
    "Canucks": "vancouver_canucks",
    "Maple Leafs": "toronto_maple_leafs",
    "Senators": "ottawa_senators",
    "Canadiens": "montreal_canadiens",
    "Bruins": "boston_bruins",
    "Sabres": "buffalo_sabres",
    "Rangers": "new_york_rangers",
    "Islanders": "new_york_islanders",
    "Devils": "new_jersey_devils",
    "Flyers": "philadelphia_flyers",
    "Penguins": "pittsburgh_penguins",
    "Capitals": "washington_capitals",
    "Hurricanes": "carolina_hurricanes",
    "Panthers": "florida_panthers",
    "Lightning": "tampa_bay_lightning",
    "Red Wings": "detroit_red_wings",
    "Blackhawks": "chicago_blackhawks",
    "Blues": "st_louis_blues",
    "Wild": "minnesota_wild",
    "Jets": "winnipeg_jets",
    "Avalanche": "colorado_avalanche",
    "Stars": "dallas_stars",
    "Predators": "nashville_predators",
    "Coyotes": "arizona_coyotes",
    "Golden Knights": "vegas_golden_knights",
    "Kraken": "seattle_kraken",
    "Sharks": "san_jose_sharks",
    "Kings": "los_angeles_kings",
    "Ducks": "anaheim_ducks",
    
    # NFL Teams
    "49ers": "san_francisco_49ers",
    "Bears": "chicago_bears",
    "Bengals": "cincinnati_bengals",
    "Bills": "buffalo_bills",
    "Broncos": "denver_broncos",
    "Browns": "cleveland_browns",
    "Buccaneers": "tampa_bay_buccaneers",
    "Cardinals": "arizona_cardinals",
    "Chargers": "los_angeles_chargers",
    "Chiefs": "kansas_city_chiefs",
    "Colts": "indianapolis_colts",
    "Cowboys": "dallas_cowboys",
    "Dolphins": "miami_dolphins",
    "Eagles": "philadelphia_eagles",
    "Falcons": "atlanta_falcons",
    "Giants": "new_york_giants",
    "Jaguars": "jacksonville_jaguars",
    "Jets": "new_york_jets",
    "Lions": "detroit_lions",
    "Packers": "green_bay_packers",
    "Panthers": "carolina_panthers",
    "Patriots": "new_england_patriots",
    "Raiders": "las_vegas_raiders",
    "Rams": "los_angeles_rams",
    "Ravens": "baltimore_ravens",
    "Saints": "new_orleans_saints",
    "Seahawks": "seattle_seahawks",
    "Steelers": "pittsburgh_steelers",
    "Texans": "houston_texans",
    "Titans": "tennessee_titans",
    "Vikings": "minnesota_vikings",
    "Commanders": "washington_commanders"
}

def normalize_team_name(team_name: str) -> str:
    """Normalize team name to match logo file naming convention."""
    # First check if we have a direct mapping
    if team_name in TEAM_MAPPINGS:
        return TEAM_MAPPINGS[team_name]
    
    # If no direct mapping, try to normalize the name
    normalized = team_name.lower().replace(" ", "_")
    return normalized 