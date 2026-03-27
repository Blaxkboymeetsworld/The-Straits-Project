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

# ── Console encoding (Windows cp1252 fix) ────────────────────────────
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ─────────────────────────────────────────
# Module imports (same directory)
# ─────────────────────────────────────────
from crew import CrewManager, CrewMember, load_crew_data, recruitment_menu, slave_recruit_event
from economy import Economy, GOODS_CATALOG, MAX_CARGO, haggle
from faction import FactionManager, port_to_faction
from quests import QuestManager, load_quests
from time_system import TimeSystem, TRAVEL_TIMES, DEFAULT_TRAVEL_TIME
from systems import get_ibu_malam_appearance, maybe_trigger_lore, roll_check
from combat import naval_combat, personal_combat, bodyguard_intercept

# ─────────────────────────────────────────
# Paths
# ─────────────────────────────────────────
ROOT_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_DIR  = os.path.join(ROOT_DIR, "data")
SAVE_DIR  = os.path.join(ROOT_DIR, "saves")
EVENTS_PATH = os.path.join(DATA_DIR, "events.json")
WORLD_PATH  = os.path.join(DATA_DIR, "world.json")
SAVE_PATH   = os.path.join(SAVE_DIR, "slot1.json")

NPC_KNOWLEDGE_PATH = os.path.join(DATA_DIR, "npc_knowledge.json")

VALID_EVENT_POOLS = {"sea_events", "harbor_events", "village_events", "special_events"}

# ── Internationalization (i18n) ───────────────────────────────────────
LOCALE: Dict[str, str] = {}

def load_locale(lang: str):
    global LOCALE
    path = os.path.join(DATA_DIR, f"lang_{lang}.json")
    with open(path, "r", encoding="utf-8") as f:
        LOCALE = json.load(f)

def t(key: str) -> str:
    return LOCALE.get(key, f"[{key}]")

# Maps port name → harbor master NPC id for query_npc resolution
PORT_HARBOR_MASTERS: Dict[str, str] = {
    "Malacca Harbor": "hang_kassim_malacca",
    "Bantam":         "raden_aria_bantam",
    "Hormuz":         "abbas_ibn_yusuf_hormuz",
    "Quanzhou":       "wu_liangchen_quanzhou",
    "Aden Harbor":    "ibrahim_al_yamani_aden",
    "Goa Harbor":     "rodrigo_rabelo_goa",
    "Calicut":        "koya_moopan_calicut",
}


# ─────────────────────────────────────────
# Utility
# ─────────────────────────────────────────

def clear():
    try:
        os.system("cls" if os.name == "nt" else "clear")
    except Exception:
        pass

def press_enter():
    input(f"\n  {t('press_enter')}")

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

def harbor_master_for(port_name: str, world: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return the harbor_master dict from within the port's entry, or None.
    Reads from major_ports (and villages) — NOT from the empty harbor_masters array.
    """
    port = find_port(port_name, world)
    return port.get("harbor_master") if port else None


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

        # Protagonist name (set during opening scene)
        self.protagonist_name: str = {
            "Portuguese Conquistador": "Tomé de Faro",
            "Ottoman Trader":          "Mehmed Bey",
            "Chinese Trader":          "Chen Mingzhi",
        }.get(role, "Unknown")

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

        # Provisions (consumed at sea; cook reduces drain rate)
        self.provisions: int = 60

        # Crew
        self.crew = CrewManager()

        # Quests
        self.quests = QuestManager()

        # Factions
        self.factions = FactionManager()

        # Per-NPC disposition scores (default 50 when absent)
        self.npc_dispositions: Dict[str, int] = {}

        # New fields (v0.2.0-pass1)
        self.reputation_tier: int = 0       # 0=Unknown 1=Noted 2=Familiar 3=Well Received 4=Trusted 5=Insider
        self.faction_standing: Dict[str, int] = {}  # faction_id -> tier 0-5
        self.assignments_completed: int = 0         # increments on quest completion
        self.seen_lore_flags: List[str] = []        # tracks which historical blurbs have been shown
        self.player_traits: List[str] = []          # STUB — empty for now, do not implement trait logic yet
        # NOTE: self.crew is already a CrewManager above
        self.slaves_aboard: int = 0                 # count (separate from slave_cargo in holds)
        self.combat_enabled: bool = False           # STUB — do not implement combat yet
        self.lang: str = "en"                       # language selection, saved and restored

        # TODO v0.3: Player traits assigned at character creation
        # player_traits field stubbed and ready
        # Traits will be selected during intro sequences and affect
        # dialogue options, haggle modifiers, and NPC reactions.

        # Role adjustments + faction starting rep
        if role == "Portuguese Conquistador":
            self.gold += 10
            self.morale += 5
            self.factions.adjust_disposition("estado_da_india", +20)   # 50→70 Friendly
            self.factions.adjust_disposition("hadrami_silsila", -15)   # 45→30 Suspicious
        elif role == "Ottoman Trader":
            self.gold += 20
            self.spices += 3
            self.morale += 8
            self.cargo["pepper"] = 2
            # Ottoman Trader starts friendly with the Hadrami network, hostile to Portuguese
            self.factions.adjust_disposition("hadrami_silsila", +20)   # 45→65 Friendly
            self.factions.adjust_disposition("estado_da_india", -40)   # 50→10 Hostile
        elif role == "Chinese Trader":
            self.gold += 15
            self.spices += 5
            self.cargo["silk"] = 3
            self.cargo["porcelain"] = 2
            self.factions.adjust_disposition("ming_dynasty", +15)      # 45→60 Friendly

    @property
    def day(self) -> int:
        return self.time.day

    @property
    def year(self) -> int:
        """In-game year number (1–15)."""
        return (self.time.day - 1) // 365 + 1

    @property
    def calendar_year(self) -> int:
        """Historical calendar year."""
        return 1510 + self.year

    def cargo_capacity(self) -> int:
        """Returns the ship's cargo capacity (ship upgrades can override this)."""
        return MAX_CARGO

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "protagonist_name": self.protagonist_name,
            "gold": self.gold,
            "spices": self.spices,
            "ship_health": self.ship_health,
            "morale": self.morale,
            "provisions": self.provisions,
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
            "factions": self.factions.to_dict(),
            "npc_dispositions": self.npc_dispositions,
            # v0.2.0-pass1 fields
            "reputation_tier": self.reputation_tier,
            "faction_standing": self.faction_standing,
            "assignments_completed": self.assignments_completed,
            "seen_lore_flags": self.seen_lore_flags,
            "player_traits": self.player_traits,
            "slaves_aboard": self.slaves_aboard,
            "combat_enabled": self.combat_enabled,
            "lang": self.lang,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any], world: Dict[str, Any]) -> "GameState":
        obj = cls.__new__(cls)
        obj.role = d.get("role", "Portuguese Conquistador")
        obj.protagonist_name = d.get("protagonist_name", {
            "Portuguese Conquistador": "Tomé de Faro",
            "Ottoman Trader":          "Mehmed Bey",
            "Chinese Trader":          "Chen Mingzhi",
        }.get(obj.role, "Unknown"))
        obj.gold = int(d.get("gold", 0))
        obj.spices = int(d.get("spices", 0))
        obj.ship_health = int(d.get("ship_health", 100))
        obj.morale = int(d.get("morale", 50))
        obj.provisions = int(d.get("provisions", 60))
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
        obj.factions = FactionManager.from_dict(d.get("factions", {}))
        obj.npc_dispositions = d.get("npc_dispositions", {})
        # v0.2.0-pass1 fields — defaults prevent crashes on pre-pass1 saves
        obj.reputation_tier = int(d.get("reputation_tier", 0))
        obj.faction_standing = d.get("faction_standing", {})
        obj.assignments_completed = int(d.get("assignments_completed", 0))
        obj.seen_lore_flags = d.get("seen_lore_flags", [])
        obj.player_traits = d.get("player_traits", [])
        obj.slaves_aboard = int(d.get("slaves_aboard", 0))
        obj.combat_enabled = bool(d.get("combat_enabled", False))
        obj.lang = d.get("lang", "en")
        return obj

    def apply_effect(self, effect: Dict[str, Any]):
        self.gold        = max(0, self.gold        + int(effect.get("gold", 0)))
        self.spices      = max(0, self.spices      + int(effect.get("spices", 0)))
        self.ship_health = max(0, min(100, self.ship_health + int(effect.get("ship_health", 0))))
        self.morale      = max(0, min(100, self.morale      + int(effect.get("morale", 0))))

    def is_game_over(self) -> bool:
        if self.ship_health <= 0:
            print(f"\n  ⚓ {t('game_over_ship')}")
            return True
        if self.morale <= 0:
            print(f"\n  ⚓ {t('game_over_morale')}")
            return True
        return False

    def apply_daily_crew_effects(self):
        """Called each time a day passes at sea."""
        self.morale = min(100, self.morale + self.crew.morale_per_day_bonus())
        drain = self.crew.daily_morale_drain()
        if drain:
            self.morale = max(0, self.morale - drain)

        # ── Provisions consumption ──
        # Cook reduces drain from 2/day to 1/day
        provision_drain = 1 if self.crew.has_occupation("cook") else 2
        if self.provisions > 0:
            self.provisions = max(0, self.provisions - provision_drain)
        else:
            # No provisions: morale -5/day, risk of crew casualty
            self.morale = max(0, self.morale - 5)
            if roll_check(0.10):
                alive = self.crew.alive_members()
                if alive:
                    victim = random.choice(alive)
                    victim.alive = False
                    print(f"\n  ⚠  {victim.name} has died from hunger and exhaustion.")

        # ── Priest/Imam/Monk morale recovery ──
        # Without one, morale recovers slower (no bonus). With one: +1/day extra.
        if not self.crew.has_occupation("priest"):  # priest covers imam/monk in crew_data
            # Morale recovers 1 point slower per day without spiritual support
            self.morale = max(0, self.morale - 1)

        # ── Cook absence: additional morale drain ──
        if not self.crew.has_occupation("cook"):
            self.morale = max(0, self.morale - 2)

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
        prov_warn = "  ⚠ LOW" if self.provisions < 10 else ""
        return (
            f"  {t('status_day')}: {self.time.display}  •  Year {self.year} ({self.calendar_year})\n"
            f"  {t('status_role')}: {self.role}  —  {self.protagonist_name}\n"
            f"  {t('status_location')}: {self.current_location} ({self.current_location_type.replace('_',' ')})\n"
            f"  {t('status_gold')}: {self.gold}  |  Provisions: {self.provisions}{prov_warn}  |  Cargo: {cargo_used}/{self.cargo_capacity()}\n"
            f"  {t('status_ship_health')}: {self.ship_health}  |  {t('status_morale')}: {self.morale}\n"
            f"  Crew: {self.crew.count()} aboard  |  Active quests: {active_q}"
        )


