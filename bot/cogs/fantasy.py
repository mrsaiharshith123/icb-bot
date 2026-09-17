import discord
from discord.ext import commands
from bot.database.players import get_player, players_col

class Fantasy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="cards", aliases=["collection"], description="View your Fantasy Cricket cards")
    async def cards_cmd(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        discord_id = str(target.id)
        player = await get_player(discord_id)
        
        cards = player.get("fantasy", {}).get("cards", [])
        if not cards:
            await ctx.send(f"❌ {target.display_name} doesn't own any Fantasy cards yet. Buy a Mystery Pack from the `-shop`!")
            return
            
        # Sort by rating (descending)
        cards.sort(key=lambda x: x.get("rating", 0), reverse=True)
        
        embed = discord.Embed(title=f"🃏 {target.display_name}'s Collection", color=discord.Color.purple())
        embed.description = f"**Total Cards:** {len(cards)}\n\n"
        
        # Display top 10
        for i, card in enumerate(cards[:10]):
            rarity = card.get('rarity', 'Common')
            rating = card.get('rating', 50)
            
            rarity_emoji = {
                "Common": "⚪",
                "Rare": "🔵",
                "Epic": "🟣",
                "Legendary": "🟡",
                "Mythic": "🔴"
            }.get(rarity, "⚪")
            
            embed.description += f"`{i+1}.` {rarity_emoji} **{card.get('name', 'Unknown')}** • ⭐ {rating} `({rarity})`\n"
            
        if len(cards) > 10:
            embed.set_footer(text=f"Showing top 10 of {len(cards)} cards.")
            
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Fantasy(bot))
