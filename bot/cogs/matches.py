import discord
from discord.ext import commands
from bot.config import ORIGINAL_HC_BOT_ID, CAREER_CHANNEL_IDS
from bot.services.match_detector import is_match_start, is_catch_event, parse_catch, is_raw_statistics, is_catch_result, parse_catch_result, is_hattrick_event, parse_hattrick
from bot.services.stats_parser import parse_raw_statistics
from bot.services.points_calculator import calculate_player_points
from bot.database.matches import create_match, get_active_match, add_catch_to_match, set_pending_catch, resolve_pending_catch, cancel_match, set_match_pending, get_pending_match, approve_match_stats, add_hattrick_to_match
from bot.database.players import get_player, update_player_stats
from bot.database.db import upcoming_matches_col, config_col
from bot.utils.permissions import is_staff_ctx
from datetime import datetime, timezone
from bot.services.match_detector import is_raw_statistics
class AddStatsConfirmView(discord.ui.View):
    def __init__(self, cog, ctx, match, players_data, upcoming):
        super().__init__(timeout=300)
        self.cog = cog
        self.ctx = ctx
        self.match = match
        self.players_data = players_data
        self.upcoming = upcoming
        
    @discord.ui.button(label="Confirm & Finalize Match", style=discord.ButtonStyle.success)
    async def confirm_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        from bot.database.db import upcoming_matches_col
        latest_upcoming = await upcoming_matches_col.find_one({"_id": self.upcoming["_id"]}) if self.upcoming else None
        
        for child in self.children:
            child.disabled = True
            
        msg = await interaction.followup.edit_message(message_id=interaction.message.id, content="⏳ Processing stats and awarding points... please wait.", embed=None, view=self)
        
        await self.cog._process_and_finalize_stats(self.ctx, self.match, self.players_data, latest_upcoming, progress_msg=msg)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="❌ Finalization cancelled. You can run `!addstats` again when ready.", embed=None, view=self)

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

