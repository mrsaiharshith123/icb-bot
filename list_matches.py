import asyncio
from bot.database.db import upcoming_matches_col

async def show():
    cursor = upcoming_matches_col.find()
    async for m in cursor:
        print(f"Match {m.get('match_number')}: {m.get('status')}, Channel: {m.get('channel_id')}")

if __name__ == '__main__':
    asyncio.run(show())
