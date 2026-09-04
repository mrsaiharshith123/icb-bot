import discord
from discord.ext import commands
import os
from bot.config import DISCORD_TOKEN
from bot.database.db import setup_indexes

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class HCCareerBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="-", intents=intents, help_command=None)
        
    async def setup_hook(self):
        # Load cogs
        cogs = [
            'bot.cogs.profile',
            'bot.cogs.leaderboard',
            'bot.cogs.matches',
            'bot.cogs.roadmap',
            'bot.cogs.setup',
            'bot.cogs.announcements',
            'bot.cogs.staff_info',
            'bot.cogs.ai_chat',
            'bot.cogs.economy',
            'bot.cogs.daily',
            'bot.cogs.achievements',
            'bot.cogs.intelligence',
            'bot.cogs.help',
            'bot.cogs.fun',
            'bot.cogs.chat_listener',
            'bot.cogs.fantasy'
        ]
        for cog in cogs:
            try:
                await self.load_extension(cog)
                print(f"Loaded {cog}")
            except Exception as e:
                print(f"Failed to load {cog}: {e}")
        
        # Ensure DB indexes
        await setup_indexes()
        
        # Sync slash commands
        await self.tree.sync()
        print("Slash commands synced")

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print("HC Career Mode Support Bot is ready!")

    async def on_message(self, message: discord.Message):
        if "profile" in message.content.lower():
            print(f"[DEBUG-ON-MESSAGE] Received from {message.author.name}: {message.content!r}")
        await super().on_message(message)

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.send("❌ You don't have enough permissions to use this command.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"⚠️ **Missing Argument:** `{error.param.name}` is required.\nUsage: `{ctx.prefix}{ctx.command.name} {ctx.command.signature}`")
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"⚠️ **Bad Argument:** Please provide the correct type of value.\nUsage: `{ctx.prefix}{ctx.command.name} {ctx.command.signature}`")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ **Cooldown:** Please wait {error.retry_after:.1f} seconds before using this command again.")
        elif isinstance(error, commands.CommandNotFound):
            pass  # Ignore invalid commands
        else:
            print(f"Ignoring exception in command {ctx.command}: {error}")

if __name__ == "__main__":
    if not DISCORD_TOKEN or DISCORD_TOKEN == "your_bot_token_here":
        print("Error: DISCORD_TOKEN environment variable not set in .env")
    else:
        bot = HCCareerBot()
        bot.run(DISCORD_TOKEN)
