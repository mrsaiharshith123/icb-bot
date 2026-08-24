import io
from bot.services.roadmap_card import generate_roadmap_page

def run_tests():
    test_cases = [
        {"name": "0xp_player", "xp": 0},
        {"name": "mid_player", "xp": 1400},
        {"name": "high_player", "xp": 35000},
        {"name": "max_player", "xp": 55000}
    ]
    
    for case in test_cases:
        xp = case["xp"]
        name = case["name"]
        
        try:
            # Test page 1
            print(f"Generating {name} Page 1 (XP: {xp})...")
            out_p1 = generate_roadmap_page(xp, 1)
            with open(f"test_roadmap_p1_{name}.png", "wb") as f:
                f.write(out_p1.read())
                
            # Test page 2
            print(f"Generating {name} Page 2 (XP: {xp})...")
            out_p2 = generate_roadmap_page(xp, 2)
            with open(f"test_roadmap_p2_{name}.png", "wb") as f:
                f.write(out_p2.read())
                
            print(f"Successfully generated tests for {name}.")
        except Exception as e:
            print(f"Failed to generate tests for {name}: {e}")

if __name__ == "__main__":
    run_tests()
