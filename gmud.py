#!/usr/bin/env python3
import os
import time
from datetime import timezone
from dotenv import load_dotenv
import json
import time
from datetime import datetime
import asyncio
import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram import html

BOT_START_TIME = time.time()
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    print("Error: TELEGRAM_BOT_TOKEN not set in .env")
    exit(1)

DATA_FILE = "gmud_data.json"
COOLDOWN_MINUTES = 30
MAX_SUPPLY = 34_000_000
MAX_RECENT_DAMAGES = 5
SUPPLY_FETCH_ATTEMPTS=5
SUPPLY_FETCH_SES=4
# DEAD_WALLET_BALANCE = 311603
DEAD_WALLET_BALANCE = 0
DATA_LOCK = asyncio.Lock()

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
    return nickname[:max_length - 2] + ".."

def generate_progress_bar(current, maximum, length=25):
    # Progress toward next million
    current_million = current % 1_000_000
    ratio = current_million / 1_000_000
    filled = int(ratio * length)
    filled = min(length, filled+1) if current_million > 0 else 0
    empty = length - filled
    return "█" * filled + "-" * empty

def format_supplarius(current_supply, recent_damages, last_attacker, last_damage, players):
    progress_bar = generate_progress_bar(current_supply, MAX_SUPPLY)
    current_str = f"{current_supply:,}".replace(",", " ")
    max_str = f"{MAX_SUPPLY:,}".replace(",", " ")
    supply_line = f"[{current_str:>11} /{max_str:>11} ]"

    damage_lines = []
    for dmg, attacker in recent_damages[-MAX_RECENT_DAMAGES:]:
        if dmg == 0:
            nick = truncate_nickname(attacker, 12)
            line = f"      <miss>  "
            damage_lines.append(line.ljust(27))

        elif attacker == "":
            # Healing event
            heal_str = f"+{dmg:,}".replace(",", " ")
            line = f"{heal_str}               "
            damage_lines.append(line.rjust(27))

        else:
            dmg_str = f"{dmg:,}".replace(",", " ")
            nick = truncate_nickname(attacker, 12)
            line = f"-{dmg_str}  {nick:<12} "
            damage_lines.append(line.rjust(27))

    attacker_lines = []
    TOTAL_WIDTH = 27
    any_effect = True

    if last_damage > 0 and last_attacker != "":
        dmg_str = f"{last_damage:,}".replace(",", " ")
        attacker_nick = truncate_nickname(last_attacker)
        attacker_lines.append(f" > {attacker_nick} deals  ".ljust(TOTAL_WIDTH))
        attacker_lines.append(f"   {dmg_str} [Fire Damage]".ljust(TOTAL_WIDTH))
        attacker_lines.append("   to the Dragonlord.    ".ljust(TOTAL_WIDTH))

    elif last_damage == 0 and last_attacker != "":
        attacker_nick = truncate_nickname(last_attacker)
        attacker_lines.append(f" > {attacker_nick} misses!".ljust(TOTAL_WIDTH))
        attacker_lines.append("   Attack had no effect! ".ljust(TOTAL_WIDTH))
        any_effect = False

    elif last_attacker == "" and last_damage > 0:
        heal_str = f"{last_damage:,}".replace(",", " ")
        attacker_lines.append(" > The Dragonlord heals!  ".ljust(TOTAL_WIDTH))
        attacker_lines.append(f"   +{heal_str} Hit Points. ".ljust(TOTAL_WIDTH))

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
        ".[ Until next million:     ].",
        f".[{progress_bar}].",
        ".                           .",
    ]

    for line in reversed(damage_lines):
        lines.append(f".{line}.")

    if any_effect:
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
        ])

    lines.extend([
        "-----------------------------",
    ])

    for line in attacker_lines:
        lines.append(f".{line}.")

    lines.append("-----------------------------")

    return "\n".join(lines)

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            data.setdefault('recent_damages', [])
            data.setdefault('last_attacker', "")
            data.setdefault('last_damage', 0)
            return data
    return {
        "last_supply": None,
        "players": {},
        "recent_damages": [],
        "last_attacker": "",
        "last_damage": 0
    }

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def get_cooldown_remaining(last_attack_time):
    if not last_attack_time:
        return 0
    elapsed = time.time() - last_attack_time
    return max(0, COOLDOWN_MINUTES * 60 - elapsed)

