import re
import discord

def is_match_start(message: discord.Message) -> bool:
    """
    Checks if a message from Original HC Bot indicates a match start.
    It deliberately stops reading before the username so it works for ANY player.
    """
    phrases = [
        "A game of ELITE Multiplayer cricket has been started by",
        "A game of Hand Cricket Multiplayer has been started by"
    ]
    
    for phrase in phrases:
        if phrase in message.content:
            return True
            
        for embed in message.embeds:
            if embed.description and phrase in embed.description:
                return True
            if embed.title and phrase in embed.title:
                return True
            for field in embed.fields:
                if field.name and phrase in field.name:
                    return True
                if field.value and phrase in field.value:
                    return True
                    
    return False

def is_hattrick_event(message: discord.Message) -> bool:
    """Checks if a message contains a hattrick event."""
    phrase = "AND IT'S AN HAT-TRICK FOR"
    if phrase in message.content.upper():
        return True
    for embed in message.embeds:
        if embed.description and phrase in embed.description.upper():
            return True
        if embed.title and phrase in embed.title.upper():
            return True
    return False

def parse_hattrick(message: discord.Message):
    """Parses the hattrick event and returns the player ID."""
    try:
        text = message.content + "\n"
        for embed in message.embeds:
            if embed.description:
                text += embed.description + "\n"
                
        mentions = re.findall(r"<@!?(\d+)>", text)
        if mentions:
            return mentions[0]
    except Exception as e:
        print(f"Failed to parse hattrick: {e}")
    return None

def is_catch_event(message: discord.Message) -> bool:
    """
    Checks if a message contains a catch event.
    Checks both embeds and plain text (for testing).
    """
    content = message.content.upper()
    if "CHANCE OF WICKET" in content:
        return True
        
    for embed in message.embeds:
        # Check title or description
        if embed.title and "CHANCE OF WICKET" in embed.title.upper():
            return True
        if embed.description and "CHANCE OF WICKET" in embed.description.upper():
            return True
        for field in embed.fields:
            if field.name and "CHANCE OF WICKET" in field.name.upper():
                return True
            if field.value and "CHANCE OF WICKET" in field.value.upper():
                return True
            
    return False

def parse_catch(message: discord.Message):
    """
    Parses the catch event and returns a dict with 'catcher_id' and 'batter_id'.
    Since discord user mentions are formatted as <@123456789>, we can extract IDs.
    Returns None if parsing fails.
    """
    try:
        # Extract text from content and embeds
        text = message.content + "\n"
        for embed in message.embeds:
            if embed.description:
                text += embed.description + "\n"
            for field in embed.fields:
                if field.name:
                    text += field.name + "\n"
                if field.value:
                    text += field.value + "\n" 
        # A catch opportunity is coming toward <@123456>!
        # If <@123456> takes this catch, <@654321> will be out!
        
        # Find all mentions in order
        mentions = re.findall(r"<@!?(\d+)>", text)
        
        if len(mentions) >= 2:
            # The catcher is mentioned first (and often twice). The batter is the last mention.
            catcher_id = mentions[0]
            # To handle both "coming toward @X! If @X takes... @Y is out" (3 mentions)
            # and just "@X caught @Y" (2 mentions), the batter is usually the last one.
            batter_id = mentions[-1]
            
            # Sanity check: catcher and batter shouldn't be the same if there are multiple unique mentions
            if catcher_id == batter_id and len(set(mentions)) > 1:
                # If for some reason the last mention is same as first, find the different one
                for m in mentions:
                    if m != catcher_id:
                        batter_id = m
                        break
                        
            return {
                "catcher_id": catcher_id,
                "batter_id": batter_id
            }
    except Exception as e:
        print(f"Failed to parse catch: {e}")
        
    return None

def is_catch_result(message: discord.Message) -> bool:
    """Checks if a message contains the result of a pending catch."""
    content = message.content.upper()
    if "DROPPED THE CATCH" in content or "TOOK THE CATCH" in content or "DROPPED IT" in content or "CAUGHT IT" in content:
        return True
        
    for embed in message.embeds:
        desc = (embed.description or "").upper()
        if "DROPPED THE CATCH" in desc or "TOOK THE CATCH" in desc or "DROPPED IT" in desc or "CAUGHT IT" in desc:
            return True
        for field in embed.fields:
            name = (field.name or "").upper()
            val = (field.value or "").upper()
            if "DROPPED THE CATCH" in name or "TOOK THE CATCH" in name or "DROPPED IT" in name or "CAUGHT IT" in name:
                return True
            if "DROPPED THE CATCH" in val or "TOOK THE CATCH" in val or "DROPPED IT" in val or "CAUGHT IT" in val:
                return True
            
    return False

def parse_catch_result(message: discord.Message) -> bool:
    """Returns True if the catch was taken, False if dropped."""
    content = message.content.upper()
    for embed in message.embeds:
        content += " " + (embed.description or "").upper()
        for field in embed.fields:
            content += " " + (field.name or "").upper()
            content += " " + (field.value or "").upper()
        
    if "TOOK THE CATCH" in content or "CAUGHT IT" in content:
        return True
    return False

def is_raw_statistics(message: discord.Message) -> bool:
    """
    Checks if the message looks like the final raw statistics block.
    We'll do a simple check: multiple lines of comma-separated numbers starting with a Discord ID.
    """
    content = message.content or ""
    
    # Check embeds if not in content
    if "```" not in content:
        for embed in message.embeds:
            if embed.description and "```" in embed.description:
                content += "\n" + embed.description
                
    if "```" not in content:
        return False
        
    # Remove markdown code blocks like parse_raw_statistics does
    content = re.sub(r"```[a-zA-Z]*\s*\n(.*?)```", r"\1", content, flags=re.DOTALL)
        
    lines = content.strip().split("\n")
    if not lines:
        return False
        
    for line in lines:
        parts = line.split(",")
        if len(parts) == 7:
            try:
                # Check if first part is a valid discord ID
                discord_id = parts[0].strip()
                if not discord_id.isdigit() or len(discord_id) < 15:
                    continue
                    
                # Ensure all parts are integers
                [int(p.strip()) for p in parts]
                
                # Ensure last part is 0 or 1 (out status)
                if int(parts[6].strip()) in (0, 1):
                    return True
            except ValueError:
                continue
                
    return False
