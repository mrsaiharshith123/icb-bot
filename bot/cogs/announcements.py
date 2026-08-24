import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import asyncio

from bot.database.db import config_col, upcoming_matches_col, daily_announcements_col
from bot.utils.permissions import is_staff_ctx

MATCH_TYPES = {
    "CLASSIC": "CLASSIC",
    "ELITE_NO_CATCHES": "ELITE WITHOUT CATCH",
    "ELITE_CATCHES": "ELITE WITH CATCH"
}

class MatchReminderSelectView(discord.ui.View):
    def __init__(self, daily_id: str):
        super().__init__(timeout=60)
        self.daily_id = daily_id
        
    @discord.ui.select(
        placeholder="Select which matches to be reminded for...",
        min_values=1,
        max_values=3,
        options=[
            discord.SelectOption(label="Classic", value="CLASSIC"),
            discord.SelectOption(label="Elite Without Catch", value="ELITE_NO_CATCHES"),
            discord.SelectOption(label="Elite With Catch", value="ELITE_CATCHES")
        ]
    )
    async def select_matches(self, interaction: discord.Interaction, select: discord.ui.Select):
        selected_types = select.values
        user_id = str(interaction.user.id)
        
        # We need to find the specific match documents linked to this daily announcement
        from bson import ObjectId
        matches = await upcoming_matches_col.find({"daily_announcement_id": ObjectId(self.daily_id)}).to_list(length=3)
        
        if not matches:
            await interaction.response.edit_message(content="❌ These matches are no longer available.", view=None)
            return
            
        success_types = []
        for match in matches:
            if match["match_type"] in selected_types:
                # Add user to reminder_users
                await upcoming_matches_col.update_one(
                    {"_id": match["_id"]},
                    {"$addToSet": {"reminder_users": user_id}}
                )
                success_types.append(MATCH_TYPES[match["match_type"]])
                
        await interaction.response.edit_message(content=f"✅ You will receive DMs at the start time for:\n" + "\n".join([f"• {t}" for t in success_types]), view=None)

class DailyReminderButtonView(discord.ui.View):
    def __init__(self, daily_id: str):
        # We make it persistent by supplying a custom ID that contains the daily_id
        super().__init__(timeout=None)
        self.daily_id = daily_id
        
        btn = discord.ui.Button(label="🔔 REMIND ME", style=discord.ButtonStyle.success, custom_id=f"remind_daily_{daily_id}")
        btn.callback = self.remind_callback
        self.add_item(btn)
        
    async def remind_callback(self, interaction: discord.Interaction):
        # Show ephemeral selection menu
        view = MatchReminderSelectView(self.daily_id)
        await interaction.response.send_message("Select the matches you want to be reminded about:", view=view, ephemeral=True)


class ConfirmDailyAnnouncementView(discord.ui.View):
    def __init__(self, ctx, config, channels, times_data, announcement_text):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.config = config
        self.channels = channels
        self.times_data = times_data
        self.announcement_text = announcement_text
        
    @discord.ui.button(label="CONFIRM", style=discord.ButtonStyle.success)
    async def confirm_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        guild_id = str(interaction.guild_id)
        tz_str = self.config.get("timezone", "Asia/Kolkata")
        
        # 1. Insert Daily Announcement
        daily_doc = {
            "guild_id": guild_id,
            "scheduled_at": self.times_data["announce_utc"],
            "timezone": tz_str,
            "announcement_channel_id": self.config.get("announcement_channel_id"),
            "announcement_text": self.announcement_text,
            "announcement_sent": False,
            "announcement_message_id": None,
            "announcement_sent_at": None,
            "created_by": str(interaction.user.id),
            "created_at": datetime.now(ZoneInfo("UTC"))
        }
        
        insert_res = await daily_announcements_col.insert_one(daily_doc)
        daily_id = insert_res.inserted_id
        
        # 2. Get Next Match Number
        # We'll just grab the max match number and increment
        last_match = await upcoming_matches_col.find_one({"guild_id": guild_id}, sort=[("match_number", -1)])
        next_num = (last_match["match_number"] + 1) if last_match else 22
        
        # 3. Insert the 3 matches
        match_docs = []
        types_order = ["CLASSIC", "ELITE_NO_CATCHES", "ELITE_CATCHES"]
        for i, m_type in enumerate(types_order):
            doc = {
                "guild_id": guild_id,
                "daily_announcement_id": daily_id,
                "match_number": next_num + i,
                "match_type": m_type,
                "scheduled_at": self.times_data["match_utcs"][m_type],
                "timezone": tz_str,
                "channel_id": self.channels[m_type].id,
                "status": "SCHEDULED",
                "reminder_users": [],
                "reminder_sent_users": [],
                "og_result_message_id": None,
                "result_message_id": None,
                "result_image_url": None,
                "result_received_at": None
            }
            match_docs.append(doc)
            
        await upcoming_matches_col.insert_many(match_docs)
        
        await interaction.followup.edit_message(message_id=interaction.message.id, content="✅ Daily Schedule saved successfully! The plain-text announcement will be sent at the configured time.", embed=None, view=None)

    @discord.ui.button(label="CANCEL", style=discord.ButtonStyle.danger)
    async def cancel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ Scheduling cancelled.", embed=None, view=None)