# ─────────────────────────────────────────
# Save / Load
# ─────────────────────────────────────────

def save_game(state: GameState):
    ensure_dirs()
    with open(SAVE_PATH, "w", encoding="utf-8") as f:
        json.dump(state.to_dict(), f, ensure_ascii=False, indent=2)
    print(f"\n  💾 {t('save_confirm')}")

def load_game(world: Dict[str, Any]) -> Optional[GameState]:
    if not os.path.exists(SAVE_PATH):
        print(f"\n  {t('load_none')}")
        return None
    with open(SAVE_PATH, "r", encoding="utf-8") as f:
        d = json.load(f)
    state = GameState.from_dict(d, world)
    # Restore saved language
    load_locale(state.lang)
    print(f"\n  📂 {t('load_confirm')}")
    return state


# ─────────────────────────────────────────
# Event Engine
# ─────────────────────────────────────────

class EventEngine:

    def __init__(self, events_data: Dict[str, Any], knowledge: Dict[str, Any] = None):
        self.events = events_data
        self.knowledge = knowledge or {}

    def query_npc(self, npc_id: str, state: "GameState"):
        npc_data = self.knowledge.get(npc_id, {})
        entries  = npc_data.get("knowledge", [])
        fallback = npc_data.get("fallback", "They have nothing to add.")

        while True:
            query = input("\n  Ask about something (or press Enter to leave): ").strip().lower()
            if not query:
                break
            matched = next(
                (
                    e for e in entries
                    if query in e["topic"]
                    or any(query in a for a in e.get("aliases", []))
                    or e["topic"] in query
                ),
                None,
            )
            if not matched:
                print(f"\n  {fallback}")
                continue
            disp = state.npc_dispositions.get(npc_id, 50)
            if disp < matched.get("min_disposition", 0):
                print(f"\n  {matched.get('locked_response', 'They are not willing to discuss that.')}")
                continue
            print(f"\n  {matched['response']}")
        press_enter()

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
        for desc_key in ("description", "description_es"):
            if desc_key in out and isinstance(out[desc_key], str):
                out[desc_key] = self._format_text(out[desc_key], ctx)
        opts = out.get("options", {})
        for key, opt in list(opts.items()):
            for text_key in ("text", "text_es"):
                if text_key in opt and isinstance(opt[text_key], str):
                    opt[text_key] = self._format_text(opt[text_key], ctx)
        return out

    def _context_for_event(self, state: GameState) -> Dict[str, Any]:
        hm = harbor_master_for(state.current_location, state.world)
        harbor_fee = hm["fees"] if hm else 10
        return {
            "current_port": state.current_location,
            "harbormaster_name": hm["name"] if hm else "the harbor master",
            "harbor_fee": harbor_fee,
        }

    def _resolve_event(self, event: Dict[str, Any], state: GameState, once_key: Optional[str] = None):
        clear()
        lang = getattr(state, "lang", "en")
        title = event.get("id", "Event").replace("_", " ").title()
        print(f"\n  ── {title} ──\n")

        # Serve description in active language, fall back to English
        desc = event.get("description", "An event occurs.")
        if lang != "en":
            desc = event.get(f"description_{lang}", desc)
        print(f"  {desc}\n")

        options = event.get("options", {})
        if not options:
            press_enter()
            return

        keys_sorted = sorted(options.keys(), key=lambda k: str(k))

        # Only show options the player can actually take
        available_keys = [k for k in keys_sorted if self._check_requirement(options[k].get("requires", {}), state)]
        unavailable_keys = [k for k in keys_sorted if k not in available_keys]

        for k in available_keys:
            opt_text = options[k].get("text", "...")
            if lang != "en":
                opt_text = options[k].get(f"text_{lang}", opt_text)
            print(f"  {k}) {opt_text}")
        if unavailable_keys:
            print(f"\n  (Some options unavailable — crew lacks the required skill, item, or gold)")

        print()
        choice = input("  > ").strip()

        if choice not in available_keys:
            print(f"\n  {t('you_hesitate')}")
        else:
            effect = options[choice].get("effect", {})
            state.apply_effect(effect)
            print(f"\n  {t('outcome_applied')}")

        if once_key:
            state.once_flags.append(once_key)

        # If the event names an NPC, open the free-text query sub-loop
        npc_id = event.get("npc_id")
        if npc_id == "harbor_master":
            npc_id = PORT_HARBOR_MASTERS.get(state.current_location)
        if npc_id and npc_id in self.knowledge:
            self.query_npc(npc_id, state)
        else:
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
# Provisions restocking
# ─────────────────────────────────────────

