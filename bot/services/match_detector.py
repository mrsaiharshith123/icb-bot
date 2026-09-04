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

def extract_hc_event_text(message: discord.Message) -> str:
    """Robust helper to extract all text from a message and its embeds for event matching."""
    parts = [message.content]
    for embed in message.embeds:
        if embed.title:
            parts.append(embed.title)
        if embed.description:
            parts.append(embed.description)
        if embed.author and embed.author.name:
            parts.append(embed.author.name)
        if embed.footer and embed.footer.text:
            parts.append(embed.footer.text)
        for field in embed.fields:
            if field.name:
                parts.append(field.name)
            if field.value:
                parts.append(field.value)
    
    # Normalize whitespace/case
    text = " ".join(filter(None, parts))
    text = re.sub(r'\s+', ' ', text).strip()
    return text.upper()

def is_catch_event(message: discord.Message) -> bool:
    """
    Checks if a message contains a catch opportunity event.
    """
    content = extract_hc_event_text(message)
    if "CHANCE OF WICKET" in content:
        # Debug logging as requested
        import logging
        logging.debug(f"[CATCH_EVENT] Matched CHANCE OF WICKET: {message.id} | channel: {message.channel.id} | author: {message.author.id}")
        return True
            
    return False

def parse_catch(message: discord.Message):
    """
    Parses the catch event and returns a dict with 'catcher_id' and 'batter_id'.
    """
    try:
        text = extract_hc_event_text(message)
        # Find all mentions in order
        mentions = re.findall(r"<@!?(\d+)>", text)
        
        if len(mentions) >= 2:
            catcher_id = mentions[0]
            batter_id = mentions[-1]
            
            # Sanity check: catcher and batter shouldn't be the same if there are multiple unique mentions
            if catcher_id == batter_id and len(set(mentions)) > 1:
                for m in mentions:
                    if m != catcher_id:
                        batter_id = m
                        break
                        
            return {
                "catcher_id": catcher_id,
                "batter_id": batter_id
            }
    except Exception as e:
        import logging
        logging.error(f"Failed to parse catch: {e}")
        
    return None

def is_catch_result(message: discord.Message) -> bool:
    """Checks if a message contains the result of a pending catch."""
    content = extract_hc_event_text(message)
    if "DROPPED THE CATCH" in content or "TOOK THE CATCH" in content or "DROPPED IT" in content or "CAUGHT IT" in content:
        import logging
        logging.debug(f"[CATCH_RESULT] Matched result: {message.id} | channel: {message.channel.id} | author: {message.author.id}")
        return True
            
    return False

def parse_catch_result(message: discord.Message) -> bool:
    """Returns True if the catch was taken, False if dropped."""
    content = extract_hc_event_text(message)
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
