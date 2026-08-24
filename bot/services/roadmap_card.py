import io
from PIL import Image, ImageDraw, ImageFont
import os
from bot.services.career import get_career_level

# --- CONFIGURATION ---
# IMPORTANT: You must update these coordinates visually based on roadmap1.png and roadmap2.png.
# card_box = (x, y, width, height) of the entire card (used for the glowing border)
# req_box = (x, y, width, height) of the existing "NEED X XP" text area (used for covering it up)
ROADMAP_COORDS = {
    "Local Team": {"page": 1, "card_box": (0, 0, 0, 0), "req_box": (0, 0, 0, 0)},
    "Under 15": {"page": 1, "card_box": (0, 0, 0, 0), "req_box": (0, 0, 0, 0)},
    "District Team": {"page": 1, "card_box": (0, 0, 0, 0), "req_box": (0, 0, 0, 0)},
    "Ranji Team": {"page": 1, "card_box": (0, 0, 0, 0), "req_box": (0, 0, 0, 0)},
    "Vijay Hazare": {"page": 1, "card_box": (0, 0, 0, 0), "req_box": (0, 0, 0, 0)},
    "Under 19": {"page": 1, "card_box": (0, 0, 0, 0), "req_box": (0, 0, 0, 0)},
    "Indian Premier League": {"page": 1, "card_box": (0, 0, 0, 0), "req_box": (0, 0, 0, 0)},
    "Country Team B": {"page": 1, "card_box": (0, 0, 0, 0), "req_box": (0, 0, 0, 0)},
    "Country Team A": {"page": 1, "card_box": (0, 0, 0, 0), "req_box": (0, 0, 0, 0)},
    "Country Grade C": {"page": 1, "card_box": (0, 0, 0, 0), "req_box": (0, 0, 0, 0)},
    "Country Grade B": {"page": 2, "card_box": (0, 0, 0, 0), "req_box": (0, 0, 0, 0)},
    "Country Grade A": {"page": 2, "card_box": (0, 0, 0, 0), "req_box": (0, 0, 0, 0)},
    "Country Grade A+": {"page": 2, "card_box": (0, 0, 0, 0), "req_box": (0, 0, 0, 0)},
}

FONT_BOLD_PATH = "bot/fonts/Rajdhani-Bold.ttf"
NAVY_BG_COLOR = "#0f172a" # Change this if the template background is a different hex

def draw_centered_text(draw, text, box, font_path, max_font_size, fill="white"):
    x, y, w, h = box
    text = str(text)
    
    font_size = max_font_size
    font = ImageFont.truetype(font_path, font_size)
    
    while font_size > 10:
        bbox = font.getbbox(text)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        
        if text_w <= w * 0.95 and text_h <= h * 0.95:
            break
        font_size -= 2
        font = ImageFont.truetype(font_path, font_size)
        
    bbox = font.getbbox(text)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    
    cx = x + (w - text_w) / 2 - bbox[0]
    cy = y + (h - text_h) / 2 - bbox[1]
    
    # Shadow/glow for readability
    shadow_offset = 2
    draw.text((cx + shadow_offset, cy + shadow_offset), text, font=font, fill="#00aaff") # Subtle blue glow
    draw.text((cx, cy), text, font=font, fill=fill)

def generate_roadmap_page(player_xp: int, page: int) -> io.BytesIO:
    template_path = f"roadmap{page}.png"
    
    try:
        base = Image.open(template_path).convert("RGBA")
    except FileNotFoundError:
        # Fallback for local testing if files aren't placed yet
        base = Image.new("RGBA", (1536, 1024), (20, 20, 30, 255))
        
    draw = ImageDraw.Draw(base, "RGBA")
    
    # Draw YOUR XP in top right
    if page == 1:
        xp_box = (1258, 84, 218, 65)
    else:
        xp_box = (1294, 110, 176, 63)
        
    formatted_xp = f"{player_xp:,}"
    draw_centered_text(draw, formatted_xp, xp_box, FONT_BOLD_PATH, 55, fill="white")
    
    # Use existing career levels config to know requirements and order
    levels = [
        {"name": "Local Team", "xp": 0},
        {"name": "Under 15", "xp": 200},
        {"name": "District Team", "xp": 350},
        {"name": "Ranji Team", "xp": 500},
        {"name": "Vijay Hazare", "xp": 1000},
        {"name": "Under 19", "xp": 2000},
        {"name": "Indian Premier League", "xp": 5000},
        {"name": "Country Team B", "xp": 10000},
        {"name": "Country Team A", "xp": 15000},
        {"name": "Country Grade C", "xp": 20000},
        {"name": "Country Grade B", "xp": 30000},
        {"name": "Country Grade A", "xp": 40000},
        {"name": "Country Grade A+", "xp": 50000}
    ]
    
    career_status = get_career_level(player_xp)
    current_level_name = career_status["current"]
    
    has_passed_current = False
    
    for lvl in levels:
        lvl_name = lvl["name"]
        
        # Check if we should process this level on the current page
        config = ROADMAP_COORDS.get(lvl_name)
        if not config or config["page"] != page:
            if lvl_name == current_level_name:
                has_passed_current = True
            continue
            
        req_points = lvl["xp"]
        card_box = config["card_box"]
        req_box = config["req_box"]
        
        is_current = (lvl_name == current_level_name)
        is_unlocked = player_xp >= req_points
        
        # If the boxes are set properly
        if sum(card_box) > 0 and sum(req_box) > 0:
            
            if is_current:
                # 1. Brighter blue glow / border on card_box
                cx, cy, cw, ch = card_box
                draw.rounded_rectangle((cx, cy, cx+cw, cy+ch), radius=12, outline="#00ffff", width=5)
                # 2. Cover old text and write CURRENT LEVEL
                rx, ry, rw, rh = req_box
                draw.rectangle((rx, ry, rx+rw, ry+rh), fill=NAVY_BG_COLOR)
                draw_centered_text(draw, "CURRENT LEVEL", req_box, FONT_BOLD_PATH, 30, fill="#00ffcc")
                
            elif is_unlocked:
                # Unlocked but not current (past level)
                rx, ry, rw, rh = req_box
                draw.rectangle((rx, ry, rx+rw, ry+rh), fill=NAVY_BG_COLOR)
                draw_centered_text(draw, "UNLOCKED", req_box, FONT_BOLD_PATH, 30, fill="#a0a0a0")
                
            else:
                # Locked (future level)
                points_needed = req_points - player_xp
                rx, ry, rw, rh = req_box
                draw.rectangle((rx, ry, rx+rw, ry+rh), fill=NAVY_BG_COLOR)
                text = f"NEED {points_needed:,} POINTS\nTO UNLOCK"
                
                if lvl_name == "Country Grade A+":
                    text = "MAX LEVEL"
                    
                draw_centered_text(draw, text, req_box, FONT_BOLD_PATH, 25, fill="#ff4444" if points_needed > 0 else "white")
                
        if is_current:
            has_passed_current = True

    out = io.BytesIO()
    base.save(out, format="PNG")
    out.seek(0)
    return out
