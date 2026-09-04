import pytz
from datetime import datetime

def is_janmashtami() -> bool:
    tz = pytz.timezone('Asia/Kolkata')
    now = datetime.now(tz)
    return now.strftime("%Y-%m-%d") == "2026-09-04"
