#!/usr/bin/env python3
import os
import re
import time
from datetime import timezone, datetime, timedelta
from dateutil.relativedelta import relativedelta
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

BACKEND_URL = "https://backend-polygon.gains.trade/stats"
DATA_FILE = "gmud_data.json"
COOLDOWN_MINUTES = 30
MAX_SUPPLY = 34_000_000
MAX_RECENT_DAMAGES = 5
SUPPLY_FETCH_ATTEMPTS = 5
SUPPLY_FETCH_SES = 4
# DEAD_WALLET_BALANCE = 311603
DEAD_WALLET_BALANCE = 0
DATA_LOCK = asyncio.Lock()

extra_message_last_shown_date = None  # Track last date the extra message was shown

def boss_name(supply):
    if supply < 26_000_000:
        return "Serpent"

    return "Dragonlord"

def code_block(text: str) -> str:
    replacements = {
        '\\': '\\\\',
        '`': '\\`',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return "```\n" + text + "\n```"

def clean_string(s):
    # Remove emojis / surrogate pairs
    # This regex removes characters outside the basic multilingual plane (BMP)
    return re.sub(r'[\U00010000-\U0010FFFF]', '', s)

def truncate_nickname(nickname, max_length=15):
    cleaned = clean_string(nickname)
    if len(cleaned) <= max_length:
        return cleaned
    return cleaned[:max_length - 2] + ".."

def generate_progress_bar(current, maximum, length=25):
    # Progress toward next million
    current_million = current % 1_000_000
    ratio = current_million / 1_000_000
    filled = int(ratio * length)
    filled = min(length, filled+1) if current_million > 0 else 0
    empty = length - filled
    return "█" * filled + "-" * empty

def format_supplarius(current_supply, recent_damages, last_attacker, last_damage, players, crossed_million=False):
    global extra_message_last_shown_date

    progress_bar = generate_progress_bar(current_supply, MAX_SUPPLY)
    current_str = f"{current_supply:,}".replace(",", " ")
    max_str = f"{MAX_SUPPLY:,}".replace(",", " ")
    supply_line = f"[{current_str:>11} /{max_str:>11} ]"

    damage_lines = []
    for dmg, attacker in recent_damages[-MAX_RECENT_DAMAGES:]:
        if dmg == 0:
            nick = truncate_nickname(attacker, 12)
            line = f"      <miss>  {nick:<12} "
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

    dragon_name = boss_name(current_supply)

    if last_damage > 0 and last_attacker != "":
        dmg_str = f"{last_damage:,}".replace(",", " ")
        attacker_nick = truncate_nickname(last_attacker)
        attacker_lines.append(f" > {attacker_nick} deals  ".ljust(TOTAL_WIDTH))
        attacker_lines.append(f"   {dmg_str} [Fire Damage]".ljust(TOTAL_WIDTH))
        attacker_lines.append(f"   to the {dragon_name}.    ".ljust(TOTAL_WIDTH))

    elif last_damage == 0 and last_attacker != "":
        attacker_nick = truncate_nickname(last_attacker)
        attacker_lines.append(f" > {attacker_nick} misses!".ljust(TOTAL_WIDTH))
        attacker_lines.append("   Attack had no effect! ".ljust(TOTAL_WIDTH))
        any_effect = False

    elif last_attacker == "" and last_damage > 0:
        heal_str = f"{last_damage:,}".replace(",", " ")
        attacker_lines.append(f" > The {dragon_name} heals!  ".ljust(TOTAL_WIDTH))
        attacker_lines.append(f"   +{heal_str} Hit Points. ".ljust(TOTAL_WIDTH))

    sorted_players = sorted(players.items(), key=lambda x: x[1]['damage'], reverse=True)
    leaderboard_lines = []
    for username, data in sorted_players[:3]:
        nick = truncate_nickname(username, 15)
        dmg_str = f"{data['damage']:,}".replace(",", " ")
        leaderboard_lines.append(f" {nick:<15} {dmg_str:>9} ")

    guild_total = sum(p['damage'] for p in players.values())
    guild_str = f"{guild_total:,}".replace(",", " ")


    if current_supply < 26_000_000:
        lines = [
            "-----------------------------",
            ".[   THE ANCIENT SERPENT   ].",
            ".[                         ].",
        ]
    else:
        lines = [
            "-----------------------------",
            ".[SUPPLARIUS THE DRAGONLORD].",
            ".[                         ].",
        ]

    lines = lines + [
        f".{supply_line}.",
        ".[ Until next million:     ].",
        f".[{progress_bar}].",
        ".                           .",
    ]

    for line in reversed(damage_lines):
        lines.append(f".{line}.")

    if any_effect:
        if crossed_million:
            lines.extend([
                ".                           .",
                ".###########################.",
                ".       CRITICAL HIT        .",
                ".###########################.",
                ".  BOSS ENTERS NEXT STAGE!  .",
                ".###########################.",
                ".                           .",
                ".        ,-'         ,-,-   .",
                ".       (-_         / / |   .",
                ". ,-'      #:     _/ / /    .",
                ".(-_      #'  _,-' `Z_/     .",
                ". \"#:      ,-'_,-.    \\  _  .",
                ".  #'    _(XX'_XX\\     \\\" | .",
                ".,--_,--'                 | .",
                ". \"\"                      L-.",
                ".\------v--v-.         /   \\.",
                ". --^--------/         |    .",
                ". \\_________________,-'     .",
                ".                           .",
            ])
        else:
            if current_supply < 26_000_000:
                lines.extend([
                    ".                           .",
                    ".      ,===:'.,             .",                    
                    ". ,-'       `:.`---.__      .",                  
                    ".(-_          `:.     `--.  .",                  
                    ". \"#:          \.        `..",                  
                    ".  #'   (,,(,    \.         .",
                    ".    (,'     `/   \.   ,--._.",                  
                    ".,  ,'  ,--.  `,   \.;'     .",                  
                    ". `{D, {    \  :    \;      .",                  
                    ".   V,,'    /  /    //      .",                  
                    ".   j;;    /  ,' ,-//.    ,-.",                  
                    ".   \;'   /  ,' /  _  \  /  .",                  
                    ".         \   `'  / \  `'  /.",                  
                    ".          `.___,'   `.__,' .",
                    ".                           ."
                ])
            elif current_supply < 27_000_000:
                # Show extra message once per day
                today = datetime.now(timezone.utc).date()
                show_extra_message = (extra_message_last_shown_date is None or 
                                     extra_message_last_shown_date != today)
                
                if show_extra_message:
                    lines.extend([
                        ".                           .",
                        ".---------------------------.",
                        ".     ABANDON ALL HOPE,     .",
                        ".         YE, WHO           .",
                        ".       DARE FIGHT ME       .",
                        ".---------------------------.",
                    ])
                    extra_message_last_shown_date = today

                lines.extend([
                    ".                           .",
                    ".           /           /   .",                                                    
                    ".  ,-'     /' .,,,,  ./     .",                                           
                    ". (-_     /';'     ,/       .",                                           
                    ".  \"#:   / /   ,,//,`'`     .",                                           
                    ".   #'  (_,, '_,  ,,,' ``   .",                                           
                    ".   #   |@\__/@  ,,, ;\" `   .",                                           
                    ". (-,  /        ,''/' `,``  .",                                           
                    ".   - /   .     ./, `,, ` ; .",                                           
                    ".  ,./  .   ,-,',` ,,/''\\,' .",                                           
                    ". |   /; ./,,'`,,'' |   |   .",                                           
                    ". |     /   ','    /    |   .",                                           
                    ".  \\___/'   '     |     |   .",                                           
                    ".    `,,'  |      /     `\\  .",                                           
                    ".         /      |        ~\\.",                                           
                    ".        '       (          .",                                           
                    ".       :                   .",                                           
                    ".      ; .         \--      .",                                           
                    ".    :   \         ;        ."
                ])
            else:
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
    url = BACKEND_URL

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
            if attempt < SUPPLY_FETCH_ATTEMPTS - 1:
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
        
        # Check if we crossed a million mark downwards
        # e.g. 30,050,000 -> 29,950,000
        old_millions = data['last_supply'] // 1_000_000
        new_millions = current_supply // 1_000_000
        crossed_million = (new_millions < old_millions)

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
            data['players'],
            crossed_million=crossed_million
        )

        if crossed_million:
            data['recent_damages'] = []
            save_data(data)

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
            await message.reply("No attacks have been recorded yet", parse_mode="MarkdownV2")
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

