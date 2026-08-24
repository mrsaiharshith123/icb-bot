import discord
from discord.ext import commands
from discord import app_commands
from zoneinfo import ZoneInfo

from bot.database.db import upcoming_matches_col
from bot.utils.permissions import is_staff_ctx

class StaffInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot



    @commands.command(name="matchinfo", help="Get info for a specific match")
    @is_staff_ctx()
    async def matchinfo(self, ctx: commands.Context, match_number: int):
        guild_id = str(ctx.guild.id)
        
        match = await upcoming_matches_col.find_one({"guild_id": guild_id, "match_number": match_number})
        
        if not match:
            await ctx.send(f"❌ Match #{match_number} not found.")
            return
            
        status = match["status"]
        channel_ping = f"<#{match['channel_id']}>" if match['channel_id'] else "TBD"
        
        try:
            tz = ZoneInfo(match["timezone"])
        except Exception:
            tz = ZoneInfo("Asia/Kolkata")
            
        local_dt = match["scheduled_at"].astimezone(tz)
        date_str = local_dt.strftime("%d %b %Y")
        time_str = local_dt.strftime("%I:%M %p")
        
        embed = discord.Embed(
            title=f"🏏 MATCH #{match_number}",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Status", value=status, inline=False)
        embed.add_field(name="Schedule", value=f"📅 {date_str}\n⏰ {time_str}\n📍 {channel_ping}", inline=False)
        
        if status in ["RESULT_RECEIVED", "FINALIZED"]:
            res_link = "Not available"
            if match.get("result_message_id") and match.get("match_info_channel_id"):
                res_link = f"https://discord.com/channels/{guild_id}/{match['match_info_channel_id']}/{match['result_message_id']}"
                res_link = f"[View Result Message]({res_link})"
                
            embed.add_field(name="Result", value=res_link, inline=False)
            
            if status == "FINALIZED":
                embed.add_field(name="Finalized By", value=f"<@{match.get('finalized_by')}>", inline=False)
        
        if match.get("announcement_message_id") and match.get("announcement_channel_id"):
            ann_link = f"https://discord.com/channels/{guild_id}/{match['announcement_channel_id']}/{match['announcement_message_id']}"
            embed.add_field(name="Announcement", value=f"[View Announcement]({ann_link})", inline=False)
            
        await ctx.send(embed=embed)

    @commands.command(name="forcepromotions", help="Retroactively send promotion announcements for players who have already ranked up")
    @is_staff_ctx()
    async def forcepromotions(self, ctx: commands.Context):
        from bot.database.db import players_col, config_col
        from bot.services.career import get_career_level
        import asyncio
        
        await ctx.send("⏳ Scanning all players to check for valid promotions...")
        
        guild_id = str(ctx.guild.id)
        config = await config_col.find_one({"guild_id": guild_id})
        ranks_channel = None
        if config and config.get("player_ranks_channel_id"):
            ranks_channel = ctx.guild.get_channel(config["player_ranks_channel_id"])
            
        if not ranks_channel:
            await ctx.send("❌ **Player Ranks Channel** is not configured. Please run `!setup` first to set it!")
            return
            
        # Get all players
        cursor = players_col.find({"points": {"$gt": 0}})
        players = await cursor.to_list(length=None)
        
        promotions_sent = 0
        
        for p in players:
            discord_id = p["_id"]
            points = p.get("points", 0)
            level_data = get_career_level(points)
            
            # If they are anything above Local Team, they deserve a celebration!
            if level_data["current"] != "Local Team":
                member = ctx.guild.get_member(int(discord_id))
                if member:
                    # Give them the role if they don't have it
                    new_role = discord.utils.get(ctx.guild.roles, name=level_data["current"])
                    if new_role and new_role not in member.roles:
                        try:
                            await member.add_roles(new_role, reason="Retroactive career promotion")
                        except:
                            pass
                            
                    # Send announcement as plain text
                    promo_msg = f"🎉 **CAREER PROMOTION (Catch-up)**\n{member.mention} has leveled up to **{level_data['current'].upper()}**! *(Career Points: {points})*"
                    try:
                        await ranks_channel.send(promo_msg)
                        promotions_sent += 1
                        await asyncio.sleep(1) # Prevent rate limits
                    except discord.Forbidden:
                        pass
                        
        await ctx.send(f"✅ Successfully sent **{promotions_sent}** retroactive promotion announcements to {ranks_channel.mention}!")

    @commands.command(name="totalplayers", help="See the total number of players registered in the database")
    @is_staff_ctx()
    async def totalplayers(self, ctx: commands.Context):
        from bot.database.db import players_col
        total = await players_col.count_documents({})
        
        embed = discord.Embed(
            title="📊 Database Statistics",
            description=f"There are currently **{total}** total players registered in the database.",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(StaffInfo(bot))
