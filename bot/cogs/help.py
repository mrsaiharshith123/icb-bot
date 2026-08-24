import discord
from discord.ext import commands

class HelpDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Career & Stats", emoji="🏆", description="Profile, Leaderboards, Achievements"),
            discord.SelectOption(label="Economy & Daily", emoji="💰", description="Balance, Shop, Daily Rewards"),
            discord.SelectOption(label="Intelligence", emoji="🧠", description="Batting Tips, Coach, Training"),
            discord.SelectOption(label="Staff & Utils", emoji="⚙️", description="Setup, Moderation, Penalties")
        ]
        super().__init__(placeholder="Select a category...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(color=discord.Color.blue())
        
        if self.values[0] == "Career & Stats":
            embed.title = "🏆 Career & Stats Commands"
            embed.description = (
                "`-profile` | `-me` - View your dynamic Career Mode profile card\n"
                "`-leaderboard` | `-lb` - View the server leaderboards (Points, Runs, etc.)\n"
                "`-achievements` - View your unlocked milestones\n"
                "`-roadmap` - View the HC Career Mode progression roadmap\n"
                "`-stats` - Link your Discord account to HC stats"
            )
        elif self.values[0] == "Economy & Daily":
            embed.title = "💰 Economy & Daily Commands"
            embed.description = (
                "`-balance` | `-bal` - Check your HC Coin balance\n"
                "`-daily` - Claim your daily coins and build your streak\n"
                "`-shop` - View the HC Coin shop\n"
                "`-buy <item_id>` - Purchase an item from the shop\n"
                "`-inventory` | `-inv` - Check your inventory\n"
                "`-give <@user> <amount>` - Transfer coins to another player"
            )
        elif self.values[0] == "Intelligence":
            embed.title = "🧠 HC Intelligence Commands"
            embed.description = (
                "`-tips` | `-batting` - Learn HC Batting Fundamentals\n"
                "`-coach` - Get a personalized tip from your HC Coach\n"
                "`-training` - Practice reading HC scenarios"
            )
        elif self.values[0] == "Staff & Utils":
            embed.title = "⚙️ Staff & Utility Commands"
            embed.description = (
                "`-setup` - Initialize server channels (Staff)\n"
                "`-announce` - Announce a match with custom comments (Staff)\n"
                "`-deduct` - Manually deduct points (Staff)\n"
                "`-addcoins` - Give coins to a player (Staff)\n"
                "`-penalties` - View all manual penalties applied to a player"
            )
            
        await interaction.response.edit_message(embed=embed, view=self.view)

class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(HelpDropdown())

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="help", description="View all available commands")
    async def help_cmd(self, ctx):
        embed = discord.Embed(
            title="👋 Welcome to the HC Companion Bot",
            description="I am your ultimate Hand Cricket career and community hub! Use the dropdown below to explore my features.",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Select a category from the menu below")
        
        view = HelpView()
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Help(bot))
