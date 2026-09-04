import discord
from discord import app_commands
from discord.ext import commands
import io
from bot.database.players import get_player
from bot.database.db import matches_col, players_col
from bot.services.career import get_career_level
from bot.services.profile_card import generate_profile_card
from bot.utils.permissions import is_staff_ctx

class ProfileView(discord.ui.View):
    def __init__(self, target_user: discord.User):
        super().__init__(timeout=300)
        self.target_user = target_user

    @discord.ui.button(label="🏆 Career", style=discord.ButtonStyle.primary)
    async def career_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # We can implement a text breakdown of career later
        await interaction.response.send_message(f"Displaying Career for {self.target_user.display_name}...", ephemeral=True)

    @discord.ui.button(label="🃏 Fantasy", style=discord.ButtonStyle.secondary)
    async def fantasy_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Fantasy system coming soon!", ephemeral=True)

    @discord.ui.button(label="💰 Economy", style=discord.ButtonStyle.success)
    async def economy_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        from bot.database.economy import get_balance
        from bot.database.players import get_player
        
        discord_id = str(self.target_user.id)
        balance = await get_balance(discord_id)
        player = await get_player(discord_id)
        streak = player.get("economy", {}).get("daily_streak", 0)
        
        embed = discord.Embed(title=f"💰 {self.target_user.display_name}'s Economy", color=discord.Color.gold())
        embed.add_field(name="HC Coins", value=f"{balance:,} 🪙")
        embed.add_field(name="Daily Streak", value=f"🔥 {streak} days")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="📊 Stats", style=discord.ButtonStyle.secondary)
    async def stats_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"Detailed Stats coming soon!", ephemeral=True)
        
    @discord.ui.button(label="🏅 Achievements", style=discord.ButtonStyle.secondary)
    async def achievements_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Trigger the achievements command logic
        from bot.cogs.achievements import ACHIEVEMENTS_DB
        from bot.database.players import get_player
        
        player = await get_player(str(self.target_user.id))
        unlocked = player.get("career", {}).get("achievements", [])
        
        embed = discord.Embed(title=f"🏅 {self.target_user.display_name}'s Achievements", color=discord.Color.gold())
        if not unlocked:
            embed.description = "No achievements unlocked yet."
        else:
            embed.description = f"**Unlocked:** {len(unlocked)} / {len(ACHIEVEMENTS_DB)}\n\n"
            for key in unlocked:
                if key in ACHIEVEMENTS_DB:
                    ach = ACHIEVEMENTS_DB[key]
                    embed.description += f"**{ach['name']}**\n*{ach['desc']}*\n\n"
        await interaction.response.send_message(embed=embed, ephemeral=True)

