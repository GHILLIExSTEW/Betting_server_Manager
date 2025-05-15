"""Configuration for team name mappings."""

# Team name mappings for logo file naming
TEAM_MAPPINGS = {
    # NFL Teams (already provided, verified)
    "49ers": "san_francisco_49ers", "SF 49ers": "san_francisco_49ers",
    "Bears": "chicago_bears", "Chicago Bears": "chicago_bears",
    "Bengals": "cincinnati_bengals", "Cincinnati Bengals": "cincinnati_bengals",
    "Bills": "buffalo_bills", "Buffalo Bills": "buffalo_bills",
    "Broncos": "denver_broncos", "Denver Broncos": "denver_broncos",
    "Browns": "cleveland_browns", "Cleveland Browns": "cleveland_browns",
    "Buccaneers": "tampa_bay_buccaneers", "Tampa Bay Buccaneers": "tampa_bay_buccaneers",
    "Cardinals": "arizona_cardinals", "Arizona Cardinals": "arizona_cardinals",
    "Chargers": "los_angeles_chargers", "Los Angeles Chargers": "los_angeles_chargers", "LA Chargers": "los_angeles_chargers",
    "Chiefs": "kansas_city_chiefs", "Kansas City Chiefs": "kansas_city_chiefs",
    "Colts": "indianapolis_colts", "Indianapolis Colts": "indianapolis_colts",
    "Cowboys": "dallas_cowboys", "Dallas Cowboys": "dallas_cowboys",
    "Dolphins": "miami_dolphins", "Miami Dolphins": "miami_dolphins",
    "Eagles": "philadelphia_eagles", "Philadelphia Eagles": "philadelphia_eagles",
    "Falcons": "atlanta_falcons", "Atlanta Falcons": "atlanta_falcons",
    "Giants": "new_york_giants", "New York Giants": "new_york_giants", "NY Giants": "new_york_giants",
    "Jaguars": "jacksonville_jaguars", "Jacksonville Jaguars": "jacksonville_jaguars",
    "Jets": "new_york_jets", "New York Jets": "new_york_jets", "NY Jets": "new_york_jets",
    "Lions": "detroit_lions", "Detroit Lions": "detroit_lions",
    "Packers": "green_bay_packers", "Green Bay Packers": "green_bay_packers",
    "Panthers": "carolina_panthers", "Carolina Panthers": "carolina_panthers",
    "Patriots": "new_england_patriots", "New England Patriots": "new_england_patriots",
    "Raiders": "las_vegas_raiders", "Las Vegas Raiders": "las_vegas_raiders",
    "Rams": "los_angeles_rams", "Los Angeles Rams": "los_angeles_rams", "LA Rams": "los_angeles_rams",
    "Ravens": "baltimore_ravens", "Baltimore Ravens": "baltimore_ravens",
    "Saints": "new_orleans_saints", "New Orleans Saints": "new_orleans_saints",
    "Seahawks": "seattle_seahawks", "Seattle Seahawks": "seattle_seahawks",
    "Steelers": "pittsburgh_steelers", "Pittsburgh Steelers": "pittsburgh_steelers",
    "Texans": "houston_texans", "Houston Texans": "houston_texans",
    "Titans": "tennessee_titans", "Tennessee Titans": "tennessee_titans",
    "Vikings": "minnesota_vikings", "Minnesota Vikings": "minnesota_vikings",
    "Commanders": "washington_commanders", "Washington Commanders": "washington_commanders",

    # NBA Teams
    "Hawks": "atlanta_hawks", "Atlanta Hawks": "atlanta_hawks",
    "Celtics": "boston_celtics", "Boston Celtics": "boston_celtics",
    "Nets": "brooklyn_nets", "Brooklyn Nets": "brooklyn_nets",
    "Hornets": "charlotte_hornets", "Charlotte Hornets": "charlotte_hornets",
    "Bulls": "chicago_bulls", "Chicago Bulls": "chicago_bulls",
    "Cavaliers": "cleveland_cavaliers", "Cleveland Cavaliers": "cleveland_cavaliers", "Cavs": "cleveland_cavaliers",
    "Mavericks": "dallas_mavericks", "Dallas Mavericks": "dallas_mavericks", "Mavs": "dallas_mavericks",
    "Nuggets": "denver_nuggets", "Denver Nuggets": "denver_nuggets",
    "Pistons": "detroit_pistons", "Detroit Pistons": "detroit_pistons",
    "Warriors": "golden_state_warriors", "Golden State Warriors": "golden_state_warriors",
    "Rockets": "houston_rockets", "Houston Rockets": "houston_rockets",
    "Pacers": "indiana_pacers", "Indiana Pacers": "indiana_pacers",
    "Clippers": "los_angeles_clippers", "Los Angeles Clippers": "los_angeles_clippers", "LA Clippers": "los_angeles_clippers",
    "Lakers": "los_angeles_lakers", "Los Angeles Lakers": "los_angeles_lakers", "LA Lakers": "los_angeles_lakers",
    "Grizzlies": "memphis_grizzlies", "Memphis Grizzlies": "memphis_grizzlies",
    "Heat": "miami_heat", "Miami Heat": "miami_heat",
    "Bucks": "milwaukee_bucks", "Milwaukee Bucks": "milwaukee_bucks",
    "Timberwolves": "minnesota_timberwolves", "Minnesota Timberwolves": "minnesota_timberwolves", "Wolves": "minnesota_timberwolves",
    "Pelicans": "new_orleans_pelicans", "New Orleans Pelicans": "new_orleans_pelicans",
    "Knicks": "new_york_knicks", "New York Knicks": "new_york_knicks", "NY Knicks": "new_york_knicks",
    "Thunder": "oklahoma_city_thunder", "Oklahoma City Thunder": "oklahoma_city_thunder", "OKC Thunder": "oklahoma_city_thunder",
    "Magic": "orlando_magic", "Orlando Magic": "orlando_magic",
    "76ers": "philadelphia_76ers", "Philadelphia 76ers": "philadelphia_76ers", "Sixers": "philadelphia_76ers",
    "Suns": "phoenix_suns", "Phoenix Suns": "phoenix_suns",
    "Trail Blazers": "portland_trail_blazers", "Portland Trail Blazers": "portland_trail_blazers", "Blazers": "portland_trail_blazers",
    "Kings": "sacramento_kings", "Sacramento Kings": "sacramento_kings",
    "Spurs": "san_antonio_spurs", "San Antonio Spurs": "san_antonio_spurs",
    "Raptors": "toronto_raptors", "Toronto Raptors": "toronto_raptors",
    "Jazz": "utah_jazz", "Utah Jazz": "utah_jazz",
    "Wizards": "washington_wizards", "Washington Wizards": "washington_wizards",

    # MLB Teams
    "Diamondbacks": "arizona_diamondbacks", "Arizona Diamondbacks": "arizona_diamondbacks", "D-backs": "arizona_diamondbacks",
    "Braves": "atlanta_braves", "Atlanta Braves": "atlanta_braves",
    "Orioles": "baltimore_orioles", "Baltimore Orioles": "baltimore_orioles",
    "Red Sox": "boston_red_sox", "Boston Red Sox": "boston_red_sox",
    "Cubs": "chicago_cubs", "Chicago Cubs": "chicago_cubs",
    "White Sox": "chicago_white_sox", "Chicago White Sox": "chicago_white_sox",
    "Reds": "cincinnati_reds", "Cincinnati Reds": "cincinnati_reds",
    "Guardians": "cleveland_guardians", "Cleveland Guardians": "cleveland_guardians",
    "Rockies": "colorado_rockies", "Colorado Rockies": "colorado_rockies",
    "Tigers": "detroit_tigers", "Detroit Tigers": "detroit_tigers",
    "Astros": "houston_astros", "Houston Astros": "houston_astros",
    "Royals": "kansas_city_royals", "Kansas City Royals": "kansas_city_royals",
    "Angels": "los_angeles_angels", "Los Angeles Angels": "los_angeles_angels", "LA Angels": "los_angeles_angels",
    "Dodgers": "los_angeles_dodgers", "Los Angeles Dodgers": "los_angeles_dodgers", "LA Dodgers": "los_angeles_dodgers",
    "Marlins": "miami_marlins", "Miami Marlins": "miami_marlins",
    "Brewers": "milwaukee_brewers", "Milwaukee Brewers": "milwaukee_brewers",
    "Twins": "minnesota_twins", "Minnesota Twins": "minnesota_twins",
    "Mets": "new_york_mets", "New York Mets": "new_york_mets", "NY Mets": "new_york_mets",
    "Yankees": "new_york_yankees", "New York Yankees": "new_york_yankees", "NY Yankees": "new_york_yankees",
    "Athletics": "oakland_athletics", "Oakland Athletics": "oakland_athletics", "A's": "oakland_athletics",
    "Phillies": "philadelphia_phillies", "Philadelphia Phillies": "philadelphia_phillies",
    "Pirates": "pittsburgh_pirates", "Pittsburgh Pirates": "pittsburgh_pirates",
    "Padres": "san_diego_padres", "San Diego Padres": "san_diego_padres",
    "Giants": "san_francisco_giants", "San Francisco Giants": "san_francisco_giants", "SF Giants": "san_francisco_giants",
    "Mariners": "seattle_mariners", "Seattle Mariners": "seattle_mariners",
    "Cardinals": "st_louis_cardinals", "St. Louis Cardinals": "st_louis_cardinals",
    "Rays": "tampa_bay_rays", "Tampa Bay Rays": "tampa_bay_rays",
    "Rangers": "texas_rangers", "Texas Rangers": "texas_rangers",
    "Blue Jays": "toronto_blue_jays", "Toronto Blue Jays": "toronto_blue_jays",
    "Nationals": "washington_nationals", "Washington Nationals": "washington_nationals",

    # NHL Teams (already provided, verified)
    "Oilers": "edmonton_oilers", "Edmonton Oilers": "edmonton_oilers",
    "Flames": "calgary_flames", "Calgary Flames": "calgary_flames",
    "Canucks": "vancouver_canucks", "Vancouver Canucks": "vancouver_canucks",
    "Maple Leafs": "toronto_maple_leafs", "Toronto Maple Leafs": "toronto_maple_leafs",
    "Senators": "ottawa_senators", "Ottawa Senators": "ottawa_senators",
    "Canadiens": "montreal_canadiens", "Montreal Canadiens": "montreal_canadiens", "Habs": "montreal_canadiens",
    "Bruins": "boston_bruins", "Boston Bruins": "boston_bruins",
    "Sabres": "buffalo_sabres", "Buffalo Sabres": "buffalo_sabres",
    "Rangers": "new_york_rangers", "New York Rangers": "new_york_rangers", "NY Rangers": "new_york_rangers",
    "Islanders": "new_york_islanders", "New York Islanders": "new_york_islanders", "NY Islanders": "new_york_islanders",
    "Devils": "new_jersey_devils", "New Jersey Devils": "new_jersey_devils", "NJ Devils": "new_jersey_devils",
    "Flyers": "philadelphia_flyers", "Philadelphia Flyers": "philadelphia_flyers",
    "Penguins": "pittsburgh_penguins", "Pittsburgh Penguins": "pittsburgh_penguins",
    "Capitals": "washington_capitals", "Washington Capitals": "washington_capitals", "Caps": "washington_capitals",
    "Hurricanes": "carolina_hurricanes", "Carolina Hurricanes": "carolina_hurricanes", "Canes": "carolina_hurricanes",
    "Panthers": "florida_panthers", "Florida Panthers": "florida_panthers",
    "Lightning": "tampa_bay_lightning", "Tampa Bay Lightning": "tampa_bay_lightning", "Bolts": "tampa_bay_lightning",
    "Red Wings": "detroit_red_wings", "Detroit Red Wings": "detroit_red_wings",
    "Blackhawks": "chicago_blackhawks", "Chicago Blackhawks": "chicago_blackhawks",
    "Blues": "st_louis_blues", "St. Louis Blues": "st_louis_blues",
    "Wild": "minnesota_wild", "Minnesota Wild": "minnesota_wild",
    "Jets": "winnipeg_jets", "Winnipeg Jets": "winnipeg_jets",
    "Avalanche": "colorado_avalanche", "Colorado Avalanche": "colorado_avalanche", "Avs": "colorado_avalanche",
    "Stars": "dallas_stars", "Dallas Stars": "dallas_stars",
    "Predators": "nashville_predators", "Nashville Predators": "nashville_predators", "Preds": "nashville_predators",
    "Coyotes": "arizona_coyotes", "Arizona Coyotes": "arizona_coyotes",
    "Golden Knights": "vegas_golden_knights", "Vegas Golden Knights": "vegas_golden_knights", "Knights": "vegas_golden_knights",
    "Kraken": "seattle_kraken", "Seattle Kraken": "seattle_kraken",
    "Sharks": "san_jose_sharks", "San Jose Sharks": "san_jose_sharks",
    "Kings": "los_angeles_kings", "Los Angeles Kings": "los_angeles_kings", "LA Kings": "los_angeles_kings",
    "Ducks": "anaheim_ducks", "Anaheim Ducks": "anaheim_ducks",

    # MLS Teams
    "Atlanta United FC": "atlanta_united_fc", "Atlanta United": "atlanta_united_fc",
    "Austin FC": "austin_fc",
    "Charlotte FC": "charlotte_fc",
    "Chicago Fire FC": "chicago_fire_fc", "Chicago Fire": "chicago_fire_fc",
    "FC Cincinnati": "fc_cincinnati",
    "Colorado Rapids": "colorado_rapids",
    "Columbus Crew": "columbus_crew",
    "D.C. United": "dc_united", "DC United": "dc_united",
    "FC Dallas": "fc_dallas",
    "Houston Dynamo FC": "houston_dynamo_fc", "Houston Dynamo": "houston_dynamo_fc",
    "Inter Miami CF": "inter_miami_cf", "Inter Miami": "inter_miami_cf",
    "LA Galaxy": "la_galaxy",
    "Los Angeles FC": "los_angeles_fc", "LAFC": "los_angeles_fc",
    "Minnesota United FC": "minnesota_united_fc", "Minnesota United": "minnesota_united_fc",
    "CF Montréal": "cf_montreal", "CF Montreal": "cf_montreal", "Montreal Impact": "cf_montreal", # Older name
    "Nashville SC": "nashville_sc",
    "New England Revolution": "new_england_revolution", "Revolution": "new_england_revolution",
    "New York City FC": "new_york_city_fc", "NYCFC": "new_york_city_fc",
    "New York Red Bulls": "new_york_red_bulls", "NY Red Bulls": "new_york_red_bulls",
    "Orlando City SC": "orlando_city_sc", "Orlando City": "orlando_city_sc",
    "Philadelphia Union": "philadelphia_union", "Union": "philadelphia_union",
    "Portland Timbers": "portland_timbers",
    "Real Salt Lake": "real_salt_lake", "RSL": "real_salt_lake",
    "San Jose Earthquakes": "san_jose_earthquakes", "Earthquakes": "san_jose_earthquakes",
    "Seattle Sounders FC": "seattle_sounders_fc", "Seattle Sounders": "seattle_sounders_fc", "Sounders": "seattle_sounders_fc",
    "Sporting Kansas City": "sporting_kansas_city", "Sporting KC": "sporting_kansas_city",
    "St. Louis City SC": "st_louis_city_sc", "St Louis City SC": "st_louis_city_sc",
    "Toronto FC": "toronto_fc",
    "Vancouver Whitecaps FC": "vancouver_whitecaps_fc", "Vancouver Whitecaps": "vancouver_whitecaps_fc", "Whitecaps": "vancouver_whitecaps_fc",

    # Soccer - EPL (English Premier League)
    "Arsenal": "arsenal", "Arsenal FC": "arsenal",
    "Aston Villa": "aston_villa", "Aston Villa FC": "aston_villa",
    "AFC Bournemouth": "afc_bournemouth", "Bournemouth": "afc_bournemouth",
    "Brentford": "brentford", "Brentford FC": "brentford",
    "Brighton & Hove Albion": "brighton_and_hove_albion", "Brighton": "brighton_and_hove_albion",
    "Burnley": "burnley", "Burnley FC": "burnley",
    "Chelsea": "chelsea", "Chelsea FC": "chelsea",
    "Crystal Palace": "crystal_palace", "Crystal Palace FC": "crystal_palace",
    "Everton": "everton", "Everton FC": "everton",
    "Fulham": "fulham", "Fulham FC": "fulham",
    "Liverpool": "liverpool", "Liverpool FC": "liverpool",
    "Luton Town": "luton_town", "Luton Town FC": "luton_town",
    "Manchester City": "manchester_city", "Man City": "manchester_city", "Manchester City FC": "manchester_city",
    "Manchester United": "manchester_united", "Man United": "manchester_united", "Man Utd": "manchester_united", "Manchester United FC": "manchester_united",
    "Newcastle United": "newcastle_united", "Newcastle": "newcastle_united", "Newcastle United FC": "newcastle_united",
    "Nottingham Forest": "nottingham_forest", "Nottm Forest": "nottingham_forest", "Nottingham Forest FC": "nottingham_forest",
    "Sheffield United": "sheffield_united", "Sheffield Utd": "sheffield_united", "Sheffield United FC": "sheffield_united",
    "Tottenham Hotspur": "tottenham_hotspur", "Tottenham": "tottenham_hotspur", "Spurs": "tottenham_hotspur", "Tottenham Hotspur FC": "tottenham_hotspur",
    "West Ham United": "west_ham_united", "West Ham": "west_ham_united", "West Ham United FC": "west_ham_united",
    "Wolverhampton Wanderers": "wolverhampton_wanderers", "Wolves": "wolverhampton_wanderers", "Wolverhampton Wanderers FC": "wolverhampton_wanderers",
    # Add promoted/relegated teams as seasons change, e.g. Leicester City, Ipswich Town, Southampton for 24/25
    "Leicester City": "leicester_city", "Leicester City FC": "leicester_city",
    "Ipswich Town": "ipswich_town", "Ipswich Town FC": "ipswich_town",
    "Southampton": "southampton", "Southampton FC": "southampton",


    # Soccer - La Liga
    "Alavés": "alaves", "Deportivo Alavés": "alaves",
    "Almería": "almeria", "UD Almería": "almeria",
    "Athletic Club": "athletic_club_bilbao", "Athletic Bilbao": "athletic_club_bilbao", # Common name Athletic Bilbao
    "Atlético Madrid": "atletico_madrid", "Atletico Madrid": "atletico_madrid",
    "Barcelona": "fc_barcelona", "FC Barcelona": "fc_barcelona", "Barça": "fc_barcelona",
    "Real Betis": "real_betis",
    "Cádiz": "cadiz_cf", "Cadiz CF": "cadiz_cf", "Cádiz CF": "cadiz_cf",
    "Celta Vigo": "celta_vigo", "RC Celta de Vigo": "celta_vigo",
    "Getafe": "getafe_cf", "Getafe CF": "getafe_cf",
    "Girona": "girona_fc", "Girona FC": "girona_fc",
    "Granada": "granada_cf", "Granada CF": "granada_cf",
    "Las Palmas": "ud_las_palmas", "UD Las Palmas": "ud_las_palmas",
    "Mallorca": "rcd_mallorca", "RCD Mallorca": "rcd_mallorca",
    "Osasuna": "ca_osasuna", "CA Osasuna": "ca_osasuna",
    "Rayo Vallecano": "rayo_vallecano",
    "Real Madrid": "real_madrid",
    "Real Sociedad": "real_sociedad",
    "Sevilla": "sevilla_fc", "Sevilla FC": "sevilla_fc",
    "Valencia": "valencia_cf", "Valencia CF": "valencia_cf",
    "Villarreal": "villarreal_cf", "Villarreal CF": "villarreal_cf",
    # Add promoted teams as seasons change, e.g. Leganes, Valladolid for 24/25
    "Leganés": "cd_leganes", "CD Leganés": "cd_leganes",
    "Valladolid": "real_valladolid", "Real Valladolid": "real_valladolid",


    # Soccer - Serie A
    "Atalanta": "atalanta_bc", "Atalanta BC": "atalanta_bc",
    "Bologna": "bologna_fc_1909", "Bologna FC 1909": "bologna_fc_1909",
    "Cagliari": "cagliari_calcio",
    "Empoli": "empoli_fc", "Empoli FC": "empoli_fc",
    "Fiorentina": "acf_fiorentina", "ACF Fiorentina": "acf_fiorentina",
    "Frosinone": "frosinone_calcio", # Relegated for 24/25
    "Genoa": "genoa_cfc", "Genoa CFC": "genoa_cfc",
    "Inter": "inter_milan", "Inter Milan": "inter_milan", "Internazionale": "inter_milan",
    "Juventus": "juventus_fc", "Juventus FC": "juventus_fc",
    "Lazio": "ss_lazio", "SS Lazio": "ss_lazio",
    "Lecce": "us_lecce", "US Lecce": "us_lecce",
    "Milan": "ac_milan", "AC Milan": "ac_milan",
    "Monza": "ac_monza", "AC Monza": "ac_monza",
    "Napoli": "ssc_napoli", "SSC Napoli": "ssc_napoli",
    "Roma": "as_roma", "AS Roma": "as_roma",
    "Salernitana": "us_salernitana_1919", # Relegated for 24/25
    "Sassuolo": "us_sassuolo_calcio", # Relegated for 24/25
    "Torino": "torino_fc", "Torino FC": "torino_fc",
    "Udinese": "udinese_calcio",
    "Hellas Verona": "hellas_verona_fc", "Verona": "hellas_verona_fc",
    # Promoted for 24/25: Parma, Como, Venezia
    "Parma": "parma_calcio_1913",
    "Como": "como_1907",
    "Venezia": "venezia_fc", "Venezia FC": "venezia_fc",


    # Soccer - Bundesliga
    "FC Augsburg": "fc_augsburg", "Augsburg": "fc_augsburg",
    "Bayer Leverkusen": "bayer_04_leverkusen", "Leverkusen": "bayer_04_leverkusen",
    "Bayern Munich": "fc_bayern_munich", "Bayern München": "fc_bayern_munich", "FC Bayern": "fc_bayern_munich",
    "VfL Bochum": "vfl_bochum", "Bochum": "vfl_bochum",
    "Werder Bremen": "sv_werder_bremen", "Bremen": "sv_werder_bremen",
    "Darmstadt 98": "sv_darmstadt_98", "Darmstadt": "sv_darmstadt_98", # Relegated for 24/25
    "Borussia Dortmund": "borussia_dortmund", "Dortmund": "borussia_dortmund", "BVB": "borussia_dortmund",
    "Eintracht Frankfurt": "eintracht_frankfurt", "Frankfurt": "eintracht_frankfurt",
    "SC Freiburg": "sc_freiburg", "Freiburg": "sc_freiburg",
    "Borussia Mönchengladbach": "borussia_monchengladbach", "Gladbach": "borussia_monchengladbach",
    "1. FC Heidenheim": "fc_heidenheim", "Heidenheim": "fc_heidenheim",
    "TSG Hoffenheim": "tsg_1899_hoffenheim", "Hoffenheim": "tsg_1899_hoffenheim",
    "1. FC Köln": "fc_koln", "FC Koln": "fc_koln", "Köln": "fc_koln", # Relegated for 24/25
    "RB Leipzig": "rb_leipzig", "Leipzig": "rb_leipzig",
    "Mainz 05": "fsv_mainz_05", "1. FSV Mainz 05": "fsv_mainz_05", "Mainz": "fsv_mainz_05",
    "VfB Stuttgart": "vfb_stuttgart", "Stuttgart": "vfb_stuttgart",
    "Union Berlin": "fc_union_berlin", "1. FC Union Berlin": "fc_union_berlin",
    "VfL Wolfsburg": "vfl_wolfsburg", "Wolfsburg": "vfl_wolfsburg",
    # Promoted for 24/25: St. Pauli, Holstein Kiel
    "FC St. Pauli": "fc_st_pauli", "St. Pauli": "fc_st_pauli",
    "Holstein Kiel": "holstein_kiel",


    # Soccer - Ligue 1
    "AS Monaco": "as_monaco", "Monaco": "as_monaco",
    "Clermont Foot": "clermont_foot_63", "Clermont": "clermont_foot_63", # Relegated for 24/25
    "Le Havre": "le_havre_ac",
    "RC Lens": "rc_lens", "Lens": "rc_lens",
    "Lille OSC": "lille_osc", "Lille": "lille_osc", "LOSC": "lille_osc",
    "FC Lorient": "fc_lorient", "Lorient": "fc_lorient", # Relegated for 24/25
    "Olympique Lyonnais": "olympique_lyonnais", "Lyon": "olympique_lyonnais",
    "Olympique de Marseille": "olympique_marseille", "Marseille": "olympique_marseille",
    "FC Metz": "fc_metz", "Metz": "fc_metz", # Relegated for 24/25 (play-off)
    "Montpellier HSC": "montpellier_hsc", "Montpellier": "montpellier_hsc",
    "FC Nantes": "fc_nantes", "Nantes": "fc_nantes",
    "OGC Nice": "ogc_nice", "Nice": "ogc_nice",
    "Paris Saint-Germain": "paris_saint_germain", "PSG": "paris_saint_germain", "Paris SG": "paris_saint_germain",
    "Stade Brestois 29": "stade_brestois_29", "Brest": "stade_brestois_29",
    "Stade de Reims": "stade_de_reims", "Reims": "stade_de_reims",
    "Stade Rennais FC": "stade_rennais_fc", "Rennes": "stade_rennais_fc", "Stade Rennais": "stade_rennais_fc",
    "RC Strasbourg Alsace": "rc_strasbourg_alsace", "Strasbourg": "rc_strasbourg_alsace",
    "Toulouse FC": "toulouse_fc",
    # Promoted for 24/25: Auxerre, Angers
    "AJ Auxerre": "aj_auxerre", "Auxerre": "aj_auxerre",
    "Angers SCO": "angers_sco", "Angers": "angers_sco",
    # Potentially Saint-Étienne if they win playoff

    # KHL (Kontinental Hockey League) - Team names can be tricky, using common English transliterations
    "Ak Bars Kazan": "ak_bars_kazan", "Ak Bars": "ak_bars_kazan",
    "Amur Khabarovsk": "amur_khabarovsk", "Amur": "amur_khabarovsk",
    "Avangard Omsk": "avangard_omsk", "Avangard": "avangard_omsk",
    "Avtomobilist Yekaterinburg": "avtomobilist_yekaterinburg", "Avtomobilist": "avtomobilist_yekaterinburg",
    "Barys Nur-Sultan": "barys_nur_sultan", "Barys Astana": "barys_nur_sultan", "Barys": "barys_nur_sultan", # Name change
    "CSKA Moscow": "cska_moscow", "CSKA Moskva": "cska_moscow",
    "Dinamo Minsk": "dinamo_minsk",
    "Dinamo Riga": "dinamo_riga", # May not be in KHL currently
    "Dynamo Moscow": "dynamo_moscow", "Dynamo Moskva": "dynamo_moscow",
    "Jokerit Helsinki": "jokerit_helsinki", "Jokerit": "jokerit_helsinki", # Left KHL
    "Kunlun Red Star": "kunlun_red_star",
    "Lokomotiv Yaroslavl": "lokomotiv_yaroslavl", "Lokomotiv": "lokomotiv_yaroslavl",
    "Metallurg Magnitogorsk": "metallurg_magnitogorsk", "Metallurg Mg": "metallurg_magnitogorsk",
    "Neftekhimik Nizhnekamsk": "neftekhimik_nizhnekamsk", "Neftekhimik": "neftekhimik_nizhnekamsk",
    "Salavat Yulaev Ufa": "salavat_yulaev_ufa", "Salavat Yulaev": "salavat_yulaev_ufa",
    "Severstal Cherepovets": "severstal_cherepovets", "Severstal": "severstal_cherepovets",
    "Sibir Novosibirsk": "sibir_novosibirsk", "Sibir": "sibir_novosibirsk",
    "SKA Saint Petersburg": "ska_saint_petersburg", "SKA St. Petersburg": "ska_saint_petersburg", "SKA": "ska_saint_petersburg",
    "HC Sochi": "hc_sochi", "Sochi": "hc_sochi",
    "Spartak Moscow": "spartak_moscow", "Spartak Moskva": "spartak_moscow",
    "Torpedo Nizhny Novgorod": "torpedo_nizhny_novgorod", "Torpedo": "torpedo_nizhny_novgorod",
    "Traktor Chelyabinsk": "traktor_chelyabinsk", "Traktor": "traktor_chelyabinsk",
    "Vityaz Moscow Region": "vityaz_moscow_region", "Vityaz Podolsk": "vityaz_moscow_region", "Vityaz": "vityaz_moscow_region",
    "Lada Togliatti": "lada_togliatti", # Returned to KHL

    # CFL (Canadian Football League)
    "BC Lions": "bc_lions",
    "Calgary Stampeders": "calgary_stampeders", "Stampeders": "calgary_stampeders",
    "Edmonton Elks": "edmonton_elks", # Formerly Eskimos
    "Hamilton Tiger-Cats": "hamilton_tiger_cats", "Tiger-Cats": "hamilton_tiger_cats", "Ti-Cats": "hamilton_tiger_cats",
    "Montreal Alouettes": "montreal_alouettes", "Alouettes": "montreal_alouettes",
    "Ottawa Redblacks": "ottawa_redblacks", "Redblacks": "ottawa_redblacks",
    "Saskatchewan Roughriders": "saskatchewan_roughriders", "Roughriders": "saskatchewan_roughriders",
    "Toronto Argonauts": "toronto_argonauts", "Argonauts": "toronto_argonauts", "Argos": "toronto_argonauts",
    "Winnipeg Blue Bombers": "winnipeg_blue_bombers", "Blue Bombers": "winnipeg_blue_bombers", "Bombers": "winnipeg_blue_bombers",

    # WNBA Teams
    "Atlanta Dream": "atlanta_dream",
    "Chicago Sky": "chicago_sky",
    "Connecticut Sun": "connecticut_sun",
    "Dallas Wings": "dallas_wings",
    "Indiana Fever": "indiana_fever",
    "Las Vegas Aces": "las_vegas_aces", "Aces": "las_vegas_aces",
    "Los Angeles Sparks": "los_angeles_sparks", "LA Sparks": "los_angeles_sparks",
    "Minnesota Lynx": "minnesota_lynx",
    "New York Liberty": "new_york_liberty", "NY Liberty": "new_york_liberty",
    "Phoenix Mercury": "phoenix_mercury",
    "Seattle Storm": "seattle_storm",
    "Washington Mystics": "washington_mystics",
    "Golden State Valkyries": "golden_state_valkyries", # Expansion team

    # EuroLeague (Basketball) - Common English Names
    "Alba Berlin": "alba_berlin",
    "Anadolu Efes Istanbul": "anadolu_efes_istanbul", "Anadolu Efes": "anadolu_efes_istanbul",
    "AS Monaco Basket": "as_monaco_basket", # For basketball
    "Baskonia Vitoria-Gasteiz": "baskonia_vitoria_gasteiz", "Baskonia": "baskonia_vitoria_gasteiz",
    "Crvena Zvezda Meridianbet Belgrade": "crvena_zvezda_belgrade", "Crvena Zvezda": "crvena_zvezda_belgrade",
    "EA7 Emporio Armani Milan": "olimpia_milano", "Olimpia Milano": "olimpia_milano", "AX Armani Exchange Milan": "olimpia_milano",
    "FC Barcelona Bàsquet": "fc_barcelona_basquet", # For basketball
    "FC Bayern Munich Basketball": "fc_bayern_munich_basketball", # For basketball
    "Fenerbahçe Beko Istanbul": "fenerbahce_beko_istanbul", "Fenerbahce": "fenerbahce_beko_istanbul",
    "LDLC ASVEL Villeurbanne": "asvel_basket", "ASVEL": "asvel_basket",
    "Maccabi Playtika Tel Aviv": "maccabi_tel_aviv", "Maccabi Tel Aviv": "maccabi_tel_aviv",
    "Olympiacos Piraeus": "olympiacos_piraeus", "Olympiacos": "olympiacos_piraeus",
    "Panathinaikos AKTOR Athens": "panathinaikos_athens", "Panathinaikos": "panathinaikos_athens",
    "Partizan Mozzart Bet Belgrade": "partizan_belgrade", "Partizan": "partizan_belgrade",
    "Real Madrid Baloncesto": "real_madrid_baloncesto", # For basketball
    "Valencia Basket": "valencia_basket",
    "Virtus Segafredo Bologna": "virtus_bologna", "Virtus Bologna": "virtus_bologna",
    "Žalgiris Kaunas": "zalgiris_kaunas", "Zalgiris Kaunas": "zalgiris_kaunas", "Zalgiris": "zalgiris_kaunas",
    "Paris Basketball": "paris_basketball", # New for 24/25

    # NPB (Nippon Professional Baseball) - Common English Names
    # Central League
    "Yomiuri Giants": "yomiuri_giants",
    "Hanshin Tigers": "hanshin_tigers",
    "Tokyo Yakult Swallows": "tokyo_yakult_swallows", "Yakult Swallows": "tokyo_yakult_swallows",
    "Yokohama DeNA BayStars": "yokohama_dena_baystars", "DeNA BayStars": "yokohama_dena_baystars",
    "Hiroshima Toyo Carp": "hiroshima_toyo_carp", "Hiroshima Carp": "hiroshima_toyo_carp",
    "Chunichi Dragons": "chunichi_dragons",
    # Pacific League
    "Orix Buffaloes": "orix_buffaloes",
    "Fukuoka SoftBank Hawks": "fukuoka_softbank_hawks", "SoftBank Hawks": "fukuoka_softbank_hawks",
    "Saitama Seibu Lions": "saitama_seibu_lions", "Seibu Lions": "saitama_seibu_lions",
    "Tohoku Rakuten Golden Eagles": "tohoku_rakuten_golden_eagles", "Rakuten Eagles": "tohoku_rakuten_golden_eagles",
    "Chiba Lotte Marines": "chiba_lotte_marines",
    "Hokkaido Nippon-Ham Fighters": "hokkaido_nippon_ham_fighters", "Nippon-Ham Fighters": "hokkaido_nippon_ham_fighters",

    # KBO (Korea Baseball Organization) - Common English Names
    "Doosan Bears": "doosan_bears",
    "Hanwha Eagles": "hanwha_eagles",
    "Kia Tigers": "kia_tigers", "KIA Tigers": "kia_tigers",
    "Kiwoom Heroes": "kiwoom_heroes",
    "KT Wiz": "kt_wiz",
    "LG Twins": "lg_twins",
    "Lotte Giants": "lotte_giants",
    "NC Dinos": "nc_dinos",
    "Samsung Lions": "samsung_lions",
    "SSG Landers": "ssg_landers",

    # AFL (Australian Football League)
    "Adelaide Crows": "adelaide_crows", "Adelaide": "adelaide_crows",
    "Brisbane Lions": "brisbane_lions", "Brisbane": "brisbane_lions",
    "Carlton Blues": "carlton_blues", "Carlton": "carlton_blues",
    "Collingwood Magpies": "collingwood_magpies", "Collingwood": "collingwood_magpies",
    "Essendon Bombers": "essendon_bombers", "Essendon": "essendon_bombers",
    "Fremantle Dockers": "fremantle_dockers", "Fremantle": "fremantle_dockers",
    "Geelong Cats": "geelong_cats", "Geelong": "geelong_cats",
    "Gold Coast Suns": "gold_coast_suns", "Gold Coast": "gold_coast_suns",
    "GWS Giants": "gws_giants", "Greater Western Sydney Giants": "gws_giants",
    "Hawthorn Hawks": "hawthorn_hawks", "Hawthorn": "hawthorn_hawks",
    "Melbourne Demons": "melbourne_demons", "Melbourne": "melbourne_demons",
    "North Melbourne Kangaroos": "north_melbourne_kangaroos", "North Melbourne": "north_melbourne_kangaroos", "Kangaroos": "north_melbourne_kangaroos",
    "Port Adelaide Power": "port_adelaide_power", "Port Adelaide": "port_adelaide_power",
    "Richmond Tigers": "richmond_tigers", "Richmond": "richmond_tigers",
    "St Kilda Saints": "st_kilda_saints", "St Kilda": "st_kilda_saints",
    "Sydney Swans": "sydney_swans", "Sydney": "sydney_swans",
    "West Coast Eagles": "west_coast_eagles", "West Coast": "west_coast_eagles",
    "Western Bulldogs": "western_bulldogs", "Bulldogs": "western_bulldogs",
    "Tasmania Devils": "tasmania_devils", # Future team

    # Add more leagues and teams as needed based on your SPORT_CATEGORY_MAP
    # Example: Formula 1 Teams (use constructor names)
    "Mercedes-AMG Petronas": "mercedes_amg_petronas", "Mercedes": "mercedes_amg_petronas",
    "Oracle Red Bull Racing": "red_bull_racing", "Red Bull": "red_bull_racing",
    "Scuderia Ferrari": "scuderia_ferrari", "Ferrari": "scuderia_ferrari",
    "McLaren Formula 1 Team": "mclaren_f1_team", "McLaren": "mclaren_f1_team",
    "Aston Martin Aramco Formula One Team": "aston_martin_f1_team", "Aston Martin": "aston_martin_f1_team",
    "BWT Alpine F1 Team": "alpine_f1_team", "Alpine": "alpine_f1_team",
    "Williams Racing": "williams_racing", "Williams": "williams_racing",
    "Visa Cash App RB Formula One Team": "visa_cash_app_rb", "VCARB": "visa_cash_app_rb", "RB": "visa_cash_app_rb", # Formerly AlphaTauri
    "Stake F1 Team Kick Sauber": "kick_sauber", "Sauber": "kick_sauber", # Formerly Alfa Romeo
    "MoneyGram Haas F1 Team": "haas_f1_team", "Haas": "haas_f1_team",
}

def normalize_team_name(team_name: str) -> str:
    """Normalize team name to match logo file naming convention."""
    # First check if we have a direct mapping (case-sensitive for keys)
    if team_name in TEAM_MAPPINGS:
        return TEAM_MAPPINGS[team_name]
    
    # Try a case-insensitive check for common shorter names if not found directly
    # For example, if data gives "Mercedes" but mapping has "Mercedes-AMG Petronas" as the preferred long key.
    # This part can be expanded.
    for key, value in TEAM_MAPPINGS.items():
        if key.lower() == team_name.lower():
            return value
        # Check if team_name is a substring of a key (e.g. data "Ferrari", key "Scuderia Ferrari")
        # or if a key is a substring of team_name (e.g. data "Haas F1 Team", key "Haas")
        # This needs careful thought to avoid wrong matches.
        # For simplicity, direct match or simple normalization is safer unless you have very specific partial match rules.

    # If no direct mapping, try to normalize the name
    normalized = team_name.lower().replace(" ", "_").replace(".", "").replace("&", "and")
    # Further specific replacements can be added here if needed for common patterns
    # e.g. normalized = normalized.replace("fc", "").replace("cf", "") if these are often omitted in filenames
    return normalized