def format_time(seconds):
    if seconds <= 0:
        return "0s"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"

async def get_gns_total_supply():
    url = "https://backend-polygon.gains.trade/stats"

    for attempt in range(SUPPLY_FETCH_ATTEMPTS):
        try:
            async with httpx.AsyncClient(timeout=SUPPLY_FETCH_SES) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                if data and 'stats' in data and len(data['stats']) > 0:
                    return data['stats'][0]['token_supply'] - DEAD_WALLET_BALANCE 
                return None

        except Exception as e:
            print(f"[Attempt {attempt+1}/{SUPPLY_FETCH_ATTEMPTS}] Error fetching supply: {e}")
            if attempt < 2:
                await asyncio.sleep(0.5)

    return None

async def handle_sup_command(message: Message):
    async with DATA_LOCK:
        print("Sup command detected")

        # Skip messages sent before bot started
        message_ts = message.date.replace(tzinfo=timezone.utc).timestamp()

        if message_ts < BOT_START_TIME:
            print("Ignoring stale message")
            return  # ignore old messages

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

        cd = get_cooldown_remaining(player['last_attack'])
        if cd > 0:
            await message.reply(f"⏳ You can attack again in: *{format_time(cd)}*", parse_mode="Markdown")
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

        # -------------------------
        # Healing logic
        # NO COOLDOWN
        # -------------------------
        if damage < 0:
            healed = -damage
            data['recent_damages'].append((healed, ""))   # empty attacker
            data['last_attacker'] = ""
            data['last_damage'] = healed

            # NOTE: cooldown NOT applied
            data['last_supply'] = current_supply
            save_data(data)

            supplarius = format_supplarius(
                current_supply,
                data['recent_damages'],
                data['last_attacker'],
                data['last_damage'],
                data['players']
            )
            await message.reply(code_block(supplarius), parse_mode="MarkdownV2")
            return

        # -------------------------
        # Normal attack logic
        # -------------------------
        data['recent_damages'].append((damage, username))
        data['last_attacker'] = username
        data['last_damage'] = damage
        player['last_attack'] = time.time()

        if damage > 0:
            player['damage'] += damage

        data['last_supply'] = current_supply
        save_data(data)

        supplarius = format_supplarius(
            current_supply,
            data['recent_damages'],
            data['last_attacker'],
            data['last_damage'],
            data['players']
        )

        await message.reply(code_block(supplarius), parse_mode="MarkdownV2")

async def handle_gmud_command(message: Message):
    async with DATA_LOCK:
        message_ts = message.date.replace(tzinfo=timezone.utc).timestamp()
        if message_ts < BOT_START_TIME:
            print("Ignoring stale message")
            return

        data = load_data()
        players = data.get("players", {})

        if not players:
            await message.reply(". No attacks have been recorded yet. .", parse_mode="MarkdownV2")
            return

        # Sort all players by damage descending
        sorted_players = sorted(players.items(), key=lambda x: x[1]['damage'], reverse=True)

        lines = [
            "---------------------------",
            ".    GMUD LEADERBOARDS    .",
            "---------------------------",
        ]

        # Format each player: nickname and total damage
        TOTAL_WIDTH = 27
        for username, pdata in sorted_players:
            nick = truncate_nickname(username, 12)  # shorter nickname to fit
            dmg_str = f"{pdata['damage']:,}".replace(",", " ")
            line_content = f" {nick:<12} {dmg_str:>10} "
            lines.append(f".{line_content}.")

        lines.append("---------------------------")

        # Send as code block
        leaderboard_text = code_block("\n".join(lines))
        await message.reply(leaderboard_text, parse_mode="MarkdownV2")

# ---------------------------------------------------
# MAIN
# ---------------------------------------------------

async def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN not set")
        return

    bot = Bot(token)
    dp = Dispatcher()

    dp.message.register(handle_sup_command, F.text.startswith("/sup"))
    dp.message.register(handle_gmud_command, F.text.startswith("/gmud"))

    print("🤖 GNS Supply Boss Bot running...")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
