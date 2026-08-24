from bot.database.db import players_col

async def get_player(discord_id: str):
    """Fetches a player from the DB, creating a default profile if they don't exist."""
    discord_id = str(discord_id)
    player = await players_col.find_one({"_id": discord_id})
    if not player:
        # Create a new one
        player = _default_player_template(discord_id)
        # Using upsert basically guarantees it will be inserted safely
        await players_col.update_one(
            {"_id": discord_id}, 
            {"$setOnInsert": player},
            upsert=True
        )
    else:
        # Check if old player is missing new schema fields
        needs_update = False
        default = _default_player_template(discord_id)
        
        # We only check top level keys for now to keep it efficient
        for key in ["economy", "career", "fantasy", "preferences"]:
            if key not in player:
                player[key] = default[key]
                needs_update = True
                
        # Handle innings migration: if innings is missing, default to matches.played
        matches_played = player.get("matches", {}).get("played", 0)
        
        if "batting" in player and "innings" not in player["batting"]:
            player["batting"]["innings"] = matches_played
            needs_update = True
            
        if "bowling" in player and "innings" not in player["bowling"]:
            player["bowling"]["innings"] = matches_played
            needs_update = True
                
        if needs_update:
            await players_col.update_one(
                {"_id": discord_id},
                {"$set": {
                    "economy": player.get("economy", default["economy"]),
                    "career": player.get("career", default["career"]),
                    "fantasy": player.get("fantasy", default["fantasy"]),
                    "preferences": player.get("preferences", default["preferences"]),
                    "batting.innings": player.get("batting", {}).get("innings", matches_played),
                    "bowling.innings": player.get("bowling", {}).get("innings", matches_played)
                }}
            )
            
    return player

async def update_player_stats(discord_id: str, stats_update: dict, set_updates: dict = None, max_updates: dict = None, push_updates: dict = None):
    """
    Applies the stats update dict using MongoDB $inc, $set, $max, and $push.
    """
    discord_id = str(discord_id)
    # Ensure player exists first before inc to set up default structure
    await get_player(discord_id)
    
    update_doc = {"$inc": stats_update}
    if set_updates:
        update_doc["$set"] = set_updates
    if max_updates:
        update_doc["$max"] = max_updates
    if push_updates:
        update_doc["$push"] = push_updates
        
    await players_col.update_one(
        {"_id": discord_id},
        update_doc
    )

def _default_player_template(discord_id: str) -> dict:
    return {
        "_id": str(discord_id),
        "season": 3,
        "points": 0,
        "penalties": [],
        "matches": {
            "played": 0
        },
        "batting": {
            "innings": 0,
            "runs": 0,
            "balls": 0,
            "fifties": 0,
            "hundreds": 0,
            "ducks": 0,
            "highest_score": 0
        },
        "bowling": {
            "innings": 0,
            "runs_conceded": 0,
            "balls": 0,
            "wickets": 0,
            "threefers": 0,
            "fivefers": 0,
            "best_wickets": 0,
            "best_runs": 0
        },
        "fielding": {
            "catches": 0,
            "catch_drops": 0
        },
        "awards": {
            "mvp": 0,
            "hattricks": 0
        },
        "status": {
            "afk": 0,
            "leaves": 0
        },
        "economy": {
            "coins": 0,
            "inventory": [],
            "daily_streak": 0,
            "highest_streak": 0,
            "last_daily": None
        },
        "career": {
            "level": 1,
            "xp": 0,
            "achievements": [],
            "titles": [],
            "active_title": None
        },
        "fantasy": {
            "cards": [],
            "fantasy_team": [],
            "captain": None,
            "vice_captain": None,
            "fantasy_points": 0,
            "season_points": 0
        },
        "preferences": {
            "reaction_enabled": True
        }
    }
