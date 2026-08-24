import discord
from discord.ext import commands
from bot.database.db import config_col

async def check_is_staff(interaction: discord.Interaction) -> bool:
    """
    Returns True if the user has Administrator, Manage Server, 
    or the configured staff role.
    """
    if await interaction.client.is_owner(interaction.user):
        return True
        
    if interaction.user.guild_permissions.administrator or interaction.user.guild_permissions.manage_guild:
        return True
        
    guild_id = str(interaction.guild_id)
    config = await config_col.find_one({"guild_id": guild_id})
    
    if config and "staff_role_id" in config:
        staff_role_id = config["staff_role_id"]
        # Check if user has this role
        if any(role.id == staff_role_id for role in interaction.user.roles):
            return True
            
    return False

def is_staff():
    """Decorator for app_commands to require staff permissions."""
    async def predicate(interaction: discord.Interaction) -> bool:
        has_permission = await check_is_staff(interaction)
        if not has_permission:
            await interaction.response.send_message("❌ You must be a staff member to use this command.", ephemeral=True)
            return False
        return True
    return discord.app_commands.check(predicate)

def is_staff_ctx():
    """Decorator for ext.commands (hybrid_command) to require staff permissions."""
    async def predicate(ctx: commands.Context) -> bool:
        # If it's an interaction (slash command), check_is_staff handles it easily
        if ctx.interaction:
            has_permission = await check_is_staff(ctx.interaction)
        else:
            # Traditional command
            if await ctx.bot.is_owner(ctx.author):
                return True
                
            if ctx.author.guild_permissions.administrator or ctx.author.guild_permissions.manage_guild:
                return True
                
            guild_id = str(ctx.guild.id)
            config = await config_col.find_one({"guild_id": guild_id})
            if config and "staff_role_id" in config:
                staff_role_id = config["staff_role_id"]
                if any(role.id == staff_role_id for role in ctx.author.roles):
                    return True
            has_permission = False
            
        if not has_permission:
            # Note: For app_commands check failed it throws an error handled by tree.error
            # But this is for text commands, or hybrid invocation
            raise commands.CheckFailure("You must be a staff member to use this command.")
        return True
    return commands.check(predicate)
