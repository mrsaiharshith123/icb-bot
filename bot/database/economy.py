from bot.database.players import get_player, players_col

async def add_coins(discord_id: str, amount: int) -> int:
    """Adds (or subtracts) coins for a user and returns their new balance."""
    discord_id = str(discord_id)
    # Ensure player exists and has the new schema
    await get_player(discord_id)
    
    res = await players_col.find_one_and_update(
        {"_id": discord_id},
        {"$inc": {"economy.coins": amount}},
        return_document=True
    )
    return res["economy"]["coins"]

async def get_balance(discord_id: str) -> int:
    """Gets a user's current coin balance."""
    player = await get_player(discord_id)
    return player.get("economy", {}).get("coins", 0)

async def add_item_to_inventory(discord_id: str, item_id: str, quantity: int = 1):
    """Adds an item to a player's inventory."""
    discord_id = str(discord_id)
    await get_player(discord_id)
    
    # Check if item exists in inventory
    player = await players_col.find_one({"_id": discord_id, "economy.inventory.item_id": item_id})
    
    if player:
        # Increment existing
        await players_col.update_one(
            {"_id": discord_id, "economy.inventory.item_id": item_id},
            {"$inc": {"economy.inventory.$.quantity": quantity}}
        )
    else:
        # Push new item
        await players_col.update_one(
            {"_id": discord_id},
            {"$push": {"economy.inventory": {"item_id": item_id, "quantity": quantity}}}
        )
