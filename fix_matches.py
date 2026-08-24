import asyncio
from bot.database.db import matches_col

async def fix():
    res = await matches_col.update_many({'status': 'PENDING_APPROVAL'}, {'$set': {'status': 'LIVE'}})
    print(f"Modified {res.modified_count} matches back to LIVE")

if __name__ == '__main__':
    asyncio.run(fix())