class DailyAnnouncementModal(discord.ui.Modal, title="Set Match & Announcement Times"):
    classic_time = discord.ui.TextInput(label="Classic Time", placeholder="7:00 PM", required=True)
    elite_nc_time = discord.ui.TextInput(label="Elite Without Catch Time", placeholder="7:30 PM", required=True)
    elite_c_time = discord.ui.TextInput(label="Elite With Catch Time", placeholder="8:00 PM", required=True)
    announce_time = discord.ui.TextInput(label="Announcement Time", placeholder="6:30 PM", required=True)
    custom_comment = discord.ui.TextInput(
        label="Custom Comment",
        style=discord.TextStyle.paragraph,
        default="PLAYER POINTS WILL COME SOON",
        required=True
    )
    
    def __init__(self, view_instance):
        super().__init__()
        self.view_instance = view_instance
        self.config = view_instance.config

    async def on_submit(self, interaction: discord.Interaction):
        # Parse timezone
        tz_str = self.config.get("timezone", "Asia/Kolkata")
        try:
            tz = ZoneInfo(tz_str)
        except Exception:
            tz_str = "Asia/Kolkata"
            tz = ZoneInfo("Asia/Kolkata")
            
        now_local = datetime.now(tz)
        
        # Parse date
        raw_date = self.view_instance.date_selection.strip().upper()
        if raw_date == "TOMORROW":
            target_date = now_local + timedelta(days=1)
            date_header = "TOMORROW'S"
        elif raw_date == "TODAY":
            target_date = now_local
            date_header = "TODAY'S"
        else:
            try:
                target_date = datetime.strptime(raw_date, "%d/%m/%Y").replace(tzinfo=tz)
                date_header = target_date.strftime("%d/%m/%Y") + "'S"
            except ValueError:
                await interaction.response.send_message("❌ Invalid date format. Please use `DD/MM/YYYY` or `TOMORROW`.", ephemeral=True)
                return

        # Helper to parse time strings
        def parse_time(time_str):
            # Parse just the time, then combine with target_date
            parsed = datetime.strptime(time_str.strip(), "%I:%M %p").time()
            return datetime.combine(target_date.date(), parsed, tzinfo=tz).astimezone(ZoneInfo("UTC"))
            
        try:
            classic_utc = parse_time(self.classic_time.value)
            elite_nc_utc = parse_time(self.elite_nc_time.value)
            elite_c_utc = parse_time(self.elite_c_time.value)
            
            # Announce time could potentially be on the current day if scheduling for tomorrow
            # We assume the announce time date is whatever is logical. Usually it's today if scheduling for tomorrow.
            # But let's just parse it using target_date, unless target_date is tomorrow and announce_time is in the past?
            # Safe assumption: use target_date for announce time as well.
            announce_utc = parse_time(self.announce_time.value)
            
            # If announcement time is logically before the current time, we should assume it meant today?
            # We'll just use target_date. If they want today, they should set Date to TODAY.
        except ValueError as e:
            await interaction.response.send_message(f"❌ Invalid time format. Please use `HH:MM AM/PM` (e.g. 7:00 PM).\nError: {e}", ephemeral=True)
            return

        times_data = {
            "announce_utc": announce_utc,
            "match_utcs": {
                "CLASSIC": classic_utc,
                "ELITE_NO_CATCHES": elite_nc_utc,
                "ELITE_CATCHES": elite_c_utc
            }
        }
        
        role_ping = ""
        if "player_role_id" in self.config:
            role_ping = f"<@&{self.config['player_role_id']}>"
            
        custom_comment_text = self.custom_comment.value.strip().upper()
            
        announcement_text = f"""{role_ping}

**{custom_comment_text}

{date_header} MATCHES:
<#{self.view_instance.channels["CLASSIC"].id}> - {self.classic_time.value.strip().upper()} (CLASSIC)
<#{self.view_instance.channels["ELITE_NO_CATCHES"].id}> - {self.elite_nc_time.value.strip().upper()} (ELITE WITHOUT CATCH)
<#{self.view_instance.channels["ELITE_CATCHES"].id}> - {self.elite_c_time.value.strip().upper()} (ELITE WITH CATCH)

IF ANY STAFF FORGETS TO START, TAG US WE WILL START THE MATCH**"""

        preview_embed = discord.Embed(title="Preview Daily Announcement", description=f"```\n{announcement_text}\n```\n**Announcement Time:** {self.announce_time.value.strip().upper()}", color=discord.Color.gold())
        
        view = ConfirmDailyAnnouncementView(self.view_instance.ctx, self.config, self.view_instance.channels, times_data, announcement_text)
        await interaction.response.edit_message(content="Please confirm the exact text that will be sent:", embed=preview_embed, view=view)


