from datetime import datetime, timezone
from bot.database.db import matches_col

async def create_match(channel_id: int, start_message_id: int, match_number: int, match_type: str, og_hc_bot_id: str) -> dict:
    match_id = f"S3-{start_message_id}"
    match_doc = {
        "_id": match_id,
        "channel_id": channel_id,
        "start_message_id": start_message_id,
        "og_hc_bot_id": og_hc_bot_id,
        "match_number": match_number,
        "match_type": match_type,
        "status": "LIVE",
        "started_at": datetime.now(timezone.utc),
        "catches": [],
        "hattricks": [],
        "pending_catch": None,
    }
    
    # Try inserting. If it already exists, this safely does nothing but returns existing
    try:
        await matches_col.insert_one(match_doc)
    except Exception:
        # Document already exists (duplicate start message)
        pass
        
    match = await matches_col.find_one({"_id": match_id})
    return match

async def add_hattrick_to_match(match_id: str, player_id: str, message_id: int) -> bool:
    """
    Records a hattrick in the active match if it hasn't been recorded yet.
    Returns True if added, False if duplicate.
    """
    result = await matches_col.update_one(
        {
            "_id": match_id, 
            "hattricks.message_id": {"$ne": message_id}
        },
        {
            "$push": {
                "hattricks": {
                    "message_id": message_id,
                    "player_id": player_id
                }
            }
        }
    )
    return result.modified_count > 0

async def get_active_match(channel_id: int):
    """Returns the currently active LIVE or RESULT_RECEIVED match in a channel, if any."""
    return await matches_col.find_one({"channel_id": channel_id, "status": {"$in": ["LIVE", "RESULT_RECEIVED"]}})

async def add_catch_to_match(match_id: str, catcher_id: str, batter_id: str, message_id: int, dropped: bool = False) -> bool:
    """
    Records a catch in the active match if it hasn't been recorded yet.
    Returns True if added, False if duplicate.
    """
    # Prevent duplicate push using $ne
    result = await matches_col.update_one(
        {
            "_id": match_id, 
            "catches.message_id": {"$ne": message_id}
        },
        {
            "$push": {
                "catches": {
                    "message_id": message_id,
                    "catcher": catcher_id,
                    "batter": batter_id,
                    "dropped": dropped
                }
            }
        }
    )
    return result.modified_count > 0

async def set_pending_catch(match_id: str, catcher_id: str, batter_id: str, message_id: int):
    """Stores a potential catch waiting for resolution with a timestamp."""
    await matches_col.update_one(
        {"_id": match_id},
        {"$set": {"pending_catch": {
            "catcher": catcher_id, 
            "batter": batter_id,
            "message_id": message_id,
            "created_at": datetime.now(timezone.utc)
        }}}
    )

async def resolve_pending_catch(match_id: str, success: bool, message_id: int) -> dict:
    """Resolves a pending catch. Returns dict with catcher and batter if successful."""
    match = await matches_col.find_one({"_id": match_id})
    if match and match.get("pending_catch"):
        pending = match["pending_catch"]
        catcher_id = pending["catcher"]
        batter_id = pending["batter"]
        created_at = pending.get("created_at")
        
        is_expired = False
        if created_at:
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            if (datetime.now(timezone.utc) - created_at).total_seconds() > 180: # 3 minutes timeout
                is_expired = True
        
        # Clear pending
        await matches_col.update_one(
            {"_id": match_id},
            {"$set": {"pending_catch": None}}
        )
        
        if is_expired:
            return {"expired": True, "catcher_id": catcher_id, "batter_id": batter_id}
        
        # Add to catches list (success or dropped)
        added = await add_catch_to_match(match_id, catcher_id, batter_id, message_id, dropped=not success)
        
        # If it was successfully added to array, return the details
        if added:
            return {"catcher_id": catcher_id, "batter_id": batter_id, "expired": False}
            
    return None

async def cancel_match(match_id: str):
    """Deletes a match from the database (used for overriding dummy matches)."""
    await matches_col.delete_one({"_id": match_id})

async def set_match_pending(match_id: str, raw_stats_message_id: int, raw_text: str) -> bool:
    """
    Marks match as PENDING_APPROVAL and saves the raw text.
    Returns True if successful.
    """
    try:
        result = await matches_col.update_one(
            {"_id": match_id},
            {
                "$set": {
                    "status": "PENDING_APPROVAL",
                    "raw_stats_message_id": raw_stats_message_id,
                    "raw_stats_text": raw_text
                }
            }
        )
        return result.modified_count > 0
    except Exception:
        return False

async def get_pending_match(channel_id: int):
    """Returns a match waiting for stats approval in this channel."""
    return await matches_col.find_one({"channel_id": channel_id, "status": "PENDING_APPROVAL"})

async def approve_match_stats(match_id: str, players_data: list) -> bool:
    """
    Marks match as FINALIZED and saves the final stats array.
    """
    result = await matches_col.update_one(
        {"_id": match_id},
        {
            "$set": {
                "status": "FINALIZED",
                "players": players_data,
                "ended_at": datetime.now(timezone.utc)
            }
        }
    )
    return result.matched_count > 0
