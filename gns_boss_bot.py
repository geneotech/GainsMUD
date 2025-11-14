#!/usr/bin/env python3
"""
GNS Supply Boss bot using aiogram 3.x
"""

import os
import json
import time
from datetime import datetime
import asyncio
import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram import html

# Configuration
DATA_FILE = "gns_boss_data.json"
COOLDOWN_MINUTES = 0.01
MAX_SUPPLY = 34_000_000
MAX_RECENT_DAMAGES = 5

def code_block(text: str) -> str:
    replacements = {
        '\\': '\\\\',
        '`': '\\`',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return "```\n" + text + "\n```"

def truncate_nickname(nickname, max_length=15):
    if len(nickname) <= max_length:
        return nickname
    return nickname[:max_length-2] + ".."

def generate_progress_bar(current, maximum, length=25):
    ratio = current / maximum
    filled = int(ratio * length)
    filled = max(filled, 1)
    empty = length - filled
    return "█" * filled + "-" * empty

def format_supplarius(current_supply, recent_damages, last_attacker, last_damage, players):
    progress_bar = generate_progress_bar(current_supply, MAX_SUPPLY)
    current_str = f"{current_supply:,}".replace(",", " ")
    max_str = f"{MAX_SUPPLY:,}".replace(",", " ")
    supply_line = f"[{current_str:>11} /{max_str:>11} ]"

    damage_lines = []
    for (dmg, attacker) in recent_damages[-MAX_RECENT_DAMAGES:]:
        nick = truncate_nickname(attacker, 12)
        if dmg == 0:
            line = f"           ✖  {nick:<12}"
            damage_lines.append(line.ljust(27))
        else:
            dmg_str = f"{dmg:,}".replace(",", " ")
            line = f"-{dmg_str}  {nick:<12} "
            damage_lines.append(line.rjust(27))

    attacker_nick = truncate_nickname(last_attacker)
    TOTAL_WIDTH = 27

    if last_damage > 0:
        dmg_str = f"{last_damage:,}".replace(",", " ")
        attacker_line1 = f" > {attacker_nick} deals  ".ljust(TOTAL_WIDTH)
        attacker_line2 = f"   {dmg_str} Fire Damage".ljust(TOTAL_WIDTH)
    else:
        attacker_line1 = f" > {attacker_nick} misses!".ljust(TOTAL_WIDTH)
        attacker_line2 = "   Attack had no effect!".ljust(TOTAL_WIDTH)

    sorted_players = sorted(players.items(), key=lambda x: x[1]['damage'], reverse=True)
    leaderboard_lines = []
    for username, data in sorted_players[:3]:
        nick = truncate_nickname(username, 15)
        dmg_str = f"{data['damage']:,}".replace(",", " ")
        leaderboard_lines.append(f" {nick:<15} {dmg_str:>9} ")

    guild_total = sum(p['damage'] for p in players.values())
    guild_str = f"{guild_total:,}".replace(",", " ")

    lines = [
        "-----------------------------",
        ".[SUPPLARIUS THE DRAGONLORD].",
        ".[                         ].",
        f".{supply_line}.",
        f".[{progress_bar}].",
        ".                           .",
    ]
    for line in reversed(damage_lines):
        lines.append(f".{line}.")

    lines.extend([
        ".                           .",
        ".                    ,-,-   .",
        ".                   / / |   .",
        ". ,-'             _/ / /    .",
        ".(-_          _,-' `Z_/     .",
        ". \"#:      ,-'_,-.    \\  _  .",
        ".  #'    _(_-'_()\\     \\\" | .",
        ".,--_,--'                 | .",
        ". \"\"                      L-.",
        ".,--^---v--v-._        /   \\.",
        ". \\_________________,-'     .",
        ".                  \\        .",
        ".                   \\       .",
        ".                    \\      .",
        ".                           .",
        "-----------------------------",
    ])

    lines.extend([
        ". Damage leaderboard:       .",
        ".                           .",
    ])

    for line in leaderboard_lines:
        lines.append(f".{line}.")

    lines.extend([
        ".                           .",
        f". Guild Total     {guild_str:>9} .",
        "-----------------------------",
    ])

    lines.extend([
        f".{attacker_line1}.",
        f".{attacker_line2}."
    ])

    if last_damage > 0:
        lines.append(".   to the Dragonlord.      .")

    lines.append("-----------------------------")

    return "\n".join(lines)

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            data.setdefault('recent_damages', [])
            data.setdefault('last_attacker', "Unknown")
            data.setdefault('last_damage', 0)
            return data
    return {
        "last_supply": None,
        "players": {},
        "recent_damages": [],
        "last_attacker": "Unknown",
        "last_damage": 0
    }

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def get_cooldown_remaining(last_attack_time):
    if not last_attack_time:
        return 0
    elapsed = time.time() - last_attack_time
    return max(0, COOLDOWN_MINUTES*60 - elapsed)

def format_time(seconds):
    if seconds <= 0:
        return "0s"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"

async def get_gns_total_supply():
    url = "https://backend-arbitrum.gains.trade/stats"

    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                if data and 'stats' in data and len(data['stats']) > 0:
                    return data['stats'][0]['token_supply']
                return None

        except Exception as e:
            print(f"[Attempt {attempt+1}/3] Error fetching supply: {e}")
            if attempt < 2:
                await asyncio.sleep(0.5)

    return None

# ---------------------------
# Command handlers
# ---------------------------

async def handle_sup_command(message: Message):
    print("Sup command detected")

    user = message.from_user
    username = (
        user.full_name
        or user.first_name
        or user.username
        or f"User{user.id}"
    )

    data = load_data()

    if username not in data['players']:
        data['players'][username] = {'damage': 0, 'last_attack': None}

    player = data['players'][username]
    cooldown_remaining = get_cooldown_remaining(player['last_attack'])
    if cooldown_remaining > 0:
        await message.reply(f"⏳ You can attack again in: *{format_time(cooldown_remaining)}*", parse_mode="Markdown")
        return

    current_supply = await get_gns_total_supply()
    if current_supply is None:
        await message.reply("❌ Failed to fetch GNS supply. Try again later.")
        return

    if data['last_supply'] is None:
        data['last_supply'] = current_supply
        save_data(data)
        await message.reply(
            f"🎮 *BOSS BATTLE INITIALIZED!*\n\n🐉 HP: *{current_supply:,}*\nAttack again to deal damage!",
            parse_mode="Markdown"
        )
        return

    damage = data['last_supply'] - current_supply

    if damage < 0:
        healed = -damage
        data['recent_damages'].append((0, username))
        data['last_attacker'] = username
        data['last_damage'] = 0
        player['last_attack'] = time.time()
        save_data(data)

        healed_str = f"{healed:,}".replace(",", " ")
        await message.reply(
            f"💚 *The Dragonlord has healed*\n{healed_str} *Hit Points!*",
            parse_mode="Markdown"
        )
        return

    # Normal damage logic
    data['recent_damages'].append((damage, username))
    data['last_attacker'] = username
    data['last_damage'] = damage
    player['last_attack'] = time.time()

    if damage > 0:
        player['damage'] += damage

    data['last_supply'] = current_supply
    save_data(data)

    supplarius = format_supplarius(current_supply, data['recent_damages'], username, damage, data['players'])
    await message.reply(code_block(supplarius), parse_mode="MarkdownV2")

async def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN not set")
        return

    bot = Bot(token)
    dp = Dispatcher()

    dp.message.register(handle_sup_command, F.text.startswith("/sup"))

    print("🤖 GNS Supply Boss Bot running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
