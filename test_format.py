#!/usr/bin/env python3
"""Test the SUPPLARIUS formatting."""

import sys
sys.path.insert(0, '.')

from gmud import format_supplarius, truncate_nickname, generate_progress_bar

print("init")
# Test data
current_supply = 26_020_000
recent_damages = [(41880, "ja"), (20116, "bardzo dlugi nickname"), (0, "inny"), (54, "inny"), (0, "ja"), (4354, ""),(54, "")]
last_attacker = "TestPlayer"
last_damage = 41880
players = {
    "Very Long User Name": {"damage": 4_138_213, "last_attack": None},
    "Some User": {"damage": 1_138_213, "last_attack": None},
    "Bob Page": {"damage": 43_213, "last_attack": None},
    "Other": {"damage": 58_448, "last_attack": None},
}

print("init2")

print("Testing truncate_nickname:")
print(f"  Short: '{truncate_nickname('Bob')}'")
print(f"  Long: '{truncate_nickname('VeryLongNicknameThatExceeds')}'")

print("\nTesting progress bar:")
print(f"  {generate_progress_bar(27_257_262, 34_000_000)}")

print("\n" + "="*50)
print("SUPPLARIUS OUTPUT:")
print("="*50)

result = format_supplarius(current_supply, recent_damages, last_attacker, last_damage, players)
print(result)

print("\n" + "="*50)
print("Testing with deflect:")
print("="*50)

result2 = format_supplarius(current_supply, recent_damages, "Deflect User", 0, players)
print(result2)

print("\n" + "="*50)
print("Testing Boss Stage (crossed_million=True):")
print("="*50)

# Test data for boss stage
boss_supply = 25_950_000
boss_damages = [(40000, "Player1"),(50000, "Player1")]
boss_attacker = "Player1"
boss_damage = 50000
boss_players = {"Player1": {"damage": 50000}}

result_boss = format_supplarius(boss_supply, boss_damages, boss_attacker, boss_damage, boss_players, crossed_million=True)
print(result_boss)

print("\n" + "="*50)
print("Testing Normal Case (crossed_million=False):")
print("="*50)

result_normal = format_supplarius(boss_supply, boss_damages, boss_attacker, boss_damage, boss_players, crossed_million=False)
print(result_normal)

result_normal = format_supplarius(boss_supply, boss_damages, boss_attacker, boss_damage, boss_players, crossed_million=False, from_status=True)
print(result_normal)

# Import whale formatting function
from gmud import format_whale

print("\n" + "="*50)
print("WHALE BOSS TESTS:")
print("="*50)

# Test 1: First attack (show_full=True)
print("\n" + "="*50)
print("Test 1: First Whale Attack (show_full=True):")
print("="*50)

whale_gns = 280_000
whale_damages = [(2500, "FirstPlayer")]
whale_players = {"FirstPlayer": {"damage": 2500}}

result_whale_first = format_whale(
    whale_gns,
    whale_damages,
    "FirstPlayer",
    2500,
    whale_players,
    show_full=True,
    defeated=False
)
print(result_whale_first)

# Test 2: Normal attack with damage history
print("\n" + "="*50)
print("Test 2: Normal Whale Attack (with damage history):")
print("="*50)

whale_gns2 = 150_000
whale_damages2 = [
    (5000, "Player1"),
    (3200, "Player2"),
    (1500, "Player3"),
    (4800, "Player1")
]
whale_players2 = {
    "Player1": {"damage": 9800},
    "Player2": {"damage": 3200},
    "Player3": {"damage": 1500}
}

result_whale_normal = format_whale(
    whale_gns2,
    whale_damages2,
    "Player1",
    4800,
    whale_players2,
    show_full=False,
    defeated=False
)
print(result_whale_normal)

# Test 3: Whale defeated (victory condition)
print("\n" + "="*50)
print("Test 3: Whale Defeated (victory condition):")
print("="*50)

whale_gns3 = 0
whale_damages3 = [
    (10000, "Hero1"),
    (5000, "Hero2"),
    (8500, "Hero1")
]
whale_players3 = {
    "Hero1": {"damage": 18500},
    "Hero2": {"damage": 5000}
}

result_whale_defeated = format_whale(
    whale_gns3,
    whale_damages3,
    "Hero1",
    8500,
    whale_players3,
    show_full=False,
    defeated=True
)
print(result_whale_defeated)

# Test 4: High damage attack
print("\n" + "="*50)
print("Test 4: High Damage Attack:")
print("="*50)

whale_gns4 = 50_000
whale_damages4 = [(50000, "BigHitter")]
whale_players4 = {"BigHitter": {"damage": 50000}}

result_whale_high = format_whale(
    whale_gns4,
    whale_damages4,
    "BigHitter",
    50000,
    whale_players4,
    show_full=False,
    defeated=False
)
print(result_whale_high)
