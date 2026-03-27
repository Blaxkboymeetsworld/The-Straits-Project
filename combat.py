#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
combat.py — Naval combat (abstracted, single-round) and
            personal/boarding combat (3-round text exchange).

Both systems route all probability through roll_check().
"""

import random
from typing import Any, Dict, List, Optional, Tuple
from systems import roll_check


# ─────────────────────────────────────────
# Naval combat
# ─────────────────────────────────────────

def naval_combat(
    state: Any,
    crew_manager: Any,
    opponent: Dict[str, Any],
    clear_fn,
    press_enter_fn,
) -> str:
    """
    Single-round naval engagement. Returns outcome string:
      "victory", "defeat", "fled", "parley"

    opponent dict keys:
      name        str    — opponent ship/captain name
      strength    int    — 1–10 combat rating
      is_pirate   bool
      faction_id  str    — optional, for rep consequences
      cargo_value int    — loot value on win
    """
    clear_fn()
    opp_name = opponent.get("name", "Unknown vessel")
    opp_str  = opponent.get("strength", 5)

    print("═" * 52)
    print("  NAVAL ENCOUNTER")
    print("═" * 52)
    print(f"\n  {opp_name} bears down on your position.")
    print(f"  Her crew looks ready. She's running with purpose.\n")

    print("  [1] Fire cannons")
    print("  [2] Board her")
    print("  [3] Flee")
    print("  [4] Parley (hail her)\n")

    choice = input("  > ").strip()

    # ── Build modifiers ──
    if choice == "1":
        # Cannon effectiveness: gunner present?
        mods = []
        if crew_manager.has_occupation("gunner"):
            mods.append(+0.20)
        # Ship health matters
        if state.ship_health < 50:
            mods.append(-0.15)
        # Opponent strength
        mods.append(-0.04 * opp_str)
        success = roll_check(0.55, mods)
        if success:
            dmg_dealt = random.randint(15, 35)
            dmg_taken = random.randint(5, 15)
            state.ship_health = max(0, state.ship_health - dmg_taken)
            state.morale = min(100, state.morale + 5)
            print(f"\n  Your broadside lands true. {opp_name} takes heavy damage.")
            print(f"  Ship damage taken: {dmg_taken}. Current health: {state.ship_health}")
            loot = opponent.get("cargo_value", 0)
            if loot:
                state.gold += loot
                print(f"  You take their cargo: {loot} gold.")
            press_enter_fn()
            return "victory"
        else:
            dmg = random.randint(15, 30)
            state.ship_health = max(0, state.ship_health - dmg)
            casualties = _roll_casualties(crew_manager, 0.20)
            state.morale = max(0, state.morale - 10)
            print(f"\n  The exchange goes badly. Ship damage: {dmg}.")
            _print_casualties(casualties)
            press_enter_fn()
            return "defeat"

    elif choice == "2":
        # Boarding: soldier/mercenary presence matters heavily
        mods = []
        if crew_manager.has_occupation("soldier") or crew_manager.has_occupation("mercenary"):
            mods.append(+0.25)
        else:
            mods.append(-0.30)   # near-impossible without fighters
        mods.append(-0.04 * opp_str)
        success = roll_check(0.45, mods)
        if success:
            casualties = _roll_casualties(crew_manager, 0.15)
            state.morale = min(100, state.morale + 10)
            loot = opponent.get("cargo_value", 0)
            if loot:
                state.gold += loot
            print(f"\n  Your crew sweeps the deck. {opp_name} is yours.")
            if loot:
                print(f"  Cargo seized: {loot} gold.")
            _print_casualties(casualties)
            # Prisoner option
            _prisoner_prompt(state, crew_manager, opponent, clear_fn, press_enter_fn)
            return "victory"
        else:
            casualties = _roll_casualties(crew_manager, 0.35)
            state.morale = max(0, state.morale - 15)
            dmg = random.randint(10, 25)
            state.ship_health = max(0, state.ship_health - dmg)
            print(f"\n  The boarding fails. Your men are thrown back.")
            print(f"  Ship damage: {dmg}. Morale: {state.morale}")
            _print_casualties(casualties)
            press_enter_fn()
            return "defeat"

    elif choice == "3":
        # Flee: navigator helps
        mods = []
        if crew_manager.has_occupation("navigator"):
            mods.append(+0.20)
        if state.ship_health < 40:
            mods.append(-0.15)
        success = roll_check(0.55, mods)
        if success:
            print(f"\n  You pull ahead. {opp_name} cannot match your speed.")
            state.morale = max(0, state.morale - 3)
            press_enter_fn()
            return "fled"
        else:
            dmg = random.randint(5, 20)
            state.ship_health = max(0, state.ship_health - dmg)
            state.morale = max(0, state.morale - 8)
            print(f"\n  She catches you broadside as you run. Damage: {dmg}.")
            press_enter_fn()
            return "defeat"

    elif choice == "4":
        # Parley: interpreter or merchant help; pirates less likely to respond
        mods = []
        if crew_manager.has_occupation("interpreter"):
            mods.append(+0.20)
        if crew_manager.has_occupation("merchant"):
            mods.append(+0.10)
        if opponent.get("is_pirate"):
            mods.append(-0.20)
        success = roll_check(0.40, mods)
        if success:
            print(f"\n  {opp_name} heaves to. Words are exchanged. She lets you pass.")
            state.morale = min(100, state.morale + 3)
            press_enter_fn()
            return "parley"
        else:
            dmg = random.randint(8, 18)
            state.ship_health = max(0, state.ship_health - dmg)
            print(f"\n  The hail is answered with shot. Damage: {dmg}.")
            press_enter_fn()
            return "defeat"

    press_enter_fn()
    return "defeat"


# ─────────────────────────────────────────
# Personal / boarding combat (3 rounds)
# ─────────────────────────────────────────

ROUND_OPTIONS = {
    "A": "Attack",
    "D": "Defend",
    "F": "Feint",
    "Q": "Disengage",
}

def personal_combat(
    state: Any,
    crew_manager: Any,
    opponent: Dict[str, Any],
    clear_fn,
    press_enter_fn,
) -> str:
    """
    3-round text-based personal/boarding combat.
    Returns: "win", "loss", "draw"

    opponent dict:
      name     str
      tier     int  1–5 (1=common guard, 5=elite warrior)
      weapon   str  (flavor)
    """
    player_hp = 3   # player can take 3 hits before losing
    opp_hp    = 3
    player_weapon_dmg = _get_player_weapon_bonus(state)
    opp_name = opponent.get("name", "your opponent")
    opp_tier = opponent.get("tier", 2)

    clear_fn()
    print("═" * 52)
    print(f"  COMBAT — {opp_name}")
    print("═" * 52)
    print(f"\n  {opp_name} faces you. {opponent.get('weapon', 'Steel in hand')}.\n")

    for rnd in range(1, 4):
        print(f"  ─ Round {rnd} ─")
        print(f"  Your condition: {'●' * player_hp}{'○' * (3 - player_hp)}")
        print(f"  {opp_name}: {'●' * opp_hp}{'○' * (3 - opp_hp)}\n")
        print("  [A] Attack    [D] Defend    [F] Feint    [Q] Disengage\n")

        choice = input("  > ").strip().upper()
        if choice not in ROUND_OPTIONS:
            choice = "A"

        result_line, player_hp, opp_hp = _resolve_round(
            choice, player_hp, opp_hp,
            player_weapon_dmg, opp_tier, crew_manager
        )
        print(f"\n  {result_line}\n")

        if choice == "Q":
            print("  You disengage. The fight ends.")
            press_enter_fn()
            return "draw"
        if opp_hp <= 0:
            print(f"  {opp_name} is down.")
            _win_resolution(state, crew_manager, opponent, clear_fn, press_enter_fn)
            return "win"
        if player_hp <= 0:
            dmg = random.randint(10, 25)
            state.ship_health = max(0, state.ship_health - dmg)
            state.morale = max(0, state.morale - 10)
            print(f"  You are overwhelmed. Ship damage {dmg}, morale suffers.")
            press_enter_fn()
            return "loss"

    # After 3 rounds with no decisive result: draw
    print("  The fight breaks off. Neither side has fallen.")
    state.morale = max(0, state.morale - 3)
    press_enter_fn()
    return "draw"


def _resolve_round(
    choice: str,
    player_hp: int,
    opp_hp: int,
    player_dmg_mod: float,
    opp_tier: int,
    crew_manager: Any,
) -> Tuple[str, int, int]:
    """Resolve one combat round. Returns (narrative_line, new_player_hp, new_opp_hp)."""
    opp_hit_chance = 0.30 + 0.08 * opp_tier

    player_mods = []
    if crew_manager.has_trait("quick"):
        player_mods.append(+0.10)
    if crew_manager.has_trait("strong"):
        player_mods.append(+0.10)
    if crew_manager.has_trait("calm_under_fire"):
        player_mods.append(+0.08)

    if choice == "A":
        # Attack: chance to hit opponent; exposed to counter
        hit = roll_check(0.55 + player_dmg_mod, player_mods)
        counter = roll_check(opp_hit_chance)
        line = ""
        if hit:
            opp_hp -= 1
            line += "Your blow connects. "
        else:
            line += "Your strike misses. "
        if counter:
            player_hp -= 1
            line += "He retaliates and draws blood."
        else:
            line += "He fails to exploit your opening."
        return line, player_hp, opp_hp

    elif choice == "D":
        # Defend: lower chance of being hit; lower chance to deal damage
        counter_blocked = roll_check(0.70, player_mods)
        counter_hit = not counter_blocked and roll_check(opp_hit_chance)
        opp_open = roll_check(0.25)
        line = ""
        if counter_blocked:
            line += "You turn his attack aside. "
        elif counter_hit:
            player_hp -= 1
            line += "He finds a gap in your guard. "
        else:
            line += "You hold your ground. "
        if opp_open:
            opp_hp -= 1
            line += "You punish his overextension."
        return line, player_hp, opp_hp

    elif choice == "F":
        # Feint: draw opponent off-balance, then strike
        feint_works = roll_check(0.50, player_mods)
        if feint_works:
            opp_hp -= 1
            line = "Your feint draws him out. A clean hit."
        else:
            # Failed feint — you're exposed
            player_hp -= 1
            line = "He reads the feint. You eat the counter."
        return line, player_hp, opp_hp

    # Disengage handled in caller
    return "You step back.", player_hp, opp_hp


def _get_player_weapon_bonus(state: Any) -> float:
    """Return a flat modifier from player's best weapon."""
    weapon_bonuses = {
        "rapier":        0.10,
        "cutlass":       0.12,
        "kris":          0.08,
        "boarding_axe":  0.15,
        "arquebus":      0.20,
    }
    best = 0.0
    for item in getattr(state, "items", []):
        if item in weapon_bonuses:
            best = max(best, weapon_bonuses[item])
    return best


