import discord
from discord.ext import commands
from bot.database.economy import get_balance, add_coins
from bot.utils.permissions import is_staff_ctx

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.hybrid_command(name="balance", aliases=["bal", "coins"], description="Check your HC Coin balance")
    async def balance_cmd(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        balance = await get_balance(str(target.id))
        
        embed = discord.Embed(
            title="💰 Account Balance",
            description=f"**{target.display_name}** currently has **{balance:,} HC Coins** 🪙",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="give", description="Give some of your coins to another player")
    async def give_cmd(self, ctx, member: discord.Member, amount: int):
        if amount <= 0:
            await ctx.send("❌ You must give a positive amount of coins.")
            return
            
        if member.id == ctx.author.id:
            await ctx.send("❌ You cannot give coins to yourself.")
            return
            
        sender_id = str(ctx.author.id)
        receiver_id = str(member.id)
        
        sender_balance = await get_balance(sender_id)
        if sender_balance < amount:
            await ctx.send(f"❌ You don't have enough coins! You only have {sender_balance:,} 🪙")
            return
            
        # Execute transfer
        await add_coins(sender_id, -amount)
        new_receiver_balance = await add_coins(receiver_id, amount)
        
        embed = discord.Embed(
            title="💸 Transfer Successful",
            description=f"You successfully sent **{amount:,} HC Coins** 🪙 to **{member.display_name}**.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        
    @commands.hybrid_command(name="addcoins", description="[STAFF] Add coins to a player")
    @is_staff_ctx()
    async def addcoins_cmd(self, ctx, member: discord.Member, amount: int):
        new_balance = await add_coins(str(member.id), amount)
        await ctx.send(f"✅ Added {amount:,} coins to **{member.display_name}**. New balance: {new_balance:,} 🪙")
        
    @commands.hybrid_command(name="shop", description="View the HC Coin shop")
    async def shop_cmd(self, ctx):
        import json
        import os
        
        shop_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'shop.json')
        if not os.path.exists(shop_path):
            await ctx.send("❌ The shop is currently empty.")
            return
            
        with open(shop_path, 'r', encoding='utf-8') as f:
            items = json.load(f)
            
        embed = discord.Embed(title="🛒 HC Coin Shop", description="Use `!buy <item_id>` to purchase an item.", color=discord.Color.blue())
        for item in items:
            embed.add_field(
                name=f"{item.get('emoji', '📦')} {item['name']} (ID: `{item['id']}`)",
                value=f"**Price:** {item['price']:,} 🪙\n{item['description']}",
                inline=False
            )
            
        await ctx.send(embed=embed)
        
    @commands.hybrid_command(name="buy", description="Buy an item from the shop")
    async def buy_cmd(self, ctx, item_id: str):
        import json
        import os
        from bot.database.economy import add_item_to_inventory
        
        shop_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'shop.json')
        if not os.path.exists(shop_path):
            await ctx.send("❌ The shop is currently empty.")
            return
            
        with open(shop_path, 'r', encoding='utf-8') as f:
            items = json.load(f)
            
        target_item = next((item for item in items if item['id'].lower() == item_id.lower()), None)
        if not target_item:
            await ctx.send(f"❌ Item ID `{item_id}` not found in the shop.")
            return
            
        discord_id = str(ctx.author.id)
        balance = await get_balance(discord_id)
        
        if balance < target_item['price']:
            await ctx.send(f"❌ You don't have enough coins! You need **{target_item['price']:,}** 🪙, but you only have **{balance:,}** 🪙.")
            return
            
        await add_coins(discord_id, -target_item['price'])
        await add_item_to_inventory(discord_id, target_item['id'], 1)
        
        await ctx.send(f"✅ You successfully purchased **{target_item['name']}** {target_item.get('emoji', '📦')} for {target_item['price']:,} 🪙!")
        
    @commands.hybrid_command(name="inventory", aliases=["inv"], description="Check your inventory")
    async def inventory_cmd(self, ctx):
        from bot.database.players import get_player
        import json
        import os
        
        discord_id = str(ctx.author.id)
        player = await get_player(discord_id)
        inventory = player.get("economy", {}).get("inventory", [])
        
        if not inventory:
            await ctx.send("🎒 Your inventory is empty.")
            return
            
        shop_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'shop.json')
        shop_items = {}
        if os.path.exists(shop_path):
            with open(shop_path, 'r', encoding='utf-8') as f:
                for item in json.load(f):
                    shop_items[item['id']] = item
                    
        embed = discord.Embed(title=f"🎒 {ctx.author.display_name}'s Inventory", color=discord.Color.blue())
        for inv_item in inventory:
            item_id = inv_item['item_id']
            qty = inv_item['quantity']
            
            shop_data = shop_items.get(item_id, {})
            name = shop_data.get('name', item_id)
            emoji = shop_data.get('emoji', '📦')
            
            embed.add_field(name=f"{emoji} {name}", value=f"Quantity: **{qty}**", inline=True)
            
        await ctx.send(embed=embed)
        
    @commands.hybrid_command(name="use", description="Use an item from your inventory")
    async def use_cmd(self, ctx, item_id: str):
        from bot.database.players import get_player, players_col
        from bot.services.fantasy_service import generate_random_card
        
        discord_id = str(ctx.author.id)
        player = await get_player(discord_id)
        inventory = player.get("economy", {}).get("inventory", [])
        
        target_item = next((i for i in inventory if i['item_id'].lower() == item_id.lower() and i['quantity'] > 0), None)
        
        if not target_item:
            await ctx.send(f"❌ You don't have a `{item_id}` in your inventory.")
            return
            
        # Deduct item
        await players_col.update_one(
            {"_id": discord_id, "economy.inventory.item_id": target_item['item_id']},
            {"$inc": {"economy.inventory.$.quantity": -1}}
        )
        
        if target_item['item_id'] == "mystery_pack":
            card = await generate_random_card(discord_id)
            if not card:
                await ctx.send("❌ Error pulling card. No eligible players in the database.")
                # Refund
                await players_col.update_one(
                    {"_id": discord_id, "economy.inventory.item_id": target_item['item_id']},
                    {"$inc": {"economy.inventory.$.quantity": 1}}
                )
                return
                
            rarity_colors = {
                "Common": discord.Color.light_grey(),
                "Rare": discord.Color.blue(),
                "Epic": discord.Color.purple(),
                "Legendary": discord.Color.gold(),
                "Mythic": discord.Color.red()
            }
            
            embed = discord.Embed(
                title="🎁 Mystery Pack Opened!",
                description=f"You pulled a **{card['rarity']}** card!",
                color=rarity_colors.get(card['rarity'], discord.Color.default())
            )
            embed.add_field(name="Player", value=f"<@{card['player_id']}>")
            embed.add_field(name="Rating", value=f"⭐ {card['rating']}")
            embed.set_footer(text="Use -cards to view your collection!")
            
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"⚠️ `{item_id}` is a cosmetic item and cannot be actively used.")

async def setup(bot):
    await bot.add_cog(Economy(bot))
