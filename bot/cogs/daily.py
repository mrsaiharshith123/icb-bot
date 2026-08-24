import discord
from discord.ext import commands
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from bot.database.players import get_player, players_col
from bot.database.economy import add_coins

class Daily(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="daily", description="Claim your daily HC Coins reward")
    async def daily_cmd(self, ctx):
        discord_id = str(ctx.author.id)
        player = await get_player(discord_id)
        
        economy = player.get("economy", {})
        last_daily = economy.get("last_daily")
        current_streak = economy.get("daily_streak", 0)
        highest_streak = economy.get("highest_streak", 0)
        
        now = datetime.now(ZoneInfo("UTC"))
        
        if last_daily:
            # Check if 24 hours have passed
            time_since = now - last_daily.replace(tzinfo=ZoneInfo("UTC")) if last_daily.tzinfo is None else now - last_daily
            if time_since < timedelta(hours=24):
                time_left = timedelta(hours=24) - time_since
                hours, remainder = divmod(int(time_left.total_seconds()), 3600)
                minutes, _ = divmod(remainder, 60)
                await ctx.send(f"⏳ You have already claimed your daily reward! Please wait **{hours}h {minutes}m**.")
                return
                
            # Check if streak broke (more than 48 hours)
            if time_since > timedelta(hours=48):
                current_streak = 0
                
        current_streak += 1
        if current_streak > highest_streak:
            highest_streak = current_streak
            
        base_reward = 1000
        streak_bonus = min(current_streak * 100, 2000) # Max 2000 bonus
        total_reward = base_reward + streak_bonus
        
        # Update DB
        await players_col.update_one(
            {"_id": discord_id},
            {
                "$set": {
                    "economy.last_daily": now,
                    "economy.daily_streak": current_streak,
                    "economy.highest_streak": highest_streak
                },
                "$inc": {
                    "economy.coins": total_reward
                }
            }
        )
        
        embed = discord.Embed(
            title="🎁 Daily Reward Claimed",
            description=f"You received **{total_reward:,} HC Coins** 🪙!",
            color=discord.Color.gold()
        )
        embed.add_field(name="Base Reward", value=f"{base_reward:,}", inline=True)
        embed.add_field(name="Streak Bonus", value=f"+{streak_bonus:,}", inline=True)
        embed.set_footer(text=f"Current Streak: {current_streak} days | Highest: {highest_streak} days")
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Daily(bot))