def _restock_provisions(state: GameState, port_data: Dict[str, Any], clear_fn, press_enter_fn):
    """Buy provisions at port. Cost scales by port remoteness."""
    clear_fn()
    print("═" * 52)
    print(f"  PROVISIONS — {port_data['name']}")
    print("═" * 52)

    # Remoteness proxy: use travel time from Malacca as a distance indicator
    remote_ports = {"Ternate", "Banda Islands", "Keelung Outpost", "Cham Coast Anchorage"}
    cost_per_unit = 3 if port_data["name"] in remote_ports else 2

    max_fill = 100 - state.provisions
    print(f"\n  Current provisions: {state.provisions}/100")
    print(f"  Cost: {cost_per_unit} gold per unit")
    print(f"  Gold available: {state.gold}\n")

    if max_fill <= 0:
        print("  Provisions are full.")
        press_enter_fn()
        return

    max_afford = state.gold // cost_per_unit
    buy_str = input(f"  Buy how many? (max {min(max_fill, max_afford)}): ").strip()
    if buy_str.isdigit():
        qty = int(buy_str)
        cost = qty * cost_per_unit
        if qty <= 0:
            pass
        elif cost > state.gold:
            print("\n  Not enough gold.")
            press_enter_fn()
        elif qty > max_fill:
            print(f"\n  You can only buy {max_fill} more units.")
            press_enter_fn()
        else:
            state.gold -= cost
            state.provisions = min(100, state.provisions + qty)
            print(f"\n  Restocked {qty} provisions for {cost} gold.")
            print(f"  Provisions: {state.provisions}/100")
            press_enter_fn()


# ─────────────────────────────────────────
# Sneak-in mechanic (barred ports)
# ─────────────────────────────────────────

def _sneak_in_menu(
    state: GameState,
    dest: str,
    dest_type: str,
    engine: "EventEngine",
    clear_fn,
    press_enter_fn,
):
    """
    Offer sneak-in options when a player tries to enter a barred port.
    Sets state._sneak_in_success = True if successful.
    """
    clear_fn()
    print("═" * 52)
    print(f"  BARRED FROM {dest.upper()}")
    print("═" * 52)
    print(
        "\n  You cannot dock openly. But there may be ways in.\n"
    )
    print("  [1] Disguise (worldly/polyglot crew required, costs gold)")
    print("  [2] Bribe the harbor watch (costs gold, lower base chance)")
    print("  [3] False flag (requires matching ethnicity crew or item)")
    print("  [4] Force entry (risky — low success, severe consequences)")
    print("  [Q] Turn back\n")

    choice = input("  > ").strip().upper()

    if choice == "Q":
        state._sneak_in_success = False
        return

    from systems import roll_check

    if choice == "1":
        # Disguise: worldly or polyglot crew needed
        if not (state.crew.has_trait("worldly") or state.crew.has_trait("polyglot")):
            print("\n  You have no one who can carry off a convincing disguise here.")
            state._sneak_in_success = False
            press_enter_fn()
            return
        cost = 30
        if state.gold < cost:
            print(f"\n  You need {cost} gold for the disguise materials.")
            state._sneak_in_success = False
            press_enter_fn()
            return
        state.gold -= cost
        success = roll_check(0.60)
        if success:
            print(f"\n  The disguise holds. You slip through the harbor gate without incident.")
            state._sneak_in_success = True
        else:
            print("\n  The disguise fails. The watch is suspicious but lets you go — for now.")
            state.morale = max(0, state.morale - 5)
            state._sneak_in_success = False
        press_enter_fn()

    elif choice == "2":
        cost = 50
        if state.gold < cost:
            print(f"\n  The bribe requires at least {cost} gold.")
            state._sneak_in_success = False
            press_enter_fn()
            return
        state.gold -= cost
        success = roll_check(0.40)
        if success:
            print("\n  The watch takes the coin and looks the other way.")
            state._sneak_in_success = True
        else:
            print("\n  The watch takes the coin — and still bars entry. You've made things worse.")
            state.factions.adjust_rep(port_to_faction(dest) or "malacca_sultanate", -1)
            state._sneak_in_success = False
        press_enter_fn()

    elif choice == "3":
        # False flag: need crew member with matching ethnicity
        faction_id = port_to_faction(dest)
        port_data = find_port(dest, state.world)
        port_culture = port_data.get("culture", "") if port_data else ""
        matching = [m for m in state.crew.alive_members() if m.ethnicity in port_culture or port_culture in m.ethnicity]
        if not matching and "cartaz" not in state.items:
            print("\n  You have no crew or papers that would pass scrutiny here.")
            state._sneak_in_success = False
            press_enter_fn()
            return
        success = roll_check(0.55)
        if success:
            print("\n  Under borrowed colors, you ease into the harbor.")
            state._sneak_in_success = True
        else:
            print("\n  The harbor master isn't fooled. You are turned away with a warning.")
            state._sneak_in_success = False
        press_enter_fn()

    elif choice == "4":
        # Force: very low base chance, severe consequences
        success = roll_check(0.15)
        if success:
            state.ship_health = max(0, state.ship_health - random.randint(10, 25))
            print("\n  You batter through. The harbor is yours — for now. This will cost you.")
            if faction_id := port_to_faction(dest):
                state.factions.adjust_rep(faction_id, -1)
            state._sneak_in_success = True
        else:
            dmg = random.randint(20, 40)
            state.ship_health = max(0, state.ship_health - dmg)
            state.morale = max(0, state.morale - 15)
            gold_loss = random.randint(20, 60)
            state.gold = max(0, state.gold - gold_loss)
            print(
                f"\n  The attempt fails. Ship damage: {dmg}. "
                f"You lose {gold_loss} gold to the chaos. Morale collapses."
            )
            state._sneak_in_success = False
        press_enter_fn()

    else:
        state._sneak_in_success = False


