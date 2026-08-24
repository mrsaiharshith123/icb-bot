import discord
from discord.ext import commands
from bot.database.db import players_col
from bot.utils.pagination import LeaderboardPagination

# Cache for sorted leaderboards to avoid frequent DB scans
# Key: category, Value: (timestamp, sorted_list)
# Since we want it simple for now, we'll fetch on demand but we can cache later if needed.

def get_sort_key_and_title(category):
    if category == "points":
        return lambda p: p.get("points", 0), True, "🏆 TOP CAREER POINTS", lambda p: f"{p.get('points', 0):,} pts"
    elif category == "runs":
        return lambda p: p.get("batting", {}).get("runs", 0), True, "🏏 TOP RUN SCORERS", lambda p: f"{p.get('batting', {}).get('runs', 0):,} runs"
    elif category == "wickets":
        return lambda p: p.get("bowling", {}).get("wickets", 0), True, "🎯 TOP WICKET TAKERS", lambda p: f"{p.get('bowling', {}).get('wickets', 0):,} wkts"
    elif category == "mvps":
        return lambda p: p.get("awards", {}).get("mvp", 0), True, "🏅 MOST MVPs", lambda p: f"{p.get('awards', {}).get('mvp', 0)} MVPs"
    elif category == "catches":
        return lambda p: p.get("fielding", {}).get("catches", 0), True, "🧤 TOP CATCHERS", lambda p: f"{p.get('fielding', {}).get('catches', 0)} catches"
    elif category == "coins":
        return lambda p: p.get("economy", {}).get("coins", 0), True, "💰 RICHEST PLAYERS", lambda p: f"{p.get('economy', {}).get('coins', 0):,} 🪙"
    elif category == "batting_avg":
        def get_batting_avg(p):
            runs = p.get("batting", {}).get("runs", 0)
            matches = p.get("matches", {}).get("played", 0)
            return runs / max(1, matches)
        return get_batting_avg, True, "🏏 BEST BATTING AVERAGE", lambda p: f"{get_batting_avg(p):.2f}"
    elif category == "economy":
        def get_economy(p):
            runs_c = p.get("bowling", {}).get("runs_conceded", 0)
            balls = p.get("bowling", {}).get("balls", 0)
            overs = balls / 6.0
            return runs_c / overs if overs > 0 else 9999.0
        return get_economy, False, "⚡ BEST ECONOMY RATE", lambda p: f"{get_economy(p):.2f}"
    return lambda p: p.get("points", 0), True, "🏆 TOP CAREER POINTS", lambda p: f"{p.get('points', 0):,} pts"

async def fetch_sorted_players(category):
    cursor = players_col.find({"$or": [
        {"matches.played": {"$gt": 0}}, 
        {"points": {"$gt": 0}},
        {"economy.coins": {"$gt": 0}}
    ]})
    players = await cursor.to_list(length=None)
    
    if category == "batting_avg":
        players = [p for p in players if p.get("batting", {}).get("runs", 0) > 0]
    elif category == "economy":
        players = [p for p in players if p.get("bowling", {}).get("balls", 0) > 0]
        
    sort_key, reverse, _, _ = get_sort_key_and_title(category)
    players.sort(key=sort_key, reverse=reverse)
    return players

