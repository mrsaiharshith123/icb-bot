import discord
from discord.ext import commands
from bot.services.gif_service import get_random_gif

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def send_gif(self, ctx, category: str, title: str):
        gif_url = get_random_gif(category)
        if not gif_url:
            await ctx.send(f"❌ No GIFs found for category: `{category}`")
            return
            
        embed = discord.Embed(title=title, color=discord.Color.random())
        embed.set_image(url=gif_url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="six", description="Hit a massive six!")
    async def six_cmd(self, ctx):
        await self.send_gif(ctx, "six", "🏏 OUT OF THE PARK!")

    @commands.hybrid_command(name="wicket", description="Take a crucial wicket!")
    async def wicket_cmd(self, ctx):
        await self.send_gif(ctx, "wicket", "🎯 BOWLED HIM!")

    @commands.hybrid_command(name="duck", description="Quack Quack")
    async def duck_cmd(self, ctx):
        await self.send_gif(ctx, "duck", "🦆 QUACK QUACK!")

    @commands.hybrid_command(name="goat", aliases=["mrplayer"], description="Acknowledge greatness")
    async def goat_cmd(self, ctx):
        await self.send_gif(ctx, "goat", "🐐 THE GOAT!")

    @commands.hybrid_command(name="gif", description="Send a random GIF by category")
    async def gif_cmd(self, ctx, category: str):
        await self.send_gif(ctx, category.lower(), f"🎬 {category.capitalize()}")

async def setup(bot):
    await bot.add_cog(Fun(bot))