# ─────────────────────────────────────────
# World events
# ─────────────────────────────────────────

def _check_world_events(state: GameState, engine: "EventEngine"):
    """Check and fire timed world events based on game year."""

    # ── Fall of Malacca — Year 1, days 1–30 ──────────────────────────
    if (
        state.year == 1
        and state.day <= 30
        and "world_event_malacca_fall" not in state.once_flags
    ):
        state.once_flags.append("world_event_malacca_fall")
        _world_event_fall_of_malacca(state)

    # ── Albuquerque's Death — Year 5 ──────────────────────────────────
    if (
        state.year >= 5
        and "world_event_albuquerque_death" not in state.once_flags
    ):
        state.once_flags.append("world_event_albuquerque_death")
        _world_event_albuquerque_death(state)

    # ── Fall of Mamluks — Year 6 ──────────────────────────────────────
    if (
        state.year >= 6
        and "world_event_mamluks_fall" not in state.once_flags
    ):
        state.once_flags.append("world_event_mamluks_fall")
        _world_event_fall_of_mamluks(state)


def _world_event_albuquerque_death(state: GameState):
    clear()
    print("═" * 52)
    print("  WORLD EVENT — THE DEATH OF ALBUQUERQUE")
    print("═" * 52)
    print(
        "\n  Word reaches you: Afonso de Albuquerque is dead.\n\n"
        "  He died at sea off Goa, returning to Portugal in disgrace —\n"
        "  his enemies in Lisbon had poisoned the king's ear against him\n"
        "  before he could answer. The man who built the Estado da India,\n"
        "  who took Goa and Malacca and Hormuz, died knowing he had been\n"
        "  betrayed by the court he served.\n\n"
        "  The ships he built are still sailing.\n"
        "  Nobody who comes after him will be what he was.\n"
    )

    if state.role == "Portuguese Conquistador":
        print(
            "  You served — in some sense — under the same Crown that\n"
            "  discarded him. That is worth sitting with.\n"
        )
    elif state.role == "Ottoman Trader":
        print(
            "  The man most dangerous to Ottoman ambitions in the Indian\n"
            "  Ocean is gone. His successors will be smaller men.\n"
            "  This is an opportunity.\n"
        )
    else:
        print(
            "  Old Liang hears the news and says nothing for a long time.\n"
            "  Then: 'A capable enemy is a known enemy. What comes next\n"
            "  will be harder to read.'\n"
        )

    # Mechanical: Estado loses some bite, Goa ruler replaced
    state.factions.adjust_disposition("estado_da_india", -5)
    state.once_flags.append("albuquerque_is_dead")
    press_enter()


def _world_event_fall_of_malacca(state: GameState):
    clear()
    print("═" * 52)
    print("  WORLD EVENT — THE FALL OF MALACCA")
    print("═" * 52)

    if state.role == "Portuguese Conquistador":
        tone = (
            "Your nation's doing. Albuquerque sails under the same Crown that issued\n"
            "  your letters. You feel pride cut with something that is not quite unease —\n"
            "  but almost."
        )
    elif state.role == "Ottoman Trader":
        tone = (
            "Cold calculation settles over you. Malacca in Portuguese hands means the\n"
            "  spice routes rewire. Some men will lose fortunes. Others will make them.\n"
            "  You intend to be the latter."
        )
    else:
        tone = (
            "Alarm. The Ming tributary order is cracking. If Malacca falls, every trade\n"
            "  relationship your family built in the strait is at risk. You need to move."
        )

    print(
        "\n  Word reaches you from a Portuguese carrack:\n\n"
        "  \"Afonso de Albuquerque has sailed from Goa with seventeen ships and\n"
        "  twelve hundred men. The fleet is bound for Malacca — richest port in\n"
        "  the world. The city will fall or hold within the month. Whatever happens\n"
        "  there will change every trade route you know.\"\n\n"
        f"  {tone}\n"
    )

    # Faction reputation shifts
    state.factions.adjust_rep("estado_da_india", +1)
    state.factions.adjust_rep("malacca_sultanate", -1)
    state.factions.adjust_disposition("estado_da_india", +10)
    state.factions.adjust_disposition("malacca_sultanate", -10)

    print("  [Arrive at Malacca to witness the siege]")
    print("  [Or continue your current course]\n")
    press_enter()

    # Ibu Malam at Malacca trigger (fires if player reaches Malacca during this window)
    state.once_flags.append("ibu_malam_malacca_available")


def _world_event_fall_of_mamluks(state: GameState):
    clear()
    print("═" * 52)
    print("  WORLD EVENT — THE FALL OF THE MAMLUKS")
    print("═" * 52)

    if state.role == "Ottoman Trader":
        # Full scene: Mustafa at the Aden anchorage at dawn
        print(
            "\n  Mustafa al-Rumi finds you at the Aden anchorage before sunrise.\n"
            "  He does not speak immediately. He sits on a mooring post\n"
            "  and watches the water until you ask him.\n\n"
            "  \"Cairo has fallen. Selim has the caliphate. The Mamluks are finished.\"\n\n"
            "  He is quiet for a moment.\n\n"
            "  \"We won.\"\n\n"
            "  He does not look like a man who has won.\n"
        )
        state.factions.adjust_rep("hadrami_silsila", +1)
        state.factions.adjust_disposition("hadrami_silsila", +15)
        # Unlock senior Ottoman quest tier
        state.once_flags.append("ottoman_senior_tier_unlocked")
        print(
            "\n  Your standing with Ottoman networks in the Gulf improves sharply.\n"
            "  New doors are opening. Others are closing for good.\n"
        )

    elif state.role == "Portuguese Conquistador":
        print(
            "\n  A despatch from the Estado da India reaches you:\n\n"
            "  Egypt is Ottoman. All Portuguese vessels in the Gulf\n"
            "  are on heightened alert. The Mamluk threat is gone —\n"
            "  but what replaces it may be worse.\n\n"
            "  You fold the letter and watch the horizon.\n"
        )

    else:  # Chinese Trader
        print(
            "\n  A Gujarati merchant at Bantam heard it from an Arab captain\n"
            "  out of Aden. The story passes through three languages\n"
            "  before it reaches you.\n\n"
            "  Old Liang says nothing for a long time.\n"
            "  Then: 'The price of pepper at Quanzhou will change.'\n\n"
            "  He is right within three months.\n"
        )
        # Price shift: Quanzhou pepper cheaper (route reopening)
        state.once_flags.append("quanzhou_pepper_price_shifted")

    # All: Karimi network collapses
    state.factions.adjust_disposition("karimi_merchants", -20)
    state.once_flags.append("karimi_network_collapsed")

    # Trigger Chen Mingzhi's Prefect quest availability
    if state.role == "Chinese Trader":
        state.once_flags.append("world_event_mamluks_fall")  # enables chen_prefect quest

    press_enter()


