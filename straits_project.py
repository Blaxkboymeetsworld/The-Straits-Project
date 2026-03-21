#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
The Straits Project — v0.2.0
Full expanded core loop integrating:
 - Sea encounters (gated until first port visit)
 - Crew system (traits, occupations, languages, morale)
 - Fluctuating economy
 - Timed quest system
 - Day/night cycle
 - Slave cargo + recruit mechanic
 - Port weapons, characters, dispositions
"""

import json
import os
import random
import sys
from copy import deepcopy
from typing import Dict, Any, List, Optional, Tuple

# ─────────────────────────────────────────
# Module imports (same directory)
# ─────────────────────────────────────────
from crew import CrewManager, CrewMember, load_crew_data, recruitment_menu, slave_recruit_event
from economy import Economy, GOODS_CATALOG, MAX_CARGO
from quests import QuestManager, load_quests
from time_system import TimeSystem

# ─────────────────────────────────────────
# Paths
# ─────────────────────────────────────────
ROOT_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_DIR  = os.path.join(ROOT_DIR, "data")
SAVE_DIR  = os.path.join(ROOT_DIR, "saves")
EVENTS_PATH = os.path.join(DATA_DIR, "events.json")
WORLD_PATH  = os.path.join(DATA_DIR, "world.json")
SAVE_PATH   = os.path.join(SAVE_DIR, "slot1.json")

VALID_EVENT_POOLS = {"sea_events", "harbor_events", "village_events", "special_events"}


# ─────────────────────────────────────────
# Utility
# ─────────────────────────────────────────

def clear():
    try:
        os.system("cls" if os.name == "nt" else "clear")
    except Exception:
        pass

def press_enter():
    input("\n  [Enter] to continue...")

def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(SAVE_DIR, exist_ok=True)

def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_events(path: str) -> Dict[str, Any]:
    data = load_json(path)
    for key in VALID_EVENT_POOLS:
        if key not in data or not isinstance(data.get(key), list):
            data[key] = []
    return data

def load_world(path: str) -> Dict[str, Any]:
    data = load_json(path)
    data.setdefault("major_ports", [])
    data.setdefault("villages", [])
    return data

def find_port(name: str, world: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    for p in world["major_ports"] + world["villages"]:
        if p["name"] == name:
            return p
    return None


# ─────────────────────────────────────────
# Game State
# ─────────────────────────────────────────

class GameState:

    def __init__(self, role: str, world: Dict[str, Any]):
        self.role = role
        self.gold = 30
        self.spices = 0             # legacy field (spices still in cargo too)
        self.ship_health = 100
        self.morale = 50
        self.world = world

        # Time system
        self.time = TimeSystem(day=1, hour=8)

        # Location
        self.current_location: str = "At Sea"
        self.current_location_type: str = "sea"

        # First port gate — sea events only fire after visiting one port
        self.has_visited_port: bool = False

        # Cargo: {good_id: qty}
        self.cargo: Dict[str, int] = {}

        # Slave cargo (separate ledger)
        self.slave_cargo: int = 0

        # Inventory items (quest rewards, cartaz, etc.)
        self.items: List[str] = []

        # One-time event flags
        self.once_flags: List[str] = []

        # Crew
        self.crew = CrewManager()

        # Quests
        self.quests = QuestManager()

        # Role adjustments
        if role == "Portuguese Conquistador":
            self.gold += 10
            self.morale += 5
        elif role == "Arab Muslim Dāʿī":
            self.spices += 2
            self.morale += 10
            self.cargo["pepper"] = 2
        elif role == "Chinese Trader":
            self.gold += 15
            self.spices += 5
            self.cargo["silk"] = 3
            self.cargo["porcelain"] = 2

    @property
    def day(self) -> int:
        return self.time.day

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "gold": self.gold,
            "spices": self.spices,
            "ship_health": self.ship_health,
            "morale": self.morale,
            "time": self.time.to_dict(),
            "current_location": self.current_location,
            "current_location_type": self.current_location_type,
            "has_visited_port": self.has_visited_port,
            "cargo": self.cargo,
            "slave_cargo": self.slave_cargo,
            "items": self.items,
            "once_flags": self.once_flags,
            "crew": self.crew.to_list(),
            "quests": self.quests.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any], world: Dict[str, Any]) -> "GameState":
        obj = cls.__new__(cls)
        obj.role = d.get("role", "Portuguese Conquistador")
        obj.gold = int(d.get("gold", 0))
        obj.spices = int(d.get("spices", 0))
        obj.ship_health = int(d.get("ship_health", 100))
        obj.morale = int(d.get("morale", 50))
        obj.world = world
        obj.time = TimeSystem.from_dict(d.get("time", {}))
        obj.current_location = d.get("current_location", "At Sea")
        obj.current_location_type = d.get("current_location_type", "sea")
        obj.has_visited_port = d.get("has_visited_port", False)
        obj.cargo = d.get("cargo", {})
        obj.slave_cargo = int(d.get("slave_cargo", 0))
        obj.items = d.get("items", [])
        obj.once_flags = d.get("once_flags", [])
        obj.crew = CrewManager.from_list(d.get("crew", []))
        obj.quests = QuestManager.from_dict(d.get("quests", {}))
        return obj

    def apply_effect(self, effect: Dict[str, Any]):
        self.gold        = max(0, self.gold        + int(effect.get("gold", 0)))
        self.spices      = max(0, self.spices      + int(effect.get("spices", 0)))
        self.ship_health = max(0, min(100, self.ship_health + int(effect.get("ship_health", 0))))
        self.morale      = max(0, min(100, self.morale      + int(effect.get("morale", 0))))

    def is_game_over(self) -> bool:
        if self.ship_health <= 0:
            print("\n  ⚓ Your ship has been wrecked. The sea keeps its debts.")
            return True
        if self.morale <= 0:
            print("\n  ⚓ Your crew has deserted. The voyage ends here.")
            return True
        return False

    def apply_daily_crew_effects(self):
        """Called each time a day passes at sea."""
        self.morale = min(100, self.morale + self.crew.morale_per_day_bonus())
        drain = self.crew.daily_morale_drain()
        if drain:
            self.morale = max(0, self.morale - drain)

    def pay_crew_wages(self):
        """Pay wages when entering a port."""
        wages = self.crew.total_wages()
        if wages > 0:
            if self.gold >= wages:
                self.gold -= wages
                print(f"\n  ⚖  Crew wages paid: {wages} gold.")
            else:
                short = wages - self.gold
                self.gold = 0
                self.morale = max(0, self.morale - 10)
                print(f"\n  ⚠  Could not fully pay wages. Short by {short} gold. Crew morale falls.")

    def check_port_incidents(self):
        """Check for crew negative trait incidents at port."""
        incidents = self.crew.check_for_incidents()
        for inc in incidents:
            print(f"\n  {inc}")
            # Small gold and morale costs for incidents
            self.gold = max(0, self.gold - random.randint(3, 8))
            self.morale = max(0, self.morale - 2)

    def status_text(self) -> str:
        cargo_used = sum(self.cargo.values())
        active_q = len([q for q in self.quests.active if not q.completed and not q.failed])
        return (
            f"  {self.time.display}\n"
            f"  Role: {self.role}\n"
            f"  Location: {self.current_location} ({self.current_location_type.replace('_',' ')})\n"
            f"  Gold: {self.gold}  |  Cargo: {cargo_used}/{MAX_CARGO}  |  Slave cargo: {self.slave_cargo}\n"
            f"  Ship Health: {self.ship_health}  |  Morale: {self.morale}\n"
            f"  Crew: {self.crew.count()} aboard  |  Active quests: {active_q}"
        )


# ─────────────────────────────────────────
# Save / Load
# ─────────────────────────────────────────

def save_game(state: GameState):
    ensure_dirs()
    with open(SAVE_PATH, "w", encoding="utf-8") as f:
        json.dump(state.to_dict(), f, ensure_ascii=False, indent=2)
    print("\n  💾 Game saved to slot 1.")

def load_game(world: Dict[str, Any]) -> Optional[GameState]:
    if not os.path.exists(SAVE_PATH):
        print("\n  No save found in slot 1.")
        return None
    with open(SAVE_PATH, "r", encoding="utf-8") as f:
        d = json.load(f)
    print("\n  📂 Loaded save from slot 1.")
    return GameState.from_dict(d, world)


# ─────────────────────────────────────────
# Event Engine
# ─────────────────────────────────────────

class EventEngine:

    def __init__(self, events_data: Dict[str, Any]):
        self.events = events_data

    def _check_requirement(self, req: Dict[str, Any], state: GameState) -> bool:
        """Check whether an option's requirements are satisfied."""
        if not req:
            return True
        if "gold" in req and state.gold < req["gold"]:
            return False
        if "crew_language" in req and not state.crew.has_language(req["crew_language"]):
            return False
        if "crew_occupation" in req and not state.crew.has_occupation(req["crew_occupation"]):
            return False
        if "crew_trait" in req and not state.crew.has_trait(req["crew_trait"]):
            return False
        if "crew_region" in req and not state.crew.has_region(req["crew_region"]):
            return False
        if "player_role" in req and state.role != req["player_role"]:
            return False
        if "item" in req and req["item"] not in state.items:
            return False
        return True

    def _match_when(self, event: Dict[str, Any], state: GameState) -> Tuple[bool, Optional[str]]:
        when = event.get("when", {})
        loc_list = when.get("location")
        if loc_list and state.current_location not in loc_list:
            return False, None
        loc_type = when.get("type")
        if loc_type and state.current_location_type != loc_type:
            return False, None
        roles = when.get("role")
        if roles and state.role not in roles:
            return False, None
        once = bool(when.get("once", False))
        once_key = None
        if once:
            scope = state.current_location if (loc_list or loc_type == "major_port") else "*"
            once_key = f"{event.get('id','?')}|{scope}"
            if once_key in state.once_flags:
                return False, once_key
        return True, once_key

    def _merge_role_variant(self, ev: Dict[str, Any], role: str) -> Dict[str, Any]:
        result = deepcopy(ev)
        variants = ev.get("variants", {})
        var = variants.get(role)
        if not var:
            return result
        if "description" in var:
            result["description"] = var["description"]
        if "options" in var:
            for k, v in var["options"].items():
                result.setdefault("options", {})
                base = result["options"].get(k, {})
                base.update(v)
                result["options"][k] = base
        return result

    def _format_text(self, text: str, ctx: Dict[str, Any]) -> str:
        try:
            return text.format(**ctx)
        except Exception:
            return text

    def _apply_templating(self, ev: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
        out = deepcopy(ev)
        if "description" in out and isinstance(out["description"], str):
            out["description"] = self._format_text(out["description"], ctx)
        opts = out.get("options", {})
        for key, opt in list(opts.items()):
            if "text" in opt and isinstance(opt["text"], str):
                opt["text"] = self._format_text(opt["text"], ctx)
        return out

    def _context_for_event(self, state: GameState) -> Dict[str, Any]:
        port_data = find_port(state.current_location, state.world)
        hm = None
        harbor_fee = 10
        if port_data:
            hm = port_data.get("harbor_master")
            harbor_fee = hm["fees"] if hm else 10
        return {
            "current_port": state.current_location,
            "harbormaster_name": hm["name"] if hm else "the harbor master",
            "harbor_fee": harbor_fee,
        }

    def _resolve_event(self, event: Dict[str, Any], state: GameState, once_key: Optional[str] = None):
        clear()
        title = event.get("id", "Event").replace("_", " ").title()
        print(f"\n  ── {title} ──\n")
        print(f"  {event.get('description', 'An event occurs.')}\n")

        options = event.get("options", {})
        if not options:
            press_enter()
            return

        keys_sorted = sorted(options.keys(), key=lambda k: str(k))

        # Only show options the player can actually take
        available_keys = [k for k in keys_sorted if self._check_requirement(options[k].get("requires", {}), state)]
        unavailable_keys = [k for k in keys_sorted if k not in available_keys]

        for k in available_keys:
            print(f"  {k}) {options[k].get('text', '...')}")
        if unavailable_keys:
            print(f"\n  (Some options unavailable — crew lacks the required skill, item, or gold)")

        print()
        choice = input("  > ").strip()

        if choice not in available_keys:
            print("\n  You hesitate. Time passes.")
        else:
            effect = options[choice].get("effect", {})
            state.apply_effect(effect)
            print("\n  Your choice is made.")

        if once_key:
            state.once_flags.append(once_key)

        press_enter()

    def trigger_random(self, pool_name: str, state: GameState):
        pool = self.events.get(pool_name, [])
        if not pool:
            return
        ev = random.choice(pool)
        ctx = self._context_for_event(state)
        ev_fmt = self._apply_templating(ev, ctx)
        self._resolve_event(ev_fmt, state, once_key=None)

    def trigger_special_if_any(self, state: GameState) -> bool:
        specials = self.events.get("special_events", [])
        eligible: List[Tuple[Dict[str, Any], Optional[str]]] = []
        for ev in specials:
            ok, once_key = self._match_when(ev, state)
            if ok:
                eligible.append((ev, once_key))
        if not eligible:
            return False
        base_ev, once_key = eligible[0]
        ev = self._merge_role_variant(base_ev, state.role)
        ctx = self._context_for_event(state)
        ev = self._apply_templating(ev, ctx)
        self._resolve_event(ev, state, once_key=once_key)
        return True


# ─────────────────────────────────────────
# Port UI
# ─────────────────────────────────────────

def port_action_menu(
    state: GameState,
    port_data: Dict[str, Any],
    engine: EventEngine,
    crew_data: Dict[str, Any],
    all_quests: List[Dict[str, Any]],
):
    """Full port interaction hub."""
    access = state.time.port_access_status()
    econ = Economy(port_data)

    # On arrival: pay wages, check incidents, quest logic
    state.pay_crew_wages()
    state.check_port_incidents()
    state.quests.check_port_arrival(
        port_data["name"], state.day, state, clear, press_enter
    )
    state.quests.check_return_to_giver(
        port_data["name"], state.day, state, clear, press_enter
    )

    # Check for quest expirations
    failed = state.quests.check_expirations(state.day)
    if failed:
        for fq in failed:
            print(f"\n  ✗ Quest expired: '{fq.title}'. {port_data.get('ruler',{}).get('name','The ruler')} is displeased.")
        press_enter()

    while True:
        clear()
        print("═" * 52)
        print(f"  ⚓ {port_data['name'].upper()}")
        disp_label = state.quests.disposition_label(port_data["name"])
        disp_val   = state.quests.get_disposition(port_data["name"])
        ruler      = port_data.get("ruler", {})
        print(f"  Ruler: {ruler.get('name','Unknown')}, {ruler.get('title','')}  |  Disposition: {disp_label} ({disp_val})")
        print(f"  {state.time.display}")
        print(f"  Culture: {port_data.get('culture','')}  |  Language: {port_data.get('language','')}")
        print(f"  Religion: {port_data.get('religion','')}")
        print("═" * 52)
        print(state.status_text())
        print()

        options = []
        def opt(key, label, available=True, reason=None):
            options.append((key, label, available, reason))

        opt("1", "Market (buy/sell goods)",   access["market_open"],  "Market closes at dusk.")
        opt("2", "Recruit crew",              access["recruitment"],   "Docks quiet — come back at dawn.")
        opt("3", "Seek missions (rulers & lords)", access["quest_board"], "Officials not available now.")
        opt("4", "Weapons shop")
        opt("5", "Ship repair",               access["ship_repair"],   "Shipwrights rest at night.")
        opt("6", "Tavern & rumors",           access["tavern"],        None)
        opt("7", "Rest until dawn")
        opt("8", "View crew roster")
        opt("9", "View active quests")
        opt("S", "Set sail (leave port)")
        opt("V", "Save game")

        for key, label, avail, _ in options:
            marker = "  " if avail else "░ "
            print(f"  {marker}[{key}] {label}")

        print()
        choice = input("  > ").strip().upper()

        # ── Market ──
        if choice == "1":
            warning = state.time.access_warning("market_open")
            if warning:
                print(f"\n  {warning}")
                press_enter()
            else:
                econ.trade_menu(state, state.crew, clear, press_enter)

        # ── Recruit ──
        elif choice == "2":
            warning = state.time.access_warning("recruitment")
            if warning:
                print(f"\n  {warning}")
                press_enter()
            else:
                recruitment_menu(port_data, crew_data, state.crew, state, clear, press_enter)

        # ── Quests ──
        elif choice == "3":
            warning = state.time.access_warning("quest_board")
            if warning:
                print(f"\n  {warning}")
                press_enter()
            else:
                state.quests.quest_board_menu(
                    port_data["name"], all_quests, state.day,
                    state, clear, press_enter
                )

        # ── Weapons shop ──
        elif choice == "4":
            weapons_shop(port_data, state, crew_data, clear, press_enter)

        # ── Ship repair ──
        elif choice == "5":
            warning = state.time.access_warning("ship_repair")
            if warning:
                print(f"\n  {warning}")
                press_enter()
            else:
                ship_repair_menu(state, port_data, clear, press_enter)

        # ── Tavern ──
        elif choice == "6":
            if not access["tavern"]:
                print("\n  The tavern doesn't open until late afternoon.")
                press_enter()
            else:
                tavern_menu(state, port_data, engine, clear, press_enter)

        # ── Rest ──
        elif choice == "7":
            clear()
            print("\n  You order the crew to rest. The ship settles in the anchorage.")
            state.time.rest_until_dawn()
            state.morale = min(100, state.morale + 5)
            print(f"\n  Dawn comes. {state.time.display}")
            print(f"  Morale +5. Current morale: {state.morale}")
            press_enter()

        # ── Crew roster ──
        elif choice == "8":
            clear()
            print("═" * 52)
            print("  CREW ROSTER")
            print("═" * 52)
            state.crew.roster_display()
            print(f"\n  Total wages per port call: {state.crew.total_wages()} gold")
            press_enter()

        # ── Active quests ──
        elif choice == "9":
            clear()
            print("═" * 52)
            print("  ACTIVE QUESTS")
            print("═" * 52)
            if not state.quests.active:
                print("\n  No active quests.")
            for q in state.quests.active:
                print(q.status_line(state.day))
                print(f"    {q.description[:100]}...")
                print()
            press_enter()

        # ── Set sail ──
        elif choice == "S":
            break

        # ── Save ──
        elif choice == "V":
            save_game(state)
            press_enter()

        else:
            print("\n  Unknown option.")
            press_enter()


# ─────────────────────────────────────────
# Weapons Shop
# ─────────────────────────────────────────

def weapons_shop(
    port_data: Dict[str, Any],
    state: GameState,
    crew_data: Dict[str, Any],
    clear_fn,
    press_enter_fn
):
    available_weapon_ids = port_data.get("weapons_available", [])
    all_weapons = crew_data.get("weapons", {})

    if not available_weapon_ids:
        print("\n  No weapons dealer operating here.")
        press_enter_fn()
        return

    while True:
        clear_fn()
        print("═" * 52)
        print(f"  WEAPONS — {port_data['name']}")
        print(f"  Your gold: {state.gold}")
        print("═" * 52)
        print()

        weapons_list = [(wid, all_weapons[wid]) for wid in available_weapon_ids if wid in all_weapons]
        for i, (wid, w) in enumerate(weapons_list, 1):
            in_inv = state.items.count(wid)
            print(f"  [{i}] {w['name']:<28} {w['cost']:>4} gold")
            print(f"       {w['description']}")
            print(f"       Type: {w['type'].title()}  |  Damage: {w['damage']}  |  In inventory: {in_inv}")
            print()

        print("  [Q] Leave\n")
        choice = input("  Buy which? > ").strip().upper()

        if choice == "Q":
            break
        elif choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(weapons_list):
                wid, w = weapons_list[idx]
                if state.gold >= w["cost"]:
                    state.gold -= w["cost"]
                    state.items.append(wid)
                    print(f"\n  Purchased: {w['name']}")
                    press_enter_fn()
                else:
                    print(f"\n  Not enough gold. Need {w['cost']}.")
                    press_enter_fn()


# ─────────────────────────────────────────
# Ship Repair
# ─────────────────────────────────────────

def ship_repair_menu(state: GameState, port_data: Dict[str, Any], clear_fn, press_enter_fn):
    clear_fn()
    print("═" * 52)
    print(f"  SHIP REPAIR — {port_data['name']}")
    print(f"  Current ship health: {state.ship_health}/100")
    print("═" * 52)

    damage = 100 - state.ship_health
    if damage == 0:
        print("\n  Your hull is sound. No repairs needed.")
        press_enter_fn()
        return

    # Cost scales with damage and whether player has a carpenter
    base_cost = damage * 2
    if state.crew.has_occupation("carpenter"):
        effective_cost = int(base_cost * 0.5)
        print(f"\n  Your ship's carpenter will lead the work. Reduced cost.")
    else:
        effective_cost = base_cost
        print(f"\n  Local shipwrights will do the work.")

    print(f"\n  Damage to repair: {damage} points")
    print(f"  Estimated cost: {effective_cost} gold\n")
    print("  [F] Full repair")
    print("  [P] Partial repair (specify gold)")
    print("  [Q] Cancel\n")

    choice = input("  > ").strip().upper()

    if choice == "F":
        if state.gold >= effective_cost:
            state.gold -= effective_cost
            state.ship_health = 100
            print(f"\n  Full repairs completed. Spent {effective_cost} gold.")
        else:
            print(f"\n  Not enough gold. Have {state.gold}, need {effective_cost}.")
        press_enter_fn()

    elif choice == "P":
        amt_str = input(f"  Spend how much? (max {state.gold}): ").strip()
        if amt_str.isdigit():
            amt = min(int(amt_str), state.gold)
            # Each gold buys 0.5 health (roughly)
            rate = 0.5 if state.crew.has_occupation("carpenter") else 0.25
            health_gain = min(damage, int(amt * rate / (effective_cost / damage)))
            state.gold -= amt
            state.ship_health = min(100, state.ship_health + health_gain)
            print(f"\n  Spent {amt} gold. Ship health restored by {health_gain}.")
        press_enter_fn()


# ─────────────────────────────────────────
# Tavern
# ─────────────────────────────────────────

def tavern_menu(state: GameState, port_data: Dict[str, Any], engine: EventEngine, clear_fn, press_enter_fn):
    clear_fn()
    print("═" * 52)
    print(f"  TAVERN — {port_data['name']}")
    print("═" * 52)
    print(
        "\n  The place is a low-ceilinged room smelling of fish oil and cheap rice wine.\n"
        "  Your crew mingles with sailors from a dozen nations. News travels faster\n"
        "  than any ship in places like this.\n"
    )

    print("  [1] Buy a round for the crew (Cost: 5 gold, +8 morale)")
    print("  [2] Listen for rumors (free)")
    print("  [3] Ask about a specific port or route")
    print("  [4] Trigger a random harbor event (stay a while)")
    print("  [Q] Leave\n")

    choice = input("  > ").strip().upper()

    if choice == "1":
        if state.gold >= 5:
            state.gold -= 5
            state.morale = min(100, state.morale + 8)
            print("\n  The crew raises their cups. Morale +8.")
        else:
            print("\n  Not enough gold.")
        press_enter_fn()

    elif choice == "2":
        _tavern_rumor(state, port_data, clear_fn, press_enter_fn)

    elif choice == "3":
        loc = input("\n  Which port do you ask about? ").strip()
        p = find_port(loc, state.world)
        if p:
            ruler = p.get("ruler", {})
            disp = state.quests.disposition_label(p["name"])
            print(f"\n  {p['name']} ({p['culture']}, {p['religion']})")
            print(f"  Ruler: {ruler.get('name','Unknown')}, {ruler.get('title','')}")
            print(f"  Specialty goods: {', '.join(p.get('specialty_goods',[]))}")
            print(f"  Your reputation there: {disp}")
        else:
            print(f"\n  No one here knows much about {loc}.")
        press_enter_fn()

    elif choice == "4":
        state.time.advance_hours(2)
        engine.trigger_random("harbor_events", state)

    elif choice == "Q":
        return


def _tavern_rumor(state: GameState, port_data: Dict[str, Any], clear_fn, press_enter_fn):
    """Random rumor system — gives hints about economy, events, quests."""
    rumors = [
        "A merchant whispers that nutmeg prices in Hormuz are sky-high — the Portuguese have disrupted the Aden route again.",
        "Someone claims a Chinese junk carrying silk went down off Pulau Tioman last month. The wreck hasn't been salvaged.",
        "A Bugis navigator says the passage east of Bantam is clear — the pirate fleet that usually lurks there has moved north.",
        "Word from Calicut: the Zamorin is furious with the Portuguese. Relations are at their worst in years.",
        "A Tamil trader mentions that cloves from Ternate are scarce — inter-island warfare has disrupted the harvest.",
        "An old Arab sailor talks about a route east that cuts four days off the Malacca-Quanzhou run, if you know the stars.",
        "The harbor master's son was seen counting coin with a Javanese factor. Something moves through this port that doesn't appear on any manifest.",
        "A freed African sailor mentions that there are men here who make cartazes — passes — that look Portuguese enough to fool anyone but the Portuguese themselves.",
        "Fever in the interior has killed three Chinese merchant factors this month. Their goods sit unclaimed in a warehouse.",
        "A drunken Portuguese soldier claims he knows where a Portuguese carrack laden with pepper went aground — and the Estado da India hasn't found it.",
    ]
    print(f"\n  ─ Rumor ─\n  {random.choice(rumors)}\n")
    press_enter_fn()


# ─────────────────────────────────────────
# Travel & Sea Passage
# ─────────────────────────────────────────

def travel_menu(world: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    clear()
    print("  Make landfall:\n")
    print("  [1] Major Ports")
    print("  [2] Villages & Anchorages")
    print("  [3] Cancel\n")
    top = input("  > ").strip()

    if top == "1":
        return choose_from_list(
            [p["name"] for p in world["major_ports"]], "major_port"
        )
    if top == "2":
        return choose_from_list(
            [v["name"] for v in world["villages"]], "village"
        )
    return None, None

def choose_from_list(names: List[str], loc_type: str) -> Tuple[Optional[str], Optional[str]]:
    clear()
    label = loc_type.replace("_", " ").title()
    print(f"  Choose destination ({label}):\n")
    for idx, n in enumerate(names, 1):
        print(f"  {idx}) {n}")
    print(f"  {len(names)+1}) Cancel\n")
    sel = input("  > ").strip()
    try:
        k = int(sel)
    except ValueError:
        return None, None
    if 1 <= k <= len(names):
        return names[k-1], loc_type
    return None, None


# ─────────────────────────────────────────
# Main Action Menu (at sea)
# ─────────────────────────────────────────

def sea_action_menu(state: GameState) -> str:
    clear()
    print("═" * 52)
    print("  ⛵  AT SEA")
    print("═" * 52)
    print(state.status_text())
    print()
    print("  [1] Sail on (roll for sea encounter)")
    print("  [2] Make landfall (travel to port or village)")
    print("  [3] Check detailed status")
    print("  [4] View crew roster")
    print("  [5] View active quests")
    print("  [6] Save game")
    print("  [Q] Quit\n")
    return input("  > ").strip().upper()


# ─────────────────────────────────────────
# Handle Landfall
# ─────────────────────────────────────────

def handle_landfall(
    state: GameState,
    engine: EventEngine,
    crew_data: Dict[str, Any],
    all_quests: List[Dict[str, Any]],
):
    port_data = find_port(state.current_location, state.world)

    # First-time port flag
    if state.current_location_type in ("major_port", "village"):
        state.has_visited_port = True

    if port_data:
        # Special events (once-per-port narrative beats)
        engine.trigger_special_if_any(state)

        if state.current_location_type == "major_port":
            port_action_menu(state, port_data, engine, crew_data, all_quests)
        else:
            # Village: simpler interaction
            engine.trigger_random("village_events", state)
    else:
        engine.trigger_random("harbor_events", state)


# ─────────────────────────────────────────
# Main Game Loop
# ─────────────────────────────────────────

def run_game(
    state: GameState,
    engine: EventEngine,
    crew_data: Dict[str, Any],
    all_quests: List[Dict[str, Any]],
):
    while True:
        if state.is_game_over():
            press_enter()
            break

        # Check quest expirations while at sea
        failed = state.quests.check_expirations(state.day)
        if failed:
            clear()
            for fq in failed:
                print(f"\n  ✗ Quest failed (time expired): '{fq.title}'")
                print(f"    {fq.giver_name} will remember this.")
            press_enter()

        if state.current_location_type == "sea":
            selection = sea_action_menu(state)
        else:
            # We've arrived — but returning to this loop means leaving port
            selection = "2"  # force travel menu

        if selection == "1":
            # Sail on — sea event if player has been to port
            state.time.advance_hours(random.randint(18, 30))
            state.apply_daily_crew_effects()
            if state.has_visited_port:
                if random.random() < 0.65:  # 65% chance per "day" of a sea encounter
                    engine.trigger_random("sea_events", state)
                else:
                    clear()
                    print("\n  The sea is quiet. The crew keeps to their duties. A day passes.")
                    press_enter()
            else:
                clear()
                print("\n  You sail calm waters. The horizon holds nothing unusual yet.")
                print("  (Sea encounters begin once you have made your first landfall.)")
                press_enter()

        elif selection == "2":
            dest, dest_type = travel_menu(state.world)
            if dest and dest_type:
                clear()
                from time_system import TRAVEL_TIMES, DEFAULT_TRAVEL_TIME
                travel_key = (state.current_location, dest)
                raw_days = TRAVEL_TIMES.get(travel_key, DEFAULT_TRAVEL_TIME)
                speed_bonus = state.crew.travel_speed_bonus()
                actual_days = state.time.travel(state.current_location, dest, speed_bonus)
                # Apply sea events during travel proportionally
                for _ in range(actual_days):
                    state.apply_daily_crew_effects()
                    if state.has_visited_port and random.random() < 0.40:
                        engine.trigger_random("sea_events", state)
                        if state.is_game_over():
                            press_enter()
                            return

                print(f"\n  You arrive at {dest} after {actual_days} day(s).")
                if speed_bonus:
                    print(f"  (Your navigator's skill saved {speed_bonus} day(s))")
                press_enter()

                state.current_location = dest
                state.current_location_type = dest_type
                handle_landfall(state, engine, crew_data, all_quests)
                # After leaving port, go back to sea
                state.current_location = "At Sea"
                state.current_location_type = "sea"
            else:
                print("\n  You remain where you are.")
                press_enter()

        elif selection == "3":
            clear()
            print(state.status_text())
            press_enter()

        elif selection == "4":
            clear()
            print("═" * 52)
            print("  CREW ROSTER")
            print("═" * 52)
            state.crew.roster_display()
            print(f"\n  Total wages per port: {state.crew.total_wages()} gold")
            print(f"  Trade bonus (current location): {int(state.crew.trade_bonus('', '')*100)}%")
            press_enter()

        elif selection == "5":
            clear()
            print("═" * 52)
            print("  ACTIVE QUESTS")
            print("═" * 52)
            if not state.quests.active:
                print("\n  No active quests.")
            for q in state.quests.active:
                print(q.status_line(state.day))
            press_enter()

        elif selection == "6":
            save_game(state)
            press_enter()

        elif selection == "Q":
            print("\n  Farewell, Captain. Until the next voyage.")
            break

        else:
            print("\n  Unknown option.")
            press_enter()


# ─────────────────────────────────────────
# Role Selection
# ─────────────────────────────────────────

def choose_role() -> str:
    clear()
    print("═" * 52)
    print("  THE STRAITS PROJECT")
    print("═" * 52)
    print("\n  Choose your background:\n")
    print("  [1] Portuguese Conquistador")
    print("       +10 gold, +5 morale. Starts with rapier.")
    print("       Carries the weight of the Estado da India.")
    print()
    print("  [2] Arab Muslim Dāʿī")
    print("       +10 morale, 2 pepper. Network of Muslim ports.")
    print("       Better received in Islamic polities.")
    print()
    print("  [3] Chinese Trader")
    print("       +15 gold, silk & porcelain cargo. Quanzhou contacts.")
    print("       The diaspora knows your name before you arrive.")
    print()
    mapping = {"1": "Portuguese Conquistador", "2": "Arab Muslim Dāʿī", "3": "Chinese Trader"}
    return mapping.get(input("\n  > ").strip(), "Portuguese Conquistador")


# ─────────────────────────────────────────
# Title Screen
# ─────────────────────────────────────────

def title_screen_text():
    clear()
    print()
    print("  ╔══════════════════════════════════════════════════╗")
    print("  ║          T H E   S T R A I T S   P R O J E C T  ║")
    print("  ║      A Historical Text RPG — Age of Discovery    ║")
    print("  ╚══════════════════════════════════════════════════╝")
    print()
    print("       Southeast Asia  •  Indian Ocean  •  East Africa")
    print()


def title_screen_pygame(img_path: str):
    try:
        import pygame
    except ModuleNotFoundError:
        return False
    abspath = os.path.abspath(img_path)
    if not os.path.isfile(abspath):
        return False

    pygame.init()
    W, H = 1280, 720
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("The Straits Project")

    bg = None
    try:
        bg = pygame.image.load(abspath).convert_alpha()
    except Exception:
        try:
            from PIL import Image
            im = Image.open(abspath).convert("RGBA")
            bg = pygame.image.fromstring(im.tobytes(), im.size, im.mode)
        except Exception:
            return False

    bw, bh = bg.get_width(), bg.get_height()
    r = min(W / bw, H / bh)
    scaled = pygame.transform.smoothscale(bg, (int(bw*r), int(bh*r)))
    ox = (W - scaled.get_width()) // 2
    oy = (H - scaled.get_height()) // 2

    GOLD = (220, 170, 60)
    BLACK = (0, 0, 0)
    font_t = pygame.font.SysFont("Georgia", 72, bold=True)
    font_p = pygame.font.SysFont("Verdana", 28)
    ts = font_t.render("THE STRAITS PROJECT", True, GOLD)
    sh = font_t.render("THE STRAITS PROJECT", True, BLACK)
    tr = ts.get_rect(center=(W//2, int(H*0.18)))
    pr = font_p.render("[ Press Enter ]", True, GOLD)
    prt = pr.get_rect(midbottom=(W//2, H - 28))

    clock = pygame.time.Clock()
    running = True
    while running:
        screen.fill((0, 0, 0))
        screen.blit(scaled, (ox, oy))
        screen.blit(sh, (tr.x + 2, tr.y + 3))
        screen.blit(ts, tr)
        screen.blit(pr, prt)
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit(0)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit(0)
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                running = False
        clock.tick(60)
    pygame.quit()
    return True


# ─────────────────────────────────────────
# Main Menu
# ─────────────────────────────────────────

def main_menu() -> str:
    clear()
    title_screen_text()
    print("  [1] New Voyage")
    print("  [2] Load (slot 1)")
    print("  [3] Quit\n")
    return input("  > ").strip()


def start_new_game(
    engine: EventEngine,
    world: Dict[str, Any],
    crew_data: Dict[str, Any],
    all_quests: List[Dict[str, Any]],
):
    role = choose_role()
    state = GameState(role, world)
    clear()
    print(f"\n  You set sail as a {role}.")
    print(f"\n  The year is 1511. The Strait of Malacca is the center of the world.\n"
          f"  Spice, silk, faith, and iron move through these waters in all directions.\n"
          f"  You are one more captain with an ambition and a leaking hull.\n")
    press_enter()
    run_game(state, engine, crew_data, all_quests)


# ─────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────

def main():
    ensure_dirs()

    try:
        events_data = load_events(EVENTS_PATH)
        world       = load_world(WORLD_PATH)
        crew_data   = load_crew_data()
        all_quests  = load_quests()
    except FileNotFoundError as e:
        print(f"\n  Missing data file: {e}")
        sys.exit(1)

    # Try pygame title screen, fall back to text
    img_path = os.path.join(ROOT_DIR, "assets", "title_straits.png")
    if not title_screen_pygame(img_path):
        clear()
        title_screen_text()
        press_enter()

    engine = EventEngine(events_data)

    while True:
        choice = main_menu()
        if choice == "1":
            start_new_game(engine, world, crew_data, all_quests)
        elif choice == "2":
            state = load_game(world)
            if state:
                press_enter()
                run_game(state, engine, crew_data, all_quests)
            else:
                press_enter()
        elif choice == "3":
            print("\n  Goodbye.")
            break
        else:
            print("\n  Invalid option.")
            press_enter()


if __name__ == "__main__":
    main()
