import discord
from discord.ext import commands
import random
import time
import aiohttp
from bot.config import ORIGINAL_HC_BOT_ID

class ChatListener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Cooldown per channel: channel_id -> float (timestamp)
        self.cooldowns = {}
        self.COOLDOWN_SECONDS = 300 # 5 minutes between random reactions in the same channel

    def get_gif_for_category(self, category: str):
        # A dictionary of contextual cute/funny/troll cat gifs
        gifs = {
            "duck": ["https://klipy.com/gifs/yuji-11", "https://tenor.com/view/cat-laugh-funny-cat-lol-laughing-cat-gif-24874457", "https://tenor.com/view/haha-cat-laughing-point-at-you-gif-23743513"],
            "wicket": ["https://klipy.com/gifs/ghee-khatam-mountolivet", "https://tenor.com/view/cat-punch-fight-slap-gif-25595998"],
            "catch_taken": ["https://tenor.com/view/ninja-cat-catch-jump-gif-24956799", "https://tenor.com/view/cat-snatch-mine-fast-gif-23635360"],
            "catch_dropped": ["https://tenor.com/view/cat-fail-clumsy-drop-gif-19777558", "https://tenor.com/view/cat-facepalm-disappointed-sigh-gif-21151609", "https://tenor.com/view/bruh-cat-disappointed-bruh-gif-25032543"],
            "six": ["https://tenor.com/view/cat-shock-surprised-omg-wow-gif-20228189", "https://tenor.com/view/cat-pog-champ-poggers-gif-19961608"],
            "fifty": ["https://tenor.com/view/cat-vibing-jamming-music-gif-18451152", "https://tenor.com/view/cat-nod-yes-approve-gif-22071871"],
            "century": ["https://tenor.com/view/cat-cool-sunglasses-swag-gif-19483321", "https://tenor.com/view/cat-dance-party-celebrate-gif-21151608"],
            "hattrick": ["https://tenor.com/view/discord-logo-sweaty-blush-gif-17329028", "https://tenor.com/view/mind-blown-cat-explode-gif-23253258"],
            "innings_break": ["https://tenor.com/view/cat-sleep-tired-nap-gif-24654923", "https://tenor.com/view/cat-drink-water-thirsty-gif-21921312"],
            "match_start": ["https://tenor.com/view/cat-typing-hacker-ready-gif-21344445", "https://tenor.com/view/cat-locked-in-stare-gif-25032542"],
            "match_end": ["https://tenor.com/view/cat-kiss-love-cute-gif-20076211", "https://tenor.com/view/cat-thumbs-up-good-job-gif-24443916"]
        }
        
        category_gifs = gifs.get(category, gifs["fifty"]) # default fallback
        return random.choice(category_gifs)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        is_og_bot = (ORIGINAL_HC_BOT_ID and message.author.id == ORIGINAL_HC_BOT_ID)
        
        if message.author.bot and not is_og_bot:
            return
            
        content = message.content.lower()
        if is_og_bot:
            for embed in message.embeds:
                if embed.description:
                    content += " " + embed.description.lower()
                if embed.title:
                    content += " " + embed.title.lower()
        
        # 1. Direct responses without cooldown
        if "mr player" in content:
            # The user specifically requested this:
            # "make a newthing like if i ping my bot and ask hey cutie who made fastest 50 here and it should reply mr player"
            if self.bot.user.mentioned_in(message) or "fastest 50" in content:
                await message.reply("🐐 **MR PLAYER** is the GOAT!")
                return
                
        # 2. Random GIF reactions (Subject to cooldown & probability)
        channel_id = message.channel.id
        last_time = self.cooldowns.get(channel_id, 0)
        current_time = time.time()
        
        if not is_og_bot:
            if current_time - last_time < self.COOLDOWN_SECONDS:
                return
                
            # Define triggers
            # Only 20% chance to trigger even if off cooldown, so it doesn't get annoying
            if random.random() > 0.20:
                return
            
        trigger_category = None
        if "hat-trick" in content or "hattrick" in content:
            trigger_category = "hattrick"
        elif "match started" in content or "toss won by" in content:
            trigger_category = "match_start"
        elif "innings break" in content:
            trigger_category = "innings_break"
        elif "raw statistics of the match" in content or "match over" in content or "match ended" in content:
            trigger_category = "match_end"
        elif "duck" in content or "0" in content.split():
            trigger_category = "duck"
        elif "century" in content or "100" in content.split():
            trigger_category = "century"
        elif "fifty" in content or "50" in content.split():
            trigger_category = "fifty"
        elif "six" in content or "6" in content.split():
            trigger_category = "six"
        elif "batter out!" in content:
            trigger_category = "wicket"
            
        if trigger_category:
            gif_url = self.get_gif_for_category(trigger_category)
            if gif_url:
                if not is_og_bot:
                    self.cooldowns[channel_id] = current_time
                await message.channel.send(gif_url)

async def setup(bot):
    await bot.add_cog(ChatListener(bot))
