import random
from bot.database.db import players_col

def calculate_player_rating(player_data: dict) -> tuple:
    """
    Calculates a fantasy rating (1-99) and determines rarity based on stats.
    Returns (rating: int, rarity: str)
    """
    matches = player_data.get("matches", {}).get("played", 0)
    runs = player_data.get("batting", {}).get("runs", 0)
    wickets = player_data.get("bowling", {}).get("wickets", 0)
    mvps = player_data.get("awards", {}).get("mvp", 0)
    
    if matches == 0:
        return 50, "Common"
        
    # Basic formula
    batting_avg = runs / matches
    bowling_wpm = wickets / matches
    
    # Weighting
    base_rating = 50
    bat_bonus = min(25, batting_avg * 0.5)
    bowl_bonus = min(20, bowling_wpm * 10)
    mvp_bonus = min(4, mvps * 0.5)
    
    rating = int(base_rating + bat_bonus + bowl_bonus + mvp_bonus)
    rating = min(99, max(40, rating))
    
    if rating >= 90:
        rarity = "Mythic"
    elif rating >= 80:
        rarity = "Legendary"
    elif rating >= 70:
        rarity = "Epic"
    elif rating >= 60:
        rarity = "Rare"
    else:
        rarity = "Common"
        
    return rating, rarity

async def generate_random_card(discord_id: str):
    """
    Pulls a random player from the DB, calculates their live rating,
    and returns a card dictionary. Adds it to the user's fantasy collection.
    """
    # Get all eligible players (played at least 1 match)
    cursor = players_col.find({"matches.played": {"$gt": 0}})
    all_players = await cursor.to_list(length=None)
    
    if not all_players:
        return None
        
    pulled_player = random.choice(all_players)
    rating, rarity = calculate_player_rating(pulled_player)
    
    card = {
        "player_id": pulled_player["_id"],
        "rating": rating,
        "rarity": rarity,
        "obtained_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    }
    
    # Add to user's collection
    await players_col.update_one(
        {"_id": str(discord_id)},
        {"$push": {"fantasy.cards": card}}
    )
    
    # Needs a name for display
    card["name"] = pulled_player.get("name", "Unknown Player")
    return card
