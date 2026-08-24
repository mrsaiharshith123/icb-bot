import re

def parse_raw_statistics(message) -> list:
    """
    Parses the raw stats block into a list of dictionaries.
    Expected format:
    Discord User ID, Runs, Balls Faced, Runs Conceded, Balls Bowled, Wickets, Out Status (0=OUT, 1=NOT OUT)
    """
    if isinstance(message, str):
        content = message
    else:
        content = message.content or ""
        if "```" not in content:
            for embed in getattr(message, 'embeds', []):
                if embed.description and "```" in embed.description:
                    content += "\n" + embed.description
                    break
                
    # Remove markdown code blocks (e.g. ```text ... ``` or just ``` ... ```)
    content = re.sub(r"```[a-zA-Z]*\s*\n(.*?)```", r"\1", content, flags=re.DOTALL)
    
    players_data = []
    lines = content.strip().split("\n")
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 7:
            print(f"Skipping invalid stats line (not 7 fields): {line}")
            continue
            
        try:
            out_status_raw = int(parts[6])
            if out_status_raw not in (0, 1):
                print(f"Skipping invalid stats line (out status not 0 or 1): {line}")
                continue
                
            player_dict = {
                "discord_id": str(int(parts[0])), # Validate it's an int, store as string
                "runs": int(parts[1]),
                "balls_faced": int(parts[2]),
                "runs_conceded": int(parts[3]),
                "balls_bowled": int(parts[4]),
                "wickets": int(parts[5]),
                "out": out_status_raw == 0,  # 0 is OUT, 1 is NOT OUT
                "catches": 0,       # To be populated later
                "catch_drops": 0    # To be populated later
            }
            players_data.append(player_dict)
        except ValueError as e:
            print(f"Error parsing values in line '{line}': {e}")
            
    return players_data