class Matches(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if after.author == self.bot.user:
            return
            
        # Only process if it's from the HC Bot to catch edits like "TOOK THE CATCH"
        from bot.config import ORIGINAL_HC_BOT_ID
        if ORIGINAL_HC_BOT_ID and after.author.id != ORIGINAL_HC_BOT_ID:
            return
            
        await self.on_message(after)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # We don't print every message to avoid spam

        # Ignore our own messages
        if message.author == self.bot.user:
            return
            
        # ---------------------------------------------------------
        # DEV-ONLY CATCH LISTENER TEST MODE
        # Easy to disable: set DEV_TEST_MODE to False
        # ---------------------------------------------------------
        DEV_TEST_MODE = True
        DEV_USER_ID = 898954315786502144
        
        if DEV_TEST_MODE and message.author.id == DEV_USER_ID:
            if is_catch_event(message):
                data = parse_catch(message)
                if data:
                    if not hasattr(self, "dev_pending_catches"):
                        self.dev_pending_catches = {}
                    self.dev_pending_catches[message.channel.id] = data
                    
                    await message.reply(
                        f"🔧 **[CATCH TEST] Opportunity detected**\n"
                        f"Fielder: <@{data['catcher_id']}>\n"
                        f"Batter: <@{data['batter_id']}>"
                    )
                return
                
            if is_catch_result(message):
                pending = getattr(self, "dev_pending_catches", {}).get(message.channel.id)
                if pending:
                    success = parse_catch_result(message)
                    fielder = pending["catcher_id"]
                    self.dev_pending_catches[message.channel.id] = None
                    
                    from bot.utils.events import is_janmashtami
                    pts = 20 if is_janmashtami() else 10
                    
                    if success:
                        await message.reply(
                            f"🔧 **[CATCH TEST] Result detected: TOOK THE CATCH**\n"
                            f"Fielder: <@{fielder}>\n"
                            f"Would award: +{pts} during Janmashtami"
                        )
                    else:
                        await message.reply(
                            f"🔧 **[CATCH TEST] Result detected: BOZO DROPPED THE CATCH**\n"
                            f"Fielder: <@{fielder}>\n"
                            f"Would award: -10"
                        )
                return
        # ---------------------------------------------------------
            
        # Check ORIGINAL_HC_BOT_ID
        from bot.config import ORIGINAL_HC_BOT_ID
        is_og_bot = (ORIGINAL_HC_BOT_ID and message.author.id == ORIGINAL_HC_BOT_ID)
            
        # Only listen to OG HC Bot, OR if it's a user pasting stats/uploading images
        if not is_og_bot and not message.author.bot:
            is_stats = is_raw_statistics(message)
            has_attachment = len(message.attachments) > 0
            if not is_stats and not has_attachment:
                return
        elif message.author.bot and not is_og_bot:
            # Ignore all other bots
            return
            
        # Optional: Only listen in specific channels
        if CAREER_CHANNEL_IDS and message.channel.id not in CAREER_CHANNEL_IDS:
            return

        channel_id = message.channel.id
        
        # Check if there's an active match in this channel
        active_match = await get_active_match(channel_id)
        
        # Check for Match Start FIRST
        if is_match_start(message):
            if active_match:
                if active_match.get("start_message_id") == message.id:
                    return
                await cancel_match(active_match["_id"])
                print(f"[MATCH] Overrode match {active_match['_id']}")
                
            # Link to upcoming match lifecycle
            upcoming = await upcoming_matches_col.find_one({
                "channel_id": channel_id, 
                "status": {"$in": ["SCHEDULED", "LIVE", "ANNOUNCED"]}
            }, sort=[("match_number", 1)])
            
            if upcoming:
                match_number = upcoming["match_number"]
                match_type = upcoming["match_type"]
                await upcoming_matches_col.update_one(
                    {"_id": upcoming["_id"]},
                    {"$set": {"status": "LIVE"}}
                )
                print(f"[MATCH] Linked start msg {message.id} to upcoming Match #{match_number}")
            else:
                match_number = 0
                match_type = "CLASSIC"
                
            new_match = await create_match(channel_id, message.id, match_number, match_type, str(ORIGINAL_HC_BOT_ID))
            match_disp = f"#{match_number}" if match_number > 0 else f"S3-{message.id}"
            
            print(f"[MATCH] Detected Match Start {match_disp}")
            await message.reply(f"🏏 **CAREER MODE MATCH DETECTED**\nMatch {match_disp} is now LIVE. Monitoring events and stats.")
            return

        if not active_match:
            return

        match_id = active_match["_id"]
        match_number = active_match.get("match_number", 0)
        match_type = active_match.get("match_type", "CLASSIC")
        match_disp = f"#{match_number}" if match_number > 0 else f"S3-{active_match['start_message_id']}"

        # Check for image (Match Summary Image)
        has_image = False
        image_url = None
        if message.attachments:
            for att in message.attachments:
                if att.content_type and att.content_type.startswith("image/"):
                    has_image = True
                    image_url = att.url
                    break
        if not has_image and message.embeds:
            for emb in message.embeds:
                if emb.image and emb.image.url:
                    has_image = True
                    image_url = emb.image.url
                    break
                elif emb.thumbnail and emb.thumbnail.url:
                    has_image = True
                    image_url = emb.thumbnail.url
                    break
                elif emb.type == 'image' and emb.url:
                    has_image = True
                    image_url = emb.url
                    break
                    
        if has_image:
            # Ignore GIFs (especially the live-status gif from OG bot)
            if image_url and (".gif" in image_url.lower() or "video-to-gif-converter" in image_url.lower()):
                has_image = False
                
        if has_image:
            upcoming_live = await upcoming_matches_col.find_one({
                "channel_id": channel_id,
                "status": {"$in": ["LIVE", "PENDING_APPROVAL"]}
            })
            if upcoming_live:
                await upcoming_matches_col.update_one(
                    {"_id": upcoming_live["_id"]},
                    {"$set": {"temp_latest_image_url": image_url}}
                )
                print(f"[MATCH] Stored result image for Match #{upcoming_live['match_number']}")
            return

        # Check for hattrick
        if is_hattrick_event(message):
            player_id = parse_hattrick(message)
            if player_id:
                added = await add_hattrick_to_match(match_id, player_id, message.id)
                if added:
                    print(f"[HATTRICK] Match {match_disp} — @{player_id}")
                    await message.reply(f"🔥 **HAT-TRICK DETECTED!** <@{player_id}> has taken a hat-trick! (+20 points)")
            return

        # Check for catch opportunities
        if match_type != "ELITE_NO_CATCHES":
            # Check if this exact message has already been processed as a completed catch result
            already_processed = any(c.get("message_id") == message.id for c in active_match.get("catches", []))
            
            # 1. Check for catch result FIRST
            if is_catch_result(message) and not already_processed:
                success = parse_catch_result(message)
                result_data = await resolve_pending_catch(match_id, success, message.id)
                
                if result_data:
                    if result_data.get("expired"):
                        print(f"[CATCH] Match {match_disp} — Pending catch expired. No points awarded.")
                        return

                    chat_cog = self.bot.get_cog("ChatListener")
                    from bot.database.players import update_player_stats
                    from bot.utils.events import is_janmashtami
                    
                    if success:
                        print(f"[CATCH] Match {match_disp} — Player {result_data['catcher_id']} caught {result_data['batter_id']}")
                        
                        catch_pts = 20 if is_janmashtami() else 10
                        
                        embed = discord.Embed(
                            title="🧤 Catch Taken!",
                            description=f"<@{result_data['catcher_id']}> successfully caught <@{result_data['batter_id']}>!\n\n**Points Update:** `+{catch_pts} Career Points`",
                            color=discord.Color.green()
                        )
                        gif_url = chat_cog.get_gif_for_category("catch_taken") if chat_cog else None
                        if gif_url:
                            embed.set_image(url=gif_url)
                            
                        await message.reply(embed=embed)
                        
                        await update_player_stats(
                            discord_id=result_data["catcher_id"],
                            stats_update={
                                "fielding.catches": 1,
                                "points": catch_pts
                            }
                        )
                    else:
                        print(f"[CATCH] Match {match_disp} — Player {result_data['catcher_id']} dropped catch")
                        
                        embed = discord.Embed(
                            title="❌ Catch Dropped!",
                            description=f"<@{result_data['catcher_id']}> dropped it!\n\n**Points Update:** `-10 Career Points`",
                            color=discord.Color.red()
                        )
                        gif_url = chat_cog.get_gif_for_category("catch_dropped") if chat_cog else None
                        if gif_url:
                            embed.set_image(url=gif_url)
                            
                        await message.reply(embed=embed)
                        
                        await update_player_stats(
                            discord_id=result_data["catcher_id"],
                            stats_update={
                                "fielding.catch_drops": 1,
                                "points": -10
                            },
                            push_updates={
                                "penalties": {
                                    "amount": 10,
                                    "reason": f"Dropped Catch in Match {match_disp}",
                                    "date": datetime.now(timezone.utc).isoformat(),
                                    "given_by": "SYSTEM"
                                }
                            }
                        )
                return

            # 2. THEN check for new catch opportunities
            if is_catch_event(message) and not already_processed:
                pending = active_match.get("pending_catch")
                # Avoid spamming if this exact message is already the active pending catch
                if pending and pending.get("message_id") == message.id:
                    return
                    
                catch_data = parse_catch(message)
                if catch_data:
                    await set_pending_catch(match_id, catch_data["catcher_id"], catch_data["batter_id"], message.id)
                    print(f"[CATCH] Pending catch detected for match {match_id}")
                    
                    embed = discord.Embed(
                        title="⏳ Catch Opportunity!",
                        description=f"Waiting to see if <@{catch_data['catcher_id']}> takes the catch...",
                        color=discord.Color.gold()
                    )
                    await message.reply(embed=embed)
                return

        if is_raw_statistics(message):
            players_data = parse_raw_statistics(message)
            if players_data:
                print(f"[STATS] Raw statistics detected. Pending approval.")
                
                # Set match to pending approval
                success = await set_match_pending(match_id, message.id, message.content)
                if success:
                    await message.channel.send(f"⚠️ **Pending Stats Detected!**\nStaff, please use `!addstats` to approve and update player profiles for Match #{match_id}.")
                else:
                    print(f"[DB] Ignoring duplicate stats for match {match_id}")
            else:
                await message.channel.send(f"⚠️ **CAREER MODE**\nDetected final stats but could not safely parse them for Match #{match_id}.")

    @commands.command(name="addstats", help="Approve pending stats for the current channel's match")
    @is_staff_ctx()
    async def addstats(self, ctx: commands.Context):
        channel_id = ctx.channel.id
        
        # Check upcoming match lifecycle status to prevent duplicates
        upcoming = await upcoming_matches_col.find_one({
            "channel_id": channel_id,
            "status": {"$in": ["LIVE", "RESULT_RECEIVED", "FINALIZED", "PENDING_APPROVAL"]}
        }, sort=[("match_number", -1)])
        
        if upcoming and upcoming["status"] == "FINALIZED":
            await ctx.send(f"❌ Match #{upcoming['match_number']} has already been finalized. Cannot award points twice.")
            return

        if ctx.message.reference and ctx.message.reference.message_id:
            replied_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            players_data = parse_raw_statistics(replied_msg)
            if players_data:
                # Treat this as a manual stat addition for the active match
                active_match = await get_active_match(channel_id)
                if not active_match:
                    # Fallback to checking if it's already pending
                    active_match = await get_pending_match(channel_id)
                
                if active_match:
                    match_id = active_match["_id"]
                    success = await set_match_pending(match_id, replied_msg.id, replied_msg.content)
                    if not success:
                        await ctx.send("❌ Failed to set match state to pending in DB.")
                        return
                else:
                    await ctx.send("❌ No active or pending match found in this channel to add these stats to.")
                    return
            else:
                await ctx.send("❌ Could not parse valid stats from the replied message. Make sure it contains the raw comma-separated list inside codeblocks.")
                return

        match = await get_pending_match(channel_id)
        if not match:
            await ctx.send("No pending match stats found. You can reply to a message containing the raw stats with `!addstats` to force them.")
            return
            
        players_data = parse_raw_statistics(match["raw_stats_text"])
        if not players_data:
            await ctx.send("Failed to parse the stored stats.")
            return
            
        embed = discord.Embed(
            title=f"🏏 Confirm Stats for Match #{upcoming.get('match_number', match['start_message_id']) if upcoming else match['start_message_id']}",
            description="Stats parsed successfully!\n\n**📸 RESULT IMAGE:**\nIf the bot hasn't automatically detected the result image yet, please **upload the result image** to this channel right now.\n\nOnce uploaded (or if it's already detected), click the **Confirm & Finalize Match** button below to award points and close the match.",
            color=discord.Color.blue()
        )
        
        if upcoming and upcoming.get("temp_latest_image_url"):
            embed.set_thumbnail(url=upcoming["temp_latest_image_url"])
            embed.add_field(name="Status", value="✅ Result image detected!")
        else:
            embed.add_field(name="Status", value="⚠️ Waiting for result image upload...")
            
        view = AddStatsConfirmView(self, ctx, match, players_data, upcoming)
        await ctx.send(embed=embed, view=view)

    async def _process_and_finalize_stats(self, ctx, match, players_data, upcoming=None, progress_msg=None):
        from bot.services.career import get_career_level
        from bot.database.players import get_player
        from bot.database.matches import approve_match_stats
        from bot.database.db import upcoming_matches_col, config_col
        from datetime import datetime, timezone
        import discord
        
        match_id = match["_id"]
        
        # Pre-fetch recorded hattricks to attribute them correctly
        recorded_hattricks = match.get("hattricks", [])
        hattrick_counts = {}
        for h in recorded_hattricks:
            h_id = h["player_id"]
            hattrick_counts[h_id] = hattrick_counts.get(h_id, 0) + 1

        # Ensure all bowlers with hattricks are in players_data
        existing_player_ids = {str(p["discord_id"]) for p in players_data}
        for cid in list(hattrick_counts.keys()):
            if cid not in existing_player_ids:
                players_data.append({
                    "discord_id": cid,
                    "player_name": f"Player {cid}",
                    "runs": 0, "balls_faced": 0, "out": False,
                    "runs_conceded": 0, "balls_bowled": 0, "wickets": 0,
                })
                existing_player_ids.add(cid)

        old_career_levels = {}
        total_players = len(players_data)

        for i, p_stat in enumerate(players_data):
            if progress_msg and (i + 1) % 5 == 0:
                try:
                    await progress_msg.edit(content=f"⏳ Updating players... ({i + 1}/{total_players})")
                except Exception:
                    pass
                    
            discord_id = p_stat["discord_id"]
            
            # Fetch existing player safely
            existing_player = await get_player(discord_id)
            
            # Store their old career level
            old_career_levels[discord_id] = get_career_level(existing_player.get("points", 0))

            # Add hattricks (Catches/Drops are now handled LIVE)
            p_stat["hattricks"] = hattrick_counts.get(discord_id, 0)

            points = calculate_player_points(p_stat)
            p_stat["points"] = points  # store calculated points for UI

            # Determine best bowling
            new_wickets = p_stat.get("wickets", 0)
            new_runs_conceded = p_stat.get("runs_conceded", 0)
            
            existing_bowling = existing_player.get("bowling", {})
            curr_best_wickets = existing_bowling.get("best_wickets", 0)
            curr_best_runs = existing_bowling.get("best_runs", 0)
            
            set_updates = {}
            if new_wickets > 0 or new_runs_conceded >= 0: # Only update if they bowled
                if p_stat.get("balls_bowled", 0) > 0:
                    is_better = False
                    if new_wickets > curr_best_wickets:
                        is_better = True
                    elif new_wickets == curr_best_wickets and new_wickets > 0:
                        if new_runs_conceded < curr_best_runs:
                            is_better = True
                    
                    if is_better:
                        set_updates["bowling.best_wickets"] = new_wickets
                        set_updates["bowling.best_runs"] = new_runs_conceded

            stats_update = {
                "points": points,
                "matches.played": 1,
                "batting.runs": p_stat.get("runs", 0),
                "batting.balls": p_stat.get("balls_faced", 0),
                "batting.fifties": 1 if 50 <= p_stat.get("runs", 0) < 100 else 0,
                "batting.hundreds": 1 if p_stat.get("runs", 0) >= 100 else 0,
                "batting.ducks": 1 if p_stat.get("runs", 0) == 0 and p_stat.get("out", False) else 0,
                "bowling.runs_conceded": p_stat.get("runs_conceded", 0),
                "bowling.balls": p_stat.get("balls_bowled", 0),
                "bowling.wickets": p_stat.get("wickets", 0),
                "bowling.threefers": 1 if 3 <= p_stat.get("wickets", 0) < 5 else 0,
                "bowling.fivefers": 1 if p_stat.get("wickets", 0) >= 5 else 0,
                "fielding.catches": p_stat.get("catches", 0),
                "fielding.catch_drops": p_stat.get("catch_drops", 0),
                "awards.hattricks": p_stat.get("hattricks", 0)
            }
            
            batted = (p_stat.get("balls_faced", 0) > 0) or (p_stat.get("runs", 0) > 0) or p_stat.get("out", False)
            bowled = (p_stat.get("balls_bowled", 0) > 0) or (p_stat.get("runs_conceded", 0) > 0) or (p_stat.get("wickets", 0) > 0)
            
            if batted:
                stats_update["batting.innings"] = 1
            if bowled:
                stats_update["bowling.innings"] = 1
            
            # Use max for highest score natively via mongo $max (handled in players.py)
            max_updates = {}
            if p_stat.get("runs", 0) > 0:
                max_updates["batting.highest_score"] = p_stat.get("runs", 0)
                
            push_updates = None
            penalties_to_log = []
            match_num_str = f"Match #{upcoming['match_number']}" if upcoming else f"Match {match_id}"
            
            # 1. Economy Penalty
            if p_stat.get("balls_bowled", 0) > 0:
                overs = p_stat.get("balls_bowled", 0) / 6.0
                economy = p_stat.get("runs_conceded", 0) / overs
                if economy >= 20.0:
                    penalties_to_log.append({
                        "amount": 10,
                        "reason": f"20+ Economy in {match_num_str}",
                        "date": datetime.now(timezone.utc).isoformat(),
                        "given_by": "SYSTEM"
                    })
                    
            # 2. Duck Penalty
            if p_stat.get("runs", 0) == 0 and p_stat.get("out", False) and p_stat.get("balls_faced", 0) > 0:
                penalties_to_log.append({
                    "amount": 20,
                    "reason": f"Duck in {match_num_str}",
                    "date": datetime.now(timezone.utc).isoformat(),
                    "given_by": "SYSTEM"
                })
                
            # 3. Catch Drop Penalty
            drops = p_stat.get("catch_drops", 0)
            if drops > 0:
                penalties_to_log.append({
                    "amount": drops * 10,
                    "reason": f"Dropped Catch ({drops}x) in {match_num_str}",
                    "date": datetime.now(timezone.utc).isoformat(),
                    "given_by": "SYSTEM"
                })
                
            if penalties_to_log:
                if len(penalties_to_log) == 1:
                    push_updates = {"penalties": penalties_to_log[0]}
                else:
                    push_updates = {"penalties": {"$each": penalties_to_log}}
                
            await update_player_stats(discord_id, stats_update, set_updates=set_updates, max_updates=max_updates, push_updates=push_updates)
            
            print(f"[POINTS] Updated player {discord_id}")

        # Finalize match in DB
        success = await approve_match_stats(match_id, players_data)
        if success:
            print(f"[DB] Match {match_id} finalized via !addstats.")
            
            # Post automatic Match Event GIFs
            from bot.services.gif_service import get_random_gif
            for pd in players_data:
                player_name = pd.get("player_name", "A player")
                runs = pd.get("runs", 0)
                wickets = pd.get("wickets", 0)
                
                gif_cat = None
                title = None
                if runs >= 100:
                    gif_cat = "century"
                    title = f"👑 {player_name} HITS A CENTURY!"
                elif runs >= 50:
                    gif_cat = "fifty"
                    title = f"🏏 {player_name} SCORES A FIFTY!"
                elif runs == 0 and pd.get("status", "").lower() == "out":
                    gif_cat = "duck"
                    title = f"🦆 {player_name} OUT FOR A DUCK!"
                elif wickets >= 5:
                    gif_cat = "fivefer"
                    title = f"🔥 {player_name} TAKES A 5-WICKET HAUL!"
                elif wickets >= 3:
                    gif_cat = "threefer"
                    title = f"🎯 {player_name} TAKES 3 WICKETS!"
                
                if gif_cat:
                    gif_url = get_random_gif(gif_cat)
                    if gif_url:
                        embed = discord.Embed(title=title, color=discord.Color.random())
                        try:
                            await self.ctx.channel.send(content=gif_url, embed=embed)
                        except:
                            pass
            
            forwarded_img_success = False
            if upcoming:
                # Forward the image to the info channel now that stats are approved
                if upcoming.get("temp_latest_image_url"):
                    guild_id = str(ctx.guild.id)
                    config = await config_col.find_one({"guild_id": guild_id})
                    if config and config.get("match_info_channel_id"):
                        info_ch = ctx.guild.get_channel(config["match_info_channel_id"])
                        if info_ch:
                            try:
                                content = f"🏏 **MATCH #{upcoming['match_number']}**\nOriginal HC Bot Result"
                                embed = discord.Embed(color=discord.Color.gold())
                                embed.set_image(url=upcoming["temp_latest_image_url"])
                                forwarded_msg = await info_ch.send(content, embed=embed)
                                
                                await upcoming_matches_col.update_one(
                                    {"_id": upcoming["_id"]},
                                    {"$set": {
                                        "result_message_id": forwarded_msg.id,
                                        "result_image_url": upcoming["temp_latest_image_url"],
                                        "result_received_at": datetime.now(timezone.utc)
                                    }}
                                )
                                forwarded_img_success = True
                                print(f"[MATCH] Forwarded final result image for Match #{upcoming['match_number']}")
                            except Exception as e:
                                print(f"[MATCH] Failed to forward final image: {e}")

                await upcoming_matches_col.update_one(
                    {"_id": upcoming["_id"]},
                    {"$set": {
                        "status": "FINALIZED",
                        "finalized_at": datetime.now(timezone.utc),
                        "finalized_by": str(ctx.author.id),
                        "raw_stats_message_id": match["raw_stats_message_id"]
                    }}
                )
            
            msg = f"✅ **Match Finalized!**\nStats and career points have been updated for {len(players_data)} players."
            
            if upcoming:
                if upcoming.get("temp_latest_image_url") and forwarded_img_success:
                    msg = f"✅ **Match #{upcoming['match_number']} Finalized!**\nStats and career points have been updated for {len(players_data)} players.\n📸 *Forwarded result image to Match Info.*"
                elif upcoming.get("temp_latest_image_url"):
                    msg = f"✅ **Match #{upcoming['match_number']} Finalized!**\nStats and career points have been updated for {len(players_data)} players.\n⚠️ *Image was detected but failed to forward (Check Match-Info channel permissions).* "
                else:
                    msg = f"✅ **Match #{upcoming['match_number']} Finalized!**\nStats and career points have been updated for {len(players_data)} players.\n⚠️ *No result image was found/detected during this match.*"
            elif progress_msg:
                # If there's a progress message and no upcoming match, edit it instead of sending a new one
                await progress_msg.edit(content=msg)
                
            if not progress_msg or upcoming:
                await ctx.send(msg)
            
            
            # --- Role Promotion Logic ---
            guild_id = str(ctx.guild.id)
            config = await config_col.find_one({"guild_id": guild_id})
            ranks_channel = None
            if config and config.get("player_ranks_channel_id"):
                ranks_channel = ctx.guild.get_channel(config["player_ranks_channel_id"])
                
            for discord_id, old_level_data in old_career_levels.items():
                try:
                    member = ctx.guild.get_member(int(discord_id))
                    if not member:
                        continue
                        
                    # Fetch new XP
                    updated_player = await get_player(discord_id)
                    new_level_data = get_career_level(updated_player.get("points", 0))
                    
                    if old_level_data["current"] != new_level_data["current"]:
                        # Level changed!
                        old_role_name = old_level_data["current"]
                        new_role_name = new_level_data["current"]
                        
                        old_role = discord.utils.get(ctx.guild.roles, name=old_role_name)
                        new_role = discord.utils.get(ctx.guild.roles, name=new_role_name)
                        
                        try:
                            if old_role and old_role in member.roles:
                                await member.remove_roles(old_role, reason="Career level promotion")
                            if new_role and new_role not in member.roles:
                                await member.add_roles(new_role, reason="Career level promotion")
                        except discord.Forbidden:
                            print(f"[WARN] Bot lacks Manage Roles permission for promotion of {member.display_name}")
                        except Exception as e:
                            print(f"[ERROR] Role promotion failed for {member.display_name}: {e}")
                            
                        # Send Promotion Announcement
                        if ranks_channel and new_role_name != "Local Team":
                            promo_msg = f"🎉 **CAREER PROMOTION**\n{member.mention} has leveled up to **{new_role_name.upper()}**! *(Career Points: {updated_player.get('points', 0)})*"
                            try:
                                await ranks_channel.send(promo_msg)
                            except discord.Forbidden:
                                pass
                                
                except Exception as e:
                    print(f"Error checking promotion for {discord_id}: {e}")

        else:
            await ctx.send("Failed to update match status in database.")

    @commands.command(name="prephistory", aliases=["prepstats"], help="Prepare a historical match for !addstats")
    @is_staff_ctx()
    async def prephistory(self, ctx: commands.Context, match_number: int, *, raw_stats: str = None):
        from bot.database.matches import get_pending_match
        from bot.database.db import matches_col
        from bot.services.stats_parser import parse_raw_statistics
        import asyncio
        
        channel_id = ctx.channel.id
        
        if not raw_stats:
            if ctx.message.reference and ctx.message.reference.message_id:
                try:
                    ref_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                    raw_stats = ref_msg
                except discord.NotFound:
                    await ctx.send("❌ Could not find the replied message.")
                    return
            else:
                await ctx.send("❌ You must either provide the raw stats or reply to a message containing them.")
                return
        
        # Check if a pending match already exists in this channel to prevent overwriting
        existing_pending = await get_pending_match(channel_id)
        if existing_pending:
            await ctx.send("❌ A pending match already exists in this channel. Please run `!addstats` or cancel it first.")
            return
            
        # Check if this exact historical match ID already exists and is finalized
        match_id = f"HIST-{match_number}"
        existing_match = await matches_col.find_one({"_id": match_id})
        if existing_match and existing_match.get("status") == "FINALIZED":
            await ctx.send(f"❌ Historical match #{match_number} has already been finalized. Duplicate processing prevented.")
            return
            
        # Extract string content for DB storage
        import discord
        if isinstance(raw_stats, discord.Message):
            raw_content = raw_stats.content or ""
            for embed in raw_stats.embeds:
                if embed.description:
                    raw_content += "\n" + embed.description
        else:
            raw_content = str(raw_stats)
            
        players_data = parse_raw_statistics(raw_stats)
        if not players_data:
            await ctx.send("❌ Failed to parse the stored stats. Check the format.")
            return
            
        # Create the historical pending match
        match_doc = {
            "_id": match_id,
            "channel_id": channel_id,
            "match_number": match_number,
            "status": "PENDING_APPROVAL",
            "raw_stats_text": raw_content.strip(),
            "source": "historical",
            "catches": [],
            "created_at": datetime.now(timezone.utc),
            "created_by": str(ctx.author.id),
            "raw_stats_message_id": ctx.message.id
        }
        
        # Upsert just in case it was created but not finalized
        await matches_col.update_one(
            {"_id": match_id},
            {"$set": match_doc},
            upsert=True
        )
        
        prompt_msg = await ctx.send(f"✅ **Historical Match #{match_number} Prepared!**\nFound {len(players_data)} players.\nPlease type `confirm` to process these stats now, or `cancel` to abort.")

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ["confirm", "cancel"]

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=60.0)
        except asyncio.TimeoutError:
            await matches_col.delete_one({"_id": match_id})
            await ctx.send("⏳ Time expired. Historical match preparation cancelled.")
            return

        if msg.content.lower() == "cancel":
            await matches_col.delete_one({"_id": match_id})
            await ctx.send("❌ Cancelled. Historical match was not saved.")
            return

        # Confirmed
        progress_msg = await ctx.send(f"⏳ Updating players... (0/{len(players_data)})")
        await self._process_and_finalize_stats(ctx, match_doc, players_data, upcoming=None, progress_msg=progress_msg)

    @commands.command(name="historystatus", help="Check the progress of historical match imports")
    @is_staff_ctx()
    async def historystatus(self, ctx: commands.Context):
        from bot.database.db import matches_col
        import discord
        
        START_MATCH = 31
        END_MATCH = 44
        TOTAL_MATCHES = (END_MATCH - START_MATCH) + 1
        
        # Query all finalized historical matches in the target range
        cursor = matches_col.find({
            "source": "historical", 
            "status": "FINALIZED",
            "match_number": {"$gte": START_MATCH, "$lte": END_MATCH}
        }).sort("match_number", 1)
        history_matches = await cursor.to_list(length=100)
        
        completed_count = len(history_matches)
        
        if completed_count == 0:
            await ctx.send(f"📊 **Historical Import Status**\n`0 / {TOTAL_MATCHES}` matches imported (Range {START_MATCH}-{END_MATCH}).\n\nStart importing by using `!prephistory {START_MATCH}`.")
            return
            
        # Get list of completed match numbers
        completed_numbers = [m["match_number"] for m in history_matches]
        
        # Calculate missing
        missing_numbers = [i for i in range(START_MATCH, END_MATCH + 1) if i not in completed_numbers]
        
        desc = f"**Progress:** `{completed_count} / {TOTAL_MATCHES}` (Matches {START_MATCH}-{END_MATCH})\n\n"
        
        if completed_count >= TOTAL_MATCHES:
            desc += "🎉 **All historical matches have been imported!**"
            color = discord.Color.green()
        else:
            desc += "**Missing Matches:**\n"
            if len(missing_numbers) > 15:
                desc += f"`{', '.join(map(str, missing_numbers[:10]))} ... and {len(missing_numbers)-10} more`"
            else:
                desc += f"`{', '.join(map(str, missing_numbers))}`"
            color = discord.Color.orange()
            
        embed = discord.Embed(
            title="📊 Historical Import Status",
            description=desc,
            color=color
        )
        await ctx.send(embed=embed)

    @commands.command(name="matches", help="View your recent matches")
    async def matches(self, ctx: commands.Context):
        from bot.database.db import matches_col
        
        discord_id = str(ctx.author.id)
        
        # Query DB for matches where this player is in the players array
        # Ensure status is FINALIZED
        cursor = matches_col.find(
            {"status": "FINALIZED", "players.discord_id": discord_id}
        ).sort("started_at", -1).limit(5)
        
        matches_list = await cursor.to_list(length=5)
        
        if not matches_list:
            await ctx.send("No recent matches found for you.")
            return
            
        desc = ""
        for m in matches_list:
            # Find the player's specific stats in this match
            p_stats = next((p for p in m["players"] if p["discord_id"] == discord_id), None)
            if p_stats:
                pts = p_stats.get('points', 0)
                runs = p_stats.get('runs', 0)
                wickets = p_stats.get('wickets', 0)
                catches = p_stats.get('catches', 0)
                desc += f"✅ **Match {m['_id']}** — {pts} pts (Runs: {runs}, Wkts: {wickets}, Catches: {catches})\n"
            
        embed = discord.Embed(
            title="🎮 Your Recent Matches",
            description=desc,
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @commands.command(name="activematches", help="List all currently active matches the bot is listening to")
    @is_staff_ctx()
    async def activematches(self, ctx: commands.Context):
        from bot.database.db import upcoming_matches_col
        upcoming = await upcoming_matches_col.find({"status": {"$in": ["LIVE", "PENDING_APPROVAL"]}}).to_list(length=20)
        
        if not upcoming:
            await ctx.send("No active matches found.")
            return
            
        desc = ""
        for m in upcoming:
            desc += f"**Match #{m['match_number']}** in <#{m['channel_id']}> ({m['status']})\n"
            
        embed = discord.Embed(
            title="📡 Active Matches",
            description=desc,
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @commands.command(name="fixdb45")
    @commands.is_owner()
    async def fixdb45(self, ctx: commands.Context):
        """Force cleans stale matches and renames today's matches to 43, 44, 45"""
        from bot.database.db import matches_col, upcoming_matches_col
        
        # 1. Rename Match 42 -> 43 (which used to be 34)
        await upcoming_matches_col.update_many({"match_number": 42}, {"$set": {"match_number": 43}})
        await matches_col.update_many({"match_number": 42}, {"$set": {"match_number": 43}})
        
        # 2. Rename Match 43 -> 44 (which used to be 35)
        await upcoming_matches_col.update_many({"match_number": 43}, {"$set": {"match_number": 44}})
        await matches_col.update_many({"match_number": 43}, {"$set": {"match_number": 44}})
        
        # 3. Rename the catches match in 1466290363382890529 (currently 44) to 45
        await upcoming_matches_col.update_many(
            {"channel_id": {"$in": [1466290363382890529, "1466290363382890529"]}, "status": {"$in": ["SCHEDULED", "LIVE", "ANNOUNCED"]}}, 
            {"$set": {"match_number": 45}}
        )
        await matches_col.update_many(
            {"channel_id": {"$in": [1466290363382890529, "1466290363382890529"]}, "status": {"$in": ["LIVE", "PENDING_APPROVAL", "RESULT_RECEIVED"]}}, 
            {"$set": {"match_number": 45}}
        )
        
        # 4. Wipe the old finalized match 25 so it stops blocking the channel if they accidentally ran addstats
        await upcoming_matches_col.delete_many({"match_number": 25})
        await matches_col.delete_many({"match_number": 25})
        await matches_col.delete_many({"_id": "HIST-25"})
        
        await ctx.send("✅ Schedule dynamically renamed! Matches are now 43, 44, and the Catches Game is 45.\nAlso deleted the conflicting Match 25 so it won't block you anymore.")


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
                preview_desc += f"- **{action}** by <@{up['catcher_id']}> ({up['pts']:+d} pts) [Msg: {msg.id}]\n"
                
        if not updates:
            await ctx.send("✅ No new missed catches found in the scanned history.")
            return
            
        embed = discord.Embed(title="Historical Catches Preview", description=preview_desc[:4000], color=discord.Color.gold())
        view = BackfillConfirmView(self, ctx, updates, processed_col)
        await ctx.send(content="⚠️ Review the pending catch recoveries below:", embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Matches(bot))