# ─────────────────────────────────────────
# Ibu Malam trigger helper
# ─────────────────────────────────────────

def _check_ibu_malam(state: GameState, trigger: str):
    """Print Ibu Malam appearance if trigger is eligible."""
    lang_map = {
        "Portuguese Conquistador": "Portuguese",
        "Ottoman Trader": "Ottoman Turkish",
        "Chinese Trader": "Mandarin",
    }
    lang = lang_map.get(state.role, "Portuguese")
    text = get_ibu_malam_appearance(trigger, state, lang)
    if text:
        print(text)
        press_enter()


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
    econ = Economy(port_data)

    # Goa temporal modifier: Albuquerque present Years 1-4
    if port_data["name"] == "Goa Harbor":
        ruler = port_data.get("ruler", {})
        active_years = ruler.get("active_years", [])
        if (
            active_years
            and state.year >= active_years[0]
            and state.year <= active_years[-1]
            and "albuquerque_is_dead" not in state.once_flags
        ):
            # Albuquerque is present — Portuguese protagonist gets a bonus
            if state.role == "Portuguese Conquistador":
                state.factions.adjust_disposition("estado_da_india", +10)
                if "goa_albuquerque_bonus_applied" not in state.once_flags:
                    state.once_flags.append("goa_albuquerque_bonus_applied")
                    clear()
                    print(
                        "\n  Dom Afonso de Albuquerque is in residence at Goa.\n"
                        "  Whatever you think of the man — and most who have met him\n"
                        "  think carefully before deciding — his presence raises your\n"
                        "  standing with the Estado da India.\n"
                    )
                    press_enter()

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
        access = state.time.port_access_status()
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
        opt("7", "Rest for several hours (+8 hrs, +5 morale)")
        opt("8", "View crew roster")
        opt("9", "View active quests")
        opt("P", "Restock provisions")
        opt("F", "Faction standing")
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
            print("\n  The crew stands down for several hours. The ship rocks gently at anchor.")
            state.time.advance_hours(8)
            state.morale = min(100, state.morale + 5)
            print(f"\n  Time passes. {state.time.display}")
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

        # ── Restock provisions ──
        elif choice == "P":
            _restock_provisions(state, port_data, clear, press_enter)

        # ── Faction standing ──
        elif choice == "F":
            clear()
            state.factions.faction_summary()
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
    # TODO v0.4: Mini-games
    # 1. Mahjong — Chinese ports (Quanzhou, Chinese-resident quarters)
    # 2. Mancala — Arab/African ports (Aden, Hormuz, Calicut)
    # 3. Third game TBD — Portuguese or Javanese, respective ports
    # Do not implement until core systems v0.3 complete.
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

def travel_menu(world: Dict[str, Any], state: Any = None) -> Tuple[Optional[str], Optional[str]]:
    clear()
    print(f"  {t('travel_menu_title')}\n")
    print(f"  [1] {t('travel_major_ports')}")
    print(f"  [2] {t('travel_villages')}")
    print(f"  [3] {t('travel_cancel')}\n")
    top = input("  > ").strip()

    if top == "1":
        return choose_from_list(
            [p["name"] for p in world["major_ports"]], "major_port", state
        )
    if top == "2":
        return choose_from_list(
            [v["name"] for v in world["villages"]], "village", state
        )
    return None, None


def _travel_estimate(origin: str, dest: str, state: Any) -> str:
    """Return a human-readable travel time estimate string."""
    base = TRAVEL_TIMES.get((origin, dest), DEFAULT_TRAVEL_TIME)
    has_nav = state.crew.has_occupation("navigator") if state else False
    if has_nav:
        lo = max(1, base - 1)
        hi = base + 1
        nav_note = " (navigator)"
    else:
        lo = base + 4
        hi = base + 6
        nav_note = " (no navigator)"
    provision_drain = 1 if (state and state.crew.has_occupation("cook")) else 2
    prov_cost = (lo + hi) // 2 * provision_drain
    return f"Estimated: {lo}–{hi} days{nav_note}  |  ~{prov_cost} provisions"


