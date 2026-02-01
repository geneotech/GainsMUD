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
GLOBAL_COOLDOWN_HOURS = 1.5
MAX_SUPPLY = 38_892_000
MAX_RECENT_DAMAGES = 3
SUPPLY_FETCH_ATTEMPTS = 5
SUPPLY_FETCH_SES = 4
# DEAD_WALLET_BALANCE = 311603
DEAD_WALLET_BALANCE = 0
DATA_LOCK = asyncio.Lock()
MAX_BURN_DISPLAY_DAYS = 365  # Maximum number of days that can be displayed in /burn command
ALLOWED_CHAT_USERNAME = "GainsPriceChat"

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

def format_supplarius(current_supply, recent_damages, last_attacker, last_damage, players, crossed_million=False, from_status=False):
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

    if False:
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
        # ".[ Until next million:     ].",
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
                add_lines = [
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
                ]
            elif current_supply < 27_000_000:
                # Show extra message once per day
                today = datetime.now(timezone.utc).date()
                show_extra_message = (extra_message_last_shown_date is None or 
                                     extra_message_last_shown_date != today)
                
                if False and show_extra_message and not from_status:
                    lines.extend([
                        ".                           .",
                        ".---------------------------.",
                        ".     ABANDON ALL HOPE,     .",
                        ".         YE, WHO           .",
                        ".       DARE FIGHT ME       .",
                        ".---------------------------.",
                    ])
                    extra_message_last_shown_date = today

                add_lines = [
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
                ]
            else:
                add_lines = [
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
                ]

            if last_damage > 0:
                n_lines = 1 + (last_damage // 500)
                add_lines = add_lines[:n_lines]

                lines = lines + add_lines

    if False:
        if not from_status:
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
            data.setdefault('last_global_attack', None)
            return data
    return {
        "last_supply": None,
        "players": {},
        "recent_damages": [],
        "last_attacker": "",
        "last_damage": 0,
        "last_global_attack": None
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
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")
        
    return " ".join(parts)

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

        if message.chat.username != ALLOWED_CHAT_USERNAME:
            await message.reply("⚠️ This command can only be used in @GainsPriceChat")
            return

        user = message.from_user
        username = (
            user.full_name
            or user.first_name
            or user.username
            or f"User{user.id}"
        )

        data = load_data()

        # Check global cooldown FIRST - blocks all actions
        if data['last_global_attack'] is not None:
            elapsed = time.time() - data['last_global_attack']
            global_cd = max(0, GLOBAL_COOLDOWN_HOURS * 3600 - elapsed)
            if global_cd > 0:
                await message.reply(f"⏳ You can attack again in: *{format_time(global_cd)}*", parse_mode="Markdown")
                return

        if username not in data['players']:
            data['players'][username] = {'damage': 0, 'last_attack': None}

        player = data['players'][username]

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
        # NO PERSONAL COOLDOWN, but triggers global cooldown
        # -------------------------
        if damage < 0:
            healed = -damage
            data['recent_damages'].append((healed, ""))   # empty attacker
            data['last_attacker'] = ""
            data['last_damage'] = healed
            data['last_global_attack'] = time.time()

            # NOTE: personal cooldown NOT applied
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
        data['last_global_attack'] = time.time()

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

async def _handle_burn_impl(message: Message, cumulative: bool):
    """Shared implementation for /burn and /burnt commands.
    
    Args:
        message: The Telegram message
        cumulative: If True, show burn since a day (cumulative /burnt). If False, show burn on a day (daily /burn).
    """
    # Skip messages sent before bot started
    message_ts = message.date.replace(tzinfo=timezone.utc).timestamp()

    if message_ts < BOT_START_TIME:
        print("Ignoring stale message")
        return  # ignore old messages

    # --- parse argument ---
    text = message.text.strip().split()
    periods_to_show = []  # list of tuples: (label, days)
    header = "  Burnt over duration:" if cumulative else "  Burn each day (days ago):"
    is_range = False  # Track if a range was specified

    if len(text) > 1:
        args = text[1].lower().split(",")
        
        # Check if single number argument without comma/dash → treat as range 0-(N-1)
        if len(args) == 1 and "-" not in args[0] and not args[0].endswith("d") and not args[0].endswith("m") and not args[0].endswith("y"):
            try:
                num_days = int(args[0])
                if num_days > 0:
                    is_range = True
                    # Treat as range from 0 to (num_days - 1)
                    end = min(num_days - 1, MAX_BURN_DISPLAY_DAYS - 1)
                    for day in range(0, end + 1):
                        period = f"{day}d"
                        periods_to_show.append((period, day))
                    args = []  # Clear args to skip the loop below
            except ValueError:
                pass  # Not a valid number, continue with normal processing
        
        for arg in args:
            try:
                # Check for range syntax (e.g., "1-7") - only for numeric values
                if "-" in arg and not arg.endswith("d") and not arg.endswith("m") and not arg.endswith("y"):
                    is_range = True
                    parts = arg.split("-")
                    if len(parts) == 2:
                        start = int(parts[0])
                        end = int(parts[1])
                        end = min(start + MAX_BURN_DISPLAY_DAYS, end)
                        if start > end:
                            await message.reply(f"❌ Invalid range: {arg} (start must be <= end)")
                            return
                        for day in range(start, end + 1):
                            period = f"{day}d"
                            periods_to_show.append((period, day))
                        continue
                
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
        if cumulative:
            periods_to_show = [("1d",1), ("7d",7), ("30d",30), ("365d",365)]
        else:
            periods_to_show = [("Today",0), ("1d",1), ("2d",2), ("3d",3), ("4d",4),("5d",5),("6d",6),("7d",7),("8d",8),("9d",9)]
    
    # --- Validate /burnt doesn't use 0 ---
    if cumulative:
        for label, days in periods_to_show:
            if days == 0:
                await message.reply("❌ Cannot show cumulative burn for 0 days. Use /burn 0 for today's burn.")
                return

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

        latest_entry = None
        latest_dt = None

        for e in entries:
            date_str = e.get("date")
            if not date_str:
                continue

            entry_dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))

            if entry_dt.date() != target_date:
                continue

            if latest_dt is None or entry_dt > latest_dt:
                latest_dt = entry_dt
                latest_entry = e

        return latest_entry

    # --- formatting helpers ---
    LABEL_WIDTH = 5  # right-align period labels
    BEFORE_PCT = 5   
    NUM_WIDTH = 10
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

    # --- prepare header for custom periods (cumulative only) ---
    if cumulative and len(periods_to_show) == 1 and text[1].lower() not in ["1d","7d","30d","365d"]:
        days = periods_to_show[0][1]
        header = f"  Burn since {(datetime.now(timezone.utc) - timedelta(days=days)).date()}:"

    burn_lines = [SEP, header, SEP]
    
    if cumulative:
        supply_lines = [SEP,f"  Supply:" + (" " * 9) + f"{today_supply:>{NUM_WIDTH},}", SEP]
    
    total_burned = 0
    total_pct = 0
    count = 0
    max_burned = 0
    max_burned_pct = 0
    max_burned_date = None
    displayed_count = 0
    truncated = False
    MAX_DISPLAY_LINES = 20  # Maximum lines to display before truncating

    for label, days in periods_to_show:
        if not cumulative:
            if label == "0d":
                label = "Today"
            if label == "1d":
                label = "Ystdy"

        if cumulative:
            # Cumulative burn: from that day until now
            entry = pick_entry_by_days_strict(entries, days)
            if not entry:
                if displayed_count < MAX_DISPLAY_LINES:
                    burn_lines.append(f"{label}: No data")
                    supply_lines.append(f"{label}: No data")
                    displayed_count += 1
                elif not truncated:
                    burn_lines.append("  (...)")
                    supply_lines.append("  (...)")
                    truncated = True
                continue

            old_supply = entry["token_supply"] - DEAD_WALLET_BALANCE
            burned = old_supply - today_supply
            pct = burned / old_supply * 100 if old_supply > 0 else 0

            if displayed_count < MAX_DISPLAY_LINES:
                burn_lines.append(format_burn_line(label, burned, pct))
                supply_lines.append(format_supply_line(label, old_supply))
                displayed_count += 1
            elif not truncated:
                burn_lines.append("  (...)")
                supply_lines.append("  (...)")
                truncated = True
        else:
            # Daily burn: on that specific day
            entry_day = pick_entry_by_days_strict(entries, days)
            entry_day_before = pick_entry_by_days_strict(entries, days + 1)
            
            if not entry_day or not entry_day_before:
                if displayed_count < MAX_DISPLAY_LINES:
                    burn_lines.append(f"{label}: No data")
                    displayed_count += 1
                elif not truncated:
                    burn_lines.append("  (...)")
                    truncated = True
                continue

            supply_day = entry_day["token_supply"] - DEAD_WALLET_BALANCE
            supply_day_before = entry_day_before["token_supply"] - DEAD_WALLET_BALANCE
            
            # Burn ON that day = supply at day before - supply at that day
            burned_on_day = supply_day_before - supply_day
            pct = burned_on_day / supply_day_before * 100 if supply_day_before > 0 else 0

            if displayed_count < MAX_DISPLAY_LINES:
                burn_lines.append(format_burn_line(label, burned_on_day, pct))
                displayed_count += 1
            elif not truncated:
                burn_lines.append("  (...)")
                truncated = True

            # Track max burn (always, even if truncated)
            if burned_on_day > max_burned:
                max_burned = burned_on_day
                max_burned_pct = pct
                # Calculate the date for this day
                max_burned_date = (datetime.now(timezone.utc) - timedelta(days=days)).date()

            total_burned += burned_on_day
            total_pct += pct
            count += 1


    if not cumulative and count > 0:
        avg_burned = total_burned / count
        avg_pct = total_pct / count

        burn_lines.append("")
        
        # Always show Avg first
        burn_lines.append(format_burn_line("Avg", int(avg_burned), avg_pct))
        
        # Always show Tot line (for any /burn command)
        burn_lines.append(format_burn_line("Tot", int(total_burned), total_pct))
        # Add "(over x days)" right-aligned to the total number
        days_text = f"(over {count} days)"
        # Calculate position: align to end of the number in previous line
        # Format: "  Tot     (pct%) total_burned"
        # We want to align days_text to end at same position as total_burned
        total_str = f"{int(total_burned):,}"
        padding = LABEL_WIDTH + BEFORE_PCT + 8 + NUM_WIDTH - len(days_text)  # 8 for "(pct%) "
        burn_lines.append(" " * padding + days_text)
        
        # Show Max line with the highest burn day
        if max_burned > 0 and max_burned_date:
            burn_lines.append(format_burn_line("Max", int(max_burned), max_burned_pct))
            # Add date in parentheses
            date_text = f"(on {max_burned_date})"
            padding = LABEL_WIDTH + BEFORE_PCT + 8 + NUM_WIDTH - len(date_text)
            burn_lines.append(" " * padding + date_text)

    if cumulative:
        await message.reply(code_block("\n".join(burn_lines + [""] + supply_lines)),
                            parse_mode="MarkdownV2")
    else:
        await message.reply(code_block("\n".join(burn_lines)),
                            parse_mode="MarkdownV2")

