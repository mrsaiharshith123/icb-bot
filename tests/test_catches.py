import pytest
import discord
from unittest.mock import MagicMock
from bot.services.match_detector import (
    is_catch_event, parse_catch, is_catch_result, parse_catch_result, extract_hc_event_text
)
from bot.services.points_calculator import calculate_player_points
from bot.utils.events import is_janmashtami

def create_mock_message(content="", embeds=None, author_id=None):
    msg = MagicMock(spec=discord.Message)
    msg.content = content
    msg.embeds = embeds or []
    msg.author.id = author_id
    msg.author.bot = True
    msg.id = 12345
    msg.channel.id = 67890
    return msg

def create_mock_embed(title="", description="", fields=None):
    embed = MagicMock(spec=discord.Embed)
    embed.title = title
    embed.description = description
    embed.author.name = None
    embed.footer.text = None
    embed.fields = fields or []
    return embed

def create_mock_field(name, value):
    field = MagicMock()
    field.name = name
    field.value = value
    return field

def test_extract_hc_event_text():
    embed = create_mock_embed(title="TITLE", description="DESC", fields=[create_mock_field("F1", "V1")])
    msg = create_mock_message(content="CONTENT", embeds=[embed])
    text = extract_hc_event_text(msg)
    assert "CONTENT" in text
    assert "TITLE" in text
    assert "DESC" in text
    assert "F1" in text
    assert "V1" in text

def test_catch_opportunity_content():
    msg = create_mock_message(content="CHANCE OF WICKET! A catch opportunity is coming toward <@123>! If <@123> takes this catch, <@456> will be out!")
    assert is_catch_event(msg)
    data = parse_catch(msg)
    assert data["catcher_id"] == "123"
    assert data["batter_id"] == "456"

def test_catch_opportunity_embed_title():
    embed = create_mock_embed(title="CHANCE OF WICKET!", description="A catch opportunity is coming toward <@111>! If <@111> takes this catch, <@222> will be out!")
    msg = create_mock_message(embeds=[embed])
    assert is_catch_event(msg)
    data = parse_catch(msg)
    assert data["catcher_id"] == "111"
    assert data["batter_id"] == "222"

def test_catch_opportunity_embed_description():
    embed = create_mock_embed(description="CHANCE OF WICKET! A catch opportunity is coming toward <@333>! If <@333> takes this catch, <@444> will be out!")
    msg = create_mock_message(embeds=[embed])
    assert is_catch_event(msg)
    data = parse_catch(msg)
    assert data["catcher_id"] == "333"
    assert data["batter_id"] == "444"

def test_took_the_catch_content():
    msg = create_mock_message(content="TOOK THE CATCH!")
    assert is_catch_result(msg)
    assert parse_catch_result(msg) is True

def test_took_the_catch_embed():
    embed = create_mock_embed(description="<@123> TOOK THE CATCH!")
    msg = create_mock_message(embeds=[embed])
    assert is_catch_result(msg)
    assert parse_catch_result(msg) is True

def test_dropped_the_catch_content():
    msg = create_mock_message(content="BOZO DROPPED THE CATCH")
    assert is_catch_result(msg)
    assert parse_catch_result(msg) is False

def test_dropped_the_catch_embed():
    embed = create_mock_embed(description="BOZO DROPPED THE CATCH")
    msg = create_mock_message(embeds=[embed])
    assert is_catch_result(msg)
    assert parse_catch_result(msg) is False

def test_janmashtami_double_points(monkeypatch):
    monkeypatch.setattr("bot.utils.events.is_janmashtami", lambda: True)
    stats = {
        "runs": 1,
        "balls_faced": 1,
        "runs_conceded": 0,
        "balls_bowled": 0,
        "wickets": 0,
        "catches": 1,
        "catch_drops": 0,
        "out": False
    }
    # 1 run = +1
    # 1 catch = +10
    # Total positive = 11. Janmashtami = 22.
    pts = calculate_player_points(stats)
    assert pts == 22

def test_janmashtami_double_deductions(monkeypatch):
    monkeypatch.setattr("bot.utils.events.is_janmashtami", lambda: True)
    stats = {
        "runs": 0,
        "balls_faced": 1,
        "runs_conceded": 0,
        "balls_bowled": 0,
        "wickets": 0,
        "catches": 0,
        "catch_drops": 0,
        "out": True
    }
    # Duck = -20. Should double to -40.
    pts = calculate_player_points(stats)
    assert pts == -40

def test_historical_non_event_points(monkeypatch):
    monkeypatch.setattr("bot.utils.events.is_janmashtami", lambda: False)
    stats = {
        "runs": 1,
        "balls_faced": 1,
        "runs_conceded": 0,
        "balls_bowled": 0,
        "wickets": 0,
        "catches": 1,
        "catch_drops": 0,
        "out": False
    }
    # 1 run = +1, 1 catch = +10 -> Total = 11.
    pts = calculate_player_points(stats)
    assert pts == 11
