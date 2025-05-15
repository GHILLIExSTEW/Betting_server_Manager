"""NCAA team nickname conflicts for betting workflow."""

# Dictionary of NCAA nickname conflicts (strict matching).
# Each key is a nickname, and the value is a list of teams with that nickname.
# Each team dictionary contains: name (full team name), identifier (standardized ID),
# division (D1 or D2), and conference.
NCAA_CONFLICTS = {
    "Aggies": [
        {"name": "Texas A&M Aggies", "identifier": "texas_a_and_m_aggies", "division": "D1", "conference": "SEC"},
        {"name": "New Mexico State Aggies", "identifier": "new_mexico_state_aggies", "division": "D1", "conference": "C-USA"},
        {"name": "Utah State Aggies", "identifier": "utah_state_aggies", "division": "D1", "conference": "Mountain West"},
        {"name": "North Carolina A&T Aggies", "identifier": "north_carolina_a_and_t_aggies", "division": "D1", "conference": "CAA"},
        {"name": "Cameron Aggies", "identifier": "cameron_aggies", "division": "D2", "conference": "LSC"}
    ],
    "Bears": [
        {"name": "Baylor Bears", "identifier": "baylor_bears", "division": "D1", "conference": "Big 12"},
        {"name": "Missouri State Bears", "identifier": "missouri_state_bears", "division": "D1", "conference": "MVC"},
        {"name": "Central Arkansas Bears", "identifier": "central_arkansas_bears", "division": "D1", "conference": "ASUN"},
        {"name": "Mercer Bears", "identifier": "mercer_bears", "division": "D1", "conference": "SoCon"},
        {"name": "Morgan State Bears", "identifier": "morgan_state_bears", "division": "D1", "conference": "MEAC"},
        {"name": "Brown Bears", "identifier": "brown_bears", "division": "D1", "conference": "Ivy League"}
    ],
    "Bobcats": [
        {"name": "Texas State Bobcats", "identifier": "texas_state_bobcats", "division": "D1", "conference": "Sun Belt"},
        {"name": "Montana State Bobcats", "identifier": "montana_state_bobcats", "division": "D1", "conference": "Big Sky"},
        {"name": "Ohio Bobcats", "identifier": "ohio_bobcats", "division": "D1", "conference": "MAC"},
        {"name": "Quinnipiac Bobcats", "identifier": "quinnipiac_bobcats", "division": "D1", "conference": "MAAC"},
        {"name": "Frostburg State Bobcats", "identifier": "frostburg_state_bobcats", "division": "D2", "conference": "MEC"}
    ],
    "Broncos": [
        {"name": "Boise State Broncos", "identifier": "boise_state_broncos", "division": "D1", "conference": "Mountain West"},
        {"name": "Western Michigan Broncos", "identifier": "western_michigan_broncos", "division": "D1", "conference": "MAC"},
        {"name": "Santa Clara Broncos", "identifier": "santa_clara_broncos", "division": "D1", "conference": "WCC"}
    ],
    "Bulldogs": [
        {"name": "Georgia Bulldogs", "identifier": "georgia_bulldogs", "division": "D1", "conference": "SEC"},
        {"name": "Mississippi State Bulldogs", "identifier": "mississippi_state_bulldogs", "division": "D1", "conference": "SEC"},
        {"name": "Butler Bulldogs", "identifier": "butler_bulldogs", "division": "D1", "conference": "Big East"},
        {"name": "Drake Bulldogs", "identifier": "drake_bulldogs", "division": "D1", "conference": "MVC"},
        {"name": "Fresno State Bulldogs", "identifier": "fresno_state_bulldogs", "division": "D1", "conference": "Mountain West"},
        {"name": "Louisiana Tech Bulldogs", "identifier": "louisiana_tech_bulldogs", "division": "D1", "conference": "C-USA"},
        {"name": "Samford Bulldogs", "identifier": "samford_bulldogs", "division": "D1", "conference": "SoCon"},
        {"name": "Citadel Bulldogs", "identifier": "citadel_bulldogs", "division": "D1", "conference": "SoCon"},
        {"name": "Alabama A&M Bulldogs", "identifier": "alabama_a_and_m_bulldogs", "division": "D1", "conference": "SWAC"},
        {"name": "South Carolina State Bulldogs", "identifier": "south_carolina_state_bulldogs", "division": "D1", "conference": "MEAC"},
        {"name": "Bryant Bulldogs", "identifier": "bryant_bulldogs", "division": "D1", "conference": "America East"},
        {"name": "UNC Asheville Bulldogs", "identifier": "unc_asheville_bulldogs", "division": "D1", "conference": "Big South"},
        {"name": "Yale Bulldogs", "identifier": "yale_bulldogs", "division": "D1", "conference": "Ivy League"},
        {"name": "Ferris State Bulldogs", "identifier": "ferris_state_bulldogs", "division": "D2", "conference": "GLIAC"}
    ],
    "Cardinals": [
        {"name": "Louisville Cardinals", "identifier": "louisville_cardinals", "division": "D1", "conference": "ACC"},
        {"name": "Ball State Cardinals", "identifier": "ball_state_cardinals", "division": "D1", "conference": "MAC"},
        {"name": "Incarnate Word Cardinals", "identifier": "incarnate_word_cardinals", "division": "D1", "conference": "Southland"},
        {"name": "Lamar Cardinals", "identifier": "lamar_cardinals", "division": "D1", "conference": "Southland"},
        {"name": "Saginaw Valley State Cardinals", "identifier": "saginaw_valley_state_cardinals", "division": "D2", "conference": "GLIAC"}
    ],
    "Cougars": [
        {"name": "BYU Cougars", "identifier": "byu_cougars", "division": "D1", "conference": "Big 12"},
        {"name": "Houston Cougars", "identifier": "houston_cougars", "division": "D1", "conference": "Big 12"},
        {"name": "Charleston Cougars", "identifier": "charleston_cougars", "division": "D1", "conference": "CAA"},
        {"name": "SIU Edwardsville Cougars", "identifier": "siu_edwardsville_cougars", "division": "D1", "conference": "OVC"},
        {"name": "Chicago State Cougars", "identifier": "chicago_state_cougars", "division": "D1", "conference": "Independent"},
        {"name": "Cal State San Marcos Cougars", "identifier": "cal_state_san_marcos_cougars", "division": "D2", "conference": "CCAA"}
    ],
    "Eagles": [
        {"name": "Boston College Eagles", "identifier": "boston_college_eagles", "division": "D1", "conference": "ACC"},
        {"name": "Georgia Southern Eagles", "identifier": "georgia_southern_eagles", "division": "D1", "conference": "Sun Belt"},
        {"name": "Florida Gulf Coast Eagles", "identifier": "florida_gulf_coast_eagles", "division": "D1", "conference": "ASUN"},
        {"name": "Eastern Washington Eagles", "identifier": "eastern_washington_eagles", "division": "D1", "conference": "Big Sky"},
        {"name": "Winthrop Eagles", "identifier": "winthrop_eagles", "division": "D1", "conference": "Big South"},
        {"name": "Morehead State Eagles", "identifier": "morehead_state_eagles", "division": "D1", "conference": "OVC"},
        {"name": "Coppin State Eagles", "identifier": "coppin_state_eagles", "division": "D1", "conference": "MEAC"},
        {"name": "North Carolina Central Eagles", "identifier": "north_carolina_central_eagles", "division": "D1", "conference": "MEAC"},
        {"name": "American Eagles", "identifier": "american_eagles", "division": "D1", "conference": "Patriot League"},
        {"name": "Eastern Michigan Eagles", "identifier": "eastern_michigan_eagles", "division": "D1", "conference": "MAC"},
        {"name": "Embry-Riddle Eagles", "identifier": "embry_riddle_eagles", "division": "D2", "conference": "SSC"},
        {"name": "Ashland Eagles", "identifier": "ashland_eagles", "division": "D2", "conference": "G-MAC"},
        {"name": "Carson-Newman Eagles", "identifier": "carson_newman_eagles", "division": "D2", "conference": "SAC"}
    ],
    "Falcons": [
        {"name": "Bowling Green Falcons", "identifier": "bowling_green_falcons", "division": "D1", "conference": "MAC"},
        {"name": "Air Force Falcons", "identifier": "air_force_falcons", "division": "D1", "conference": "Mountain West"},
        {"name": "Montevallo Falcons", "identifier": "montevallo_falcons", "division": "D2", "conference": "GSC"},
        {"name": "Texas Permian Basin Falcons", "identifier": "texas_permian_basin_falcons", "division": "D2", "conference": "LSC"},
        {"name": "Bentley Falcons", "identifier": "bentley_falcons", "division": "D2", "conference": "NE-10"},
        {"name": "Seattle Pacific Falcons", "identifier": "seattle_pacific_falcons", "division": "D2", "conference": "GNAC"}
    ],
    "Huskies": [
        {"name": "UConn Huskies", "identifier": "uconn_huskies", "division": "D1", "conference": "Big East"},
        {"name": "Northeastern Huskies", "identifier": "northeastern_huskies", "division": "D1", "conference": "CAA"},
        {"name": "Northern Illinois Huskies", "identifier": "northern_illinois_huskies", "division": "D1", "conference": "MAC"},
        {"name": "Houston Christian Huskies", "identifier": "houston_christian_huskies", "division": "D1", "conference": "Southland"},
        {"name": "St. Cloud State Huskies", "identifier": "st_cloud_state_huskies", "division": "D2", "conference": "NSIC"},
        {"name": "Bloomsburg Huskies", "identifier": "bloomsburg_huskies", "division": "D2", "conference": "PSAC"}
    ],
    "Lions": [
        {"name": "Columbia Lions", "identifier": "columbia_lions", "division": "D1", "conference": "Ivy League"},
        {"name": "Southeastern Louisiana Lions", "identifier": "southeastern_louisiana_lions", "division": "D1", "conference": "Southland"},
        {"name": "North Alabama Lions", "identifier": "north_alabama_lions", "division": "D1", "conference": "ASUN"},
        {"name": "Texas A&M-Commerce Lions", "identifier": "texas_a_and_m_commerce_lions", "division": "D1", "conference": "Southland"},
        {"name": "Loyola Marymount Lions", "identifier": "loyola_marymount_lions", "division": "D1", "conference": "WCC"},
        {"name": "Missouri Southern Lions", "identifier": "missouri_southern_lions", "division": "D2", "conference": "MIAA"},
        {"name": "Lindenwood Lions", "identifier": "lindenwood_lions", "division": "D2", "conference": "OVC"},
        {"name": "Mars Hill Lions", "identifier": "mars_hill_lions", "division": "D2", "conference": "SAC"},
        {"name": "Saint Leo Lions", "identifier": "saint_leo_lions", "division": "D2", "conference": "SSC"}
    ],
    "Mountaineers": [
        {"name": "Appalachian State Mountaineers", "identifier": "appalachian_state_mountaineers", "division": "D1", "conference": "Sun Belt"},
        {"name": "West Virginia Mountaineers", "identifier": "west_virginia_mountaineers", "division": "D1", "conference": "Big 12"},
        {"name": "Mount St. Mary’s Mountaineers", "identifier": "mount_st_marys_mountaineers", "division": "D1", "conference": "MAAC"}
    ],
    "Mustangs": [
        {"name": "SMU Mustangs", "identifier": "smu_mustangs", "division": "D1", "conference": "AAC/ACC"},
        {"name": "Midwestern State Mustangs", "identifier": "midwestern_state_mustangs", "division": "D2", "conference": "LSC"},
        {"name": "Western New Mexico Mustangs", "identifier": "western_new_mexico_mustangs", "division": "D2", "conference": "LSC"},
        {"name": "Southwest Minnesota State Mustangs", "identifier": "southwest_minnesota_state_mustangs", "division": "D2", "conference": "NSIC"}
    ],
    "Panthers": [
        {"name": "Pittsburgh Panthers", "identifier": "pittsburgh_panthers", "division": "D1", "conference": "ACC"},
        {"name": "Georgia State Panthers", "identifier": "georgia_state_panthers", "division": "D1", "conference": "Sun Belt"},
        {"name": "Florida International Panthers", "identifier": "florida_international_panthers", "division": "D1", "conference": "C-USA"},
        {"name": "Northern Iowa Panthers", "identifier": "northern_iowa_panthers", "division": "D1", "conference": "MVC"},
        {"name": "High Point Panthers", "identifier": "high_point_panthers", "division": "D1", "conference": "Big South"},
        {"name": "Prairie View A&M Panthers", "identifier": "prairie_view_a_and_m_panthers", "division": "D1", "conference": "SWAC"},
        {"name": "Eastern Illinois Panthers", "identifier": "eastern_illinois_panthers", "division": "D1", "conference": "OVC"},
        {"name": "Davenport Panthers", "identifier": "davenport_panthers", "division": "D2", "conference": "GLIAC"},
        {"name": "Ohio Dominican Panthers", "identifier": "ohio_dominican_panthers", "division": "D2", "conference": "G-MAC"},
        {"name": "Adelphi Panthers", "identifier": "adelphi_panthers", "division": "D2", "conference": "NE-10"}
    ],
    "Pioneers": [
        {"name": "Denver Pioneers", "identifier": "denver_pioneers", "division": "D1", "conference": "Summit League"},
        {"name": "Sacred Heart Pioneers", "identifier": "sacred_heart_pioneers", "division": "D1", "conference": "NEC"},
        {"name": "Cal State East Bay Pioneers", "identifier": "cal_state_east_bay_pioneers", "division": "D2", "conference": "CCAA"},
        {"name": "Malone Pioneers", "identifier": "malone_pioneers", "division": "D2", "conference": "G-MAC"},
        {"name": "Glenville State Pioneers", "identifier": "glenville_state_pioneers", "division": "D2", "conference": "MEC"}
    ],
    "Rams": [
        {"name": "Colorado State Rams", "identifier": "colorado_state_rams", "division": "D1", "conference": "Mountain West"},
        {"name": "Fordham Rams", "identifier": "fordham_rams", "division": "D1", "conference": "A-10"},
        {"name": "Rhode Island Rams", "identifier": "rhode_island_rams", "division": "D1", "conference": "A-10"},
        {"name": "VCU Rams", "identifier": "vcu_rams", "division": "D1", "conference": "A-10"},
        {"name": "Angelo State Rams", "identifier": "angelo_state_rams", "division": "D2", "conference": "LSC"},
        {"name": "Shepherd Rams", "identifier": "shepherd_rams", "division": "D2", "conference": "PSAC"}
    ],
    "Spartans": [
        {"name": "Michigan State Spartans", "identifier": "michigan_state_spartans", "division": "D1", "conference": "Big Ten"},
        {"name": "San Jose State Spartans", "identifier": "san_jose_state_spartans", "division": "D1", "conference": "Mountain West"},
        {"name": "Norfolk State Spartans", "identifier": "norfolk_state_spartans", "division": "D1", "conference": "MEAC"},
        {"name": "UNC Greensboro Spartans", "identifier": "unc_greensboro_spartans", "division": "D1", "conference": "SoCon"},
        {"name": "South Carolina Upstate Spartans", "identifier": "south_carolina_upstate_spartans", "division": "D1", "conference": "Big South"},
        {"name": "Tampa Spartans", "identifier": "tampa_spartans", "division": "D2", "conference": "SSC"}
    ],
    "Tigers": [
        {"name": "Auburn Tigers", "identifier": "auburn_tigers", "division": "D1", "conference": "SEC"},
        {"name": "Clemson Tigers", "identifier": "clemson_tigers", "division": "D1", "conference": "ACC"},
        {"name": "LSU Tigers", "identifier": "lsu_tigers", "division": "D1", "conference": "SEC"},
        {"name": "Missouri Tigers", "identifier": "missouri_tigers", "division": "D1", "conference": "SEC"},
        {"name": "Memphis Tigers", "identifier": "memphis_tigers", "division": "D1", "conference": "AAC"},
        {"name": "Tennessee State Tigers", "identifier": "tennessee_state_tigers", "division": "D1", "conference": "OVC"},
        {"name": "Texas Southern Tigers", "identifier": "texas_southern_tigers", "division": "D1", "conference": "SWAC"},
        {"name": "Jackson State Tigers", "identifier": "jackson_state_tigers", "division": "D1", "conference": "SWAC"},
        {"name": "Grambling State Tigers", "identifier": "grambling_state_tigers", "division": "D1", "conference": "SWAC"},
        {"name": "Pacific Tigers", "identifier": "pacific_tigers", "division": "D1", "conference": "WCC"},
        {"name": "West Alabama Tigers", "identifier": "west_alabama_tigers", "division": "D2", "conference": "GSC"},
        {"name": "East Central Tigers", "identifier": "east_central_tigers", "division": "D2", "conference": "GAC"}
    ],
    "Trojans": [
        {"name": "USC Trojans", "identifier": "usc_trojans", "division": "D1", "conference": "Big Ten"},
        {"name": "Troy Trojans", "identifier": "troy_trojans", "division": "D1", "conference": "Sun Belt"},
        {"name": "Little Rock Trojans", "identifier": "little_rock_trojans", "division": "D1", "conference": "OVC"},
        {"name": "Anderson Trojans", "identifier": "anderson_trojans", "division": "D2", "conference": "SAC"},
        {"name": "Virginia State Trojans", "identifier": "virginia_state_trojans", "division": "D2", "conference": "Independent"}
    ],
    "Vikings": [
        {"name": "Cleveland State Vikings", "identifier": "cleveland_state_vikings", "division": "D1", "conference": "Horizon League"},
        {"name": "Portland State Vikings", "identifier": "portland_state_vikings", "division": "D1", "conference": "Big Sky"},
        {"name": "Augustana Vikings", "identifier": "augustana_vikings", "division": "D2", "conference": "NSIC"},
        {"name": "Western Washington Vikings", "identifier": "western_washington_vikings", "division": "D2", "conference": "GNAC"}
    ],
    "Warriors": [
        {"name": "Hawaii Rainbow Warriors", "identifier": "hawaii_rainbow_warriors", "division": "D1", "conference": "Mountain West"},
        {"name": "Merrimack Warriors", "identifier": "merrimack_warriors", "division": "D1", "conference": "MAAC"},
        {"name": "Wayne State Warriors", "identifier": "wayne_state_warriors", "division": "D2", "conference": "GLIAC"},
        {"name": "Stanislaus State Warriors", "identifier": "stanislaus_state_warriors", "division": "D2", "conference": "CCAA"},
        {"name": "East Stroudsburg Warriors", "identifier": "east_stroudsburg_warriors", "division": "D2", "conference": "PSAC"},
        {"name": "Winona State Warriors", "identifier": "winona_state_warriors", "division": "D2", "conference": "NSIC"}
    ],
    "Wildcats": [
        {"name": "Kentucky Wildcats", "identifier": "kentucky_wildcats", "division": "D1", "conference": "SEC"},
        {"name": "Arizona Wildcats", "identifier": "arizona_wildcats", "division": "D1", "conference": "Big 12"},
        {"name": "Kansas State Wildcats", "identifier": "kansas_state_wildcats", "division": "D1", "conference": "Big 12"},
        {"name": "New Hampshire Wildcats", "identifier": "new_hampshire_wildcats", "division": "D1", "conference": "America East"},
        {"name": "Northwestern Wildcats", "identifier": "northwestern_wildcats", "division": "D1", "conference": "Big Ten"},
        {"name": "Davidson Wildcats", "identifier": "davidson_wildcats", "division": "D1", "conference": "A-10"},
        {"name": "Villanova Wildcats", "identifier": "villanova_wildcats", "division": "D1", "conference": "Big East"},
        {"name": "Abilene Christian Wildcats", "identifier": "abilene_christian_wildcats", "division": "D1", "conference": "WAC"},
        {"name": "Weber State Wildcats", "identifier": "weber_state_wildcats", "division": "D1", "conference": "Big Sky"}
    ]
}
