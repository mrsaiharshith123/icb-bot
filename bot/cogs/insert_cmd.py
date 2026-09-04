import discord
from discord.ext import commands
from datetime import datetime, timezone

class BackfillConfirmView(discord.ui.View):
    def __init__(self, cog, ctx, pending_updates, db_collection):
        super().__init__(timeout=300)
        self.cog = cog
        self.ctx = ctx
        self.pending_updates = pending_updates
        self.db_collection = db_collection
        
    @discord.ui.button(label="Confirm & Apply", style=discord.ButtonStyle.success)
    async def confirm_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        for child in self.children:
            child.disabled = True
        msg = await interaction.followup.edit_message(message_id=interaction.message.id, content="⏳ Applying...", view=self)
        
        from bot.database.players import update_player_stats
        
        for up in self.pending_updates:
            await self.db_collection.update_one({"_id": up["msg_id"]}, {"$set": {"processed": True}}, upsert=True)
            if up["type"] == "catch":
                await update_player_stats(
                    discord_id=up["catcher_id"],
                    stats_update={"fielding.catches": 1, "points": up["pts"]}
                )
            elif up["type"] == "drop":
                await update_player_stats(
                    discord_id=up["catcher_id"],
                    stats_update={"fielding.catch_drops": 1, "points": up["pts"]},
                    push_updates={"penalties": {"amount": abs(up["pts"]), "reason": "Historical Drop Recovery", "date": datetime.now(timezone.utc).isoformat(), "given_by": "SYSTEM"}}
                )
        
        await msg.edit(content=f"✅ Applied {len(self.pending_updates)} historical catch/drop stats!")

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="❌ Cancelled.", view=self)


def insert_code():
    with open(r"c:\Users\mrsai\OneDrive\Desktop\ICB BOT\bot\cogs\matches.py", "r", encoding="utf-8") as f:
        content = f.read()

    # Prepend BackfillConfirmView
    if "class BackfillConfirmView" not in content:
        import inspect
        view_code = inspect.getsource(BackfillConfirmView)
        content = content.replace("class Matches(commands.Cog):", view_code + "\nclass Matches(commands.Cog):")

    command_code = """
    @commands.command(name="backfillcatches", help="Recover missed catch stats from channel history")
    @is_staff_ctx()
    async def backfillcatches(self, ctx: commands.Context, limit: int = 200):
        await ctx.send(f"⏳ Scanning the last {limit} messages in this channel for missed catches...")
        from bot.config import ORIGINAL_HC_BOT_ID
        from bot.database.db import db
        processed_col = db["processed_catches"]
        
        history = [msg async for msg in ctx.channel.history(limit=limit, oldest_first=True)]
        
        pending_opportunity = None
        updates = []
        preview_desc = ""
        
        from bot.services.match_detector import is_catch_event, parse_catch, is_catch_result, parse_catch_result
        from bot.utils.events import is_janmashtami
        
        catch_pts = 20 if is_janmashtami() else 10
        drop_pts = -10
        
        for msg in history:
            if ORIGINAL_HC_BOT_ID and msg.author.id != ORIGINAL_HC_BOT_ID:
                continue
                
            doc = await processed_col.find_one({"_id": msg.id})
            if doc:
                continue
                
            if is_catch_event(msg):
                data = parse_catch(msg)
                if data:
                    pending_opportunity = data
            elif pending_opportunity and is_catch_result(msg):
                success = parse_catch_result(msg)
                
                up = {
                    "msg_id": msg.id,
                    "catcher_id": pending_opportunity["catcher_id"],
                    "batter_id": pending_opportunity["batter_id"],
                    "type": "catch" if success else "drop",
                    "pts": catch_pts if success else drop_pts
                }
                updates.append(up)
                pending_opportunity = None
                
                action = "Caught" if success else "Dropped"
                preview_desc += f"- **{action}** by <@{up['catcher_id']}> ({up['pts']:+d} pts) [Msg: {msg.id}]\\n"
                
        if not updates:
            await ctx.send("✅ No new missed catches found in the scanned history.")
            return
            
        embed = discord.Embed(title="Historical Catches Preview", description=preview_desc[:4000], color=discord.Color.gold())
        view = BackfillConfirmView(self, ctx, updates, processed_col)
        await ctx.send(content="⚠️ Review the pending catch recoveries below:", embed=embed, view=view)
"""

    if "def backfillcatches" not in content:
        content = content.replace("async def setup(bot):", command_code + "\nasync def setup(bot):")

    with open(r"c:\Users\mrsai\OneDrive\Desktop\ICB BOT\bot\cogs\matches.py", "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    insert_code()
    print("Done")