def choose_from_list(
    names: List[str], loc_type: str, state: Any = None
) -> Tuple[Optional[str], Optional[str]]:
    clear()
    label = loc_type.replace("_", " ").title()
    origin = state.current_location if state else "At Sea"
    print(f"  Choose destination ({label}):\n")
    for idx, n in enumerate(names, 1):
        if state:
            est = _travel_estimate(origin, n, state)
            barred, _ = state.factions.port_access_modifier(n)
            bar_tag = "  [BARRED]" if not barred else ""
            print(f"  {idx}) {n:<26} {est}{bar_tag}")
        else:
            print(f"  {idx}) {n}")
    print(f"  {len(names)+1}) Cancel\n")
    sel = input("  > ").strip()
    try:
        k = int(sel)
    except ValueError:
        return None, None
    if 1 <= k <= len(names):
        chosen = names[k-1]
        # Confirm with travel estimate
        if state:
            clear()
            est = _travel_estimate(origin, chosen, state)
            print(f"\n  Destination: {chosen}")
            print(f"  {est}")
            print(f"  Provisions aboard: {state.provisions}\n")
            confirm = input("  Set sail? [Y/N] ").strip().upper()
            if confirm != "Y":
                return None, None
        return chosen, loc_type
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
    print(f"  [1] {t('action_sail')}")
    print(f"  [2] {t('action_landfall')}")
    print(f"  [3] {t('action_status')}")
    print("  [4] View crew roster")
    print("  [5] View active quests")
    print(f"  [6] {t('action_save')}")
    print(f"  [Q] {t('action_quit')}\n")
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
    is_first_port = not state.has_visited_port

    # First-time port flag
    if state.current_location_type in ("major_port", "village"):
        state.has_visited_port = True

    # Ibu Malam — first port appearance
    if is_first_port:
        _check_ibu_malam(state, "ibu_malam_first_port")

    # Ibu Malam — Malacca (if world event fired and player arrives here)
    if (
        state.current_location == "Malacca Harbor"
        and "ibu_malam_malacca_available" in state.once_flags
    ):
        _check_ibu_malam(state, "ibu_malam_malacca_fall")

    # Ibu Malam — Hormuz for Ottoman player
    if state.current_location == "Hormuz" and state.role == "Ottoman Trader":
        _check_ibu_malam(state, "ibu_malam_hormuz_mehmed")

    # Ibu Malam — Quanzhou for Chinese player
    if state.current_location == "Quanzhou" and state.role == "Chinese Trader":
        _check_ibu_malam(state, "ibu_malam_quanzhou_chen")

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

        # World events (timed, once-per-game)
        _check_world_events(state, engine)

        # Check quest expirations while at sea
        failed = state.quests.check_expirations(state.day)
        if failed:
            clear()
            for fq in failed:
                print(f"\n  ✗ Quest failed (time expired): '{fq.title}'")
                print(f"    {fq.giver_name} will remember this.")
                # Rep penalty for faction when quest expires
                if faction_id := port_to_faction(fq.giver_port):
                    state.factions.adjust_rep(faction_id, -1)
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

            # TODO v0.3: Combat system
            # Design conversation required before implementation.
            # Three protagonist combat styles will differ mechanically.
            # Portuguese: boarding actions, artillery advantage
            # Ottoman: merchant defense, crew loyalty under fire
            # Chinese: evasion, negotiation under duress
            # combat_enabled flag in GameState is False until ready.
            # Combat should feel like Heads Will Roll — explicit probability,
            # push-your-luck, visible risk. Not like the social/trade system.

            if state.has_visited_port:
                if roll_check(0.65):
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
            dest, dest_type = travel_menu(state.world, state)
            if dest and dest_type:
                # Check if player is barred at this destination
                can_dock, bar_reason = state.factions.port_access_modifier(dest)
                if not can_dock:
                    clear()
                    print(f"\n  {bar_reason}\n")
                    print("  You cannot approach openly.")
                    _sneak_in_menu(state, dest, dest_type, engine, clear, press_enter)
                    # If still blocked after sneak-in attempt, skip
                    if not getattr(state, "_sneak_in_success", False):
                        state.__dict__.pop("_sneak_in_success", None)
                        continue
                    state.__dict__.pop("_sneak_in_success", None)

                clear()
                speed_bonus = state.crew.travel_speed_bonus()
                crew_before = set(id(m) for m in state.crew.alive_members())
                actual_days = state.time.travel(state.current_location, dest, speed_bonus)
                # Apply sea events during travel proportionally
                for _ in range(actual_days):
                    state.apply_daily_crew_effects()
                    # Urban legend: 10% chance each day
                    lore = maybe_trigger_lore(state)
                    if lore:
                        print(lore)
                    if state.has_visited_port and roll_check(0.40):
                        engine.trigger_random("sea_events", state)
                        if state.is_game_over():
                            press_enter()
                            return
                # Check for crew deaths during travel (Ibu Malam trigger)
                crew_after = set(id(m) for m in state.crew.alive_members())
                if crew_before - crew_after:
                    _check_ibu_malam(state, "ibu_malam_after_crew_death")

                # Navigator absence warning
                has_nav = state.crew.has_occupation("navigator")
                print(f"\n  You arrive at {dest} after {actual_days} day(s).")
                if speed_bonus:
                    print(f"  (Your navigator's skill saved {speed_bonus} day(s))")
                elif not has_nav:
                    print("  (No navigator — the crossing took longer than it should.)")
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
            print(f"\n  {t('farewell')}")
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
    print(f"  {t('menu_title')}")
    print("═" * 52)
    print(f"\n  {t('role_choose')}\n")
    print(f"  [1] {t('role_portuguese')}")
    print("       +10 gold, +5 morale. Starts with rapier.")
    print("       Carries the weight of the Estado da India.")
    print()
    print(f"  [2] {t('role_ottoman')}")
    print("       +20 gold, +3 spices, +8 morale. Istanbul connections, Levantine capital.")
    print("       Welcomed in Islamic ports. Estado da India views you with suspicion.")
    print()
    print(f"  [3] {t('role_chinese')}")
    print("       +15 gold, silk & porcelain cargo. Quanzhou contacts.")
    print("       The diaspora knows your name before you arrive.")
    print()
    mapping = {"1": "Portuguese Conquistador", "2": "Ottoman Trader", "3": "Chinese Trader"}
    return mapping.get(input("\n  > ").strip(), "Portuguese Conquistador")


# ─────────────────────────────────────────
# Title Screen
# ─────────────────────────────────────────

def title_screen_text():
    clear()
    print()
    print("  ╔══════════════════════════════════════════════════╗")
    title_padded = t("menu_title").center(48)
    print(f"  ║{title_padded}║")
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

def select_language() -> str:
    """Language selection screen — the ONLY screen with a hardcoded string.
    Everything after this point uses the locale system via t()."""
    clear()
    print("\n  Select your language / Selecciona tu idioma")
    print("  1) English")
    print("  2) Español\n")
    choice = input("  > ").strip()
    return "es" if choice == "2" else "en"


def main_menu() -> str:
    clear()
    title_screen_text()
    print(f"  [1] {t('menu_start')}")
    print(f"  [2] {t('menu_load')}")
    print(f"  [3] {t('menu_quit')}\n")
    return input("  > ").strip()


def _make_crew_member(
    name: str, ethnicity: str, native_tongue: str, occupation: str,
    other_languages: List[str], religion: str, world_region: str,
    positive_trait_ids: List[str], negative_trait_ids: List[str],
    wage: int, crew_data: Dict[str, Any],
) -> CrewMember:
    """Helper to build a hardcoded starting crew member."""
    occ_map = {o["id"]: o for o in crew_data.get("occupations", [])}
    pos_map = {t["id"]: t for t in crew_data.get("positive_traits", [])}
    neg_map = {t["id"]: t for t in crew_data.get("negative_traits", [])}
    return CrewMember(
        name=name,
        ethnicity=ethnicity,
        native_tongue=native_tongue,
        other_languages=other_languages,
        occupation=occupation,
        occupation_data=occ_map.get(occupation, {"id": occupation, "name": occupation.title()}),
        religion=religion,
        world_region=world_region,
        positive_traits=[pos_map[t] for t in positive_trait_ids if t in pos_map],
        negative_traits=[neg_map[t] for t in negative_trait_ids if t in neg_map],
        wage=wage,
    )


