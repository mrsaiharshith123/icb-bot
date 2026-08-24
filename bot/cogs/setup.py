import discord
from discord.ext import commands
from bot.database.db import config_col
from bot.utils.permissions import is_staff_ctx

class SetupView(discord.ui.View):
    def __init__(self, ctx: commands.Context):
        super().__init__(timeout=300)
        self.ctx = ctx
        self.player_role_id = None
        self.staff_role_id = None
        self.announcement_channel_id = None
        self.match_info_channel_id = None
        self.player_ranks_channel_id = None

    async def _check_and_save(self, interaction: discord.Interaction):
        if not all([self.player_role_id, self.staff_role_id, self.announcement_channel_id, self.match_info_channel_id, self.player_ranks_channel_id]):
            return False

        guild_id = str(interaction.guild.id)
        timezone = "Asia/Kolkata" # Default timezone
        
        config = {
            "guild_id": guild_id,
            "player_role_id": self.player_role_id,
            "staff_role_id": self.staff_role_id,
            "announcement_channel_id": self.announcement_channel_id,
            "match_info_channel_id": self.match_info_channel_id,
            "player_ranks_channel_id": self.player_ranks_channel_id,
            "timezone": timezone
        }
        
        await config_col.update_one(
            {"guild_id": guild_id},
            {"$set": config},
            upsert=True
        )
        
        embed = discord.Embed(
            title="⚙️ Career Mode Setup Complete",
            description="The server has been configured successfully.",
            color=discord.Color.green()
        )
        embed.add_field(name="Player Role", value=f"<@&{self.player_role_id}>", inline=True)
        embed.add_field(name="Staff Role", value=f"<@&{self.staff_role_id}>", inline=True)
        embed.add_field(name="Timezone", value=timezone, inline=True)
        embed.add_field(name="Announcement Channel", value=f"<#{self.announcement_channel_id}>", inline=False)
        embed.add_field(name="Match Info Channel", value=f"<#{self.match_info_channel_id}>", inline=False)
        embed.add_field(name="Player Ranks Channel", value=f"<#{self.player_ranks_channel_id}>", inline=False)
        
        await interaction.message.edit(content="Configuration saved!", embed=embed, view=None)
        print(f"[SETUP] Configuration updated for guild {guild_id}")
        return True

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="Select Player Role", custom_id="sel_player_role")
    async def select_player_role(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        self.player_role_id = select.values[0].id
        saved = await self._check_and_save(interaction)
        await interaction.response.send_message("✅ Setup Complete!" if saved else f"✅ Player Role selected: {select.values[0].mention}", ephemeral=True)

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="Select Staff Role", custom_id="sel_staff_role")
    async def select_staff_role(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        self.staff_role_id = select.values[0].id
        saved = await self._check_and_save(interaction)
        await interaction.response.send_message("✅ Setup Complete!" if saved else f"✅ Staff Role selected: {select.values[0].mention}", ephemeral=True)

    @discord.ui.select(cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.text], placeholder="Select Announcement Channel", custom_id="sel_ann_chan")
    async def select_ann_channel(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        self.announcement_channel_id = select.values[0].id
        saved = await self._check_and_save(interaction)
        await interaction.response.send_message("✅ Setup Complete!" if saved else f"✅ Announcement Channel selected: {select.values[0].mention}", ephemeral=True)

    @discord.ui.select(cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.text], placeholder="Select Match Info Channel", custom_id="sel_info_chan")
    async def select_info_channel(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        self.match_info_channel_id = select.values[0].id
        saved = await self._check_and_save(interaction)
        await interaction.response.send_message("✅ Setup Complete!" if saved else f"✅ Match Info Channel selected: {select.values[0].mention}", ephemeral=True)

    @discord.ui.select(cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.text], placeholder="Select Player Ranks Channel", custom_id="sel_ranks_chan")
    async def select_ranks_channel(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        self.player_ranks_channel_id = select.values[0].id
        saved = await self._check_and_save(interaction)
        await interaction.response.send_message("✅ Setup Complete!" if saved else f"✅ Player Ranks Channel selected: {select.values[0].mention}", ephemeral=True)

class EditSetupView(discord.ui.View):
    def __init__(self, ctx: commands.Context):
        super().__init__(timeout=300)
        self.ctx = ctx

    @discord.ui.button(label="Edit Setup", style=discord.ButtonStyle.primary, emoji="✏️")
    async def edit_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="⚙️ Edit Server Configuration",
            description="Please use the dropdowns below to update the required roles and channels for the Career Mode bot.\n\nOnce you have selected all 4 options, click **Save Configuration**.",
            color=discord.Color.blue()
        )
        view = SetupView(self.ctx)
        await interaction.response.edit_message(embed=embed, view=view)

class Setup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setup", help="Configure server settings for Career Mode via interactive dropdowns")
    @is_staff_ctx()
    async def setup_cmd(self, ctx: commands.Context):
        guild_id = str(ctx.guild.id)
        config = await config_col.find_one({"guild_id": guild_id})
        
        # Check if setup is already complete
        if config and all(k in config for k in ["player_role_id", "staff_role_id", "announcement_channel_id", "match_info_channel_id", "player_ranks_channel_id"]):
            embed = discord.Embed(
                title="⚙️ Current Configuration",
                description="The server is already configured. Here are your current settings:",
                color=discord.Color.green()
            )
            embed.add_field(name="Player Role", value=f"<@&{config['player_role_id']}>", inline=True)
            embed.add_field(name="Staff Role", value=f"<@&{config['staff_role_id']}>", inline=True)
            embed.add_field(name="Timezone", value=config.get('timezone', 'Asia/Kolkata'), inline=True)
            embed.add_field(name="Announcement Channel", value=f"<#{config['announcement_channel_id']}>", inline=False)
            embed.add_field(name="Match Info Channel", value=f"<#{config['match_info_channel_id']}>", inline=False)
            embed.add_field(name="Player Ranks Channel", value=f"<#{config['player_ranks_channel_id']}>", inline=False)
            
            view = EditSetupView(ctx)
            await ctx.send(embed=embed, view=view)
        else:
            embed = discord.Embed(
                title="⚙️ Server Configuration",
                description="Please use the dropdowns below to select the required roles and channels for the Career Mode bot.\n\nOnce you have selected all 4 options, click **Save Configuration**.",
                color=discord.Color.blue()
            )
            view = SetupView(ctx)
            await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Setup(bot))
