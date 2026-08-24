import asyncio
import motor.motor_asyncio

async def run():
    client = motor.motor_asyncio.AsyncIOMotorClient('mongodb://localhost:27017')
    db = client['hc_stats_db']
    col = db['upcoming_matches']
    
    print("Updating Match 27...")
    res = await col.update_one({"match_number": 27}, {"$set": {"status": "FINALIZED"}})
    print(f"Match 27 modified: {res.modified_count}")
    
    print("Updating Match 28...")
    res = await col.update_one({"match_number": 28}, {"$set": {"status": "LIVE"}})
    print(f"Match 28 modified: {res.modified_count}")
    
    print("Updating Match 29...")
    res = await col.update_one({"match_number": 29}, {"$set": {"status": "LIVE"}})
    print(f"Match 29 modified: {res.modified_count}")
    
    # Also create active matches in the matches collection if they don't exist
    matches_col = db['matches']
    
    async def ensure_active(match_num):
        upcoming = await col.find_one({"match_number": match_num})
        if upcoming:
            ch_id = upcoming["channel_id"]
            m_type = upcoming.get("match_type", "ELITE_NO_CATCHES")
            # Usually start_message_id is used, but we can fake it or use match_num
            match_id = f"S3-M{match_num}"
            existing = await matches_col.find_one({"_id": match_id})
            if not existing:
                from datetime import datetime, timezone
                doc = {
                    "_id": match_id,
                    "channel_id": ch_id,
                    "start_message_id": match_num,
                    "og_hc_bot_id": 0,
                    "match_number": match_num,
                    "match_type": m_type,
                    "status": "LIVE",
                    "started_at": datetime.now(timezone.utc),
                    "catches": [],
                    "hattricks": [],
                    "pending_catch": None,
                }
                await matches_col.insert_one(doc)
                print(f"Created active tracking doc for Match {match_num} in matches collection.")
                
    await ensure_active(28)
    await ensure_active(29)

asyncio.run(run())
