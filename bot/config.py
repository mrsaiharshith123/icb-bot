import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "hc_career_mode")

# ID of the Original HC Bot to listen to
ORIGINAL_HC_BOT_ID = int(os.getenv("ORIGINAL_HC_BOT_ID", 0))

# Channels where matches are played and should be monitored (comma separated IDs)
_CAREER_CHANNELS = os.getenv("CAREER_CHANNEL_IDS", "")
CAREER_CHANNEL_IDS = []
if _CAREER_CHANNELS:
    for c in _CAREER_CHANNELS.split(","):
        c = c.strip()
        if c:
            try:
                CAREER_CHANNEL_IDS.append(int(c))
            except ValueError:
                print(f"Warning: '{c}' is not a valid channel ID. Skipping.")

_LOG_CHANNEL = os.getenv("LOG_CHANNEL_ID", "")
LOG_CHANNEL_ID = None
if _LOG_CHANNEL:
    try:
        LOG_CHANNEL_ID = int(_LOG_CHANNEL.strip())
    except ValueError:
        print(f"Warning: '{_LOG_CHANNEL}' is not a valid log channel ID. Skipping.")