class LeaderboardDropdown(discord.ui.Select):
    def __init__(self, current_category, current_user_id):
        self.current_user_id = current_user_id
        options = [
            discord.SelectOption(label="Career Points", emoji="🏆", value="points", default=(current_category=="points")),
            discord.SelectOption(label="Runs", emoji="🏏", value="runs", default=(current_category=="runs")),
            discord.SelectOption(label="Wickets", emoji="🎯", value="wickets", default=(current_category=="wickets")),
            discord.SelectOption(label="Coins", emoji="💰", value="coins", default=(current_category=="coins")),
            discord.SelectOption(label="MVPs", emoji="🏅", value="mvps", default=(current_category=="mvps")),
            discord.SelectOption(label="Catches", emoji="🧤", value="catches", default=(current_category=="catches")),
            discord.SelectOption(label="Batting Average", emoji="🏏", value="batting_avg", default=(current_category=="batting_avg")),
            discord.SelectOption(label="Bowling Economy", emoji="⚡", value="economy", default=(current_category=="economy"))
        ]
        super().__init__(placeholder="🏆 Select a Leaderboard Category...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        category = self.values[0]
        players = await fetch_sorted_players(category)
        
        per_page = 10
        total_pages = max(1, (len(players) + per_page - 1) // per_page)
        
        async def get_page(page, current_user_id):
            target_page = None
            if page == 0:
                # Find user rank
                for i, p in enumerate(players):
                    if p["_id"] == current_user_id:
                        target_page = (i // per_page) + 1
                        break
                page = target_page or 1
                
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            page_players = players[start_idx:end_idx]
            
            _, _, title, format_val = get_sort_key_and_title(category)
            embed = discord.Embed(title=title, color=discord.Color.gold())
            
            desc = ""
            for i, p in enumerate(page_players, start=start_idx + 1):
                prefix = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                
                # Highlight if it's the user
                if p["_id"] == current_user_id:
                    desc += f"**{prefix} <@{p['_id']}> — {format_val(p)}** 👤\n"
                else:
                    desc += f"{prefix} <@{p['_id']}> — {format_val(p)}\n"
                    
            embed.description = desc or "No players found."
            
            # Find user rank for footer
            user_rank_str = "Unranked"
            user_val_str = "0"
            for i, p in enumerate(players, start=1):
                if p["_id"] == current_user_id:
                    user_rank_str = f"#{i}"
                    user_val_str = format_val(p)
                    break
                    
            embed.set_footer(text=f"👤 Your Rank: {user_rank_str} • Score: {user_val_str}")
            
            if target_page is not None:
                return embed, page
            return embed
            
        initial_embed, init_page = await get_page(0, self.current_user_id) # Start on user's page if they have one, else 1
        
        view = LeaderboardPagination(interaction, get_page, total_pages, self.current_user_id)
        view.current_page = init_page
        view.update_buttons()
        # Re-add the dropdown
        view.add_item(LeaderboardDropdown(category, self.current_user_id))
        
        await interaction.response.edit_message(embed=initial_embed, view=view)


class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="leaderboard", aliases=["lb", "rank"], description="View the Server Leaderboards")
    async def leaderboard(self, ctx: commands.Context):
        category = "points"
        players = await fetch_sorted_players(category)
        
        per_page = 10
        total_pages = max(1, (len(players) + per_page - 1) // per_page)
        
        async def get_page(page, current_user_id):
            target_page = None
            if page == 0:
                for i, p in enumerate(players):
                    if p["_id"] == current_user_id:
                        target_page = (i // per_page) + 1
                        break
                page = target_page or 1
                
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            page_players = players[start_idx:end_idx]
            
            _, _, title, format_val = get_sort_key_and_title(category)
            embed = discord.Embed(title=title, color=discord.Color.gold())
            
            desc = ""
            for i, p in enumerate(page_players, start=start_idx + 1):
                prefix = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                if p["_id"] == current_user_id:
                    desc += f"**{prefix} <@{p['_id']}> — {format_val(p)}** 👤\n"
                else:
                    desc += f"{prefix} <@{p['_id']}> — {format_val(p)}\n"
                    
            embed.description = desc or "No players found."
            
            user_rank_str = "Unranked"
            user_val_str = "0"
            for i, p in enumerate(players, start=1):
                if p["_id"] == current_user_id:
                    user_rank_str = f"#{i}"
                    user_val_str = format_val(p)
                    break
                    
            embed.set_footer(text=f"👤 Your Rank: {user_rank_str} • Score: {user_val_str}")
            
            if target_page is not None:
                return embed, page
            return embed
            
        initial_embed, init_page = await get_page(0, str(ctx.author.id))
        
        view = LeaderboardPagination(None, get_page, total_pages, str(ctx.author.id))
        view.current_page = init_page
        view.update_buttons()
        view.add_item(LeaderboardDropdown(category, str(ctx.author.id)))
        
        await ctx.send(embed=initial_embed, view=view)

async def setup(bot):
    await bot.add_cog(Leaderboard(bot))
