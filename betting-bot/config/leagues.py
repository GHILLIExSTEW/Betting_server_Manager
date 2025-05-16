# betting-bot/config/leagues.py

# LEAGUE_CONFIG stores detailed settings for each league key.
# The keys (e.g., "NFL", "EPL") are what the user might select or what your bot uses internally.
# 'name' is the display name.
# 'id' is TheSportsDB league ID (can be None if not applicable or for manual entry leagues).
# 'sport_type' helps group similar sports (e.g., "Team Sport", "Individual Player", "Racing").
# 'participant_label' is what you call the main entity (Team, Player, Driver, etc.).
# 'team_placeholder' is an example for that entity.
# 'line_placeholder_game' is for game/match-level bets.
# 'line_placeholder_player' is for player-specific props (if applicable).

LEAGUE_CONFIG = {
    "NFL": {
        "id": "4391", "sport": "American Football", "name": "NFL",
        "sport_type": "Team Sport",
        "participant_label": "Team / Player", # For team bets or player props
        "team_placeholder": "e.g., Kansas City Chiefs OR Patrick Mahomes",
        "line_placeholder_game": "e.g., Moneyline, Spread -7.5, Total O/U 48.5",
        "line_placeholder_player": "e.g., Passing Yards Over 250.5, First TD Scorer"
    },
    "EPL": {
        "id": "4328", "sport": "Soccer", "name": "English Premier League",
        "sport_type": "Team Sport",
        "participant_label": "Team / Player",
        "team_placeholder": "e.g., Arsenal OR Erling Haaland",
        "line_placeholder_game": "e.g., Arsenal to Win, Over 2.5 Goals, Both Teams to Score",
        "line_placeholder_player": "e.g., To Score Anytime, xG Over 0.5"
    },
    "NBA": {
        "id": "4387", "sport": "Basketball", "name": "NBA",
        "sport_type": "Team Sport",
        "participant_label": "Team / Player",
        "team_placeholder": "e.g., Boston Celtics OR LeBron James",
        "line_placeholder_game": "e.g., Moneyline, Spread +3.5, Total O/U 215.5",
        "line_placeholder_player": "e.g., Points Over 25.5, Rebounds Under 8.0"
    },
    "MLB": {
        "id": "4424", "sport": "Baseball", "name": "MLB",
        "sport_type": "Team Sport",
        "participant_label": "Team / Pitcher",
        "team_placeholder": "e.g., New York Yankees OR Gerrit Cole",
        "line_placeholder_game": "e.g., Moneyline, Run Line -1.5, Total O/U 8.5",
        "line_placeholder_player": "e.g., Strikeouts Over 6.5, Hits Over 0.5"
    },
    "NHL": {
        "id": "4380", "sport": "Ice Hockey", "name": "NHL",
        "sport_type": "Team Sport",
        "participant_label": "Team / Player",
        "team_placeholder": "e.g., Edmonton Oilers OR Connor McDavid",
        "line_placeholder_game": "e.g., Moneyline, Puck Line -1.5, Total O/U 6.5",
        "line_placeholder_player": "e.g., Shots on Goal Over 3.5, To Score a Goal"
    },
    "La Liga": {
        "id": "4335", "sport": "Soccer", "name": "La Liga",
        "sport_type": "Team Sport",
        "participant_label": "Team / Player",
        "team_placeholder": "e.g., Real Madrid OR Jude Bellingham",
        "line_placeholder_game": "e.g., Real Madrid -1.5, Under 3.5 Goals",
        "line_placeholder_player": "e.g., To Score a Hat-trick"
    },
    "NCAAF": { # Example for NCAA Football
        "id": "4329", "sport": "American Football", "name": "NCAA Football", # Using a general ID, specific conferences may vary
        "sport_type": "Team Sport",
        "participant_label": "Team / Player",
        "team_placeholder": "e.g., Georgia Bulldogs OR Caleb Williams (example)",
        "line_placeholder_game": "e.g., Moneyline, Spread -10.5, Total O/U 55.5",
        "line_placeholder_player": "e.g., Rushing Yards Over 80.5"
    },
    "Bundesliga": {
        "id": "4331", "sport": "Soccer", "name": "Bundesliga", # Corrected ID
        "sport_type": "Team Sport",
        "participant_label": "Team / Player",
        "team_placeholder": "e.g., Bayern Munich OR Harry Kane",
        "line_placeholder_game": "e.g., Bayern Munich -2.5, Over 3.5 Goals",
        "line_placeholder_player": "e.g., Assists Over 0.5"
    },
    "Serie A": {
        "id": "4332", "sport": "Soccer", "name": "Serie A", # Corrected ID
        "sport_type": "Team Sport",
        "participant_label": "Team / Player",
        "team_placeholder": "e.g., Inter Milan OR Victor Osimhen",
        "line_placeholder_game": "e.g., Inter Milan to Win to Nil",
        "line_placeholder_player": "e.g., Shots on Target Over 1.5"
    },
    "Ligue 1": {
        "id": "4334", "sport": "Soccer", "name": "Ligue 1",
        "sport_type": "Team Sport",
        "participant_label": "Team / Player",
        "team_placeholder": "e.g., Paris Saint-Germain OR Kylian Mbappé",
        "line_placeholder_game": "e.g., PSG -1 Handicap",
        "line_placeholder_player": "e.g., To be First Goalscorer"
    },
    "MLS": {
        "id": "4346", "sport": "Soccer", "name": "MLS",
        "sport_type": "Team Sport",
        "participant_label": "Team / Player",
        "team_placeholder": "e.g., LAFC OR Lionel Messi",
        "line_placeholder_game": "e.g., LAFC to Win & Over 2.5 Goals",
        "line_placeholder_player": "e.g., Free Kick Goals Over 0.5"
    },
    "F1": { # Formula 1 example
        "id": "4370", "sport": "Motorsport", "name": "Formula 1", # Example ID, may vary or be event-based
        "sport_type": "Racing",
        "participant_label": "Driver / Team", # Bets can be on drivers or constructor teams
        "team_placeholder": "e.g., Max Verstappen OR Red Bull Racing",
        "line_placeholder_game": "e.g., To Win Race, Podium Finish, Fastest Lap", # "Game" refers to the race event
        "line_placeholder_player": "e.g., Head-to-Head Driver Matchup" # "Player" refers to driver prop
    },
    "ATP": { # Tennis example
        "id": "4479", "sport": "Tennis", "name": "ATP Tour", # Example ID for a tour
        "sport_type": "Individual Player",
        "participant_label": "Player",
        "team_placeholder": "e.g., Novak Djokovic", # 'team' field will be used for the player name
        "line_placeholder_game": "e.g., To Win Match, Set Handicap -1.5, Total Games O/U 22.5",
        # Player props are essentially match lines in tennis unless very specific (e.g., Aces Over/Under)
        "line_placeholder_player": "e.g., Aces Over 10.5"
    },
    "UFC": { # Fighting example
        "id": "4458", "sport": "Fighting", "name": "UFC", # Example ID for UFC events/league
        "sport_type": "Individual Player",
        "participant_label": "Fighter",
        "team_placeholder": "e.g., Jon Jones",
        "line_placeholder_game": "e.g., To Win Fight, Method of Victory (KO/Sub/Decision)",
        "line_placeholder_player": "e.g., Fight to go the Distance - Yes/No, Round Betting"
    },
    "WNBA": {
        "id": "4410", "sport": "Basketball", "name": "WNBA",
        "sport_type": "Team Sport",
        "participant_label": "Team / Player",
        "team_placeholder": "e.g., Las Vegas Aces OR A'ja Wilson",
        "line_placeholder_game": "e.g., Moneyline, Spread -5.5, Total O/U 160.5",
        "line_placeholder_player": "e.g., Points + Rebounds + Assists Over 30.5"
    },
     "PGA": { # Golf example
        "id": None, "sport": "Golf", "name": "PGA Tour Events", # Golf is event-based, specific event IDs might be better
        "sport_type": "Individual Player",
        "participant_label": "Golfer",
        "team_placeholder": "e.g., Scottie Scheffler",
        "line_placeholder_game": "e.g., To Win Tournament, Top 5 Finish, Make/Miss Cut", # "Game" refers to the tournament
        "line_placeholder_player": "e.g., Head-to-Head Matchup (vs another golfer)"
    },
    # Add other leagues similarly...
    # For leagues without teams (like Darts players), the structure would focus on individuals
    "PDC Darts": {
        "id": "4499", "sport": "Darts", "name": "PDC Darts",
        "sport_type": "Individual Player",
        "participant_label": "Player",
        "team_placeholder": "e.g., Luke Humphries",
        "line_placeholder_game": "e.g., To Win Match, Correct Leg Score, Most 180s",
        "line_placeholder_player": "e.g., 180s Over/Under 5.5"
    },
    # Generic fallback if a league is not in this config
    "OTHER": {
        "id": None, "sport": "Unknown", "name": "Other League",
        "sport_type": "Unknown",
        "participant_label": "Team/Participant",
        "team_placeholder": "Enter participant name",
        "line_placeholder_game": "Enter game line (e.g., Moneyline)",
        "line_placeholder_player": "Enter player prop details"
    }
}

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