async def handle_burnt_command(message: Message):
    """Handle /burnt command - shows cumulative burn since a specific day."""
    await _handle_burn_impl(message, cumulative=True)

async def handle_burn_command(message: Message):
    """Handle /burn command - shows daily burn on specific days."""
    await _handle_burn_impl(message, cumulative=False)

async def handle_burnd_command(message: Message):
    """Handle deprecated /burnd command - redirect to /burn with message."""
    await message.reply("/burnd has been renamed to just /burn.\nUse /burnt for cumulative burn.")
# ---------------------------------------------------
# MAIN
# ---------------------------------------------------

async def handle_drag_command(message: Message):
    async with DATA_LOCK:
        # Skip messages sent before bot started
        message_ts = message.date.replace(tzinfo=timezone.utc).timestamp()
        if message_ts < BOT_START_TIME:
            return

        if message.chat.username == ALLOWED_CHAT_USERNAME:
            await message.reply("⚠️ DM bot directly to check dragon status, to avoid spam.\nAttack here with /sup.")
            return

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

        if message.chat.username == ALLOWED_CHAT_USERNAME:
            # Check per-user cooldown
            cd = get_cooldown_remaining(player['last_attack'])
            if cd > 0:
                await message.reply(f"⏳ You can check status again in: *{format_time(cd)}*", parse_mode="Markdown")
                return

        current_supply = await get_gns_total_supply()
        if current_supply is None:
            await message.reply("❌ Failed to fetch GNS supply. Try again later.")
            return

        # Trigger per-user cooldown
        player['last_attack'] = time.time()
        
        if data['last_supply'] is None:
            data['last_supply'] = current_supply
            save_data(data)
            await message.reply(
                f"🎮 *BOSS BATTLE STATUS*\n\n🐉 HP: *{current_supply:,}*",
                parse_mode="Markdown"
            )
            return
            
        save_data(data)

        supplarius = format_supplarius(
            current_supply,
            data['recent_damages'],
            data['last_attacker'],
            data['last_damage'],
            data['players'],
            crossed_million=False,
            from_status=True
        )
        await message.reply(code_block(supplarius), parse_mode="MarkdownV2")

async def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN not set")
        return

    bot = Bot(token)
    dp = Dispatcher()

    dp.message.register(handle_sup_command, F.text.startswith("/sup"))
    dp.message.register(handle_drag_command, F.text.startswith("/drag"))
    dp.message.register(handle_gmud_command, F.text.startswith("/gmud"))
    dp.message.register(handle_burnd_command, Command("burnd"))  # deprecated, shows message
    dp.message.register(handle_burnt_command, Command("burnt"))
    dp.message.register(handle_burn_command, Command("burn"))

    print("🤖 GNS Supply Boss Bot running...")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
