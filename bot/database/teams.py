from bot.database.db import teams_col, config_col

async def get_team(role_id: str):
    return await teams_col.find_one({"_id": role_id})

async def get_all_teams():
    cursor = teams_col.find({}).sort([("points", -1), ("nrr", -1), ("runs_for", -1)])
    return await cursor.to_list(length=None)

async def get_user_team(discord_id: str):
    team = await teams_col.find_one({"members": str(discord_id)})
    return team["_id"] if team else None

async def create_manual_team(name: str):
    import uuid
    # Check for duplicate name
    existing = await teams_col.find_one({"name": {"$regex": f"^{name}$", "$options": "i"}})
    if existing:
        return None
        
    team_id = f"TEAM-{str(uuid.uuid4())[:8].upper()}"
    await teams_col.insert_one({
        "_id": team_id,
        "name": name,
        "members": [],
        "captain": None,
        "matches_played": 0,
        "wins": 0,
        "losses": 0,
        "draws": 0,
        "points": 0,
        "runs_for": 0,
        "overs_faced": 0.0,
        "runs_against": 0,
        "overs_bowled": 0.0,
        "nrr": 0.0,
        "is_manual": True
    })
    return team_id

async def upsert_team(role_id: str, name: str, members: list):
    # Upserts basic team info during sync
    await teams_col.update_one(
        {"_id": role_id},
        {
            "$set": {
                "name": name,
                "members": members
            },
            "$setOnInsert": {
                "captain": None,
                "matches_played": 0,
                "wins": 0,
                "losses": 0,
                "draws": 0,
                "points": 0,
                "runs_for": 0,
                "overs_faced": 0.0,
                "runs_against": 0,
                "overs_bowled": 0.0,
                "nrr": 0.0
            }
        },
        upsert=True
    )

def _overs_to_balls(overs: float) -> int:
    o = int(overs)
    b = int(round((overs - o) * 10))
    return o * 6 + b

def _balls_to_overs(balls: int) -> float:
    return (balls // 6) + (balls % 6) / 10.0

async def update_team_stats(role_id: str, is_win: bool, is_loss: bool, is_draw: bool, runs_for: int, balls_faced: int, runs_against: int, balls_bowled: int):
    team = await get_team(role_id)
    if not team: return
    
    mp = team.get("matches_played", 0) + 1
    w = team.get("wins", 0) + (1 if is_win else 0)
    l = team.get("losses", 0) + (1 if is_loss else 0)
    d = team.get("draws", 0) + (1 if is_draw else 0)
    pts = team.get("points", 0)
    
    # Standard League Rules: Win = 2, Draw/Tie = 1, Loss = 0
    if is_win: pts += 2
    elif is_draw: pts += 1
    
    new_rf = team.get("runs_for", 0) + runs_for
    new_ra = team.get("runs_against", 0) + runs_against
    
    total_balls_faced = _overs_to_balls(team.get("overs_faced", 0.0)) + balls_faced
    total_balls_bowled = _overs_to_balls(team.get("overs_bowled", 0.0)) + balls_bowled
    
    rr_for = (new_rf / total_balls_faced * 6) if total_balls_faced > 0 else 0
    rr_against = (new_ra / total_balls_bowled * 6) if total_balls_bowled > 0 else 0
    nrr = rr_for - rr_against
    
    await teams_col.update_one(
        {"_id": role_id},
        {"$set": {
            "matches_played": mp,
            "wins": w,
            "losses": l,
            "draws": d,
            "points": pts,
            "runs_for": new_rf,
            "overs_faced": _balls_to_overs(total_balls_faced),
            "runs_against": new_ra,
            "overs_bowled": _balls_to_overs(total_balls_bowled),
            "nrr": round(nrr, 3)
        }}
    )