def _build_portuguese_crew(crew_data: Dict[str, Any]) -> List[CrewMember]:
    return [
        _make_crew_member(
            "Camila de Faro", "Portuguese", "Portuguese", "soldier",
            [], "Catholic", "Europe",
            ["calm_under_fire", "quick"], [], 8, crew_data
        ),
        _make_crew_member(
            "Rui Brandão", "Portuguese", "Portuguese", "sailor",
            [], "Catholic", "Europe",
            ["veteran_sailor"], ["superstitious"], 5, crew_data
        ),
        _make_crew_member(
            "Simão", "Portuguese", "Portuguese", "soldier",
            [], "Catholic", "Europe",
            ["strong", "pious"], [], 6, crew_data
        ),
        _make_crew_member(
            "Estêvão da Guiné", "Portuguese", "Portuguese", "interpreter",
            ["Arabic", "Malay"],  # developing
            "Catholic", "Europe",
            ["worldly", "polyglot"], [], 7, crew_data
        ),
    ]


def _build_ottoman_crew(crew_data: Dict[str, Any]) -> List[CrewMember]:
    return [
        _make_crew_member(
            "Yusuf al-Halabi", "Persian", "Persian", "navigator",
            ["Arabic", "Turkish"], "Islam", "Ottoman",
            ["worldly", "veteran_sailor"], [], 8, crew_data
        ),
        _make_crew_member(
            "Ibrahim", "Arab", "Arabic", "merchant",
            ["Turkish", "Persian"], "Islam", "Ottoman",
            ["sharp_trader", "polyglot"], [], 7, crew_data
        ),
        _make_crew_member(
            "Baraka", "East African", "Swahili", "physician",
            ["Arabic"], "Islam", "East Africa",
            ["healer"], ["haunted"], 6, crew_data
        ),
    ]


def _build_chinese_crew(crew_data: Dict[str, Any]) -> List[CrewMember]:
    return [
        _make_crew_member(
            "Old Liang", "Chinese (Hokkien)", "Hokkien", "navigator",
            ["Malay"], "Buddhism", "East Asia",
            ["veteran_sailor", "storyteller"], [], 6, crew_data
        ),
        _make_crew_member(
            "Ah Kow", "Chinese (Fujian)", "Hokkien", "sailor",
            [], "Buddhism", "East Asia",
            ["quick"], ["seasick"], 4, crew_data
        ),
        _make_crew_member(
            "Wei Chongde", "Chinese (Hokkien)", "Mandarin", "merchant",
            ["Hokkien", "Malay"], "Confucian", "East Asia",
            ["sharp_trader", "polyglot"], ["gossip"], 7, crew_data
        ),
    ]


def _opening_scene_portuguese(state: GameState):
    clear()
    print(
        "\n  You are Tomé de Faro, son of a minor Fidalgo house from the Algarve.\n"
        "  Your father's debts did not make the journey east. You did.\n\n"
        "  In your hold: pepper futures you cannot yet afford to buy, letters of\n"
        "  introduction to men who do not remember your father's name, and one cousin\n"
        "  who insisted on coming and whom you could not, in good conscience, refuse —\n"
        "  because she is the better sailor.\n"
    )
    press_enter()

    clear()
    print("  ── A WOMAN ON MY SHIP ──\n")
    print(
        "  At sea. Before first port.\n"
        "  Rui Brandão corners you at the tiller.\n\n"
        "  Rui: \"Captain. A word. About your cousin.\"\n"
    )

    print("  [1] \"She stays. End of discussion.\"")
    print("  [2] \"Watch your tone, Rui.\"")
    print("  [3] \"You want to tell her yourself?\"")
    print("  [4] [Deliver a rousing speech about equality]\n")
    choice = input("  > ").strip()

    camila = next((m for m in state.crew.alive_members() if m.name == "Camila de Faro"), None)
    rui = next((m for m in state.crew.alive_members() if m.name == "Rui Brandão"), None)

    if choice == "1":
        print("\n  Rui goes quiet. He nods once and returns to the rigging.")
        if rui:
            state.morale = max(0, state.morale - 2)
        if camila:
            state.morale = min(100, state.morale + 3)
        print("  (Rui: −2 morale. Camila: +3 morale.)")
    elif choice == "2":
        print("\n  He straightens. \"Aye, Captain.\" The tension sits in the air unresolved.")
        print("  (Neutral. The matter is stored.)")
    elif choice == "3":
        print(
            "\n  Rui goes pale. \"She'd run me through with that saber.\"\n"
            "  Camila drops from the rigging above — apparently she has been there the whole time.\n"
            "  The crew find this extremely funny."
        )
        state.morale = min(100, state.morale + 5)
        print("  (Crew morale +5.)")
    else:
        print(
            "\n  You clear your throat and begin. Something about the sea having no regard for\n"
            "  birth, and every hand being equal before God and the wind.\n\n"
            "  The crew exchange glances. Rui stares at his boots.\n"
            "  Camila sighs audibly from the rigging.\n\n"
            "  You are not, it turns out, an orator."
        )
        state.morale = max(0, state.morale - 3)
        state.once_flags.append("tome_is_not_an_orator")
        print("  (Morale −3. Stored: Tomé is not a speechmaker.)")

    press_enter()


def _opening_scene_ottoman(state: GameState):
    clear()
    print(
        "\n  You are Mehmed Bey, a junior bey of Levantine stock — which is to say,\n"
        "  you are Turkish enough for Istanbul and Arab enough for Aden, and neither\n"
        "  of those things matters once you are east of Hormuz.\n\n"
        "  In Southeast Asia you are simply a foreign merchant with a good ship\n"
        "  and better contacts. Baraka has been with you three years.\n"
        "  He does not speak of his family. You do not ask.\n"
    )
    press_enter()

    clear()
    print("  ── AT SEA, THREE DAYS OUT OF HORMUZ ──\n")
    baraka = next((m for m in state.crew.alive_members() if m.name == "Baraka"), None)
    if baraka:
        print(
            "  Baraka stands at the stern, watching the water.\n"
            "  He has been watching it for an hour.\n\n"
            "  You can leave him to it, or say something.\n"
        )
        print("  [1] Leave him to his thoughts")
        print("  [2] Stand beside him. Say nothing.")
        print("  [3] \"You all right?\"\n")
        choice = input("  > ").strip()
        if choice == "1":
            print("\n  You leave him. He does not move for another hour.")
        elif choice == "2":
            print(
                "\n  You stand there. He does not look at you.\n"
                "  After a while he says: \"Thank you, Captain.\"\n"
                "  You are not sure what for."
            )
            state.morale = min(100, state.morale + 3)
        else:
            print(
                "\n  He turns. Considers. \"I am where I choose to be.\"\n"
                "  He goes back to watching the water.\n"
                "  It is not unfriendly. It is simply true."
            )
    press_enter()