def _roll_casualties(crew_manager: Any, base_chance: float) -> List[str]:
    """
    Roll for crew casualties. Returns list of affected crew names.
    Physician halves the chance.
    """
    mods = []
    if crew_manager.has_occupation("physician"):
        mods.append(-base_chance * 0.5)
    casualties = []
    for member in crew_manager.alive_members():
        if roll_check(base_chance, mods):
            # 50% injury vs 50% death
            if random.random() < 0.50:
                member.alive = False
                casualties.append(f"{member.name} — killed")
            else:
                casualties.append(f"{member.name} — wounded")
    return casualties


def _print_casualties(casualties: List[str]):
    if casualties:
        print()
        for c in casualties:
            print(f"  ✗ {c}")


def _prisoner_prompt(
    state: Any,
    crew_manager: Any,
    opponent: Dict[str, Any],
    clear_fn,
    press_enter_fn
):
    """After a boarding win, offer prisoner options if opponent has soldiers/warriors."""
    if not opponent.get("has_prisoners", False):
        return

    tier = opponent.get("prisoner_tier", 1)  # 1=common, 2=officer, 3=noble
    ransom_value = {1: 20, 2: 80, 3: 250}.get(tier, 20)

    print("\n  Some of the crew surrender. You have prisoners.")
    print(f"\n  [R] Hold for ransom  ({ransom_value} gold, {random.randint(3,8)} days wait)")
    print("  [S] Sell at next slave market")
    print("  [F] Free them and let them go")
    print()
    choice = input("  > ").strip().upper()

    # Baraka morale effect
    baraka_present = any(
        m.name == "Baraka" for m in crew_manager.alive_members()
    )

    if choice == "R":
        # Store pending ransom in state (simplified: immediate gold, time cost handled elsewhere)
        state.gold += ransom_value
        print(f"\n  Word is sent. The ransom is paid. {ransom_value} gold.")
        state.time.advance_hours(random.randint(3, 8) * 24)
        press_enter_fn()

    elif choice == "S":
        state.slave_cargo += tier  # tier as rough quantity proxy
        print(f"\n  The prisoners are confined in the hold.")
        if baraka_present:
            state.morale = max(0, state.morale - 5)
            print("  Baraka says nothing. But you know what he thinks.")
        press_enter_fn()

    elif choice == "F":
        state.morale = min(100, state.morale + 5)
        print("\n  You cut them loose. They wade ashore without looking back.")
        press_enter_fn()


