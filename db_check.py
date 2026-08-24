import asyncio
import motor.motor_asyncio

async def run():
    client = motor.motor_asyncio.AsyncIOMotorClient('mongodb://localhost:27017')
    db = client['hc_stats_db']
    col = db['upcoming_matches']
    matches = await col.find().sort('match_number', -1).to_list(length=10)
    for m in matches:
        print(f"Match {m.get('match_number')}: {m.get('status')} - Channel: {m.get('channel_id')}")

asyncio.run(run())