def _opening_scene_chinese(state: GameState):
    clear()
    print(
        "\n  You are Chen Mingzhi of Quanzhou — third son of a merchant family\n"
        "  with good silk contacts and a complicated relationship with the haijin.\n\n"
        "  Your father did not technically break the ban on private maritime trade.\n"
        "  You are simply not doing it technically either.\n\n"
        "  Wei Chongde came with the ship. You have decided not to examine this too closely.\n"
    )
    press_enter()

    clear()
    print("  ── THE CREDENTIALS ──\n")
    wei = next((m for m in state.crew.alive_members() if m.name == "Wei Chongde"), None)
    old_liang = next((m for m in state.crew.alive_members() if m.name == "Old Liang"), None)
    ah_kow = next((m for m in state.crew.alive_members() if m.name == "Ah Kow"), None)

    print(
        "  Wei Chongde unrolls a scroll of credentials. It is longer than he is tall.\n"
        "  Old Liang and Ah Kow stare.\n\n"
        "  Wei: \"I am Wei Chongde, appointed secretary and — ahem — court eunuch,\n"
        "  in service of the trading house of Chen. My credentials are, as you can\n"
        "  see, entirely in order.\"\n"
    )
    print("  [1] Accept at face value.")
    print("  [2] \"Are you... actually a eunuch?\"")
    print("  [3] \"I've sailed with stranger men.\"")
    print("  [4] Press the question.\n")
    choice = input("  > ").strip()

    loyalty_flag = "wei_loyalty_standard"

    if choice == "1":
        print("\n  Wei beams. Loyalty: high.")
        if old_liang:
            print("  Old Liang raises an eyebrow and returns to the rigging.")
        loyalty_flag = "wei_loyalty_high"
    elif choice == "2":
        print(
            "\n  Wei sweats. He stammers. You let it go.\n"
            "  He is visibly grateful. More grateful than the moment warrants."
        )
        loyalty_flag = "wei_loyalty_very_high"
    elif choice == "3":
        print(
            "\n  Wei relaxes entirely — his shoulders drop, his hands stop fidgeting.\n"
            "  \"That is. Very reassuring.\"\n"
            "  Old Liang nods once. This is his highest form of approval."
        )
        loyalty_flag = "wei_loyalty_very_high"
    else:
        print(
            "\n  Wei goes quiet. Then, very quietly: \"No. I am not. I ask for your discretion.\"\n"
            "  He has given you something he cannot take back.\n"
            "  He will not forget that you hold it."
        )
        loyalty_flag = "wei_loyalty_maximum"

    state.once_flags.append(loyalty_flag)
    press_enter()


def start_new_game(
    engine: EventEngine,
    world: Dict[str, Any],
    crew_data: Dict[str, Any],
    all_quests: List[Dict[str, Any]],
    lang: str = "en",
):
    role = choose_role()
    state = GameState(role, world)
    state.lang = lang

    # Build starting crew
    if role == "Portuguese Conquistador":
        for member in _build_portuguese_crew(crew_data):
            state.crew.add(member)
        # Portuguese starting gear
        state.items.append("rapier")
        _opening_scene_portuguese(state)

    elif role == "Ottoman Trader":
        for member in _build_ottoman_crew(crew_data):
            state.crew.add(member)
        _opening_scene_ottoman(state)

    elif role == "Chinese Trader":
        for member in _build_chinese_crew(crew_data):
            state.crew.add(member)
        _opening_scene_chinese(state)

    run_game(state, engine, crew_data, all_quests)


# ─────────────────────────────────────────
# Narrative Endings
# ─────────────────────────────────────────

def show_ending(ending_id: str, state: GameState):
    """Display a narrative ending screen."""
    clear()
    if ending_id == "ending_arab_network":
        print("\n  " + "═" * 52)
        print("  THE WEB HOLDS")
        print("  " + "═" * 52)
        print(
            "\n"
            "  The Hadrami silsila does not break — it bends, and the Portuguese\n"
            "  find no single throat to cut. You have become a thread in that web:\n"
            "  known in Aden, trusted in Calicut, received in Malacca without\n"
            "  suspicion. The cannon you brokered from the governor's factors sits\n"
            "  in a dhow hold somewhere in the Red Sea, and the Ottoman intentions\n"
            "  you relayed reach ears in Cairo before any courier from Istanbul.\n"
            "\n"
            "  You are not a conqueror. You are something older and harder to kill.\n"
            "\n"
            "  The sea does not care who claims it. It carries everyone.\n"
        )
        print(f"  Days at sea: {state.day}  |  Gold: {state.gold}  |  Crew: {state.crew.count()}")
        print("  " + "═" * 52)

    elif ending_id == "ending_portuguese_privateer":
        print("\n  " + "═" * 52)
        print("  THE KING'S LETTER")
        print("  " + "═" * 52)
        print(
            "\n"
            "  The cartaz hangs in a lacquered frame above your chart table.\n"
            "  You are no longer a pirate — you are the Estado da India's\n"
            "  instrument in waters too distant for its fleets to hold.\n"
            "  The Viceroy's seal buys you passage. Whether it buys you safety\n"
            "  is a different question.\n"
        )
        print("  " + "═" * 52)

    elif ending_id == "ending_pirate_legacy":
        print("\n  " + "═" * 52)
        print("  THE GHOST OF CHEN ZUYI")
        print("  " + "═" * 52)
        print(
            "\n"
            "  They say Chen Zuyi haunts the Strait still — that his network\n"
            "  never truly broke when Zheng He's fleet put him to the sword.\n"
            "  You know it is true. You have eaten at his table.\n"
        )
        print("  " + "═" * 52)

    elif ending_id == "ending_merchant_prince":
        print("\n  " + "═" * 52)
        print("  MERCHANT PRINCE")
        print("  " + "═" * 52)
        print(
            "\n"
            "  Three sultans know your name. Two guilds owe you favours.\n"
            "  The sea is a ledger and you are, for now, on the profitable side.\n"
        )
        print("  " + "═" * 52)

    else:
        print(f"\n  Ending: {ending_id}")

    press_enter()


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
        with open(NPC_KNOWLEDGE_PATH, encoding="utf-8") as _f:
            _raw_knowledge = json.load(_f)
        knowledge = {npc["id"]: npc for npc in _raw_knowledge.get("npcs", [])}
    except FileNotFoundError as e:
        print(f"\n  Missing data file: {e}")
        sys.exit(1)

    # Language selection — the single hardcoded screen. Everything after uses t().
    selected_lang = select_language()
    load_locale(selected_lang)

    # Try pygame title screen, fall back to text
    img_path = os.path.join(ROOT_DIR, "assets", "title_straits.png")
    title_screen_pygame(img_path)

    engine = EventEngine(events_data, knowledge)

    while True:
        choice = main_menu()
        if choice == "1":
            start_new_game(engine, world, crew_data, all_quests, lang=selected_lang)
        elif choice == "2":
            state = load_game(world)
            if state:
                # Reload locale to match the save's language
                load_locale(state.lang)
                press_enter()
                run_game(state, engine, crew_data, all_quests)
            else:
                press_enter()
        elif choice == "3":
            print(f"\n  {t('farewell')}")
            break
        else:
            print("\n  Invalid option.")
            press_enter()


if __name__ == "__main__":
    main()