async def handle_burn_command(message: Message):
    # Skip messages sent before bot started
    message_ts = message.date.replace(tzinfo=timezone.utc).timestamp()

    if message_ts < BOT_START_TIME:
        print("Ignoring stale message")
        return  # ignore old messages

    # --- parse argument ---
    text = message.text.strip().split()
    periods_to_show = []  # list of tuples: (label, days)
    header = "    Burn:"

    if len(text) > 1:
        args = text[1].lower().split(",")
        for arg in args:
            try:
                added_arg = arg
                if arg.endswith("d"):
                    days = int(arg[:-1])
                elif arg.endswith("m"):
                    # subtract months properly
                    target_date = datetime.now(timezone.utc) - relativedelta(months=int(arg[:-1]))
                    days = (datetime.now(timezone.utc).date() - target_date.date()).days
                elif arg.endswith("y"):
                    # subtract years properly
                    target_date = datetime.now(timezone.utc) - relativedelta(years=int(arg[:-1]))
                    days = (datetime.now(timezone.utc).date() - target_date.date()).days
                else:
                    # no suffix, treat as days
                    days = int(arg)
                    added_arg = arg + "d"
                periods_to_show.append((added_arg, days))
            except ValueError:
                await message.reply(f"❌ Invalid number format: {arg}")
                return
    else:
        # default periods
        periods_to_show = [("1d",1), ("7d",7), ("30d",30), ("365d",365)]

    # --- fetch supply history ---
    async with httpx.AsyncClient(timeout=5) as client:
        try:
            r = await client.get(BACKEND_URL)
            r.raise_for_status()
            entries = r.json().get("stats", [])
        except:
            await message.reply("❌ Failed to fetch supply history.")
            return

    if not entries:
        await message.reply("❌ No supply history available.")
        return

    today_supply = entries[0]["token_supply"] - DEAD_WALLET_BALANCE

    # --- helper: pick entry by exact date ---
    def pick_entry_by_days_strict(entries, days: int):
        target_date = (datetime.now(timezone.utc) - timedelta(days=days)).date()
        for e in entries:
            date_str = e.get("date")
            if not date_str:
                continue
            entry_date = datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()
            if entry_date == target_date:
                return e
        return None

    # --- formatting helpers ---
    LABEL_WIDTH = 5  # right-align period labels
    BEFORE_PCT = 5   
    NUM_WIDTH = 10
    PCT_WIDTH = 7
    SEP="----------------------------"

    def format_burn_line(label, burned, pct):
        if pct < 10:
            # two decimals, no leading space
            pct_fmt = f"{pct:.2f}%"
        else:
            # one decimal, right-aligned
            pct_fmt = f"{pct:>4.1f}%"

        return (
            f"{label:>{LABEL_WIDTH}}"
            + (" " * BEFORE_PCT)
            + f"({pct_fmt}) {burned:>{NUM_WIDTH},}"
        )

    def format_supply_line(label, supply):
        return f"{label:>{LABEL_WIDTH}} ago" + (" " * 9) + f"{supply:>{NUM_WIDTH},}"

    # --- prepare header for custom periods ---
    if len(periods_to_show) == 1 and text[1].lower() not in ["1d","7d","30d","365d"]:
        days = periods_to_show[0][1]
        header = f"  Burn since {(datetime.now(timezone.utc) - timedelta(days=days)).date()}:"

    burn_lines = [SEP, header, SEP]
    supply_lines = [SEP,f"  Supply:" + (" " * 9) + f"{today_supply:>{NUM_WIDTH},}", SEP]

    for label, days in periods_to_show:
        entry = pick_entry_by_days_strict(entries, days)
        if not entry:
            burn_lines.append(f"{label}: No data")
            supply_lines.append(f"{label}: No data")
            continue

        old_supply = entry["token_supply"] - DEAD_WALLET_BALANCE
        burned = old_supply - today_supply
        pct = burned / old_supply * 100 if old_supply > 0 else 0

        burn_lines.append(format_burn_line(label, burned, pct))
        supply_lines.append(format_supply_line(label, old_supply))

    await message.reply(code_block("\n".join(burn_lines + [""] + supply_lines)),
                        parse_mode="MarkdownV2")
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
    dp.message.register(handle_burn_command, F.text.startswith("/burn"))

    print("🤖 GNS Supply Boss Bot running...")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
