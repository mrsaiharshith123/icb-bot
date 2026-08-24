import discord

class LeaderboardPagination(discord.ui.View):
    def __init__(self, interaction, get_page_func, total_pages, current_user_id):
        super().__init__(timeout=120)
        self.interaction = interaction
        self.get_page_func = get_page_func
        self.total_pages = total_pages
        self.current_page = 1
        self.current_user_id = current_user_id
        
        # Update buttons initial state
        self.update_buttons()
        
    def update_buttons(self):
        self.first_btn.disabled = self.current_page == 1
        self.prev_btn.disabled = self.current_page == 1
        self.next_btn.disabled = self.current_page == self.total_pages
        self.last_btn.disabled = self.current_page == self.total_pages
        self.page_indicator.label = f"Page {self.current_page} / {self.total_pages}"
        
    async def update_page(self, interaction):
        embed = await self.get_page_func(self.current_page, self.current_user_id)
        self.update_buttons()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(emoji="⏪", style=discord.ButtonStyle.secondary, custom_id="lb_first")
    async def first_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 1
        await self.update_page(interaction)
        
    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.primary, custom_id="lb_prev")
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page -= 1
        await self.update_page(interaction)

    @discord.ui.button(label="Page 1 / 1", style=discord.ButtonStyle.secondary, disabled=True, custom_id="lb_indicator")
    async def page_indicator(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass # Just an indicator
        
    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.primary, custom_id="lb_next")
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page += 1
        await self.update_page(interaction)

    @discord.ui.button(emoji="⏩", style=discord.ButtonStyle.secondary, custom_id="lb_last")
    async def last_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = self.total_pages
        await self.update_page(interaction)

    @discord.ui.button(label="🔎 My Rank", style=discord.ButtonStyle.success, row=1)
    async def my_rank_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # The embed generation logic handles pinning "Your Rank" at the bottom footer.
        # But if they click this, maybe we jump to the page containing their rank?
        # That would require fetching their rank index. We will let the `get_page_func` handle it by passing page 0.
        embed, target_page = await self.get_page_func(0, self.current_user_id) # 0 means "find my page"
        if target_page:
            self.current_page = target_page
        self.update_buttons()
        await interaction.response.edit_message(embed=embed, view=self)
