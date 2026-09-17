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
            'bot.cogs.fantasy',
            'bot.cogs.teams'
        ]
        
        print("--- STARTUP DIAGNOSTICS ---")
        print(f"Message Content Intent: {self.intents.message_content}")
        print(f"Command Prefix: {self.command_prefix}")
        
        for cog in cogs:
            try:
                await self.load_extension(cog)
                print(f"Loaded {cog}")
            except Exception as e:
                print(f"Failed to load {cog}: {e}")
                
        # Register a simple ping command for testing
        @self.command(name="ping")
        async def _ping(ctx):
            await ctx.send("Pong")
            print("[DEBUG] Ping command executed.")
            
        is_profile_registered = 'profile' in [c.name for c in self.commands]
        print(f"Is 'profile' command registered? {is_profile_registered}")
        print("---------------------------")
        
        # Ensure DB indexes
        await setup_indexes()
        
        # Sync slash commands
        await self.tree.sync()
        print("Slash commands synced")

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print("HC Career Mode Support Bot is ready!")

    async def on_message(self, message: discord.Message):
        if not message.author.bot:
            print(f"[DEBUG-INCOMING-MSG] User ID: {message.author.id}, Is Bot: {message.author.bot}, Channel ID: {message.channel.id}, Content: {message.content!r}")
            
            if message.content.startswith("-profile"):
                print(f"[DEBUG-PROFILE-MATCH] Message starts with -profile! Content: {message.content!r}")
                
        await super().on_message(message)
        if not message.author.bot:
            print("[DEBUG-PROCESS] process_commands() has been called via super().on_message.")

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
