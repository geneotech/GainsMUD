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
boss_supply = 29_950_000
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