def _win_resolution(
    state: Any,
    crew_manager: Any,
    opponent: Dict[str, Any],
    clear_fn,
    press_enter_fn
):
    """Handle loot and prisoner options after a combat win."""
    loot = opponent.get("cargo_value", 0)
    if loot:
        state.gold += loot
        print(f"\n  You take what's worth taking: {loot} gold.")
    _prisoner_prompt(state, crew_manager, opponent, clear_fn, press_enter_fn)
    press_enter_fn()


# ─────────────────────────────────────────
# Bodyguard protection
# ─────────────────────────────────────────

def bodyguard_intercept(
    state: Any,
    crew_manager: Any,
    clear_fn,
    press_enter_fn,
) -> bool:
    """
    When an assassination or attack event fires at rep -4/-5,
    check if a soldier/mercenary intercepts. 60% chance they are
    injured or killed doing so. Returns True if intercepted (player safe),
    False if player takes full consequences.
    """
    guards = [
        m for m in crew_manager.alive_members()
        if m.occupation in ("soldier", "mercenary")
    ]
    if not guards:
        return False

    guard = guards[0]
    clear_fn()
    print("═" * 52)
    print("  ASSASSINATION ATTEMPT")
    print("═" * 52)
    print(f"\n  {guard.name} steps between you and the blade.\n")

    if roll_check(0.60):
        if random.random() < 0.50:
            guard.alive = False
            print(f"  {guard.name} takes the blow meant for you. He is dead.")
            state.morale = max(0, state.morale - 15)
        else:
            print(f"  {guard.name} is badly wounded but alive. He pushed them back.")
            state.morale = max(0, state.morale - 5)
        press_enter_fn()
        return True   # player protected

    print(f"  {guard.name} tries but is overwhelmed. They reach you.")
    press_enter_fn()
    return False  # player still exposed
