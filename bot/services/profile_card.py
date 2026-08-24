import io
from PIL import Image, ImageDraw, ImageFont

FONT_BOLD_PATH = "bot/fonts/Rajdhani-Bold.ttf"
FONT_SEMIBOLD_PATH = "bot/fonts/Rajdhani-SemiBold.ttf"
FONT_MEDIUM_PATH = "bot/fonts/Rajdhani-Medium.ttf"
TEMPLATE_PATH = "profile.png"

def draw_centered_text(draw, text, box, font_path, max_font_size, fill="white"):
    x, y, w, h = box
    text = str(text)
    
    # Auto-scale font
    font_size = max_font_size
    font = ImageFont.truetype(font_path, font_size)
    
    # Check width and height
    while font_size > 10:
        bbox = font.getbbox(text)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        
        if text_w <= w and text_h <= h:
            break
        font_size -= 2
        font = ImageFont.truetype(font_path, font_size)
        
    # Calculate perfect center
    bbox = font.getbbox(text)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    
    cx = x + (w - text_w) / 2 - bbox[0]
    cy = y + (h - text_h) / 2 - bbox[1]
    
    draw.text((cx, cy), text, font=font, fill=fill)

def generate_profile_card(player_data: dict, rank_data: dict, form_matches: list, avatar_bytes: bytes) -> io.BytesIO:
    try:
        base = Image.open(TEMPLATE_PATH).convert("RGBA")
    except FileNotFoundError:
        base = Image.new("RGBA", (1664, 936), (0, 0, 0, 255))

    draw = ImageDraw.Draw(base)

    # --- Avatar ---
    if avatar_bytes:
        try:
            avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
            # x=700, y=220, width=250, height=250
            avatar = avatar.resize((250, 250), Image.Resampling.LANCZOS)
            mask = Image.new("L", (250, 250), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, 250, 250), fill=255)
            base.paste(avatar, (710, 224), mask)
        except Exception as e:
            print(f"Error applying avatar: {e}")

    # --- Name ---
    player_name = player_data.get("name", "Unknown Player")
    # Using Rajdhani Bold as main title since italic isn't available
    draw_centered_text(draw, player_name.upper(), (324, 130, 1000, 75), FONT_BOLD_PATH, 65, fill="white")
    
    # --- Stats Data ---
    matches_played = player_data.get("matches", {}).get("played", 0)
    fielding = player_data.get("fielding", {})
    awards = player_data.get("awards", {})
    career = player_data.get("career", {})
    
    batting = player_data.get("batting", {})
    batting_runs = batting.get("runs", 0)
    batting_innings = batting.get("innings", 0)
    batting_avg = batting.get("average", round(batting_runs / max(1, batting_innings), 1) if batting_innings > 0 else 0.0)
    
    bowling = player_data.get("bowling", {})
    bowling_wickets = bowling.get("wickets", 0)
    bowling_runs_conceded = bowling.get("runs_conceded", 0)
    bowling_balls = bowling.get("balls", 0)
    bowling_innings = bowling.get("innings", 0)
    bowling_avg = bowling.get("average", round(bowling_runs_conceded / max(1, bowling_wickets), 1) if bowling_wickets > 0 else 0.0)
    economy = bowling.get("economy", round(bowling_runs_conceded / max(1, bowling_balls / 6.0), 1) if bowling_balls > 0 else 0.0)

    # --- Batting ---
    draw_centered_text(draw, batting_innings, (310, 309, 230, 52), FONT_BOLD_PATH, 42)
    draw_centered_text(draw, batting_runs, (310, 372, 230, 52), FONT_BOLD_PATH, 42)
    draw_centered_text(draw, batting_avg, (310, 438, 230, 52), FONT_BOLD_PATH, 42)
    draw_centered_text(draw, f"{batting.get('fifties', 0)} / {batting.get('hundreds', 0)}", (310, 503, 230, 52), FONT_BOLD_PATH, 42)
    draw_centered_text(draw, batting.get("highest_score", 0), (310, 567, 230, 52), FONT_BOLD_PATH, 42)
    draw_centered_text(draw, batting.get("ducks", 0), (310, 632, 230, 52), FONT_BOLD_PATH, 42)

    # --- Bowling ---
    draw_centered_text(draw, bowling_innings, (1390, 309, 230, 52), FONT_BOLD_PATH, 42)
    draw_centered_text(draw, bowling_wickets, (1390, 373, 230, 52), FONT_BOLD_PATH, 42)
    draw_centered_text(draw, bowling_avg, (1390, 438, 230, 52), FONT_BOLD_PATH, 42)
    draw_centered_text(draw, f"{bowling.get('threefers', 0)} / {bowling.get('fivefers', 0)}", (1390, 503, 230, 52), FONT_BOLD_PATH, 42)
    draw_centered_text(draw, economy, (1390, 567, 230, 52), FONT_BOLD_PATH, 42)
    
    best_wkts = bowling.get("best_wickets", 0)
    best_runs = bowling.get("best_runs", 0)
    best_str = f"{best_wkts}-{best_runs}" if best_wkts > 0 else "0"
    draw_centered_text(draw, best_str, (1390, 631, 230, 52), FONT_BOLD_PATH, 42)

    # --- Center Career ---
    level_name = career.get("current", "Unknown")
    draw_centered_text(draw, level_name.upper(), (585, 510, 495, 55), FONT_BOLD_PATH, 42)
    
    xp = career.get("current_xp", 0)
    draw_centered_text(draw, f"{xp}", (585, 595, 495, 55), FONT_BOLD_PATH, 42)

    is_max = career.get("is_max", False)
    bar_box = (594, 700, 495, 35)
    
    if is_max:
        # Full bar for max level
        draw.rounded_rectangle((bar_box[0], bar_box[1], bar_box[0] + bar_box[2], bar_box[1] + bar_box[3]), radius=18, fill="#00d2ff")
        draw_centered_text(draw, "MAX LEVEL", (585, 795, 210, 55), FONT_BOLD_PATH, 42, fill="white")
        draw_centered_text(draw, "0", (850, 795, 210, 55), FONT_MEDIUM_PATH, 42, fill="white")
    else:
        next_xp = career.get("next_xp", 1000)
        pct = min(1.0, xp / next_xp)
        fill_w = int(bar_box[2] * pct)
        if fill_w > 0:
            draw.rounded_rectangle((bar_box[0], bar_box[1], bar_box[0] + fill_w, bar_box[1] + bar_box[3]), radius=18, fill="#00d2ff")
            
        draw_centered_text(draw, career.get('next', 'UNKNOWN').upper(), (595, 810, 210, 55), FONT_BOLD_PATH, 42, fill="white")
        needed = next_xp - xp
        draw_centered_text(draw, f"{needed}", (860, 810, 210, 55), FONT_BOLD_PATH, 42, fill="white")

    # --- Fielding ---
    draw_centered_text(draw, fielding.get("catches", 0), (310, 814, 230, 52), FONT_BOLD_PATH, 42)

    # --- Awards ---
    draw_centered_text(draw, awards.get("mvp", 0), (1350, 814, 230, 52), FONT_BOLD_PATH, 42)

    out = io.BytesIO()
    base.save(out, format="PNG")
    out.seek(0)
    return out
