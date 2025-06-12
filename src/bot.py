import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import tonkcoin

# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# Set up intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Create bot instance
bot = commands.Bot(command_prefix="$", intents=intents, help_command=None)

@bot.event
async def on_ready():
    await tonkcoin.setup_db()
    activity = discord.Activity(type=discord.ActivityType.listening, name="$help")
    await bot.change_presence(status=discord.Status.online, activity=activity)
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")

@bot.command()
async def balance(ctx):
    bal = await tonkcoin.get_balance(ctx.author.id)
    await ctx.send(f"{ctx.author.mention}, you have {bal} 🪙 TonkCoins.")

@bot.command()
async def mine(ctx):
    try:
        block = await tonkcoin.mine_block(ctx.author.id)
        await ctx.send(
            f"{ctx.author.mention} mined block #{block['index']} and earned {block['value']} 🪙 TonkCoins!\n"
            f"Hash: `{block['hash'][:16]}...`"
        )
    except Exception as e:
        print(f"Error in mine: {e}")  # Log the error for yourself
        await ctx.send("❌ An error occurred while mining. Please try again later.")

@bot.command()
async def pay(ctx, member: discord.Member, amount: int):
    if member.id == ctx.author.id:
        await ctx.send("You can't pay yourself.")
        return

    success = await tonkcoin.transfer(ctx.author.id, member.id, amount)
    if success:
        await ctx.send(f"{ctx.author.mention} sent {amount} 🪙 TonkCoins to {member.mention}!")
    else:
        await ctx.send("❌ Transaction failed. Do you have enough TonkCoins?")

@bot.command()
async def gamble(ctx, amount: int):
    if amount <= 0:
        await ctx.send("You must gamble more than 0 TonkCoins.")
        return

    bal = await tonkcoin.get_balance(ctx.author.id)
    if bal < amount:
        await ctx.send("You don't have enough TonkCoins to gamble that amount.")
        return

    from random import random
    if random() < 0.5:
        await tonkcoin.change_balance(ctx.author.id, -amount)
        await ctx.send(f"{ctx.author.mention}, you lost {amount} 🪙 TonkCoins. Better luck next time!")
    else:
        await tonkcoin.change_balance(ctx.author.id, amount)
        await ctx.send(f"{ctx.author.mention}, you won {amount} 🪙 TonkCoins! Nice!")

@bot.command()
async def leaderboard(ctx):
    top = await tonkcoin.get_leaderboard()
    if not top:
        await ctx.send("Leaderboard is empty.")
        return

    msg = "**🏆 TonkCoin Leaderboard 🏆**\n"
    for i, (user_id, balance) in enumerate(top, 1):
        user = await bot.fetch_user(int(user_id))
        msg += f"{i}. {user.name} — {balance} 🪙\n"

    await ctx.send(msg)

@bot.command()
async def give(ctx, member: discord.Member, amount: int):
    if ctx.author.id != ADMIN_ID:
        await ctx.send("❌ You are not authorized to use this command.")
        return

    if amount <= 0:
        await ctx.send("Amount must be greater than 0.")
        return

    await tonkcoin.add_balance(member.id, amount)
    await ctx.send(f"{ctx.author.mention} gave {amount} 🪙 TonkCoins to {member.mention}.")

@bot.command()
async def remove(ctx, member: discord.Member, amount: int):
    if ctx.author.id != ADMIN_ID:
        await ctx.send("❌ You are not authorized to use this command.")
        return
    
    if amount <= 0:
        await ctx.send("Amount must be greater than 0")
        return
    
    await tonkcoin.lower_balance(member.id, amount)
    await ctx.send(f"{ctx.author.mention} removed {amount} 🪙 TonkCoins from {member.mention}.")

@bot.command()
async def reset(ctx, member: discord.Member):
    if ctx.author.id != ADMIN_ID:
        await ctx.send("❌ You are not authorized to use this command.")
        return

    success = await tonkcoin.reset_balance(member.id)
    if success:
        await ctx.send(f"{ctx.author.mention} reset 🪙 TonkCoins for {member.mention}.")
    else:
        await ctx.send("User not found or could not reset balance.")


@bot.command(name="help")
async def custom_help(ctx):
    help_message = """
**📖 TonkCoin Bot Help**

🪙 `$mine` — Mine TonkCoins (10-minute cooldown).
💰 `$balance` — Check your TonkCoin balance.
💸 `$pay @user <amount>` — Send TonkCoins to another user.
🎰 `$gamble <amount>` — Gamble your TonkCoins (50/50 chance).
🏆 `$leaderboard` — Show the top 10 richest users.
🛠️ `$help` — Show this help message.

🔒 Admin-only:
⚙️ `$give @user <amount>` — Give TonkCoins to a user (admin only).
⚙️ `$remove @user <amount>` — Remove TonkCoins from a user (admin only).
⚙️ `$reset @user` — Reset user coin balance (admin only).

*If the bot doesn't respond, check if you have DMs enabled!*
"""
    try:
        await ctx.author.send(help_message)
        await ctx.send(f"{ctx.author.mention}, I’ve sent you a DM with all my commands! 💌")
    except discord.Forbidden:
        await ctx.send(f"{ctx.author.mention}, I couldn't DM you. Please enable DMs from server members.")

@bot.command()
async def stop(ctx):
    await ctx.send("Shutting down...")
    await bot.close()

bot.run(TOKEN)