class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="profile", aliases=["me"], description="View your dynamic Career Mode profile card")
    async def profile(self, ctx: commands.Context, user: discord.User = None):
        await ctx.defer()
        target = user or ctx.author
        discord_id = str(target.id)
        
        player_data = await get_player(discord_id)
        player_data["name"] = target.display_name
        
        # 1. Fetch avatar bytes
        avatar_bytes = b""
        avatar_asset = target.display_avatar or target.default_avatar
        if avatar_asset:
            try:
                avatar_bytes = await avatar_asset.read()
            except Exception as e:
                print(f"Failed to fetch display avatar, falling back to default: {e}")
                try:
                    avatar_bytes = await target.default_avatar.read()
                except Exception as ex:
                    print(f"Failed to fetch default avatar as well: {ex}")

        # 2. Get career level
        xp = player_data.get("points", 0)
        player_data["career"] = get_career_level(xp)
        
        # 3. Calculate Season Rank
        cursor = players_col.find({"points": {"$gt": xp}})
        higher_players = await cursor.to_list(length=None)
        season_rank = len(higher_players) + 1
        rank_data = {"season_rank": season_rank}
        
        # 4. Fetch last 5 finalized matches for form
        cursor = matches_col.find(
            {"status": "FINALIZED", "players.discord_id": discord_id}
        ).sort("started_at", -1).limit(5)
        matches_list = await cursor.to_list(length=5)
        
        form_matches = []
        for m in matches_list:
            p_stats = next((p for p in m["players"] if p["discord_id"] == discord_id), None)
            if p_stats:
                form_matches.append(p_stats)
                
        # Generate Pillow card
        card_io = generate_profile_card(player_data, rank_data, form_matches, avatar_bytes)
        
        # Send
        file = discord.File(card_io, filename="profile.png")
        view = ProfileView(target)
        await ctx.send(file=file, view=view)

    @commands.command(name="deduct", help="Manually deduct points from a player (Bot Dev only)")
    @commands.is_owner()
    async def deduct(self, ctx: commands.Context, user: discord.User, amount: int, *, reason: str):
        from datetime import datetime, timezone
        from bot.utils.events import is_janmashtami

        if amount <= 0:
            await ctx.send("❌ Amount must be a positive number to deduct.")
            return
            
        if is_janmashtami():
            amount *= 2
            reason += " (Janmashtami 2x Penalty)"
            
        discord_id = str(user.id)
        player = await get_player(discord_id)
        
        penalty_log = {
            "amount": amount,
            "reason": reason,
            "date": datetime.now(timezone.utc).isoformat(),
            "given_by": str(ctx.author.id)
        }
        
        await players_col.update_one(
            {"_id": discord_id},
            {
                "$inc": {"points": -amount},
                "$push": {"penalties": penalty_log}
            }
        )
        
        new_points = player.get("points", 0) - amount
        
        embed = discord.Embed(
            title="📉 Penalty Applied",
            description=f"**{amount} points** have been deducted from {user.mention}.",
            color=discord.Color.red()
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="New Career Points", value=str(new_points), inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name="addpoints", help="Manually add points to a player (Bot Dev only)")
    @commands.is_owner()
    async def addpoints(self, ctx: commands.Context, user: discord.User, amount: int, *, reason: str):
        if amount <= 0:
            await ctx.send("❌ Amount must be a positive number to add.")
            return
            
        discord_id = str(user.id)
        player = await get_player(discord_id)
        
        await players_col.update_one(
            {"_id": discord_id},
            {
                "$inc": {"points": amount}
            }
        )
        
        new_points = player.get("points", 0) + amount
        
        embed = discord.Embed(
            title="📈 Points Added",
            description=f"**{amount} points** have been added to {user.mention}.",
            color=discord.Color.green()
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="New Career Points", value=str(new_points), inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name="penalties", help="View all manual penalties applied to a player")
    async def penalties(self, ctx: commands.Context, user: discord.User = None):
        target = user or ctx.author
        discord_id = str(target.id)
        
        player = await get_player(discord_id)
        penalties = player.get("penalties", [])
        
        if not penalties:
            await ctx.send(f"✅ {target.mention} has a clean record! (No manual penalties applied)")
            return
            
        embed = discord.Embed(
            title=f"⚠️ Penalty Log: {target.display_name}",
            color=discord.Color.orange()
        )
        
        total_deducted = sum(p.get("amount", 0) for p in penalties)
        
        # Show last 10 penalties
        for i, p in enumerate(reversed(penalties[-10:])):
            amount = p.get("amount", 0)
            reason = p.get("reason", "Unknown")
            date_str = p.get("date", "")[:10] if p.get("date") else "Unknown Date"
            
            embed.add_field(
                name=f"-{amount} Points",
                value=f"**Reason:** {reason}\n*Date: {date_str}*",
                inline=False
            )
            
        if len(penalties) > 10:
            embed.set_footer(text=f"Showing latest 10 of {len(penalties)} penalties. Total deducted: {total_deducted}")
        else:
            embed.set_footer(text=f"Total points deducted: {total_deducted}")
            
        await ctx.send(embed=embed)

    @commands.command(name="manualstats", help="Add manual stats: !manualstats @player <catches> <drops> <hattricks> <mvps>")
    @is_staff_ctx()
    async def manualstats(self, ctx: commands.Context, target: discord.Member, catches: int = 0, drops: int = 0, hattricks: int = 0, mvps: int = 0):
        from bot.database.players import update_player_stats, get_player
        from datetime import datetime, timezone
        
        if catches == 0 and drops == 0 and hattricks == 0 and mvps == 0:
            await ctx.send("❌ You must specify at least one stat to add. Example: `!manualstats @player 1 0 0 1` (1 catch, 0 drops, 0 hattricks, 1 mvp).")
            return
            
        discord_id = str(target.id)
        
        point_change = (catches * 10) + (drops * -10) + (hattricks * 20) + (mvps * 20)
        
        stats_update = {}
        if catches > 0: stats_update["fielding.catches"] = catches
        if drops > 0: stats_update["fielding.catch_drops"] = drops
        if hattricks > 0: stats_update["awards.hattricks"] = hattricks
        if mvps > 0: stats_update["awards.mvp"] = mvps
        stats_update["points"] = point_change
        
        push_updates = None
        if drops > 0:
            push_updates = {
                "penalties": {
                    "amount": drops * 10,
                    "reason": f"Manual Catch Drop ({drops}x)",
                    "date": datetime.now(timezone.utc).isoformat(),
                    "given_by": str(ctx.author.id)
                }
            }
            
        await update_player_stats(discord_id, stats_update, push_updates=push_updates)
        player_data = await get_player(discord_id)
        current_points = player_data.get("points", 0)
        
        desc = []
        if catches > 0: desc.append(f"**{catches}** Catches")
        if drops > 0: desc.append(f"**{drops}** Catch Drops")
        if hattricks > 0: desc.append(f"**{hattricks}** Hattricks")
        if mvps > 0: desc.append(f"**{mvps}** MVPs")
        
        embed = discord.Embed(
            title=f"✅ Updated Stats: {target.display_name}",
            description=f"Added {', '.join(desc)} to {target.mention}.",
            color=discord.Color.green()
        )
        embed.add_field(name="Points Change", value=f"{point_change:+d} points", inline=True)
        embed.add_field(name="New Total Points", value=f"**{current_points}** points", inline=True)
        
        await ctx.send(embed=embed)

    @commands.command(name="batchstats", help="Batch add manual stats. Format each line: @player catches=1 drops=2 hattricks=0 mvps=1")
    @is_staff_ctx()
    async def batchstats(self, ctx: commands.Context, *, raw_text: str = None):
        from bot.database.players import update_player_stats, get_player
        from datetime import datetime, timezone
        import re
        
        if not raw_text:
            if ctx.message.reference and ctx.message.reference.message_id:
                try:
                    ref_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                    raw_text = ref_msg.content
                except discord.NotFound:
                    await ctx.send("❌ Could not find the replied message.")
                    return
            else:
                await ctx.send("❌ Provide the text or reply to a message containing the stats.")
                return
                
        lines = raw_text.strip().split('\n')
        updated_count = 0
        
        for line in lines:
            line = line.strip().lower()
            if not line: continue
            
            # Extract mentions (could be <@123> or <@!123>)
            mention_match = re.search(r'<@!?(\d+)>', line)
            if not mention_match:
                continue
                
            discord_id = mention_match.group(1)
            
            # Find values using regex
            c_match = re.search(r'(?:c|catches|catch)\s*=\s*(\d+)', line)
            d_match = re.search(r'(?:d|drops|drop)\s*=\s*(\d+)', line)
            h_match = re.search(r'(?:h|hattricks|hattrick)\s*=\s*(\d+)', line)
            m_match = re.search(r'(?:m|mvps|mvp)\s*=\s*(\d+)', line)
            
            catches = int(c_match.group(1)) if c_match else 0
            drops = int(d_match.group(1)) if d_match else 0
            hattricks = int(h_match.group(1)) if h_match else 0
            mvps = int(m_match.group(1)) if m_match else 0
            
            if catches == 0 and drops == 0 and hattricks == 0 and mvps == 0:
                continue
                
            point_change = (catches * 10) + (drops * -10) + (hattricks * 20) + (mvps * 20)
            
            stats_update = {}
            if catches > 0: stats_update["fielding.catches"] = catches
            if drops > 0: stats_update["fielding.catch_drops"] = drops
            if hattricks > 0: stats_update["awards.hattricks"] = hattricks
            if mvps > 0: stats_update["awards.mvp"] = mvps
            stats_update["points"] = point_change
            
            push_updates = None
            if drops > 0:
                push_updates = {
                    "penalties": {
                        "amount": drops * 10,
                        "reason": f"Manual Catch Drop ({drops}x)",
                        "date": datetime.now(timezone.utc).isoformat(),
                        "given_by": str(ctx.author.id)
                    }
                }
                
            await update_player_stats(discord_id, stats_update, push_updates=push_updates)
            updated_count += 1
            
        await ctx.send(f"✅ Successfully processed batch stats for **{updated_count}** players!")

async def setup(bot):
    await bot.add_cog(Profile(bot))
