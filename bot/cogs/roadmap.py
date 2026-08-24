import discord
from discord.ext import commands
from discord import app_commands
import io

from bot.database.players import get_player
from bot.services.roadmap_card import generate_roadmap_page

class RoadmapPagination(discord.ui.View):
    def __init__(self, player_xp: int, target_user: discord.User):
        super().__init__(timeout=180)
        self.player_xp = player_xp
        self.target_user = target_user
        self.current_page = 1
        self.update_buttons()
        
    def update_buttons(self):
        self.prev_button.disabled = (self.current_page == 1)
        self.next_button.disabled = (self.current_page == 2)
        
    async def generate_embed_and_file(self):
        # Generate the correct image
        image_io = generate_roadmap_page(self.player_xp, self.current_page)
        file = discord.File(image_io, filename=f"roadmap_page_{self.current_page}.png")
        
        embed = discord.Embed(
            title=f"{self.target_user.display_name}'s Career Roadmap",
            description=f"Page {self.current_page} / 2",
            color=discord.Color.blue()
        )
        embed.set_image(url=f"attachment://roadmap_page_{self.current_page}.png")
        return embed, file

    @discord.ui.button(label="◀ Previous", style=discord.ButtonStyle.primary, custom_id="roadmap_prev")
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 1
        self.update_buttons()
        embed, file = await self.generate_embed_and_file()
        await interaction.response.edit_message(embed=embed, attachments=[file], view=self)
        
    @discord.ui.button(label="▶ Next", style=discord.ButtonStyle.primary, custom_id="roadmap_next")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 2
        self.update_buttons()
        embed, file = await self.generate_embed_and_file()
        await interaction.response.edit_message(embed=embed, attachments=[file], view=self)

class Roadmap(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="roadmap", description="View the career mode roadmap and unlock progress")
    async def roadmap(self, ctx: commands.Context, user: discord.User = None):
        await ctx.defer()
        target = user or ctx.author
        discord_id = str(target.id)
        
        try:
            player_data = await get_player(discord_id)
            player_xp = player_data.get("points", 0) if player_data else 0
        except Exception as e:
            # Handle MongoDB temporarily unavailable or other errors gracefully
            await ctx.send(f"Error accessing career database. Please try again later. ({str(e)})")
            return
            
        view = RoadmapPagination(player_xp, target)
        embed, file = await view.generate_embed_and_file()
        
        await ctx.send(embed=embed, file=file, view=view)

async def setup(bot):
    await bot.add_cog(Roadmap(bot))
