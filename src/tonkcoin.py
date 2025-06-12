import aiosqlite
from datetime import datetime, timedelta
import random
import os
import hashlib
import time

# Global variables
BLOCKCHAIN = []
DIFFICULTY = 5; # Number of leading zeros required
DB = os.path.join(os.path.dirname(__file__), "database.db")
MINE_COOLDOWN = timedelta(minutes=10)

# Database init
async def setup_db():
    async with aiosqlite.connect(DB) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            balance INTEGER DEFAULT 0,
            last_mine TEXT
        )""")
        await db.commit()

# Crypto functions
def calculate_hash(index, timestamp, value, previous_hash, nonce):
    block_string = f"{index}{timestamp}{value}{previous_hash}{nonce}"
    return hashlib.sha256(block_string.encode()).hexdigest()

def create_genesis_block():
    return {
        "index": 0,
        "timestamp": time.time(),
        "value": 0,
        "previous_hash": "0",
        "nonce": 0,
        "hash": calculate_hash(0, time.time(), 0, "0", 0),
        "miner_id": None
    }

def get_last_block():
    if not BLOCKCHAIN:
        BLOCKCHAIN.append(create_genesis_block())
    return BLOCKCHAIN[-1]

async def mine_block(user_id):
    last_block = get_last_block()
    index = last_block["index"] + 1
    timestamp = time.time()
    value = random.randint(10, 50)
    previous_hash = last_block["hash"]
    nonce = 0

    while True:
        hash_attempt = calculate_hash(index, timestamp, value, previous_hash, nonce)
        if hash_attempt.startswith("0" * DIFFICULTY):
            break
        nonce += 1

    block = {
        "index": index,
        "timestamp": timestamp,
        "value": value,
        "previous_hash": previous_hash,
        "nonce": nonce,
        "hash": hash_attempt,
        "miner_id": user_id
    }
    BLOCKCHAIN.append(block)
    await add_balance(user_id, value)
    return block

# General bot functions
async def get_balance(user_id):
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("SELECT balance FROM users WHERE user_id = ?", (str(user_id),))
        row = await cursor.fetchone()
        return row[0] if row else 0

async def add_user(user_id):
    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (str(user_id),))
        await db.commit()

async def mine(user_id):
    await add_user(user_id)
    now = datetime.utcnow()
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("SELECT last_mine FROM users WHERE user_id = ?", (str(user_id),))
        row = await cursor.fetchone()
        if row and row[0]:
            last_mine = datetime.fromisoformat(row[0])
            if now - last_mine < MINE_COOLDOWN:
                return None  # Too early to mine

        reward = random.randint(10, 50)
        await db.execute("UPDATE users SET balance = balance + ?, last_mine = ? WHERE user_id = ?",
                         (reward, now.isoformat(), str(user_id)))
        await db.commit()
        return reward

async def transfer(sender_id, receiver_id, amount):
    if amount <= 0:
        return False
    await add_user(sender_id)
    await add_user(receiver_id)
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("SELECT balance FROM users WHERE user_id = ?", (str(sender_id),))
        row = await cursor.fetchone()
        if row[0] < amount:
            return False
        await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, str(sender_id)))
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, str(receiver_id)))
        await db.commit()
        return True

async def add_balance(user_id, amount):
    await add_user(user_id)
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, str(user_id)))
        await db.commit()

async def lower_balance(user_id, amount):
    await add_user(user_id)
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("SELECT balance FROM users WHERE user_id = ?", (str(user_id),))
        row = await cursor.fetchone()
        if row and row[0] < amount:
            return False
        await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, str(user_id)))
        await db.commit()
        return True

async def reset_balance(user_id):
    await add_user(user_id)
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("UPDATE users SET balance = 0 WHERE user_id = ?", (str(user_id),))
        await db.commit()
        return cursor.rowcount > 0

async def get_leaderboard(limit=10):
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT ?", (limit,))
        return await cursor.fetchall()

async def change_balance(user_id, amount):
    await add_user(user_id)
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, str(user_id)))
        await db.commit()
