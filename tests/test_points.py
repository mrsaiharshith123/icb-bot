from bot.services.points_calculator import calculate_player_points

def test_basic_points():
    stats = {
        "runs": 10,
        "balls_faced": 10,
        "runs_conceded": 0,
        "balls_bowled": 0,
        "wickets": 1,
        "catches": 1,
        "catch_drops": 0,
        "out": False
    }
    # 10 runs = 10, 1 wicket = 15, 1 catch = 10 -> Total 35
    assert calculate_player_points(stats) == 35

def test_duck_penalty():
    stats = {
        "runs": 0,
        "balls_faced": 2,
        "runs_conceded": 0,
        "balls_bowled": 0,
        "wickets": 0,
        "catches": 0,
        "catch_drops": 0,
        "out": True
    }
    # 0 runs, out, balls faced > 0 -> Duck penalty -20
    assert calculate_player_points(stats) == -20

def test_catch_drop_penalty():
    stats = {
        "runs": 0,
        "balls_faced": 0,
        "runs_conceded": 0,
        "balls_bowled": 0,
        "wickets": 0,
        "catches": 0,
        "catch_drops": 2,
        "out": False
    }
    # 2 catch drops = -20
    assert calculate_player_points(stats) == -20

def test_economy_penalty():
    stats = {
        "runs": 0,
        "balls_faced": 0,
        "runs_conceded": 25,
        "balls_bowled": 6, # 1 over
        "wickets": 0,
        "catches": 0,
        "catch_drops": 0,
        "out": False
    }
    # Economy = 25/1 = 25 (>= 20) -> -10
    assert calculate_player_points(stats) == -10

def test_milestone_points():
    # 50 test
    stats_50 = {"runs": 50, "balls_faced": 30, "out": False}
    assert calculate_player_points(stats_50) == 60 # 50 (runs) + 10 (50 bonus)
    
    # 100 test (Non-stacking)
    stats_100 = {"runs": 100, "balls_faced": 60, "out": False}
    assert calculate_player_points(stats_100) == 120 # 100 (runs) + 20 (100 bonus)

    # 3-fer test
    stats_3fer = {"wickets": 3}
    assert calculate_player_points(stats_3fer) == 55 # 3*15 (45) + 10 (3fer bonus)

    # 5-fer test (Non-stacking)
    stats_5fer = {"wickets": 5}
    assert calculate_player_points(stats_5fer) == 90 # 5*15 (75) + 15 (5fer bonus)
