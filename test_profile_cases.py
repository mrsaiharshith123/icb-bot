import io
from bot.services.profile_card import generate_profile_card

avatar_bytes = open('template_debug.png', 'rb').read() 

# 1. 0 XP player (No matches)
player_1 = {
    'name': 'NEW PLAYER',
    'career': {'current': 'LOCAL TEAM', 'current_xp': 0, 'next': 'UNDER 15', 'next_xp': 200, 'is_max': False},
    'batting': {'runs': 0, 'balls': 0, 'fifties': 0, 'hundreds': 0, 'highest_score': 0, 'ducks': 0},
    'bowling': {'wickets': 0, 'runs_conceded': 0, 'balls': 0, 'threefers': 0, 'fivefers': 0, 'best_wickets': 0, 'best_runs': 0},
    'fielding': {'catches': 0, 'catch_drops': 0},
    'awards': {'mvp': 0, 'hattricks': 0},
    'matches': {'played': 0}
}
with open('test_1_0xp.png', 'wb') as f:
    f.write(generate_profile_card(player_1, {'season_rank': 999}, [], avatar_bytes).read())

# 2. Mid-level player (with 5+ finalized matches)
player_2 = {
    'name': 'MRPLAYER',
    'career': {'current': 'VIJAY HAZARE', 'current_xp': 1500, 'next': 'UNDER 19', 'next_xp': 2000, 'is_max': False},
    'batting': {'runs': 450, 'balls': 320, 'fifties': 2, 'hundreds': 0, 'highest_score': 84, 'ducks': 1},
    'bowling': {'wickets': 15, 'runs_conceded': 210, 'balls': 180, 'threefers': 1, 'fivefers': 0, 'best_wickets': 3, 'best_runs': 15},
    'fielding': {'catches': 5, 'catch_drops': 1},
    'awards': {'mvp': 1, 'hattricks': 0},
    'matches': {'played': 12}
}
matches_2 = [{'points': 45}, {'points': -10}, {'points': 80}, {'points': 30}, {'points': -5}, {'points': 20}]
with open('test_2_midlevel.png', 'wb') as f:
    f.write(generate_profile_card(player_2, {'season_rank': 42}, matches_2, avatar_bytes).read())

# 3. Long username
player_3 = dict(player_2)
player_3['name'] = 'VERY LONG USERNAME EXTREME'
with open('test_3_long_name.png', 'wb') as f:
    f.write(generate_profile_card(player_3, {'season_rank': 42}, matches_2, avatar_bytes).read())

# 4. Indian Premier League
player_4 = dict(player_2)
player_4['name'] = 'STAR PLAYER'
player_4['career'] = {'current': 'INDIAN PREMIER LEAGUE', 'current_xp': 6500, 'next': 'COUNTRY TEAM B', 'next_xp': 10000, 'is_max': False}
with open('test_4_ipl.png', 'wb') as f:
    f.write(generate_profile_card(player_4, {'season_rank': 5}, matches_2, avatar_bytes).read())

# 5. Country Grade A+
player_5 = dict(player_2)
player_5['name'] = 'THE GOAT'
player_5['career'] = {'current': 'COUNTRY GRADE A+', 'current_xp': 55000, 'next': 'MAX', 'next_xp': 50000, 'is_max': True}
with open('test_5_grade_aplus.png', 'wb') as f:
    f.write(generate_profile_card(player_5, {'season_rank': 1}, matches_2, avatar_bytes).read())

# 6. Large statistics values
player_6 = {
    'name': 'STAT PADDER',
    'career': {'current': 'COUNTRY GRADE A+', 'current_xp': 99999, 'next': 'MAX', 'next_xp': 50000, 'is_max': True},
    'batting': {'runs': 12500, 'balls': 9800, 'fifties': 145, 'hundreds': 42, 'highest_score': 312, 'ducks': 5},
    'bowling': {'wickets': 850, 'runs_conceded': 15400, 'balls': 12000, 'threefers': 120, 'fivefers': 45, 'best_wickets': 8, 'best_runs': 15},
    'fielding': {'catches': 450, 'catch_drops': 12},
    'awards': {'mvp': 85, 'hattricks': 12},
    'matches': {'played': 450}
}
with open('test_6_large_stats.png', 'wb') as f:
    f.write(generate_profile_card(player_6, {'season_rank': 2}, matches_2, avatar_bytes).read())

print("Generated 6 test cards (covering all 8 conditions).")
