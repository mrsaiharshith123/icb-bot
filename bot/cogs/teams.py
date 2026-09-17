import discord
from discord.ext import commands
from bot.database.teams import get_team, get_all_teams, upsert_team
from bot.database.db import config_col, teams_col
from bot.utils.permissions import is_staff_ctx

class Teams(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_team_roles(self, guild_id: str):
        config = await config_col.find_one({"guild_id": guild_id})
        if config and "team_roles" in config:
            return config["team_roles"]
        return []

    async def get_user_team_role(self, member: discord.Member):
        team_roles = await self.get_team_roles(str(member.guild.id))
        user_teams = []
        for role in member.roles:
            if str(role.id) in team_roles:
                user_teams.append(str(role.id))
                
        if len(user_teams) == 1:
            return user_teams[0]
        elif len(user_teams) > 1:
            return "CONFLICT"
        return None

    @commands.group(name="teamconfig", invoke_without_command=True, help="Configure team roles (Staff only)")
    @is_staff_ctx()
    async def teamconfig(self, ctx: commands.Context):
        await ctx.send("Usage: `!teamconfig add @role` or `!teamconfig remove @role`")

    @teamconfig.command(name="add")
    @is_staff_ctx()
    async def teamconfig_add(self, ctx: commands.Context, role: discord.Role):
        guild_id = str(ctx.guild.id)
        await config_col.update_one(
            {"guild_id": guild_id},
            {"$addToSet": {"team_roles": str(role.id)}},
            upsert=True
        )
        await ctx.send(f"✅ Added {role.name} as a configured team role.")

    @teamconfig.command(name="remove")
    @is_staff_ctx()
    async def teamconfig_remove(self, ctx: commands.Context, role: discord.Role):
        guild_id = str(ctx.guild.id)
        await config_col.update_one(
            {"guild_id": guild_id},
            {"$pull": {"team_roles": str(role.id)}},
            upsert=True
        )
        await ctx.send(f"✅ Removed {role.name} from configured team roles.")

    @commands.command(name="teamsync", help="Sync configured team roles and their members to the database")
    @is_staff_ctx()
    async def teamsync(self, ctx: commands.Context):
        team_role_ids = await self.get_team_roles(str(ctx.guild.id))
        if not team_role_ids:
            await ctx.send("❌ No team roles configured. Use `!teamconfig add @role` first.")
            return

        sync_log = []
        member_team_count = {}
        conflicts = []

        # Count teams per member to detect conflicts
        for role_id_str in team_role_ids:
            role = ctx.guild.get_role(int(role_id_str))
            if role:
                for m in role.members:
                    member_team_count[m.id] = member_team_count.get(m.id, 0) + 1

        for member_id, count in member_team_count.items():
            if count > 1:
                member = ctx.guild.get_member(member_id)
                name = member.display_name if member else str(member_id)
                conflicts.append(f"⚠️ {name} has {count} team roles!")

        for role_id_str in team_role_ids:
            role = ctx.guild.get_role(int(role_id_str))
            if not role:
                sync_log.append(f"⚠️ Role ID {role_id_str} not found in server.")
                continue

            # Only add members who have exactly 1 team role to avoid messing up stats
            members = [str(m.id) for m in role.members if member_team_count.get(m.id, 0) == 1]
            await upsert_team(role_id_str, role.name, members)
            sync_log.append(f"✅ Synced **{role.name}** with {len(members)} members.")

        if conflicts:
            sync_log.extend(["", "**CONFLICTS DETECTED (Skipped these members):**"] + conflicts)

        embed = discord.Embed(title="🔄 Team Sync Complete", description="\n".join(sync_log[:40]), color=discord.Color.green())
        if len(sync_log) > 40:
            embed.set_footer(text="Log truncated due to length.")
        await ctx.send(embed=embed)

    @commands.command(name="createteam", help="Create a manual tournament team (Staff only)")
    @is_staff_ctx()
    async def createteam(self, ctx: commands.Context, *, team_name: str):
        from bot.database.teams import create_manual_team
        team_id = await create_manual_team(team_name)
        if not team_id:
            await ctx.send(f"❌ A team with the name '{team_name}' already exists.")
            return
            
        embed = discord.Embed(title="🏏 TEAM CREATED", color=discord.Color.green())
        embed.add_field(name="Team", value=team_name, inline=False)
        embed.add_field(name="Team ID", value=team_id, inline=False)
        embed.set_footer(text="The team is now ready for players to be assigned.")
        await ctx.send(embed=embed)

    @commands.command(name="team", aliases=["myteam", "squad"], help="Display a team, or assign a player to a team (Staff only)")
    async def team(self, ctx: commands.Context, user: discord.Member = None, *, team_name: str = None):
        from bot.database.teams import get_user_team
        from bot.utils.permissions import check_is_staff
        
        # ASSIGNMENT MODE
        if user and team_name:
            if not await check_is_staff(ctx):
                await ctx.send("❌ Only staff can assign players to a team.")
                return
                
            # Check if team exists
            team_data = await teams_col.find_one({"name": {"$regex": f"^{team_name}$", "$options": "i"}})
            if not team_data:
                await ctx.send(f"❌ Could not find a team named '{team_name}'. Please create it first.")
                return
                
            # Check if user already in a team
            existing_team_id = await get_user_team(str(user.id))
            if existing_team_id and existing_team_id != team_data["_id"]:
                existing_team = await get_team(existing_team_id)
                e_name = existing_team.get("name", "Unknown") if existing_team else "Unknown"
                await ctx.send(f"❌ {user.display_name} already belongs to **{e_name}**. Please remove them first using `-teamremove @user`.")
                return
                
            # Assign them
            await teams_col.update_one({"_id": team_data["_id"]}, {"$addToSet": {"members": str(user.id)}})
            
            embed = discord.Embed(title="✅ PLAYER ASSIGNED", color=discord.Color.green())
            embed.add_field(name="Player", value=user.mention, inline=False)
            embed.add_field(name="Team", value=team_data["name"], inline=False)
            embed.set_footer(text="The player can now use -team to view their tournament information.")
            await ctx.send(embed=embed)
            return

        # LOOKUP MODE
        target = user or ctx.author
        
        # Check DB directly to find their team (works for both manual and role-synced)
        role_id_str = await get_user_team(str(target.id))
        
        if not role_id_str:
            if target == ctx.author:
                await ctx.send("❌ You are not currently assigned to a tournament team.")
            else:
                await ctx.send(f"❌ {target.display_name} is currently not assigned to a tournament team.")
            return
            
        team_data = await get_team(role_id_str)
        if not team_data:
            await ctx.send("❌ Team data not found in database.")
            return
            
        # Optional: grab color if it's a role
        role = ctx.guild.get_role(int(role_id_str)) if role_id_str.isdigit() else None
        color = role.color if role else discord.Color.blue()
        team_name = team_data.get("name", "Unknown Team")
        
        embed = discord.Embed(title="🏏 YOUR TOURNAMENT TEAM" if target == ctx.author else f"🏏 {target.display_name.upper()}'S TEAM", color=color)
        
        embed.add_field(name="Team", value=team_name, inline=False)
        
        captain_id = team_data.get("captain")
        captain_str = f"<@{captain_id}>" if captain_id else "None assigned"
        embed.add_field(name="👑 Captain", value=captain_str, inline=False)
        
        members = team_data.get("members", [])
        members_str = "\n".join([f"• <@{m}>" for m in members]) if members else "No members"
        
        if len(members_str) > 1024:
            members_str = f"• {len(members)} players (too many to list)"
            
        embed.add_field(name="👥 Squad", value=members_str, inline=False)
        
        # Stats
        mp = team_data.get("matches_played", 0)
        w = team_data.get("wins", 0)
        l = team_data.get("losses", 0)
        d = team_data.get("draws", 0)
        pts = team_data.get("points", 0)
        rf = team_data.get("runs_for", 0)
        ra = team_data.get("runs_against", 0)
        nrr = team_data.get("nrr", 0.0)
        
        stats_str = f"Matches: {mp}\nWins: {w}\nLosses: {l}\nDraws: {d}\nPoints: {pts}\nRuns For: {rf}\nRuns Against: {ra}\nNRR: {nrr:.3f}"
        embed.add_field(name="📊 TOURNAMENT RECORD", value=stats_str, inline=False)
        
        embed.add_field(name="📅 FIXTURES", value="No fixtures scheduled yet.", inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name="teams", help="List all tournament teams")
    async def teams(self, ctx: commands.Context):
        teams = await get_all_teams()
        if not teams:
            await ctx.send("❌ No tournament teams have been created yet.")
            return
            
        embed = discord.Embed(title="🏆 TOURNAMENT TEAMS", color=discord.Color.gold())
        
        desc = ""
        for i, t in enumerate(teams):
            name = t.get("name", "Unknown Team")
            m_count = len(t.get("members", []))
            desc += f"{i+1}. {name} — {m_count} players\n"
            
        embed.description = desc
        await ctx.send(embed=embed)

    @commands.command(name="teaminfo", help="Display details for a specific team")
    async def teaminfo(self, ctx: commands.Context, *, team_query: str):
        # Allow resolving by role mention, ID, or team name
        role_id_str = None
        
        # Check if it's a role mention
        if team_query.startswith("<@&") and team_query.endswith(">"):
            role_id_str = team_query[3:-1]
            team_data = await get_team(role_id_str)
        else:
            # Check if it's a direct ID
            team_data = await get_team(team_query)
            if not team_data:
                # Try to match by name (case insensitive)
                team_data = await teams_col.find_one({"name": {"$regex": f"^{team_query}$", "$options": "i"}})
                
        if not team_data:
            await ctx.send("❌ Could not find a team matching that name or mention.")
            return
            
        role_id_str = team_data["_id"]
        role = ctx.guild.get_role(int(role_id_str)) if role_id_str.isdigit() else None
        color = role.color if role else discord.Color.blue()
        team_name = team_data.get("name", "Unknown Team")
        
        embed = discord.Embed(title=f"🏏 Team {team_name}", color=color)
        
        captain_id = team_data.get("captain")
        captain_str = f"<@{captain_id}>" if captain_id else "None assigned"
        embed.add_field(name="Captain", value=captain_str, inline=False)
        
        members = team_data.get("members", [])
        members_str = "\n".join([f"• <@{m}>" for m in members]) if members else "No members"
        if len(members_str) > 1024:
            members_str = f"• {len(members)} players (too many to list)"
        embed.add_field(name="Squad", value=members_str, inline=False)
        
        mp = team_data.get("matches_played", 0)
        w = team_data.get("wins", 0)
        l = team_data.get("losses", 0)
        d = team_data.get("draws", 0)
        pts = team_data.get("points", 0)
        rf = team_data.get("runs_for", 0)
        ra = team_data.get("runs_against", 0)
        nrr = team_data.get("nrr", 0.0)
        
        stats_str = f"Matches: {mp}\nWins: {w} | Losses: {l} | Draws/Ties: {d}\nPoints: {pts}\nRuns For: {rf} | Runs Against: {ra}\nNRR: {nrr:.3f}"
        embed.add_field(name="Statistics", value=stats_str, inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name="standings", aliases=["table"], help="Display the league standings")
    async def standings(self, ctx: commands.Context):
        teams = await get_all_teams()
        if not teams:
            await ctx.send("❌ No teams found in the database.")
            return
            
        # Teams are already sorted by points DESC, NRR DESC, Runs For DESC via the DB query
        
        embed = discord.Embed(title="🏆 LEAGUE STANDINGS", color=discord.Color.gold())
        
        desc = "```\nPOS | TEAM                 | MP | W | L | D | PTS | NRR\n"
        desc += "-" * 57 + "\n"
        
        for i, t in enumerate(teams):
            name = t.get("name", "Unknown")[:20]
            mp = t.get("matches_played", 0)
            w = t.get("wins", 0)
            l = t.get("losses", 0)
            d = t.get("draws", 0)
            pts = t.get("points", 0)
            nrr = t.get("nrr", 0.0)
            
            # Format rows safely
            row = f"{i+1:2d}. | {name:<20} | {mp:2d} | {w} | {l} | {d} | {pts:3d} | {nrr:+.3f}\n"
            desc += row
            
        desc += "```"
        embed.description = desc
        
        await ctx.send(embed=embed)

    @commands.command(name="teamsetcaptain", help="Set the captain of a team (Staff only)")
    @is_staff_ctx()
    async def teamsetcaptain(self, ctx: commands.Context, user: discord.Member, *, team_query: str):
        team_data = await teams_col.find_one({"name": {"$regex": f"^{team_query}$", "$options": "i"}})
        
        # Fallback to checking by ID if name isn't found
        if not team_data:
            if team_query.startswith("<@&") and team_query.endswith(">"):
                team_data = await get_team(team_query[3:-1])
            else:
                team_data = await get_team(team_query)
                
        if not team_data:
            await ctx.send("❌ Could not find a team matching that name or mention.")
            return
            
        if str(user.id) not in team_data.get("members", []):
            await ctx.send(f"❌ {user.display_name} is not a member of **{team_data['name']}**. Please assign them to the team first.")
            return
            
        await teams_col.update_one(
            {"_id": team_data["_id"]},
            {"$set": {"captain": str(user.id)}}
        )
        await ctx.send(f"✅ Successfully set {user.mention} as the captain of **{team_data['name']}**.")


    @commands.command(name="teamremove", help="Remove a member from a team (Staff only)")
    @is_staff_ctx()
    async def teamremove(self, ctx: commands.Context, user: discord.Member):
        from bot.database.teams import get_user_team
        team_id = await get_user_team(str(user.id))
        
        if not team_id:
            await ctx.send(f"❌ {user.display_name} is not currently assigned to any team.")
            return
            
        team_data = await get_team(team_id)
        team_name = team_data.get("name", "Unknown Team")
            
        # Try to remove role if it's a role-based team
        if team_id.isdigit():
            role = ctx.guild.get_role(int(team_id))
            if role and role in user.roles:
                try:
                    await user.remove_roles(role)
                except Exception as e:
                    pass # Ignore if we can't remove the role or it's manual
            
        await teams_col.update_one(
            {"_id": team_id},
            {"$pull": {"members": str(user.id)}}
        )
        
        # If they were captain, remove them as captain
        if team_data and team_data.get("captain") == str(user.id):
            await teams_col.update_one({"_id": team_id}, {"$set": {"captain": None}})
            
        await ctx.send(f"✅ Removed {user.mention} from **{team_name}**.")

async def setup(bot):
    await bot.add_cog(Teams(bot))
