def get_career_level(xp: int) -> dict:
    """
    Returns the career level information based on the player's XP.
    """
    levels = [
        {"name": "Local Team", "xp": 0},
        {"name": "Under 15", "xp": 200},
        {"name": "District Team", "xp": 350},
        {"name": "Ranji Team", "xp": 500},
        {"name": "Vijay Hazare", "xp": 1000},
        {"name": "Under 19", "xp": 2000},
        {"name": "Indian Premier League", "xp": 5000},
        {"name": "Country Team B", "xp": 10000},
        {"name": "Country Team A", "xp": 15000},
        {"name": "Country Grade C", "xp": 20000},
        {"name": "Country Grade B", "xp": 30000},
        {"name": "Country Grade A", "xp": 40000},
        {"name": "Country Grade A+", "xp": 50000}
    ]
    
    current_level = levels[0]
    next_level = levels[1]
    
    for i, level in enumerate(levels):
        if xp >= level["xp"]:
            current_level = level
            if i + 1 < len(levels):
                next_level = levels[i + 1]
            else:
                next_level = None
        else:
            break
            
    return {
        "current": current_level["name"],
        "current_xp": xp,
        "next": next_level["name"] if next_level else None,
        "next_xp": next_level["xp"] if next_level else None,
        "is_max": next_level is None
    }