class DailyChannelsSelectView(discord.ui.View):
    def __init__(self, ctx, config):
        super().__init__(timeout=300)
        self.ctx = ctx
        self.config = config
        self.channels = {
            "CLASSIC": None,
            "ELITE_NO_CATCHES": None,
            "ELITE_CATCHES": None
        }
        self.date_selection = None

    @discord.ui.select(cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.text], placeholder="Select Classic Channel", row=0)
    async def select_classic(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        self.channels["CLASSIC"] = select.values[0]
        await self.check_ready(interaction)

    @discord.ui.select(cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.text], placeholder="Select Elite Without Catch Channel", row=1)
    async def select_elite_nc(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        self.channels["ELITE_NO_CATCHES"] = select.values[0]
        await self.check_ready(interaction)
        
    @discord.ui.select(cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.text], placeholder="Select Elite With Catch Channel", row=2)
    async def select_elite_c(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        self.channels["ELITE_CATCHES"] = select.values[0]
        await self.check_ready(interaction)
        
    @discord.ui.select(
        placeholder="Select Date",
        options=[
            discord.SelectOption(label="Today", value="TODAY"),
            discord.SelectOption(label="Tomorrow", value="TOMORROW")
        ],
        row=3
    )
    async def select_date(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.date_selection = select.values[0]
        await self.check_ready(interaction)
        
    async def check_ready(self, interaction: discord.Interaction):
        if all(self.channels.values()) and self.date_selection:
            self.btn_next.disabled = False
        await interaction.response.edit_message(view=self)
        
    @discord.ui.button(label="Next: Set Times", style=discord.ButtonStyle.primary, row=4, disabled=True, custom_id="btn_next")
    async def btn_next(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(DailyAnnouncementModal(self))


class Announcements(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.announcement_loop.start()
        self.reminder_loop.start()

    def cog_unload(self):
        self.announcement_loop.cancel()
        self.reminder_loop.cancel()

    @commands.command(name="announce", help="Schedule the plain-text daily matches announcement.")
    @is_staff_ctx()
    async def announce(self, ctx: commands.Context):
        guild_id = str(ctx.guild.id)
        config = await config_col.find_one({"guild_id": guild_id})
        
        if not config or not config.get("announcement_channel_id"):
            await ctx.send("❌ Server is not configured. Please ask an admin to use `!setup`.")
            return
            
        embed = discord.Embed(
            title="📅 Schedule Daily Matches",
            description="Select the 3 match channels using the dropdowns below. Once all 3 are selected, click **Next**.",
            color=discord.Color.blue()
        )
        
        view = DailyChannelsSelectView(ctx, config)
        await ctx.send(embed=embed, view=view)

    @commands.command(name="upcoming", help="View upcoming Career Mode matches.")
    async def upcoming(self, ctx: commands.Context):
        cursor = upcoming_matches_col.find({"guild_id": str(ctx.guild.id), "status": "SCHEDULED"}).sort("scheduled_at", 1)
        matches = await cursor.to_list(length=10)
        
        if not matches:
            await ctx.send("There are no upcoming matches scheduled right now.")
            return
            
        desc = ""
        for m in matches:
            try: tz = ZoneInfo(m.get("timezone", "Asia/Kolkata"))
            except: tz = ZoneInfo("Asia/Kolkata")
                
            dt = m["scheduled_at"]
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=ZoneInfo("UTC"))
                
            local_dt = dt.astimezone(tz)
            time_str = local_dt.strftime("%I:%M %p")
            
            m_type_name = MATCH_TYPES.get(m.get("match_type", "CLASSIC"), "Match")
            
            desc += f"**#{m['match_number']} — {m_type_name.upper()}**\n"
            desc += f"🕐 {time_str}\n"
            desc += f"📍 <#{m['channel_id']}>\n\n"
            
        embed = discord.Embed(title="🏏 UPCOMING CAREER MODE", description=desc, color=discord.Color.green())
        await ctx.send(embed=embed)

    @tasks.loop(seconds=30)
    async def announcement_loop(self):
        now = datetime.now(ZoneInfo("UTC"))
        
        # Atomic find and update
        doc = await daily_announcements_col.find_one_and_update(
            {"announcement_sent": False, "scheduled_at": {"$lte": now}},
            {"$set": {"announcement_sent": True, "announcement_sent_at": now}}
        )
        
        if doc:
            guild_id = doc["guild_id"]
            channel_id = doc["announcement_channel_id"]
            
            guild = self.bot.get_guild(int(guild_id))
            if not guild: return
            
            channel = guild.get_channel(channel_id)
            if not channel: return
            
            view = DailyReminderButtonView(str(doc["_id"]))
            
            try:
                # Allowed mentions to ping the role but not @everyone
                allowed_mentions = discord.AllowedMentions(roles=True, users=False, everyone=False)
                msg = await channel.send(doc["announcement_text"], view=view, allowed_mentions=allowed_mentions)
                
                await daily_announcements_col.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {"announcement_message_id": msg.id}}
                )
                print(f"[MATCH] Daily Announcement {doc['_id']} sent!")
            except Exception as e:
                print(f"[MATCH] Failed to send daily announcement {doc['_id']}: {e}")
                # We could potentially revert announcement_sent = False here for retry

    @tasks.loop(seconds=30)
    async def reminder_loop(self):
        now = datetime.now(ZoneInfo("UTC"))
        
        # Find all scheduled matches whose time has come
        cursor = upcoming_matches_col.find({"status": "SCHEDULED", "scheduled_at": {"$lte": now}})
        matches = await cursor.to_list(length=None)
        
        for match in matches:
            guild_id = match["guild_id"]
            guild = self.bot.get_guild(int(guild_id))
            
            if guild:
                remind_users = match.get("reminder_users", [])
                sent_users = match.get("reminder_sent_users", [])
                
                target_chan = guild.get_channel(match["channel_id"])
                target_link = target_chan.jump_url if target_chan else f"<#{match['channel_id']}>"
                m_type_name = MATCH_TYPES.get(match.get("match_type", "CLASSIC"), "Match").upper()
                
                # Ping the channel for everyone
                if target_chan:
                    config = await config_col.find_one({"guild_id": guild_id})
                    if config and "player_role_id" in config:
                        role_ping = f"<@&{config['player_role_id']}>"
                        try:
                            await target_chan.send(
                                f"{role_ping} 🏏 **The {m_type_name} match is starting now!** Join up!",
                                allowed_mentions=discord.AllowedMentions(roles=True)
                            )
                        except Exception as e:
                            print(f"[MATCH] Failed to ping match channel {target_chan.id}: {e}")
                
                dm_content = f"🏏 **ICB CAREER MODE**\n\nYour {m_type_name} match is starting now!\n\n📍 <#{match['channel_id']}>\n\n🔗 [JOIN MATCH]({target_link})"
                
                for uid in remind_users:
                    if uid not in sent_users:
                        # Attempt to DM and atomically add to sent_users
                        # We do it atomically in DB per user to survive crashes mid-loop
                        updated = await upcoming_matches_col.update_one(
                            {"_id": match["_id"], "reminder_sent_users": {"$ne": uid}},
                            {"$push": {"reminder_sent_users": uid}}
                        )
                        if updated.modified_count > 0:
                            try:
                                user = guild.get_member(int(uid)) or await self.bot.fetch_user(int(uid))
                                if user:
                                    await user.send(dm_content)
                            except Exception:
                                pass # DMs disabled
                                
            # Mark match as LIVE
            await upcoming_matches_col.update_one(
                {"_id": match["_id"]},
                {"$set": {"status": "LIVE"}}
            )
            print(f"[MATCH] Reminders sent for Match #{match['match_number']} and set to LIVE.")

    @announcement_loop.before_loop
    @reminder_loop.before_loop
    async def before_loops(self):
        await self.bot.wait_until_ready()
        
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.component:
            custom_id = interaction.data.get("custom_id", "")
            if custom_id.startswith("remind_daily_"):
                # Handle persistent view click
                daily_id = custom_id.replace("remind_daily_", "")
                view = MatchReminderSelectView(daily_id)
                await interaction.response.send_message("Select the matches you want to be reminded about:", view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Announcements(bot))
