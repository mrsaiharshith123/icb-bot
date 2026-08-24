from bot.services.stats_parser import parse_raw_statistics

def test_parse_valid_stats():
    raw = """
    1269377591631024334, 0, 1, 29, 9, 1, 0
    1410975498510532789, 5, 3, 26, 6, 1, 0
    1076152409811853402, 11, 5, 16, 6, 1, 1
    """
    result = parse_raw_statistics(raw)
    assert len(result) == 3
    
    # Check first player
    p1 = result[0]
    assert p1["discord_id"] == "1269377591631024334"
    assert p1["runs"] == 0
    assert p1["balls_faced"] == 1
    assert p1["runs_conceded"] == 29
    assert p1["balls_bowled"] == 9
    assert p1["wickets"] == 1
    assert p1["out"] is True  # 0 is OUT
    
    # Check third player
    p3 = result[2]
    assert p3["out"] is False  # 1 is NOT OUT
    
def test_parse_with_codeblock():
    raw = "```text\n1269377591631024334, 10, 1, 0, 0, 0, 0\n```"
    result = parse_raw_statistics(raw)
    assert len(result) == 1
    assert result[0]["runs"] == 10

def test_parse_invalid_fields():
    # Only 6 fields
    raw = "1269377591631024334, 0, 1, 29, 9, 1\n1076152409811853402, 11, 5, 16, 6, 1, 1"
    result = parse_raw_statistics(raw)
    assert len(result) == 1
    assert result[0]["discord_id"] == "1076152409811853402"
