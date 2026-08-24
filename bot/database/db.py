from motor.motor_asyncio import AsyncIOMotorClient
from bot.config import MONGO_URI, DATABASE_NAME

client = AsyncIOMotorClient(MONGO_URI)
db = client[DATABASE_NAME]

players_col = db["players"]
matches_col = db["matches"]
config_col = db["server_config"]
upcoming_matches_col = db["upcoming_matches"]
daily_announcements_col = db["daily_announcements"]

async def setup_indexes():
    # Player indexes
    await players_col.create_index("_id")
    await players_col.create_index("points")
    
    # Match indexes
    await matches_col.create_index("_id")
    await matches_col.create_index("channel_id")
    await matches_col.create_index("status")
    
    # Ensure a single raw_stats_message_id is only processed once globally (to prevent duplicates)
    # partialFilterExpression so that only finalized matches with this ID are constrained, or we can just make it sparse.
    await matches_col.create_index(
        "raw_stats_message_id", 
        unique=True, 
        sparse=True
    )
    
    # Upcoming Matches indexes
    # unique index for guild_id + match_number
    await upcoming_matches_col.create_index(
        [("guild_id", 1), ("match_number", 1)],
        unique=True
    )
    await upcoming_matches_col.create_index("scheduled_at")
    await upcoming_matches_col.create_index("status")
    await upcoming_matches_col.create_index("og_result_message_id", sparse=True)
    
    # Daily Announcements indexes
    await daily_announcements_col.create_index("scheduled_at")
    await daily_announcements_col.create_index("announcement_sent")
