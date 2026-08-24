import discord
from discord.ext import commands
import os
from google import genai

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Configure Gemini
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if gemini_api_key:
            self.client = genai.Client(api_key=gemini_api_key)
        else:
            self.client = None
            print("WARNING: GEMINI_API_KEY not found in environment. AI features disabled.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore our own messages
        if message.author == self.bot.user:
            return
            
        # Only respond if the bot is explicitly mentioned
        if not self.bot.user.mentioned_in(message):
            return
            
        # Ignore @everyone or @here mentions
        if message.mention_everyone:
            return

        # Hardcoded joke response for "fastest 50"
        content = message.clean_content.lower()
        if "fastest 50" in content:
            await message.reply("Mr Player made the fastest 50 here! 🏏🔥")
            return

        # Use Gemini AI for everything else if configured
        if self.client:
            try:
                prompt = message.clean_content.replace(f"@{message.guild.me.display_name}", "").strip()
                if not prompt:
                    prompt = "Hello!"
                    
                system_instruction = (
                    "You are the ICB Career Mode Bot, a friendly, hype, and funny assistant for a Discord Cricket server. "
                    "You track player stats, catches, hat-tricks, and ranks. "
                    "Keep your responses short, funny, and cricket-themed. Use emojis."
                )
                
                async with message.channel.typing():
                    # Generate response using new API
                    response = await self.bot.loop.run_in_executor(
                        None, 
                        lambda: self.client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=f"{system_instruction}\n\nUser asked: {prompt}"
                        )
                    )
                    
                    if response.text:
                        await message.reply(response.text[:2000])
            except Exception as e:
                print(f"AI Error: {e}")

async def setup(bot):
    await bot.add_cog(AIChat(bot))
