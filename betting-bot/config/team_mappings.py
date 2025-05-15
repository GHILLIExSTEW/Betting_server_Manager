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

    # Formula 1 Teams (use constructor names)
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

    # NCAA (Combined Sports)
    # SEC (Southeastern Conference)
    "Alabama Crimson Tide": "alabama_crimson_tide", "Alabama": "alabama_crimson_tide", "Bama": "alabama_crimson_tide", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Arkansas Razorbacks": "arkansas_razorbacks", "Arkansas": "arkansas_razorbacks", "Hogs": "arkansas_razorbacks", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Auburn Tigers": "auburn_tigers", "Auburn": "auburn_tigers", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Florida Gators": "florida_gators", "Florida": "florida_gators", "UF": "florida_gators", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Georgia Bulldogs": "georgia_bulldogs", "Georgia": "georgia_bulldogs", "UGA": "georgia_bulldogs", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Kentucky Wildcats": "kentucky_wildcats", "Kentucky": "kentucky_wildcats", "UK": "kentucky_wildcats", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "LSU Tigers": "lsu_tigers", "LSU": "lsu_tigers", "Louisiana State Tigers": "lsu_tigers", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Ole Miss Rebels": "ole_miss_rebels", "Ole Miss": "ole_miss_rebels", "Mississippi Rebels": "ole_miss_rebels", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Mississippi State Bulldogs": "mississippi_state_bulldogs", "Mississippi State": "mississippi_state_bulldogs", "MSU Bulldogs": "mississippi_state_bulldogs", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Missouri Tigers": "missouri_tigers", "Missouri": "missouri_tigers", "Mizzou": "missouri_tigers", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Oklahoma Sooners": "oklahoma_sooners", "Oklahoma": "oklahoma_sooners", "OU": "oklahoma_sooners", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "South Carolina Gamecocks": "south_carolina_gamecocks", "South Carolina": "south_carolina_gamecocks", "Gamecocks": "south_carolina_gamecocks", "USC": "south_carolina_gamecocks", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Tennessee Volunteers": "tennessee_volunteers", "Tennessee": "tennessee_volunteers", "Vols": "tennessee_volunteers", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Texas Longhorns": "texas_longhorns", "Texas": "texas_longhorns", "UT": "texas_longhorns", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Texas A&M Aggies": "texas_a_and_m_aggies", "Texas A&M": "texas_a_and_m_aggies", "Aggies": "texas_a_and_m_aggies", "A&M": "texas_a_and_m_aggies", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Vanderbilt Commodores": "vanderbilt_commodores", "Vanderbilt": "vanderbilt_commodores", "Vandy": "vanderbilt_commodores", # Baseball, Basketball (M/W), Soccer (W); No Football, No Volleyball

    # Big Ten Conference
    "Illinois Fighting Illini": "illinois_fighting_illini", "Illinois": "illinois_fighting_illini", "Fighting Illini": "illinois_fighting_illini", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Indiana Hoosiers": "indiana_hoosiers", "Indiana": "indiana_hoosiers", "IU": "indiana_hoosiers", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Iowa Hawkeyes": "iowa_hawkeyes", "Iowa": "iowa_hawkeyes", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Maryland Terrapins": "maryland_terrapins", "Maryland": "maryland_terrapins", "Terps": "maryland_terrapins", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Michigan Wolverines": "michigan_wolverines", "Michigan": "michigan_wolverines", "UM": "michigan_wolverines", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Michigan State Spartans": "michigan_state_spartans", "Michigan State": "michigan_state_spartans", "MSU Spartans": "michigan_state_spartans", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Minnesota Golden Gophers": "minnesota_golden_gophers", "Minnesota": "minnesota_golden_gophers", "Golden Gophers": "minnesota_golden_gophers", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Nebraska Cornhuskers": "nebraska_cornhuskers", "Nebraska": "nebraska_cornhuskers", "Huskers": "nebraska_cornhuskers", "UN": "nebraska_cornhuskers", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Northwestern Wildcats": "northwestern_wildcats", "Northwestern": "northwestern_wildcats", "NU": "northwestern_wildcats", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Ohio State Buckeyes": "ohio_state_buckeyes", "Ohio State": "ohio_state_buckeyes", "OSU Buckeyes": "ohio_state_buckeyes", # Baseball, Basketball (M/W), Volleyball (M/W), Football, Soccer (M/W)
    "Oregon Ducks": "oregon_ducks", "Oregon": "oregon_ducks", "UO": "oregon_ducks", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Penn State Nittany Lions": "penn_state_nittany_lions", "Penn State": "penn_state_nittany_lions", "PSU": "penn_state_nittany_lions", # Baseball, Basketball (M/W), Volleyball (M/W), Football, Soccer (M/W)
    "Purdue Boilermakers": "purdue_boilermakers", "Purdue": "purdue_boilermakers", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Rutgers Scarlet Knights": "rutgers_scarlet_knights", "Rutgers": "rutgers_scarlet_knights", "RU": "rutgers_scarlet_knights", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "UCLA Bruins": "ucla_bruins", "UCLA": "ucla_bruins", # Baseball, Basketball (M/W), Volleyball (M/W), Football, Soccer (M/W)
    "USC Trojans": "usc_trojans", "USC": "usc_trojans", "Southern California Trojans": "usc_trojans", # Baseball, Basketball (M/W), Volleyball (M/W), Football, Soccer (W)
    "Washington Huskies": "washington_huskies", "Washington": "washington_huskies", "UW": "washington_huskies", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Wisconsin Badgers": "wisconsin_badgers", "Wisconsin": "wisconsin_badgers", "UW-Madison": "wisconsin_badgers", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)

    # ACC (Atlantic Coast Conference)
    "Boston College Eagles": "boston_college_eagles", "Boston College": "boston_college", "BC Eagles": "boston_college_eagles", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "California Golden Bears": "california_golden_bears", "Cal": "california_golden_bears", "California": "california_golden_bears", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Clemson Tigers": "clemson_tigers", "Clemson": "clemson_tigers", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Duke Blue Devils": "duke_blue_devils", "Duke": "duke_blue_devils", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Florida State Seminoles": "florida_state_seminoles", "Florida State": "florida_state_seminoles", "FSU": "florida_state_seminoles", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Georgia Tech Yellow Jackets": "georgia_tech_yellow_jackets", "Georgia Tech": "georgia_tech_yellow_jackets", "GT": "georgia_tech_yellow_jackets", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Louisville Cardinals": "louisville_cardinals", "Louisville": "louisville_cardinals", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Miami Hurricanes": "miami_hurricanes", "Miami (FL)": "miami_hurricanes", "The U": "miami_hurricanes", "Miami FL": "miami_hurricanes", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "North Carolina Tar Heels": "north_carolina_tar_heels", "North Carolina": "north_carolina_tar_heels", "UNC": "north_carolina_tar_heels", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "NC State Wolfpack": "nc_state_wolfpack", "NC State": "nc_state_wolfpack", "North Carolina State Wolfpack": "nc_state_wolfpack", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Notre Dame Fighting Irish": "notre_dame_fighting_irish", "Notre Dame": "notre_dame_fighting_irish", "ND": "notre_dame_fighting_irish", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football Independent
    "Pittsburgh Panthers": "pittsburgh_panthers", "Pittsburgh": "pittsburgh_panthers", "Pitt": "pittsburgh_panthers", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "SMU Mustangs": "smu_mustangs", "SMU": "smu_mustangs", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Stanford Cardinal": "stanford_cardinal", "Stanford": "stanford_cardinal", # Baseball, Basketball (M/W), Volleyball (M/W), Football, Soccer (M/W)
    "Syracuse Orange": "syracuse_orange", "Syracuse": "syracuse_orange", # Basketball (M/W), Volleyball (W), Football, Soccer (M/W); No Baseball
    "Virginia Cavaliers": "virginia_cavaliers", "Virginia": "virginia_cavaliers", "UVA": "virginia_cavaliers", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Virginia Tech Hokies": "virginia_tech_hokies", "Virginia Tech": "virginia_tech_hokies", "VT": "virginia_tech_hokies", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Wake Forest Demon Deacons": "wake_forest_demon_deacons", "Wake Forest": "wake_forest_demon_deacons", "WF": "wake_forest_demon_deacons", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)

    # Big 12 Conference
    "Arizona State Sun Devils": "arizona_state_sun_devils", "Arizona State": "arizona_state_sun_devils", "ASU": "arizona_state_sun_devils", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Arizona Wildcats": "arizona_wildcats", "Arizona": "arizona_wildcats", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Baylor Bears": "baylor_bears", "Baylor": "baylor_bears", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "BYU Cougars": "byu_cougars", "BYU": "byu_cougars", "Brigham Young Cougars": "byu_cougars", # Baseball, Basketball (M/W), Volleyball (M/W), Football, Soccer (W)
    "Cincinnati Bearcats": "cincinnati_bearcats", "Cincinnati": "cincinnati_bearcats", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Colorado Buffaloes": "colorado_buffaloes", "Colorado": "colorado_buffaloes", "Buffs": "colorado_buffaloes", # Basketball (M/W), Volleyball (W), Football, Soccer (W); No Baseball
    "Houston Cougars": "houston_cougars", "Houston": "houston_cougars", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Iowa State Cyclones": "iowa_state_cyclones", "Iowa State": "iowa_state_cyclones", "ISU": "iowa_state_cyclones", # Basketball (M/W), Volleyball (W), Football, Soccer (W); No Baseball
    "Kansas Jayhawks": "kansas_jayhawks", "Kansas": "kansas_jayhawks", "KU": "kansas_jayhawks", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Kansas State Wildcats": "kansas_state_wildcats", "Kansas State": "kansas_state_wildcats", "KSU": "kansas_state_wildcats", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Oklahoma State Cowboys": "oklahoma_state_cowboys", "Oklahoma State": "oklahoma_state_cowboys", "OSU Cowboys": "oklahoma_state_cowboys", "OK State": "oklahoma_state_cowboys", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "TCU Horned Frogs": "tcu_horned_frogs", "TCU": "tcu_horned_frogs", "Texas Christian Horned Frogs": "tcu_horned_frogs", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Texas Tech Red Raiders": "texas_tech_red_raiders", "Texas Tech": "texas_tech_red_raiders", "TTU": "texas_tech_red_raiders", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "UCF Knights": "ucf_knights", "UCF": "ucf_knights", "Central Florida Knights": "ucf_knights", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Utah Utes": "utah_utes", "Utah": "utah_utes", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "West Virginia Mountaineers": "west_virginia_mountaineers", "West Virginia": "west_virginia_mountaineers", "WVU": "west_virginia_mountaineers", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)

    # American Athletic Conference (AAC)
    "Charlotte 49ers": "charlotte_49ers", "Charlotte": "charlotte_49ers", "UNC Charlotte": "charlotte_49ers", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "East Carolina Pirates": "east_carolina_pirates", "East Carolina": "east_carolina_pirates", "ECU": "east_carolina_pirates", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Florida Atlantic Owls": "florida_atlantic_owls", "Florida Atlantic": "florida_atlantic_owls", "FAU": "florida_atlantic_owls", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Memphis Tigers": "memphis_tigers", "Memphis": "memphis_tigers", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Navy Midshipmen": "navy_midshipmen", "Navy": "navy_midshipmen", "Naval Academy": "navy_midshipmen", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "North Texas Mean Green": "north_texas_mean_green", "North Texas": "north_texas_mean_green", "UNT": "north_texas_mean_green", # Basketball (M/W), Volleyball (W), Football, Soccer (W); No Baseball
    "Rice Owls": "rice_owls", "Rice": "rice_owls", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "SMU Mustangs": "smu_mustangs", "SMU": "smu_mustangs", # Note: Also in ACC, included here for AAC history; Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "South Florida Bulls": "south_florida_bulls", "South Florida": "south_florida_bulls", "USF": "south_florida_bulls", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Temple Owls": "temple_owls", "Temple": "temple_owls", # Basketball (M/W), Volleyball (W), Football, Soccer (M/W); No Baseball
    "Tulane Green Wave": "tulane_green_wave", "Tulane": "tulane_green_wave", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Tulsa Golden Hurricane": "tulsa_golden_hurricane", "Tulsa": "tulsa_golden_hurricane", # Basketball (M/W), Volleyball (W), Football, Soccer (W); No Baseball
    "UAB Blazers": "uab_blazers", "UAB": "uab_blazers", "Alabama-Birmingham": "uab_blazers", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "UTSA Roadrunners": "utsa_roadrunners", "UTSA": "utsa_roadrunners", "Texas-San Antonio": "utsa_roadrunners", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Wichita State Shockers": "wichita_state_shockers", "Wichita State": "wichita_state_shockers", # Baseball, Basketball (M/W), Volleyball (W); No Football, No Soccer

    # Conference USA (C-USA)
    "Florida International Panthers": "florida_international_panthers", "FIU": "florida_international_panthers", "Florida International": "florida_international_panthers", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Jacksonville State Gamecocks": "jacksonville_state_gamecocks", "Jacksonville State": "jacksonville_state_gamecocks", "JSU": "jacksonville_state_gamecocks", # Baseball, Basketball (M/W), Volleyball (W), Football; No Soccer
    "Kennesaw State Owls": "kennesaw_state_owls", "Kennesaw State": "kennesaw_state_owls", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Liberty Flames": "liberty_flames", "Liberty": "liberty_flames", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Louisiana Tech Bulldogs": "louisiana_tech_bulldogs", "Louisiana Tech": "louisiana_tech_bulldogs", "LA Tech": "louisiana_tech_bulldogs", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Middle Tennessee Blue Raiders": "middle_tennessee_blue_raiders", "Middle Tennessee": "middle_tennessee_blue_raiders", "MTSU": "middle_tennessee_blue_raiders", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "New Mexico State Aggies": "new_mexico_state_aggies", "New Mexico State": "new_mexico_state_aggies", "NMSU": "new_mexico_state_aggies", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Sam Houston Bearkats": "sam_houston_bearkats", "Sam Houston": "sam_houston_bearkats", "SHSU": "sam_houston_bearkats", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "UTEP Miners": "utep_miners", "UTEP": "utep_miners", "Texas-El Paso": "utep_miners", # Basketball (M/W), Volleyball (W), Football, Soccer (W); No Baseball
    "Western Kentucky Hilltoppers": "western_kentucky_hilltoppers", "Western Kentucky": "western_kentucky_hilltoppers", "WKU": "western_kentucky_hilltoppers", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)

    # Mountain West Conference
    "Air Force Falcons": "air_force_falcons", "Air Force": "air_force_falcons", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Boise State Broncos": "boise_state_broncos", "Boise State": "boise_state_broncos", # Basketball (M/W), Volleyball (W), Football, Soccer (W); No Baseball
    "Colorado State Rams": "colorado_state_rams", "Colorado State": "colorado_state_rams", "CSU": "colorado_state_rams", # Basketball (M/W), Volleyball (W), Football, Soccer (W); No Baseball
    "Fresno State Bulldogs": "fresno_state_bulldogs", "Fresno State": "fresno_state_bulldogs", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Hawaii Rainbow Warriors": "hawaii_rainbow_warriors", "Hawaii": "hawaii_rainbow_warriors", "UH": "hawaii_rainbow_warriors", # Baseball, Basketball (M/W), Volleyball (M/W), Football, Soccer (M/W)
    "Nevada Wolf Pack": "nevada_wolf_pack", "Nevada": "nevada_wolf_pack", "UNR": "nevada_wolf_pack", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "New Mexico Lobos": "new_mexico_lobos", "New Mexico": "new_mexico_lobos", "UNM": "new_mexico_lobos", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "San Diego State Aztecs": "san_diego_state_aztecs", "San Diego State": "san_diego_state_aztecs", "SDSU": "san_diego_state_aztecs", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "San Jose State Spartans": "san_jose_state_spartans", "San Jose State": "san_jose_state_spartans", "SJSU": "san_jose_state_spartans", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "UNLV Rebels": "unlv_rebels", "UNLV": "unlv_rebels", "Nevada-Las Vegas": "unlv_rebels", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Utah State Aggies": "utah_state_aggies", "Utah State": "utah_state_aggies", "USU": "utah_state_aggies", # Basketball (M/W), Volleyball (W), Football, Soccer (W); No Baseball
    "Wyoming Cowboys": "wyoming_cowboys", "Wyoming": "wyoming_cowboys", # Basketball (M/W), Volleyball (W), Football, Soccer (W); No Baseball

    # Sun Belt Conference
    "Appalachian State Mountaineers": "appalachian_state_mountaineers", "Appalachian State": "appalachian_state_mountaineers", "App State": "appalachian_state_mountaineers", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Arkansas State Red Wolves": "arkansas_state_red_wolves", "Arkansas State": "arkansas_state_red_wolves", "A-State": "arkansas_state_red_wolves", # Baseball, Basketball (M/W), Volleyball (W), Football; No Soccer
    "Coastal Carolina Chanticleers": "coastal_carolina_chanticleers", "Coastal Carolina": "coastal_carolina_chanticleers", "CCU": "coastal_carolina_chanticleers", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Georgia Southern Eagles": "georgia_southern_eagles", "Georgia Southern": "georgia_southern_eagles", "GSU": "georgia_southern_eagles", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Georgia State Panthers": "georgia_state_panthers", "Georgia State": "georgia_state_panthers", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "James Madison Dukes": "james_madison_dukes", "James Madison": "james_madison_dukes", "JMU": "james_madison_dukes", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Louisiana Ragin' Cajuns": "louisiana_ragin_cajuns", "Louisiana": "louisiana_ragin_cajuns", "UL Lafayette": "louisiana_ragin_cajuns", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Louisiana-Monroe Warhawks": "louisiana_monroe_warhawks", "Louisiana-Monroe": "louisiana_monroe_warhawks", "ULM": "louisiana_monroe_warhawks", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Marshall Thundering Herd": "marshall_thundering_herd", "Marshall": "marshall_thundering_herd", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Old Dominion Monarchs": "old_dominion_monarchs", "Old Dominion": "old_dominion_monarchs", "ODU": "old_dominion_monarchs", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "South Alabama Jaguars": "south_alabama_jaguars", "South Alabama": "south_alabama_jaguars", "USA": "south_alabama_jaguars", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Southern Miss Golden Eagles": "southern_miss_golden_eagles", "Southern Miss": "southern_miss_golden_eagles", "USM": "southern_miss_golden_eagles", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Texas State Bobcats": "texas_state_bobcats", "Texas State": "texas_state_bobcats", "TXST": "texas_state_bobcats", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Troy Trojans": "troy_trojans", "Troy": "troy_trojans", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)

    # Mid-American Conference (MAC)
    "Akron Zips": "akron_zips", "Akron": "akron_zips", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Ball State Cardinals": "ball_state_cardinals", "Ball State": "ball_state_cardinals", # Baseball, Basketball (M/W), Volleyball (W), Football; No Soccer
    "Bowling Green Falcons": "bowling_green_falcons", "Bowling Green": "bowling_green_falcons", "BGSU": "bowling_green_falcons", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Buffalo Bulls": "buffalo_bulls", "Buffalo": "buffalo_bulls", "UB": "buffalo_bulls", # Basketball (M/W), Volleyball (W), Football, Soccer (W); No Baseball
    "Central Michigan Chippewas": "central_michigan_chippewas", "Central Michigan": "central_michigan_chippewas", "CMU": "central_michigan_chippewas", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Eastern Michigan Eagles": "eastern_michigan_eagles", "Eastern Michigan": "eastern_michigan_eagles", "EMU": "eastern_michigan_eagles", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Kent State Golden Flashes": "kent_state_golden_flashes", "Kent State": "kent_state_golden_flashes", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Miami RedHawks": "miami_redhawks", "Miami (OH)": "miami_redhawks", "Miami Ohio": "miami_redhawks", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Northern Illinois Huskies": "northern_illinois_huskies", "Northern Illinois": "northern_illinois_huskies", "NIU": "northern_illinois_huskies", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Ohio Bobcats": "ohio_bobcats", "Ohio": "ohio_bobcats", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Toledo Rockets": "toledo_rockets", "Toledo": "toledo_rockets", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Western Michigan Broncos": "western_michigan_broncos", "Western Michigan": "western_michigan_broncos", "WMU": "western_michigan_broncos", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)

    # Atlantic 10 Conference (A-10)
    "Davidson Wildcats": "davidson_wildcats", "Davidson": "davidson_wildcats", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football in Pioneer League
    "Dayton Flyers": "dayton_flyers", "Dayton": "dayton_flyers", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football in Pioneer League
    "Duquesne Dukes": "duquesne_dukes", "Duquesne": "duquesne_dukes", # Basketball (M/W), Volleyball (W), Soccer (M/W); No Baseball, Football in NEC
    "Fordham Rams": "fordham_rams", "Fordham": "fordham_rams", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football in Patriot League
    "George Mason Patriots": "george_mason_patriots", "George Mason": "george_mason_patriots", # Baseball, Basketball (M/W), Volleyball (M/W), Soccer (M/W); No Football
    "George Washington Revolutionaries": "george_washington_revolutionaries", "George Washington": "george_washington_revolutionaries", "GW": "george_washington_revolutionaries", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "La Salle Explorers": "la_salle_explorers", "La Salle": "la_salle_explorers", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Loyola Chicago Ramblers": "loyola_chicago_ramblers", "Loyola Chicago": "loyola_chicago_ramblers", # Basketball (M/W), Volleyball (M/W), Soccer (M/W); No Baseball, No Football
    "Massachusetts Minutemen": "massachusetts_minutemen", "UMass": "massachusetts_minutemen", # Baseball, Basketball (M/W), Soccer (M/W); Football Independent, No Volleyball
    "Rhode Island Rams": "rhode_island_rams", "Rhode Island": "rhode_island_rams", "URI": "rhode_island_rams", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football in CAA
    "Richmond Spiders": "richmond_spiders", "Richmond": "richmond_spiders", # Baseball, Basketball (M/W), Soccer (W); Football in CAA, No Volleyball
    "Saint Joseph’s Hawks": "saint_josephs_hawks", "Saint Joseph’s": "saint_josephs_hawks", "St. Joseph’s": "saint_josephs_hawks", # Baseball, Basketball (M/W), Soccer (M/W); No Football, No Volleyball
    "Saint Louis Billikens": "saint_louis_billikens", "Saint Louis": "saint_louis_billikens", "SLU": "saint_louis_billikens", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "St. Bonaventure Bonnies": "st_bonaventure_bonnies", "St. Bonaventure": "st_bonaventure_bonnies", # Baseball, Basketball (M/W), Soccer (M/W); No Football, No Volleyball
    "VCU Rams": "vcu_rams", "VCU": "vcu_rams", "Virginia Commonwealth": "vcu_rams", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football

    # Big East Conference
    "Butler Bulldogs": "butler_bulldogs", "Butler": "butler_bulldogs", # Basketball (M/W), Volleyball (W), Soccer (M/W); No Baseball, No Football
    "Creighton Bluejays": "creighton_bluejays", "Creighton": "creighton_bluejays", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "DePaul Blue Demons": "depaul_blue_demons", "DePaul": "depaul_blue_demons", # Basketball (M/W), Volleyball (W), Soccer (M/W); No Baseball, No Football
    "Georgetown Hoyas": "georgetown_hoyas", "Georgetown": "georgetown_hoyas", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football in Patriot League
    "Marquette Golden Eagles": "marquette_golden_eagles", "Marquette": "marquette_golden_eagles", # Basketball (M/W), Volleyball (W), Soccer (M/W); No Baseball, No Football
    "Providence Friars": "providence_friars", "Providence": "providence_friars", # Basketball (M/W), Volleyball (W), Soccer (M/W); No Baseball, No Football
    "Seton Hall Pirates": "seton_hall_pirates", "Seton Hall": "seton_hall_pirates", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "St. John’s Red Storm": "st_johns_red_storm", "St. John’s": "st_johns_red_storm", "SJU": "st_johns_red_storm", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "UConn Huskies": "uconn_huskies", "UConn": "uconn_huskies", "Connecticut": "uconn_huskies", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football Independent
    "Villanova Wildcats": "villanova_wildcats", "Villanova": "villanova_wildcats", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football in CAA
    "Xavier Musketeers": "xavier_musketeers", "Xavier": "xavier_musketeers", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football

    # Missouri Valley Conference (MVC)
    "Belmont Bruins": "belmont_bruins", "Belmont": "belmont_bruins", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Bradley Braves": "bradley_braves", "Bradley": "bradley_braves", # Baseball, Basketball (M/W), Volleyball (W); No Football, No Soccer
    "Drake Bulldogs": "drake_bulldogs", "Drake": "drake_bulldogs", # Basketball (M/W), Volleyball (W), Soccer (M/W); No Baseball, Football in Pioneer League
    "Evansville Purple Aces": "evansville_purple_aces", "Evansville": "evansville_purple_aces", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Illinois State Redbirds": "illinois_state_redbirds", "Illinois State": "illinois_state_redbirds", # Baseball, Basketball (M/W), Volleyball (W); Football in MVFC, No Soccer
    "Indiana State Sycamores": "indiana_state_sycamores", "Indiana State": "indiana_state_sycamores", # Baseball, Basketball (M/W), Volleyball (W); Football in MVFC, No Soccer
    "Missouri State Bears": "missouri_state_bears", "Missouri State": "missouri_state_bears", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football in MVFC
    "Murray State Racers": "murray_state_racers", "Murray State": "murray_state_racers", # Baseball, Basketball (M/W), Volleyball (W); Football in MVFC, No Soccer
    "Northern Iowa Panthers": "northern_iowa_panthers", "Northern Iowa": "northern_iowa_panthers", "UNI": "northern_iowa_panthers", # Basketball (M/W), Volleyball (W); Football in MVFC, No Baseball, No Soccer
    "Southern Illinois Salukis": "southern_illinois_salukis", "Southern Illinois": "southern_illinois_salukis", "SIU": "southern_illinois_salukis", # Baseball, Basketball (M/W), Volleyball (W); Football in MVFC, No Soccer
    "UIC Flames": "uic_flames", "UIC": "uic_flames", "Illinois-Chicago": "uic_flames", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Valparaiso Beacons": "valparaiso_beacons", "Valparaiso": "valparaiso_beacons", "Valpo": "valparaiso_beacons", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football in Pioneer League

    # West Coast Conference (WCC)
    "Gonzaga Bulldogs": "gonzaga_bulldogs", "Gonzaga": "gonzaga_bulldogs", "GU": "gonzaga_bulldogs", # Basketball (M/W), Volleyball (W), Soccer (M/W); No Baseball, No Football
    "Loyola Marymount Lions": "loyola_marymount_lions", "Loyola Marymount": "loyola_marymount_lions", "LMU": "loyola_marymount_lions", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Pacific Tigers": "pacific_tigers", "Pacific": "pacific_tigers", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Pepperdine Waves": "pepperdine_waves", "Pepperdine": "pepperdine_waves", # Baseball, Basketball (M/W), Volleyball (M/W), Soccer (W); No Football
    "Portland Pilots": "portland_pilots", "Portland": "portland_pilots", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Saint Mary’s Gaels": "saint_marys_gaels", "Saint Mary’s": "saint_marys_gaels", "SMC": "saint_marys_gaels", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "San Diego Toreros": "san_diego_toreros", "San Diego": "san_diego_toreros", "USD": "san_diego_toreros", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football in Pioneer League
    "San Francisco Dons": "san_francisco_dons", "San Francisco": "san_francisco_dons", "USF": "san_francisco_dons", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Santa Clara Broncos": "santa_clara_broncos", "Santa Clara": "santa_clara_broncos", "SCU": "santa_clara_broncos", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football

    # Horizon League
    "Cleveland State Vikings": "cleveland_state_vikings", "Cleveland State": "cleveland_state_vikings", "CSU": "cleveland_state_vikings", # Basketball (M/W), Volleyball (W), Soccer (M/W); No Baseball, No Football
    "Detroit Mercy Titans": "detroit_mercy_titans", "Detroit Mercy": "detroit_mercy_titans", "UDM": "detroit_mercy_titans", # Basketball (M/W), Volleyball (W), Soccer (M/W); No Baseball, No Football
    "Green Bay Phoenix": "green_bay_phoenix", "Green Bay": "green_bay_phoenix", "UWGB": "green_bay_phoenix", # Basketball (M/W), Volleyball (W), Soccer (M/W); No Baseball, No Football
    "IU Indy Jaguars": "iu_indy_jaguars", "IU Indy": "iu_indy_jaguars", "IUPUI": "iu_indy_jaguars", # Basketball (M/W), Volleyball (W), Soccer (M/W); No Baseball, No Football
    "Milwaukee Panthers": "milwaukee_panthers", "Milwaukee": "milwaukee_panthers", "UWM": "milwaukee_panthers", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Northern Kentucky Norse": "northern_kentucky_norse", "Northern Kentucky": "northern_kentucky_norse", "NKU": "northern_kentucky_norse", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Oakland Golden Grizzlies": "oakland_golden_grizzlies", "Oakland": "oakland_golden_grizzlies", # Basketball (M/W), Volleyball (W), Soccer (M/W); No Baseball, No Football
    "Purdue Fort Wayne Mastodons": "purdue_fort_wayne_mastodons", "Purdue Fort Wayne": "purdue_fort_wayne_mastodons", "PFW": "purdue_fort_wayne_mastodons", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Robert Morris Colonials": "robert_morris_colonials", "Robert Morris": "robert_morris_colonials", "RMU": "robert_morris_colonials", # Basketball (M/W), Volleyball (W), Soccer (M/W); No Baseball, Football in Big South-OVC
    "Wright State Raiders": "wright_state_raiders", "Wright State": "wright_state_raiders", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Youngstown State Penguins": "youngstown_state_penguins", "Youngstown State": "youngstown_state_penguins", "YSU": "youngstown_state_penguins", # Baseball, Basketball (M/W), Volleyball (W), Soccer (W); Football in MVFC

    # Colonial Athletic Association (CAA)
    "Campbell Fighting Camels": "campbell_fighting_camels", "Campbell": "campbell_fighting_camels", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football in CAA Football
    "Charleston Cougars": "charleston_cougars", "College of Charleston": "charleston_cougars", "CofC": "charleston_cougars", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Delaware Blue Hens": "delaware_blue_hens", "Delaware": "delaware_blue_hens", "UD": "delaware_blue_hens", "delaware Lee's": "delaware_blue_hens", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football in CAA Football
    "Drexel Dragons": "drexel_dragons", "Drexel": "drexel_dragons", # Basketball (M/W), Volleyball (W), Soccer (M/W); No Baseball, No Football
    "Elon Phoenix": "elon_phoenix", "Elon": "elon_phoenix", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football in CAA Football
    "Hampton Pirates": "hampton_pirates", "Hampton": "hampton_pirates", # Basketball (M/W), Volleyball (W), Soccer (W); Football in CAA Football, No Baseball
    "Hofstra Pride": "hofstra_pride", "Hofstra": "hofstra_pride", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Monmouth Hawks": "monmouth_hawks", "Monmouth": "monmouth_hawks", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football in CAA Football
    "North Carolina A&T Aggies": "north_carolina_a_and_t_aggies", "North Carolina A&T": "north_carolina_a_and_t_aggies", "NC A&T": "north_carolina_a_and_t_aggies", # Baseball, Basketball (M/W), Volleyball (W); Football in CAA Football, No Soccer
    "Northeastern Huskies": "northeastern_huskies", "Northeastern": "northeastern_huskies", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Stony Brook Seawolves": "stony_brook_seawolves", "Stony Brook": "stony_brook_seawolves", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football in CAA Football
    "Towson Tigers": "towson_tigers", "Towson": "towson_tigers", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football in CAA Football
    "UNC Wilmington Seahawks": "unc_wilmington_seahawks", "UNC Wilmington": "unc_wilmington_seahawks", "UNCW": "unc_wilmington_seahawks", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "William & Mary Tribe": "william_and_mary_tribe", "William & Mary": "william_and_mary_tribe", "W&M": "william_and_mary_tribe", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football in CAA Football

    # Summit League
    "Denver Pioneers": "denver_pioneers", "Denver": "denver_pioneers", "DU": "denver_pioneers", # Basketball (M/W), Volleyball (W), Soccer (M/W); No Baseball, No Football
    "Kansas City Roos": "kansas_city_roos", "Kansas City": "kansas_city_roos", "UMKC": "kansas_city_roos", # Basketball (M/W), Volleyball (W), Soccer (M/W); No Baseball, No Football
    "North Dakota Fighting Hawks": "north_dakota_fighting_hawks", "North Dakota": "north_dakota_fighting_hawks", "UND": "north_dakota_fighting_hawks", # Basketball (M/W), Volleyball (W); Football in MVFC, No Baseball, No Soccer
    "North Dakota State Bison": "north_dakota_state_bison", "North Dakota State": "north_dakota_state_bison", "NDSU": "north_dakota_state_bison", # Baseball, Basketball (M/W), Volleyball (W); Football in MVFC, No Soccer
    "Omaha Mavericks": "omaha_mavericks", "Omaha": "omaha_mavericks", "UNO": "omaha_mavericks", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Oral Roberts Golden Eagles": "oral_roberts_golden_eagles", "Oral Roberts": "oral_roberts_golden_eagles", "ORU": "oral_roberts_golden_eagles", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "South Dakota Coyotes": "south_dakota_coyotes", "South Dakota": "south_dakota_coyotes", "USD": "south_dakota_coyotes", # Basketball (M/W), Volleyball (W); Football in MVFC, No Baseball, No Soccer
    "South Dakota State Jackrabbits": "south_dakota_state_jackrabbits", "South Dakota State": "south_dakota_state_jackrabbits", "SDSU": "south_dakota_state_jackrabbits", # Baseball, Basketball (M/W), Volleyball (W); Football in MVFC, No Soccer
    "St. Thomas Tommies": "st_thomas_tommies", "St. Thomas": "st_thomas_tommies", "UST": "st_thomas_tommies", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football in Pioneer League

    # Patriot League
    "American Eagles": "american_eagles", "American": "american_eagles", "AU": "american_eagles", # Basketball (M/W), Volleyball (W), Soccer (M/W); No Baseball, No Football
    "Army Black Knights": "army_black_knights", "Army": "army_black_knights", "West Point": "army_black_knights", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football Independent
    "Boston University Terriers": "boston_university_terriers", "Boston University": "boston_university_terriers", "BU": "boston_university_terriers", # Basketball (M/W), Volleyball (W), Soccer (M/W); No Baseball, No Football
    "Bucknell Bison": "bucknell_bison", "Bucknell": "bucknell_bison", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football in Patriot League
    "Colgate Raiders": "colgate_raiders", "Colgate": "colgate_raiders", # Basketball (M/W), Volleyball (W), Soccer (M/W); Football in Patriot League, No Baseball
    "Holy Cross Crusaders": "holy_cross_crusaders", "Holy Cross": "holy_cross_crusaders", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football in Patriot League
    "Lafayette Leopards": "lafayette_leopards", "Lafayette": "lafayette_leopards", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football in Patriot League
    "Lehigh Mountain Hawks": "lehigh_mountain_hawks", "Lehigh": "lehigh_mountain_hawks", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football in Patriot League
    "Loyola Maryland Greyhounds": "loyola_maryland_greyhounds", "Loyola Maryland": "loyola_maryland_greyhounds", # Basketball (M/W), Volleyball (W), Soccer (M/W); No Baseball, No Football
    "Navy Midshipmen": "navy_midshipmen", "Navy": "navy_midshipmen", "Naval Academy": "navy_midshipmen", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football in American Athletic

    # Southern Conference (SoCon)
    "Chattanooga Mocs": "chattanooga_mocs", "Chattanooga": "chattanooga_mocs", "UTC": "chattanooga_mocs", # Basketball (M/W), Volleyball (W), Soccer (W); Football in SoCon, No Baseball
    "Citadel Bulldogs": "citadel_bulldogs", "Citadel": "citadel_bulldogs", "The Citadel": "citadel_bulldogs", # Baseball, Basketball (M/W), Football; No Volleyball, No Soccer
    "East Tennessee State Buccaneers": "east_tennessee_state_buccaneers", "East Tennessee State": "east_tennessee_state_buccaneers", "ETSU": "east_tennessee_state_buccaneers", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football in SoCon
    "Furman Paladins": "furman_paladins", "Furman": "furman_paladins", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football in SoCon
    "Mercer Bears": "mercer_bears", "Mercer": "mercer_bears", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football in SoCon
    "Samford Bulldogs": "samford_bulldogs", "Samford": "samford_bulldogs", # Baseball, Basketball (M/W), Volleyball (W); Football in SoCon, No Soccer
    "UNC Greensboro Spartans": "unc_greensboro_spartans", "UNC Greensboro": "unc_greensboro_spartans", "UNCG": "unc_greensboro_spartans", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "VMI Keydets": "vmi_keydets", "VMI": "vmi_keydets", "Virginia Military Institute": "vmi_keydets", # Baseball, Basketball (M/W), Soccer (M/W); Football in SoCon, No Volleyball
    "Western Carolina Catamounts": "western_carolina_catamounts", "Western Carolina": "western_carolina_catamounts", "WCU": "western_carolina_catamounts", # Baseball, Basketball (M/W), Volleyball (W), Soccer (W); Football in SoCon
    "Wofford Terriers": "wofford_terriers", "Wofford": "wofford_terriers", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football in SoCon

    # America East Conference
    "Albany Great Danes": "albany_great_danes", "Albany": "albany_great_danes", "UAlbany": "albany_great_danes", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Binghamton Bearcats": "binghamton_bearcats", "Binghamton": "binghamton_bearcats", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Bryant Bulldogs": "bryant_bulldogs", "Bryant": "bryant_bulldogs", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Maine Black Bears": "maine_black_bears", "Maine": "maine_black_bears", "UMaine": "maine_black_bears", # Baseball, Basketball (M/W), Soccer (W); Football in CAA Football, No Volleyball
    "UMass Lowell River Hawks": "umass_lowell_river_hawks", "UMass Lowell": "umass_lowell_river_hawks", # Baseball, Basketball (M/W), Soccer (M/W); No Football, No Volleyball
    "New Hampshire Wildcats": "new_hampshire_wildcats", "New Hampshire": "new_hampshire_wildcats", "UNH": "new_hampshire_wildcats", # Basketball (M/W), Volleyball (W), Soccer (M/W); Football in CAA Football, No Baseball
    "NJIT Highlanders": "njit_highlanders", "NJIT": "njit_highlanders", "New Jersey Institute of Technology": "njit_highlanders", # Baseball, Basketball (M/W), Volleyball (M/W), Soccer (M/W); No Football
    "UMBC Retrievers": "umbc_retrievers", "UMBC": "umbc_retrievers", "Maryland-Baltimore County": "umbc_retrievers", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Vermont Catamounts": "vermont_catamounts", "Vermont": "vermont_catamounts", "UVM": "vermont_catamounts", # Basketball (M/W), Soccer (M/W); No Baseball, No Football, No Volleyball

    # Atlantic Sun Conference (ASUN)
    "Austin Peay Governors": "austin_peay_governors", "Austin Peay": "austin_peay_governors", "APSU": "austin_peay_governors", # Baseball, Basketball (M/W), Volleyball (W), Soccer (W); Football in UAC
    "Bellarmine Knights": "bellarmine_knights", "Bellarmine": "bellarmine_knights", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Central Arkansas Bears": "central_arkansas_bears", "Central Arkansas": "central_arkansas_bears", "UCA": "central_arkansas_bears", # Baseball, Basketball (M/W), Volleyball (W), Soccer (W); Football in UAC
    "Eastern Kentucky Colonels": "eastern_kentucky_colonels", "Eastern Kentucky": "eastern_kentucky_colonels", "EKU": "eastern_kentucky_colonels", # Baseball, Basketball (M/W), Volleyball (W), Soccer (W); Football in UAC
    "Florida Gulf Coast Eagles": "florida_gulf_coast_eagles", "Florida Gulf Coast": "florida_gulf_coast_eagles", "FGCU": "florida_gulf_coast_eagles", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Jacksonville Dolphins": "jacksonville_dolphins", "Jacksonville": "jacksonville_dolphins", "JU": "jacksonville_dolphins", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Lipscomb Bisons": "lipscomb_bisons", "Lipscomb": "lipscomb_bisons", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "North Alabama Lions": "north_alabama_lions", "North Alabama": "north_alabama_lions", "UNA": "north_alabama_lions", # Baseball, Basketball (M/W), Volleyball (W), Soccer (W); Football in UAC
    "North Florida Ospreys": "north_florida_ospreys", "North Florida": "north_florida_ospreys", "UNF": "north_florida_ospreys", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Queens Royals": "queens_royals", "Queens": "queens_royals", "Queens University": "queens_royals", # Baseball, Basketball (M/W), Volleyball (M/W), Soccer (M/W); No Football
    "Stetson Hatters": "stetson_hatters", "Stetson": "stetson_hatters", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "West Georgia Wolves": "west_georgia_wolves", "West Georgia": "west_georgia_wolves", "UWG": "west_georgia_wolves", # Baseball, Basketball (M/W), Volleyball (W), Soccer (W); Football in UAC

    # Big Sky Conference
    "Eastern Washington Eagles": "eastern_washington_eagles", "Eastern Washington": "eastern_washington_eagles", "EWU": "eastern_washington_eagles", # Basketball (M/W), Volleyball (W), Football; No Baseball, No Soccer
    "Idaho Vandals": "idaho_vandals", "Idaho": "idaho_vandals", "UI": "idaho_vandals", # Basketball (M/W), Volleyball (W), Football, Soccer (W); No Baseball
    "Idaho State Bengals": "idaho_state_bengals", "Idaho State": "idaho_state_bengals", "ISU": "idaho_state_bengals", # Basketball (M/W), Volleyball (W), Football, Soccer (W); No Baseball
    "Montana Grizzlies": "montana_grizzlies", "Montana": "montana_grizzlies", "UM": "montana_grizzlies", # Basketball (M/W), Volleyball (W), Football, Soccer (W); No Baseball
    "Montana State Bobcats": "montana_state_bobcats", "Montana State": "montana_state_bobcats", "MSU": "montana_state_bobcats", # Basketball (M/W), Volleyball (W), Football; No Baseball, No Soccer
    "Northern Arizona Lumberjacks": "northern_arizona_lumberjacks", "Northern Arizona": "northern_arizona_lumberjacks", "NAU": "northern_arizona_lumberjacks", # Basketball (M/W), Volleyball (W), Football, Soccer (W); No Baseball
    "Northern Colorado Bears": "northern_colorado_bears", "Northern Colorado": "northern_colorado_bears", "UNC": "northern_colorado_bears", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Portland State Vikings": "portland_state_vikings", "Portland State": "portland_state_vikings", "PSU": "portland_state_vikings", # Basketball (M/W), Volleyball (W), Football, Soccer (W); No Baseball
    "Sacramento State Hornets": "sacramento_state_hornets", "Sacramento State": "sacramento_state_hornets", "Sac State": "sacramento_state_hornets", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Weber State Wildcats": "weber_state_wildcats", "Weber State": "weber_state_wildcats", # Basketball (M/W), Volleyball (W), Football, Soccer (W); No Baseball

    # Big South Conference
    "Charleston Southern Buccaneers": "charleston_southern_buccaneers", "Charleston Southern": "charleston_southern_buccaneers", "CSU": "charleston_southern_buccaneers", # Baseball, Basketball (M/W), Volleyball (W), Soccer (W); Football in Big South-OVC
    "Gardner-Webb Runnin’ Bulldogs": "gardner_webb_runnin_bulldogs", "Gardner-Webb": "gardner_webb_runnin_bulldogs", "GWU": "gardner_webb_runnin_bulldogs", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football in Big South-OVC
    "High Point Panthers": "high_point_panthers", "High Point": "high_point_panthers", "HPU": "high_point_panthers", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Longwood Lancers": "longwood_lancers", "Longwood": "longwood_lancers", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Presbyterian Blue Hose": "presbyterian_blue_hose", "Presbyterian": "presbyterian_blue_hose", "PC": "presbyterian_blue_hose", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football in Pioneer League
    "Radford Highlanders": "radford_highlanders", "Radford": "radford_highlanders", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "South Carolina Upstate Spartans": "south_carolina_upstate_spartans", "USC Upstate": "south_carolina_upstate_spartans", "Upstate": "south_carolina_upstate_spartans", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "UNC Asheville Bulldogs": "unc_asheville_bulldogs", "UNC Asheville": "unc_asheville_bulldogs", "UNCA": "unc_asheville_bulldogs", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Winthrop Eagles": "winthrop_eagles", "Winthrop": "winthrop_eagles", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football

    # Northeast Conference (NEC)
    "Central Connecticut Blue Devils": "central_connecticut_blue_devils", "Central Connecticut": "central_connecticut_blue_devils", "CCSU": "central_connecticut_blue_devils", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football in NEC
    "Fairleigh Dickinson Knights": "fairleigh_dickinson_knights", "FDU": "fairleigh_dickinson_knights", "Fairleigh Dickinson": "fairleigh_dickinson_knights", # Basketball (M/W), Volleyball (W), Soccer (M/W); No Baseball, No Football
    "Le Moyne Dolphins": "le_moyne_dolphins", "Le Moyne": "le_moyne_dolphins", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "LIU Sharks": "liu_sharks", "Long Island": "liu_sharks", "LIU": "liu_sharks", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football in NEC
    "Mercyhurst Lakers": "mercyhurst_lakers", "Mercyhurst": "mercyhurst_lakers", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football in NEC
    "Sacred Heart Pioneers": "sacred_heart_pioneers", "Sacred Heart": "sacred_heart_pioneers", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football in NEC
    "Saint Francis Red Flash": "saint_francis_red_flash", "Saint Francis": "saint_francis_red_flash", "SFU": "saint_francis_red_flash", # Basketball (M/W), Volleyball (W), Soccer (M/W); Football in NEC, No Baseball
    "Stonehill Skyhawks": "stonehill_skyhawks", "Stonehill": "stonehill_skyhawks", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football in NEC
    "Wagner Seahawks": "wagner_seahawks", "Wagner": "wagner_seahawks", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football in NEC

    # Ohio Valley Conference (OVC)
    "Eastern Illinois Panthers": "eastern_illinois_panthers", "Eastern Illinois": "eastern_illinois_panthers", "EIU": "eastern_illinois_panthers", # Baseball, Basketball (M/W), Volleyball (W), Soccer (W); Football in Big South-OVC
    "Lindenwood Lions": "lindenwood_lions", "Lindenwood": "lindenwood_lions", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football in Big South-OVC
    "Little Rock Trojans": "little_rock_trojans", "Little Rock": "little_rock_trojans", "UALR": "little_rock_trojans", # Basketball (M/W), Volleyball (W); No Baseball, No Football, No Soccer
    "Morehead State Eagles": "morehead_state_eagles", "Morehead State": "morehead_state_eagles", # Baseball, Basketball (M/W), Volleyball (W); Football in Pioneer League, No Soccer
    "SIU Edwardsville Cougars": "siu_edwardsville_cougars", "SIU Edwardsville": "siu_edwardsville_cougars", "SIUE": "siu_edwardsville_cougars", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Southeast Missouri Redhawks": "southeast_missouri_redhawks", "Southeast Missouri": "southeast_missouri_redhawks", "SEMO": "southeast_missouri_redhawks", # Baseball, Basketball (M/W), Volleyball (W), Soccer (W); Football in Big South-OVC
    "Southern Indiana Screaming Eagles": "southern_indiana_screaming_eagles", "Southern Indiana": "southern_indiana_screaming_eagles", "USI": "southern_indiana_screaming_eagles", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Tennessee State Tigers": "tennessee_state_tigers", "Tennessee State": "tennessee_state_tigers", "TSU": "tennessee_state_tigers", # Basketball (M/W), Volleyball (W); Football in Big South-OVC, No Baseball, No Soccer
    "Tennessee Tech Golden Eagles": "tennessee_tech_golden_eagles", "Tennessee Tech": "tennessee_tech_golden_eagles", "TTU": "tennessee_tech_golden_eagles", # Baseball, Basketball (M/W), Volleyball (W), Soccer (W); Football in Big South-OVC
    "UT Martin Skyhawks": "ut_martin_skyhawks", "UT Martin": "ut_martin_skyhawks", "UTM": "ut_martin_skyhawks", # Baseball, Basketball (M/W), Volleyball (W), Soccer (W); Football in Big South-OVC
    "Western Illinois Leathernecks": "western_illinois_leathernecks", "Western Illinois": "western_illinois_leathernecks", "WIU": "western_illinois_leathernecks", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football in Big South-OVC

    # Southland Conference
    "Houston Christian Huskies": "houston_christian_huskies", "Houston Christian": "houston_christian_huskies", "HCU": "houston_christian_huskies", # Baseball, Basketball (M/W), Volleyball (W), Soccer (W); Football in Southland
    "Incarnate Word Cardinals": "incarnate_word_cardinals", "Incarnate Word": "incarnate_word_cardinals", "UIW": "incarnate_word_cardinals", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football in Southland
    "Lamar Cardinals": "lamar_cardinals", "Lamar": "lamar_cardinals", # Baseball, Basketball (M/W), Volleyball (W), Soccer (W); Football in Southland
    "McNeese Cowboys": "mcneese_cowboys", "McNeese": "mcneese_cowboys", "McNeese State": "mcneese_cowboys", # Baseball, Basketball (M/W), Volleyball (W), Soccer (W); Football in Southland
    "New Orleans Privateers": "new_orleans_privateers", "New Orleans": "new_orleans_privateers", "UNO": "new_orleans_privateers", # Baseball, Basketball (M/W), Volleyball (W); No Football, No Soccer
    "Nicholls Colonels": "nicholls_colonels", "Nicholls": "nicholls_colonels", "Nicholls State": "nicholls_colonels", # Baseball, Basketball (M/W), Volleyball (W), Soccer (W); Football in Southland
    "Northwestern State Demons": "northwestern_state_demons", "Northwestern State": "northwestern_state_demons", "NSU": "northwestern_state_demons", # Baseball, Basketball (M/W), Volleyball (W), Soccer (W); Football in Southland
    "Southeastern Louisiana Lions": "southeastern_louisiana_lions", "Southeastern Louisiana": "southeastern_louisiana_lions", "SLU": "southeastern_louisiana_lions", # Baseball, Basketball (M/W), Volleyball (W), Soccer (]== "southeastern_louisiana_lions", # Baseball, Basketball (M/W), Volleyball (W), Soccer (W); Football in Southland
    "Stephen F. Austin Lumberjacks": "stephen_f_austin_lumberjacks", "Stephen F. Austin": "stephen_f_austin_lumberjacks", "SFA": "stephen_f_austin_lumberjacks", # Baseball, Basketball (M/W), Volleyball (W), Soccer (W); Football in Southland
    "Texas A&M-Commerce Lions": "texas_a_and_m_commerce_lions", "Texas A&M-Commerce": "texas_a_and_m_commerce_lions", "TAMUC": "texas_a_and_m_commerce_lions", # Baseball, Basketball (M/W), Volleyball (W), Soccer (W); Football in Southland
    "Texas A&M-Corpus Christi Islanders": "texas_a_and_m_corpus_christi_islanders", "Texas A&M-Corpus Christi": "texas_a_and_m_corpus_christi_islanders", "TAMUCC": "texas_a_and_m_corpus_christi_islanders", # Baseball, Basketball (M/W), Volleyball (W), Soccer (W); No Football

    # Southwestern Athletic Conference (SWAC)
    "Alabama A&M Bulldogs": "alabama_a_and_m_bulldogs", "Alabama A&M": "alabama_a_and_m_bulldogs", "AAMU": "alabama_a_and_m_bulldogs", # Baseball, Basketball (M/W), Volleyball (W), Soccer (W); Football in SWAC
    "Alabama State Hornets": "alabama_state_hornets", "Alabama State": "alabama_state_hornets", "ASU": "alabama_state_hornets", # Baseball, Basketball (M/W), Volleyball (W), Soccer (W); Football in SWAC
    "Alcorn State Braves": "alcorn_state_braves", "Alcorn State": "alcorn_state_braves", # Baseball, Basketball (M/W), Volleyball (W), Soccer (W); Football in SWAC
    "Arkansas-Pine Bluff Golden Lions": "arkansas_pine_bluff_golden_lions", "Arkansas-Pine Bluff": "arkansas_pine_bluff_golden_lions", "UAPB": "arkansas_pine_bluff_golden_lions", # Baseball, Basketball (M/W), Volleyball (W), Soccer (W); Football in SWAC
    "Bethune-Cookman Wildcats": "bethune_cookman_wildcats", "Bethune-Cookman": "bethune_cookman_wildcats", "B-CU": "bethune_cookman_wildcats", # Baseball, Basketball (M/W), Volleyball (W); Football in SWAC, No Soccer
    "Florida A&M Rattlers": "florida_a_and_m_rattlers", "Florida A&M": "florida_a_and_m_rattlers", "FAMU": "florida_a_and_m_rattlers", # Baseball, Basketball (M/W), Volleyball (W); Football in SWAC, No Soccer
    "Grambling State Tigers": "grambling_state_tigers", "Grambling State": "grambling_state_tigers", "GSU": "grambling_state_tigers", # Baseball, Basketball (M/W), Volleyball (W), Soccer (W); Football in SWAC
    "Jackson State Tigers": "jackson_state_tigers", "Jackson State": "jackson_state_tigers", "JSU": "jackson_state_tigers", # Baseball, Basketball (M/W), Volleyball (W), Soccer (W); Football in SWAC
    "Mississippi Valley State Delta Devils": "mississippi_valley_state_delta_devils", "Mississippi Valley State": "mississippi_valley_state_delta_devils", "MVSU": "mississippi_valley_state_delta_devils", # Baseball, Basketball (M/W), Volleyball (W), Soccer (W); Football in SWAC
    "Prairie View A&M Panthers": "prairie_view_a_and_m_panthers", "Prairie View A&M": "prairie_view_a_and_m_panthers", "PVAMU": "prairie_view_a_and_m_panthers", # Baseball, Basketball (M/W), Volleyball (W), Soccer (W); Football in SWAC
    "Southern Jaguars": "southern_jaguars", "Southern": "southern_jaguars", "SUBR": "southern_jaguars", # Baseball, Basketball (M/W), Volleyball (W), Soccer (W); Football in SWAC
    "Texas Southern Tigers": "texas_southern_tigers", "Texas Southern": "texas_southern_tigers", "TSU": "texas_southern_tigers", # Baseball, Basketball (M/W), Volleyball (W), Soccer (W); Football in SWAC

    # Western Athletic Conference (WAC)
    "Abilene Christian Wildcats": "abilene_christian_wildcats", "Abilene Christian": "abilene_christian_wildcats", "ACU": "abilene_christian_wildcats", # Baseball, Basketball (M/W), Volleyball (W), Soccer (W); Football in UAC
    "Cal Baptist Lancers": "cal_baptist_lancers", "Cal Baptist": "cal_baptist_lancers", "CBU": "cal_baptist_lancers", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Grand Canyon Antelopes": "grand_canyon_antelopes", "Grand Canyon": "grand_canyon_antelopes", "GCU": "grand_canyon_antelopes", # Baseball, Basketball (M/W), Volleyball (M/W), Soccer (M/W); No Football
    "Seattle U Redhawks": "seattle_u_redhawks", "Seattle U": "seattle_u_redhawks", "SU": "seattle_u_redhawks", # Basketball (M/W), Volleyball (W), Soccer (M/W); No Baseball, No Football
    "Southern Utah Thunderbirds": "southern_utah_thunderbirds", "Southern Utah": "southern_utah_thunderbirds", "SUU": "southern_utah_thunderbirds", # Basketball (M/W), Volleyball (W), Soccer (W); Football in UAC, No Baseball
    "Tarleton State Texans": "tarleton_state_texans", "Tarleton State": "tarleton_state_texans", "TSU": "tarleton_state_texans", # Baseball, Basketball (M/W), Volleyball (W), Soccer (W); Football in UAC
    "Utah Tech Trailblazers": "utah_tech_trailblazers", "Utah Tech": "utah_tech_trailblazers", # Baseball, Basketball (M/W), Volleyball (W), Soccer (W); Football in UAC
    "Utah Valley Wolverines": "utah_valley_wolverines", "Utah Valley": "utah_valley_wolverines", "UVU": "utah_valley_wolverines", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "UT Rio Grande Valley Vaqueros": "ut_rio_grande_valley_vaqueros", "UT Rio Grande Valley": "ut_rio_grande_valley_vaqueros", "UTRGV": "ut_rio_grande_valley_vaqueros", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football

    # Ivy League
    "Brown Bears": "brown_bears", "Brown": "brown_bears", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football in Ivy League (FCS)
    "Columbia Lions": "columbia_lions", "Columbia": "columbia_lions", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football in Ivy League (FCS)
    "Cornell Big Red": "cornell_big_red", "Cornell": "cornell_big_red", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football in Ivy League (FCS)
    "Dartmouth Big Green": "dartmouth_big_green", "Dartmouth": "dartmouth_big_green", # Baseball, Basketball (M/W), Soccer (M/W); Football in Ivy League (FCS), No Volleyball
    "Harvard Crimson": "harvard_crimson", "Harvard": "harvard_crimson", # Baseball, Basketball (M/W), Volleyball (M/W), Soccer (M/W); Football in Ivy League (FCS)
    "Penn Quakers": "penn_quakers", "Penn": "penn_quakers", "Pennsylvania": "penn_quakers", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football in Ivy League (FCS)
    "Princeton Tigers": "princeton_tigers", "Princeton": "princeton_tigers", # Baseball, Basketball (M/W), Volleyball (M/W), Soccer (M/W); Football in Ivy League (FCS)
    "Yale Bulldogs": "yale_bulldogs", "Yale": "yale_bulldogs", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); Football in Ivy League (FCS)

    # Metro Atlantic Athletic Conference (MAAC)
    "Canisius Golden Griffins": "canisius_golden_griffins", "Canisius": "canisius_golden_griffins", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Fairfield Stags": "fairfield_stags", "Fairfield": "fairfield_stags", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Iona Gaels": "iona_gaels", "Iona": "iona_gaels", # Basketball (M/W), Volleyball (W), Soccer (M/W); No Baseball, No Football
    "Manhattan Jaspers": "manhattan_jaspers", "Manhattan": "manhattan_jaspers", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Marist Red Foxes": "marist_red_foxes", "Marist": "marist_red_foxes", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Merrimack Warriors": "merrimack_warriors", "Merrimack": "merrimack_warriors", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Mount St. Mary’s Mountaineers": "mount_st_marys_mountaineers", "Mount St. Mary’s": "mount_st_marys_mountaineers", "The Mount": "mount_st_marys_mountaineers", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Niagara Purple Eagles": "niagara_purple_eagles", "Niagara": "niagara_purple_eagles", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Quinnipiac Bobcats": "quinnipiac_bobcats", "Quinnipiac": "quinnipiac_bobcats", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Rider Broncs": "rider_broncs", "Rider": "rider_broncs", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Siena Saints": "siena_saints", "Siena": "siena_saints", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Saint Peter’s Peacocks": "saint_peters_peacocks", "Saint Peter’s": "saint_peters_peacocks", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football

    # Mid-Eastern Athletic Conference (MEAC)
    "Coppin State Eagles": "coppin_state_eagles", "Coppin State": "coppin_state_eagles", # Baseball, Basketball (M/W), Volleyball (W); No Football, No Soccer
    "Delaware State Hornets": "delaware_state_hornets", "Delaware State": "delaware_state_hornets", "DSU": "delaware_state_hornets", # Baseball, Basketball (M/W), Volleyball (W), Soccer (W); Football in MEAC
    "Howard Bison": "howard_bison", "Howard": "howard_bison", # Basketball (M/W), Volleyball (W), Soccer (M/W); Football in MEAC, No Baseball
    "Morgan State Bears": "morgan_state_bears", "Morgan State": "morgan_state_bears", # Basketball (M/W), Volleyball (W); Football in MEAC, No Baseball, No Soccer
    "Norfolk State Spartans": "norfolk_state_spartans", "Norfolk State": "norfolk_state_spartans", "NSU": "norfolk_state_spartans", # Baseball, Basketball (M/W), Volleyball (W); Football in MEAC, No Soccer
    "North Carolina Central Eagles": "north_carolina_central_eagles", "North Carolina Central": "north_carolina_central_eagles", "NCCU": "north_carolina_central_eagles", # Baseball, Basketball (M/W), Volleyball (W); Football in MEAC, No Soccer
    "South Carolina State Bulldogs": "south_carolina_state_bulldogs", "South Carolina State": "south_carolina_state_bulldogs", "SCSU": "south_carolina_state_bulldogs", # Basketball (M/W), Volleyball (W), Soccer (W); Football in MEAC, No Baseball

    # Big West Conference
    "Cal Poly Mustangs": "cal_poly_mustangs", "Cal Poly": "cal_poly_mustangs", "Cal Poly SLO": "cal_poly_mustangs", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Cal State Bakersfield Roadrunners": "cal_state_bakersfield_roadrunners", "Cal State Bakersfield": "cal_state_bakersfield_roadrunners", "CSUB": "cal_state_bakersfield_roadrunners", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Cal State Fullerton Titans": "cal_state_fullerton_titans", "Cal State Fullerton": "cal_state_fullerton_titans", "CSUF": "cal_state_fullerton_titans", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Cal State Northridge Matadors": "cal_state_northridge_matadors", "Cal State Northridge": "cal_state_northridge_matadors", "CSUN": "cal_state_northridge_matadors", # Baseball, Basketball (M/W), Volleyball (M/W), Soccer (M/W); No Football
    "Long Beach State Beach": "long_beach_state_beach", "Long Beach State": "long_beach_state_beach", "LBSU": "long_beach_state_beach", # Baseball, Basketball (M/W), Volleyball (M/W), Soccer (W); No Football
    "UC Davis Aggies": "uc_davis_aggies", "UC Davis": "uc_davis_aggies", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "UC Irvine Anteaters": "uc_irvine_anteaters", "UC Irvine": "uc_irvine_anteaters", "UCI": "uc_irvine_anteaters", # Baseball, Basketball (M/W), Volleyball (M/W), Soccer (M/W); No Football
    "UC Riverside Highlanders": "uc_riverside_highlanders", "UC Riverside": "uc_riverside_highlanders", "UCR": "uc_riverside_highlanders", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "UC San Diego Tritons": "uc_san_diego_tritons", "UC San Diego": "uc_san_diego_tritons", "UCSD": "uc_san_diego_tritons", # Baseball, Basketball (M/W), Volleyball (M/W), Soccer (M/W); No Football
    "UC Santa Barbara Gauchos": "uc_santa_barbara_gauchos", "UC Santa Barbara": "uc_santa_barbara_gauchos", "UCSB": "uc_santa_barbara_gauchos", # Baseball, Basketball (M/W), Volleyball (M/W), Soccer (M/W); No Football

    # Independent or Smaller Affiliations
    "Chicago State Cougars": "chicago_state_cougars", "Chicago State": "chicago_state_cougars", # Basketball (M/W), Volleyball (W), Soccer (M/W); No Baseball, No Football

    #Configuration for NCAA Division II team name mappings.
    # Great Lakes Intercollegiate Athletic Conference (GLIAC)
    "Davenport Panthers": "davenport_panthers", "Davenport": "davenport_panthers", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Ferris State Bulldogs": "ferris_state_bulldogs", "Ferris State": "ferris_state_bulldogs", # Basketball (M/W), Volleyball (W), Football, Soccer (W); No Baseball
    "Grand Valley State Lakers": "grand_valley_state_lakers", "Grand Valley State": "grand_valley_state_lakers", "GVSU": "grand_valley_state_lakers", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Lake Superior State Lakers": "lake_superior_state_lakers", "Lake Superior State": "lake_superior_state_lakers", "LSSU": "lake_superior_state_lakers", # Basketball (M/W); No Baseball, No Football, No Volleyball, No Soccer
    "Michigan Tech Huskies": "michigan_tech_huskies", "Michigan Tech": "michigan_tech_huskies", "MTU": "michigan_tech_huskies", # Basketball (M/W), Volleyball (W), Football; No Baseball, No Soccer
    "Northern Michigan Wildcats": "northern_michigan_wildcats", "Northern Michigan": "northern_michigan_wildcats", "NMU": "northern_michigan_wildcats", # Basketball (M/W), Volleyball (W), Football; No Baseball, No Soccer
    "Roosevelt Lakers": "roosevelt_lakers", "Roosevelt": "roosevelt_lakers", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Saginaw Valley State Cardinals": "saginaw_valley_state_cardinals", "Saginaw Valley State": "saginaw_valley_state_cardinals", "SVSU": "saginaw_valley_state_cardinals", # Basketball (M/W), Volleyball (W), Football, Soccer (M/W); No Baseball
    "Wayne State Warriors": "wayne_state_warriors", "Wayne State": "wayne_state_warriors", "WSU": "wayne_state_warriors", # Baseball, Basketball (M/W), Volleyball (W), Football; No Soccer
    "Wisconsin-Parkside Rangers": "wisconsin_parkside_rangers", "Wisconsin-Parkside": "wisconsin_parkside_rangers", "UWP": "wisconsin_parkside_rangers", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football

    # Gulf South Conference (GSC)
    "Alabama Huntsville Chargers": "alabama_huntsville_chargers", "Alabama Huntsville": "alabama_huntsville_chargers", "UAH": "alabama_huntsville_chargers", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Auburn Montgomery Warhawks": "auburn_montgomery_warhawks", "Auburn Montgomery": "auburn_montgomery_warhawks", "AUM": "auburn_montgomery_warhawks", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Christian Brothers Buccaneers": "christian_brothers_buccaneers", "Christian Brothers": "christian_brothers_buccaneers", "CBU": "christian_brothers_buccaneers", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Delta State Statesmen": "delta_state_statesmen", "Delta State": "delta_state_statesmen", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W); No Soccer (M)
    "Lee Flames": "lee_flames", "Lee": "lee_flames", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Mississippi College Choctaws": "mississippi_college_choctaws", "Mississippi College": "mississippi_college_choctaws", "MC": "mississippi_college_choctaws", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Montevallo Falcons": "montevallo_falcons", "Montevallo": "montevallo_falcons", "UM": "montevallo_falcons", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Shorter Hawks": "shorter_hawks", "Shorter": "shorter_hawks", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Union Bulldogs": "union_bulldogs", "Union": "union_bulldogs", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Valdosta State Blazers": "valdosta_state_blazers", "Valdosta State": "valdosta_state_blazers", "VSU": "valdosta_state_blazers", # Baseball, Basketball (M/W), Volleyball (W), Football; No Soccer
    "West Alabama Tigers": "west_alabama_tigers", "West Alabama": "west_alabama_tigers", "UWA": "west_alabama_tigers", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "West Florida Argonauts": "west_florida_argonauts", "West Florida": "west_florida_argonauts", "UWF": "west_florida_argonauts", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "West Georgia Wolves": "west_georgia_wolves", "West Georgia": "west_georgia_wolves", "UWG": "west_georgia_wolves", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)

    # Lone Star Conference (LSC)
    "Angelo State Rams": "angelo_state_rams", "Angelo State": "angelo_state_rams", "ASU": "angelo_state_rams", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Cameron Aggies": "cameron_aggies", "Cameron": "cameron_aggies", # Baseball, Basketball (M/W), Volleyball (W); No Football, No Soccer
    "Dallas Baptist Patriots": "dallas_baptist_patriots", "Dallas Baptist": "dallas_baptist_patriots", "DBU": "dallas_baptist_patriots", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Eastern New Mexico Greyhounds": "eastern_new_mexico_greyhounds", "Eastern New Mexico": "eastern_new_mexico_greyhounds", "ENMU": "eastern_new_mexico_greyhounds", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Lubbock Christian Chaparrals": "lubbock_christian_chaparrals", "Lubbock Christian": "lubbock_christian_chaparrals", "LCU": "lubbock_christian_chaparrals", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Midwestern State Mustangs": "midwestern_state_mustangs", "Midwestern State": "midwestern_state_mustangs", "MSU": "midwestern_state_mustangs", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Oklahoma Christian Eagles": "oklahoma_christian_eagles", "Oklahoma Christian": "oklahoma_christian_eagles", "OC": "oklahoma_christian_eagles", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "St. Edward’s Hilltoppers": "st_edwards_hilltoppers", "St. Edward’s": "st_edwards_hilltoppers", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "St. Mary’s Rattlers": "st_marys_rattlers", "St. Mary’s": "st_marys_rattlers", "STMU": "st_marys_rattlers", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Sul Ross State Lobos": "sul_ross_state_lobos", "Sul Ross State": "sul_ross_state_lobos", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Texas A&M International Dustdevils": "texas_a_and_m_international_dustdevils", "Texas A&M International": "texas_a_and_m_international_dustdevils", "TAMIU": "texas_a_and_m_international_dustdevils", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Texas A&M-Kingsville Javelinas": "texas_a_and_m_kingsville_javelinas", "Texas A&M-Kingsville": "texas_a_and_m_kingsville_javelinas", "TAMUK": "texas_a_and_m_kingsville_javelinas", # Baseball, Basketball (M/W), Volleyball (W), Football; No Soccer
    "Texas Permian Basin Falcons": "texas_permian_basin_falcons", "Texas Permian Basin": "texas_permian_basin_falcons", "UTPB": "texas_permian_basin_falcons", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Texas Woman’s Pioneers": "texas_womans_pioneers", "Texas Woman’s": "texas_womans_pioneers", "TWU": "texas_womans_pioneers", # Basketball (W), Volleyball (W); No Baseball, No Football, No Soccer (M)
    "UT Tyler Patriots": "ut_tyler_patriots", "UT Tyler": "ut_tyler_patriots", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "West Texas A&M Buffaloes": "west_texas_a_and_m_buffaloes", "West Texas A&M": "west_texas_a_and_m_buffaloes", "WTAMU": "west_texas_a_and_m_buffaloes", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Western New Mexico Mustangs": "western_new_mexico_mustangs", "Western New Mexico": "western_new_mexico_mustangs", "WNMU": "western_new_mexico_mustangs", # Baseball, Basketball (M/W), Volleyball (W), Football; No Soccer

    # Pennsylvania State Athletic Conference (PSAC)
    "Bloomsburg Huskies": "bloomsburg_huskies", "Bloomsburg": "bloomsburg_huskies", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "California Vulcans": "california_vulcans", "California (PA)": "california_vulcans", "Cal U": "california_vulcans", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Clarion Golden Eagles": "clarion_golden_eagles", "Clarion": "clarion_golden_eagles", # Basketball (M/W), Volleyball (W), Football; No Baseball, No Soccer
    "East Stroudsburg Warriors": "east_stroudsburg_warriors", "East Stroudsburg": "east_stroudsburg_warriors", "ESU": "east_stroudsburg_warriors", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Edinboro Fighting Scots": "edinboro_fighting_scots", "Edinboro": "edinboro_fighting_scots", # Basketball (M/W), Volleyball (W), Football; No Baseball, No Soccer
    "Gannon Golden Knights": "gannon_golden_knights", "Gannon": "gannon_golden_knights", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Indiana Crimson Hawks": "indiana_crimson_hawks", "Indiana (PA)": "indiana_crimson_hawks", "IUP": "indiana_crimson_hawks", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Kutztown Golden Bears": "kutztown_golden_bears", "Kutztown": "kutztown_golden_bears", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Lock Haven Bald Eagles": "lock_haven_bald_eagles", "Lock Haven": "lock_haven_bald_eagles", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Mansfield Mountaineers": "mansfield_mountaineers", "Mansfield": "mansfield_mountaineers", # Baseball, Basketball (M/W); No Football, No Volleyball, No Soccer
    "Mercyhurst Lakers": "mercyhurst_lakers", "Mercyhurst": "mercyhurst_lakers", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Millersville Marauders": "millersville_marauders", "Millersville": "millersville_marauders", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Pitt-Johnstown Mountain Cats": "pitt_johnstown_mountain_cats", "Pitt-Johnstown": "pitt_johnstown_mountain_cats", "UPJ": "pitt_johnstown_mountain_cats", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Seton Hill Griffins": "seton_hill_griffins", "Seton Hill": "seton_hill_griffins", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Shepherd Rams": "shepherd_rams", "Shepherd": "shepherd_rams", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Shippensburg Raiders": "shippensburg_raiders", "Shippensburg": "shippensburg_raiders", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "Slippery Rock The Rock": "slippery_rock_the_rock", "Slippery Rock": "slippery_rock_the_rock", "SRU": "slippery_rock_the_rock", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W)
    "West Chester Golden Rams": "west_chester_golden_rams", "West Chester": "west_chester_golden_rams", "WCU": "west_chester_golden_rams", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)

    # California Collegiate Athletic Association (CCAA)
    "Cal Poly Humboldt Lumberjacks": "cal_poly_humboldt_lumberjacks", "Cal Poly Humboldt": "cal_poly_humboldt_lumberjacks", "Humboldt State": "cal_poly_humboldt_lumberjacks", # Basketball (M/W), Volleyball (W), Soccer (M/W); No Baseball, No Football
    "Cal Poly Pomona Broncos": "cal_poly_pomona_broncos", "Cal Poly Pomona": "cal_poly_pomona_broncos", "CPP": "cal_poly_pomona_broncos", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Cal State Dominguez Hills Toros": "cal_state_dominguez_hills_toros", "Cal State Dominguez Hills": "cal_state_dominguez_hills_toros", "CSUDH": "cal_state_dominguez_hills_toros", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Cal State East Bay Pioneers": "cal_state_east_bay_pioneers", "Cal State East Bay": "cal_state_east_bay_pioneers", "CSUEB": "cal_state_east_bay_pioneers", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Cal State Los Angeles Golden Eagles": "cal_state_los_angeles_golden_eagles", "Cal State Los Angeles": "cal_state_los_angeles_golden_eagles", "CSULA": "cal_state_los_angeles_golden_eagles", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Cal State Monterey Bay Otters": "cal_state_monterey_bay_otters", "Cal State Monterey Bay": "cal_state_monterey_bay_otters", "CSUMB": "cal_state_monterey_bay_otters", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Cal State San Bernardino Coyotes": "cal_state_san_bernardino_coyotes", "Cal State San Bernardino": "cal_state_san_bernardino_coyotes", "CSUSB": "cal_state_san_bernardino_coyotes", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Cal State San Marcos Cougars": "cal_state_san_marcos_cougars", "Cal State San Marcos": "cal_state_san_marcos_cougars", "CSUSM": "cal_state_san_marcos_cougars", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Chico State Wildcats": "chico_state_wildcats", "Chico State": "chico_state_wildcats", "CSUC": "chico_state_wildcats", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "San Francisco State Gators": "san_francisco_state_gators", "San Francisco State": "san_francisco_state_gators", "SFSU": "san_francisco_state_gators", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Sonoma State Seawolves": "sonoma_state_seawolves", "Sonoma State": "sonoma_state_seawolves", "SSU": "sonoma_state_seawolves", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Stanislaus State Warriors": "stanislaus_state_warriors", "Stanislaus State": "stanislaus_state_warriors", "CSUS": "stanislaus_state_warriors", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football

    # Northeast-10 Conference (NE-10)
    "Adelphi Panthers": "adelphi_panthers", "Adelphi": "adelphi_panthers", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "American International Yellow Jackets": "american_international_yellow_jackets", "American International": "american_international_yellow_jackets", "AIC": "american_international_yellow_jackets", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Assumption Greyhounds": "assumption_greyhounds", "Assumption": "assumption_greyhounds", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Bentley Falcons": "bentley_falcons", "Bentley": "bentley_falcons", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Franklin Pierce Ravens": "franklin_pierce_ravens", "Franklin Pierce": "franklin_pierce_ravens", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "New Haven Chargers": "new_haven_chargers", "New Haven": "new_haven_chargers", "UNH": "new_haven_chargers", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Pace Setters": "pace_setters", "Pace": "pace_setters", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W); No Soccer (M)
    "Saint Anselm Hawks": "saint_anselm_hawks", "Saint Anselm": "saint_anselm_hawks", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Saint Michael’s Purple Knights": "saint_michaels_purple_knights", "Saint Michael’s": "saint_michaels_purple_knights", "SMC": "saint_michaels_purple_knights", # Baseball, Basketball (M/W), Soccer (M/W); No Football, No Volleyball
    "Saint Rose Golden Knights": "saint_rose_golden_knights", "Saint Rose": "saint_rose_golden_knights", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Southern Connecticut State Owls": "southern_connecticut_state_owls", "Southern Connecticut State": "southern_connecticut_state_owls", "SCSU": "southern_connecticut_state_owls", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Southern New Hampshire Penmen": "southern_new_hampshire_penmen", "Southern New Hampshire": "southern_new_hampshire_penmen", "SNHU": "southern_new_hampshire_penmen", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football

    # Great Midwest Athletic Conference (G-MAC)
    "Ashland Eagles": "ashland_eagles", "Ashland": "ashland_eagles", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Cedarville Yellow Jackets": "cedarville_yellow_jackets", "Cedarville": "cedarville_yellow_jackets", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Findlay Oilers": "findlay_oilers", "Findlay": "findlay_oilers", "UF": "findlay_oilers", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Hillsdale Chargers": "hillsdale_chargers", "Hillsdale": "hillsdale_chargers", # Baseball, Basketball (M/W), Volleyball (W), Football; No Soccer
    "Kentucky Wesleyan Panthers": "kentucky_wesleyan_panthers", "Kentucky Wesleyan": "kentucky_wesleyan_panthers", "KWC": "kentucky_wesleyan_panthers", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Lake Erie Storm": "lake_erie_storm", "Lake Erie": "lake_erie_storm", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Malone Pioneers": "malone_pioneers", "Malone": "malone_pioneers", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Northwood Timberwolves": "northwood_timberwolves", "Northwood": "northwood_timberwolves", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Ohio Dominican Panthers": "ohio_dominican_panthers", "Ohio Dominican": "ohio_dominican_panthers", "ODU": "ohio_dominican_panthers", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Thomas More Saints": "thomas_more_saints", "Thomas More": "thomas_more_saints", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Tiffin Dragons": "tiffin_dragons", "Tiffin": "tiffin_dragons", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Trevecca Nazarene Trojans": "trevecca_nazarene_trojans", "Trevecca Nazarene": "trevecca_nazarene_trojans", "TNU": "trevecca_nazarene_trojans", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Walsh Cavaliers": "walsh_cavaliers", "Walsh": "walsh_cavaliers", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)

    # Great American Conference (GAC)
    "Arkansas-Monticello Boll Weevils": "arkansas_monticello_boll_weevils", "Arkansas-Monticello": "arkansas_monticello_boll_weevils", "UAM": "arkansas_monticello_boll_weevils", # Baseball, Basketball (M/W), Volleyball (W), Football; No Soccer
    "Arkansas Tech Wonder Boys": "arkansas_tech_wonder_boys", "Arkansas Tech": "arkansas_tech_wonder_boys", "ATU": "arkansas_tech_wonder_boys", # Baseball, Basketball (M/W), Volleyball (W), Football; No Soccer
    "East Central Tigers": "east_central_tigers", "East Central": "east_central_tigers", "ECU": "east_central_tigers", # Baseball, Basketball (M/W), Volleyball (W), Football; No Soccer
    "Harding Bisons": "harding_bisons", "Harding": "harding_bisons", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Henderson State Reddies": "henderson_state_reddies", "Henderson State": "henderson_state_reddies", "HSU": "henderson_state_reddies", # Baseball, Basketball (M/W), Volleyball (W), Football; No Soccer
    "Northwestern Oklahoma State Rangers": "northwestern_oklahoma_state_rangers", "Northwestern Oklahoma State": "northwestern_oklahoma_state_rangers", "NWOSU": "northwestern_oklahoma_state_rangers", # Baseball, Basketball (M/W), Volleyball (W), Football; No Soccer
    "Oklahoma Baptist Bison": "oklahoma_baptist_bison", "Oklahoma Baptist": "oklahoma_baptist_bison", "OBU": "oklahoma_baptist_bison", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Ouachita Baptist Tigers": "ouachita_baptist_tigers", "Ouachita Baptist": "ouachita_baptist_tigers", "OBU": "ouachita_baptist_tigers", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W); No Soccer (M)
    "Southeastern Oklahoma State Savage Storm": "southeastern_oklahoma_state_savage_storm", "Southeastern Oklahoma State": "southeastern_oklahoma_state_savage_storm", "SEOSU": "southeastern_oklahoma_state_savage_storm", # Baseball, Basketball (M/W), Volleyball (W), Football; No Soccer
    "Southern Arkansas Muleriders": "southern_arkansas_muleriders", "Southern Arkansas": "southern_arkansas_muleriders", "SAU": "southern_arkansas_muleriders", # Baseball, Basketball (M/W), Volleyball (W), Football; No Soccer
    "Southern Nazarene Crimson Storm": "southern_nazarene_crimson_storm", "Southern Nazarene": "southern_nazarene_crimson_storm", "SNU": "southern_nazarene_crimson_storm", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Southwestern Oklahoma State Bulldogs": "southwestern_oklahoma_state_bulldogs", "Southwestern Oklahoma State": "southwestern_oklahoma_state_bulldogs", "SWOSU": "southwestern_oklahoma_state_bulldogs", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W); No Soccer (M)

    # Great Northwest Athletic Conference (GNAC)
    "Alaska Anchorage Seawolves": "alaska_anchorage_seawolves", "Alaska Anchorage": "alaska_anchorage_seawolves", "UAA": "alaska_anchorage_seawolves", # Basketball (M/W), Volleyball (W); No Baseball, No Football, No Soccer
    "Alaska Fairbanks Nanooks": "alaska_fairbanks_nanooks", "Alaska Fairbanks": "alaska_fairbanks_nanooks", "UAF": "alaska_fairbanks_nanooks", # Basketball (M/W); No Baseball, No Football, No Volleyball, No Soccer
    "Central Washington Wildcats": "central_washington_wildcats", "Central Washington": "central_washington_wildcats", "CWU": "central_washington_wildcats", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W); No Soccer (M)
    "Montana State Billings Yellowjackets": "montana_state_billings_yellowjackets", "Montana State Billings": "montana_state_billings_yellowjackets", "MSUB": "montana_state_billings_yellowjackets", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Northwest Nazarene Nighthawks": "northwest_nazarene_nighthawks", "Northwest Nazarene": "northwest_nazarene_nighthawks", "NNU": "northwest_nazarene_nighthawks", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Saint Martin’s Saints": "saint_martins_saints", "Saint Martin’s": "saint_martins_saints", "SMU": "saint_martins_saints", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Seattle Pacific Falcons": "seattle_pacific_falcons", "Seattle Pacific": "seattle_pacific_falcons", "SPU": "seattle_pacific_falcons", # Basketball (M/W), Volleyball (W), Soccer (M/W); No Baseball, No Football
    "Simon Fraser Red Leafs": "simon_fraser_red_leafs", "Simon Fraser": "simon_fraser_red_leafs", "SFU": "simon_fraser_red_leafs", # Basketball (M/W), Volleyball (W), Soccer (M/W); No Baseball, No Football
    "Western Oregon Wolves": "western_oregon_wolves", "Western Oregon": "western_oregon_wolves", "WOU": "western_oregon_wolves", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Western Washington Vikings": "western_washington_vikings", "Western Washington": "western_washington_vikings", "WWU": "western_washington_vikings", # Basketball (M/W), Volleyball (W), Soccer (M/W); No Baseball, No Football

    # Mid-America Intercollegiate Athletics Association (MIAA)
    "Central Missouri Mules": "central_missouri_mules", "Central Missouri": "central_missouri_mules", "UCM": "central_missouri_mules", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W); No Soccer (M)
    "Central Oklahoma Bronchos": "central_oklahoma_bronchos", "Central Oklahoma": "central_oklahoma_bronchos", "UCO": "central_oklahoma_bronchos", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W); No Soccer (M)
    "Emporia State Hornets": "emporia_state_hornets", "Emporia State": "emporia_state_hornets", "ESU": "emporia_state_hornets", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W); No Soccer (M)
    "Fort Hays State Tigers": "fort_hays_state_tigers", "Fort Hays State": "fort_hays_state_tigers", "FHSU": "fort_hays_state_tigers", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Missouri Southern Lions": "missouri_southern_lions", "Missouri Southern": "missouri_southern_lions", "MSSU": "missouri_southern_lions", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W); No Soccer (M)
    "Missouri Western Griffons": "missouri_western_griffons", "Missouri Western": "missouri_western_griffons", "MWSU": "missouri_western_griffons", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Nebraska-Kearney Lopers": "nebraska_kearney_lopers", "Nebraska-Kearney": "nebraska_kearney_lopers", "UNK": "nebraska_kearney_lopers", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W); No Soccer (M)
    "Northeastern State RiverHawks": "northeastern_state_riverhawks", "Northeastern State": "northeastern_state_riverhawks", "NSU": "northeastern_state_riverhawks", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Northwest Missouri State Bearcats": "northwest_missouri_state_bearcats", "Northwest Missouri State": "northwest_missouri_state_bearcats", "NWMSU": "northwest_missouri_state_bearcats", # Baseball, Basketball (M/W), Volleyball (W), Football; No Soccer
    "Pittsburg State Gorillas": "pittsburg_state_gorillas", "Pittsburg State": "pittsburg_state_gorillas", "PSU": "pittsburg_state_gorillas", # Baseball, Basketball (M/W), Volleyball (W), Football; No Soccer
    "Rogers State Hillcats": "rogers_state_hillcats", "Rogers State": "rogers_state_hillcats", "RSU": "rogers_state_hillcats", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Washburn Ichabods": "washburn_ichabods", "Washburn": "washburn_ichabods", "WU": "washburn_ichabods", # Baseball, Basketball (M/W), Volleyball (W), Football; No Soccer

    # Mountain East Conference (MEC)
    "Charleston Golden Eagles": "charleston_golden_eagles", "Charleston (WV)": "charleston_golden_eagles", "UCWV": "charleston_golden_eagles", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Concord Mountain Lions": "concord_mountain_lions", "Concord": "concord_mountain_lions", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Davis & Elkins Senators": "davis_and_elkins_senators", "Davis & Elkins": "davis_and_elkins_senators", "D&E": "davis_and_elkins_senators", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Fairmont State Falcons": "fairmont_state_falcons", "Fairmont State": "fairmont_state_falcons", # Baseball, Basketball (M/W), Volleyball (W), Football; No Soccer
    "Frostburg State Bobcats": "frostburg_state_bobcats", "Frostburg State": "frostburg_state_bobcats", "FSU": "frostburg_state_bobcats", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Glenville State Pioneers": "glenville_state_pioneers", "Glenville State": "glenville_state_pioneers", # Baseball, Basketball (M/W), Volleyball (W), Football; No Soccer
    "Notre Dame Falcons": "notre_dame_falcons", "Notre Dame (OH)": "notre_dame_falcons", "NDC": "notre_dame_falcons", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "West Liberty Hilltoppers": "west_liberty_hilltoppers", "West Liberty": "west_liberty_hilltoppers", "WLU": "west_liberty_hilltoppers", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "West Virginia State Yellow Jackets": "west_virginia_state_yellow_jackets", "West Virginia State": "west_virginia_state_yellow_jackets", "WVSU": "west_virginia_state_yellow_jackets", # Baseball, Basketball (M/W), Volleyball (W), Football; No Soccer
    "West Virginia Wesleyan Bobcats": "west_virginia_wesleyan_bobcats", "West Virginia Wesleyan": "west_virginia_wesleyan_bobcats", "WVWC": "west_virginia_wesleyan_bobcats", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Wheeling Cardinals": "wheeling_cardinals", "Wheeling": "wheeling_cardinals", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)

    # Northern Sun Intercollegiate Conference (NSIC)
    "Augustana Vikings": "augustana_vikings", "Augustana (SD)": "augustana_vikings", # Baseball, Basketball (M/W), Volleyball (W), Football; No Soccer
    "Bemidji State Beavers": "bemidji_state_beavers", "Bemidji State": "bemidji_state_beavers", "BSU": "bemidji_state_beavers", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W); No Soccer (M)
    "Concordia-St. Paul Golden Bears": "concordia_st_paul_golden_bears", "Concordia-St. Paul": "concordia_st_paul_golden_bears", "CSP": "concordia_st_paul_golden_bears", # Baseball, Basketball (M/W), Volleyball (W), Football; No Soccer
    "Mary Marauders": "mary_marauders", "University of Mary": "mary_marauders", "UMary": "mary_marauders", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Minot State Beavers": "minot_state_beavers", "Minot State": "minot_state_beavers", "MiSU": "minot_state_beavers", # Baseball, Basketball (M/W), Volleyball (W), Football; No Soccer
    "Minnesota Crookston Golden Eagles": "minnesota_crookston_golden_eagles", "Minnesota Crookston": "minnesota_crookston_golden_eagles", "UMC": "minnesota_crookston_golden_eagles", # Baseball, Basketball (M/W), Volleyball (W), Soccer (W); No Football
    "Minnesota Duluth Bulldogs": "minnesota_duluth_bulldogs", "Minnesota Duluth": "minnesota_duluth_bulldogs", "UMD": "minnesota_duluth_bulldogs", # Baseball, Basketball (M/W), Volleyball (W), Football; No Soccer
    "Minnesota State Mavericks": "minnesota_state_mavericks", "Minnesota State": "minnesota_state_mavericks", "MSU": "minnesota_state_mavericks", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W); No Soccer (M)
    "Minnesota State Moorhead Dragons": "minnesota_state_moorhead_dragons", "Minnesota State Moorhead": "minnesota_state_moorhead_dragons", "MSUM": "minnesota_state_moorhead_dragons", # Basketball (M/W), Volleyball (W), Football; No Baseball, No Soccer
    "Northern State Wolves": "northern_state_wolves", "Northern State": "northern_state_wolves", "NSU": "northern_state_wolves", # Baseball, Basketball (M/W), Volleyball (W), Football; No Soccer
    "Sioux Falls Cougars": "sioux_falls_cougars", "Sioux Falls": "sioux_falls_cougars", "USF": "sioux_falls_cougars", # Baseball, Basketball (M/W), Volleyball (W), Football; No Soccer
    "Southwest Minnesota State Mustangs": "southwest_minnesota_state_mustangs", "Southwest Minnesota State": "southwest_minnesota_state_mustangs", "SMSU": "southwest_minnesota_state_mustangs", # Baseball, Basketball (M/W), Volleyball (W), Football; No Soccer
    "St. Cloud State Huskies": "st_cloud_state_huskies", "St. Cloud State": "st_cloud_state_huskies", "SCSU": "st_cloud_state_huskies", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Wayne State Wildcats": "wayne_state_wildcats", "Wayne State (NE)": "wayne_state_wildcats", "WSC": "wayne_state_wildcats", # Baseball, Basketball (M/W), Volleyball (W), Football; No Soccer
    "Winona State Warriors": "winona_state_warriors", "Winona State": "winona_state_warriors", "WSU": "winona_state_warriors", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (W); No Soccer (M)

    # Pacific West Conference (PacWest)
    "Academy of Art Urban Knights": "academy_of_art_urban_knights", "Academy of Art": "academy_of_art_urban_knights", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Azusa Pacific Cougars": "azusa_pacific_cougars", "Azusa Pacific": "azusa_pacific_cougars", "APU": "azusa_pacific_cougars", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Biola Eagles": "biola_eagles", "Biola": "biola_eagles", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Chaminade Silverswords": "chaminade_silverswords", "Chaminade": "chaminade_silverswords", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Concordia Irvine Eagles": "concordia_irvine_eagles", "Concordia Irvine": "concordia_irvine_eagles", "CUI": "concordia_irvine_eagles", # Baseball, Basketball (M/W), Volleyball (M/W), Soccer (M/W); No Football
    "Dominican Penguins": "dominican_penguins", "Dominican (CA)": "dominican_penguins", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Fresno Pacific Sunbirds": "fresno_pacific_sunbirds", "Fresno Pacific": "fresno_pacific_sunbirds", "FPU": "fresno_pacific_sunbirds", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Hawai’i Hilo Vulcans": "hawaii_hilo_vulcans", "Hawai’i Hilo": "hawaii_hilo_vulcans", "UHH": "hawaii_hilo_vulcans", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Hawai’i Pacific Sharks": "hawaii_pacific_sharks", "Hawai’i Pacific": "hawaii_pacific_sharks", "HPU": "hawaii_pacific_sharks", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Point Loma Nazarene Sea Lions": "point_loma_nazarene_sea_lions", "Point Loma Nazarene": "point_loma_nazarene_sea_lions", "PLNU": "point_loma_nazarene_sea_lions", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Westmont Warriors": "westmont_warriors", "Westmont": "westmont_warriors", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football

    # Rocky Mountain Athletic Conference (RMAC)
    "Adams State Grizzlies": "adams_state_grizzlies", "Adams State": "adams_state_grizzlies", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Black Hills State Yellow Jackets": "black_hills_state_yellow_jackets", "Black Hills State": "black_hills_state_yellow_jackets", "BHSU": "black_hills_state_yellow_jackets", # Basketball (M/W), Volleyball (W), Football; No Baseball, No Soccer
    "Chadron State Eagles": "chadron_state_eagles", "Chadron State": "chadron_state_eagles", "CSC": "chadron_state_eagles", # Basketball (M/W), Volleyball (W), Football; No Baseball, No Soccer
    "Colorado Christian Cougars": "colorado_christian_cougars", "Colorado Christian": "colorado_christian_cougars", "CCU": "colorado_christian_cougars", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Colorado Mesa Mavericks": "colorado_mesa_mavericks", "Colorado Mesa": "colorado_mesa_mavericks", "CMU": "colorado_mesa_mavericks", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Colorado Mines Orediggers": "colorado_mines_orediggers", "Colorado Mines": "colorado_mines_orediggers", "CSM": "colorado_mines_orediggers", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Colorado State Pueblo ThunderWolves": "colorado_state_pueblo_thunderwolves", "Colorado State Pueblo": "colorado_state_pueblo_thunderwolves", "CSUP": "colorado_state_pueblo_thunderwolves", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Fort Lewis Skyhawks": "fort_lewis_skyhawks", "Fort Lewis": "fort_lewis_skyhawks", "FLC": "fort_lewis_skyhawks", # Basketball (M/W), Volleyball (W), Football, Soccer (M/W); No Baseball
    "MSU Denver Roadrunners": "msu_denver_roadrunners", "MSU Denver": "msu_denver_roadrunners", "MSUD": "msu_denver_roadrunners", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "New Mexico Highlands Cowboys": "new_mexico_highlands_cowboys", "New Mexico Highlands": "new_mexico_highlands_cowboys", "NMHU": "new_mexico_highlands_cowboys", # Baseball, Basketball (M/W), Volleyball (W), Football; No Soccer
    "Regis Rangers": "regis_rangers", "Regis": "regis_rangers", "RU": "regis_rangers", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "South Dakota Mines Hardrockers": "south_dakota_mines_hardrockers", "South Dakota Mines": "south_dakota_mines_hardrockers", "SDSMT": "south_dakota_mines_hardrockers", # Basketball (M/W), Volleyball (W), Football; No Baseball, No Soccer
    "UCCS Mountain Lions": "uccs_mountain_lions", "UCCS": "uccs_mountain_lions", "UC Colorado Springs": "uccs_mountain_lions", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Western Colorado Mountaineers": "western_colorado_mountaineers", "Western Colorado": "western_colorado_mountaineers", "WCU": "western_colorado_mountaineers", # Baseball, Basketball (M/W), Volleyball (W), Football; No Soccer

    # South Atlantic Conference (SAC)
    "Anderson Trojans": "anderson_trojans", "Anderson (SC)": "anderson_trojans", "AU": "anderson_trojans", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Carson-Newman Eagles": "carson_newman_eagles", "Carson-Newman": "carson_newman_eagles", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Catawba Indians": "catawba_indians", "Catawba": "catawba_indians", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Coker Cobras": "coker_cobras", "Coker": "coker_cobras", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Emory & Henry Wasps": "emory_and_henry_wasps", "Emory & Henry": "emory_and_henry_wasps", "E&H": "emory_and_henry_wasps", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Lenoir-Rhyne Bears": "lenoir_rhyne_bears", "Lenoir-Rhyne": "lenoir_rhyne_bears", "LR": "lenoir_rhyne_bears", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Limestone Saints": "limestone_saints", "Limestone": "limestone_saints", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Lincoln Memorial Railsplitters": "lincoln_memorial_railsplitters", "Lincoln Memorial": "lincoln_memorial_railsplitters", "LMU": "lincoln_memorial_railsplitters", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Mars Hill Lions": "mars_hill_lions", "Mars Hill": "mars_hill_lions", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Newberry Wolves": "newberry_wolves", "Newberry": "newberry_wolves", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Tusculum Pioneers": "tusculum_pioneers", "Tusculum": "tusculum_pioneers", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)
    "Virginia-Wise Cavaliers": "virginia_wise_cavaliers", "Virginia-Wise": "virginia_wise_cavaliers", "UVA Wise": "virginia_wise_cavaliers", # Baseball, Basketball (M/W), Volleyball (W), Football; No Soccer
    "Wingate Bulldogs": "wingate_bulldogs", "Wingate": "wingate_bulldogs", # Baseball, Basketball (M/W), Volleyball (W), Football, Soccer (M/W)

    # Sunshine State Conference (SSC)
    "Barry Buccaneers": "barry_buccaneers", "Barry": "barry_buccaneers", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Eckerd Tritons": "eckerd_tritons", "Eckerd": "eckerd_tritons", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Embry-Riddle Eagles": "embry_riddle_eagles", "Embry-Riddle": "embry_riddle_eagles", "ERAU": "embry_riddle_eagles", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Florida Southern Moccasins": "florida_southern_moccasins", "Florida Southern": "florida_southern_moccasins", "FSC": "florida_southern_moccasins", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Florida Tech Panthers": "florida_tech_panthers", "Florida Tech": "florida_tech_panthers", "FIT": "florida_tech_panthers", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Lynn Fighting Knights": "lynn_fighting_knights", "Lynn": "lynn_fighting_knights", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Nova Southeastern Sharks": "nova_southeastern_sharks", "Nova Southeastern": "nova_southeastern_sharks", "NSU": "nova_southeastern_sharks", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Palm Beach Atlantic Sailfish": "palm_beach_atlantic_sailfish", "Palm Beach Atlantic": "palm_beach_atlantic_sailfish", "PBA": "palm_beach_atlantic_sailfish", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Rollins Tars": "rollins_tars", "Rollins": "rollins_tars", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Saint Leo Lions": "saint_leo_lions", "Saint Leo": "saint_leo_lions", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Tampa Spartans": "tampa_spartans", "Tampa": "tampa_spartans", "UT": "tampa_spartans", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football

    # Independents or Smaller Affiliations
    "Bluefield State Big Blue": "bluefield_state_big_blue", "Bluefield State": "bluefield_state_big_blue", # Baseball, Basketball (M/W), Volleyball (W); No Football, No Soccer
    "Emmanuel Lions": "emmanuel_lions", "Emmanuel (GA)": "emmanuel_lions", # Baseball, Basketball (M/W), Volleyball (M/W), Soccer (M/W); No Football
    "Post Eagles": "post_eagles", "Post": "post_eagles", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Salem Tigers": "salem_tigers", "Salem (WV)": "salem_tigers", # Baseball, Basketball (M/W), Volleyball (W), Soccer (M/W); No Football
    "Virginia State Trojans": "virginia_state_trojans", "Virginia State": "virginia_state_trojans", "VSU": "virginia_state_trojans", # Baseball, Basketball (M/W), Volleyball (W), Football; No Soccer   
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
