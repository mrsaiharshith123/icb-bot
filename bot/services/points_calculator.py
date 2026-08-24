def calculate_player_points(stats: dict) -> int:
    """
    Calculates total points for a player for a single match.
    Expected keys in stats: runs, balls_faced, runs_conceded, balls_bowled, wickets, catches, catch_drops, out (bool)
    """
    points = 0
    
    runs = stats.get("runs", 0)
    balls_faced = stats.get("balls_faced", 0)
    runs_conceded = stats.get("runs_conceded", 0)
    balls_bowled = stats.get("balls_bowled", 0)
    wickets = stats.get("wickets", 0)
    catches = stats.get("catches", 0)
    catch_drops = stats.get("catch_drops", 0)
    hattricks = stats.get("hattricks", 0)
    is_out = stats.get("out", False)

    # POSITIVE POINTS
    points += runs * 1
    points += wickets * 15
    points += catches * 10
    points += hattricks * 20
    
    # 50s and 100s (Non-stacking per Season 3 rules: +10 for 50, +20 for 100)
    if runs >= 100:
        points += 20
    elif runs >= 50:
        points += 10
        
    # Wicket hauls (Non-stacking per Season 3 rules: +10 for 3fer, +15 for 5fer)
    if wickets >= 5:
        points += 15
    elif wickets >= 3:
        points += 10
        
    # NEGATIVE POINTS
    
    # AFK, Leave, and Catch Drops are handled manually by admins
    
    # Duck (0 runs and Out)
    if runs == 0 and is_out and balls_faced > 0:
        points -= 20
        
    # Economy (Must have bowled at least one ball)
    if balls_bowled > 0:
        overs = balls_bowled / 6.0
        economy = runs_conceded / overs
        if economy >= 20.0:
            points -= 10
            
    return points
