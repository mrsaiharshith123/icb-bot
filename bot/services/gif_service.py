import json
import os
import random

GIF_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'gifs.json')

def get_random_gif(category: str) -> str:
    """Returns a random GIF URL for a given category, or None if category doesn't exist."""
    if not os.path.exists(GIF_FILE):
        return None
        
    try:
        with open(GIF_FILE, 'r', encoding='utf-8') as f:
            gifs = json.load(f)
            
        category_gifs = gifs.get(category.lower(), [])
        if not category_gifs:
            return None
            
        return random.choice(category_gifs)
    except Exception as e:
        print(f"Error loading GIF for category {category}: {e}")
        return None
