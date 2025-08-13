#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
The Straits Project — text RPG core loop
Locations + named harbor masters + role variants + Pygame title screen (uses your PNG)

Adds:
- Named harbor masters per major port via world.json.
- Role-specific variants for "harbormaster_intro" (description/options overrides).
- Lightweight templating: {harbormaster_name}, {current_port}, {harbor_fee}.
- Once-per-port behavior for harbormaster_intro (scoped by location).
- Full-color Pygame title screen that displays your provided PNG with centered title overlay.
"""

import json
import os
import random
import sys
from copy import deepcopy
from typing import Dict, Any, List, Optional, Tuple

# -------------------------
# Paths / constants
# -------------------------
ROOT_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(ROOT_DIR, "data")
SAVE_DIR = os.path.join(ROOT_DIR, "saves")

EVENTS_PATH = os.path.join(DATA_DIR, "events.json")
WORLD_PATH = os.path.join(DATA_DIR, "world.json")
SAVE_PATH = os.path.join(SAVE_DIR, "slot1.json")

VALID_EVENT_POOLS = {"sea_events", "harbor_events", "village_events", "special_events"}

# -------------------------
# Utility
# -------------------------
def clear():
    try:
        os.system("cls" if os.name == "nt" else "clear")
    except Exception:
        pass

def press_enter():
    input("\n[Enter] to continue...")

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

def load_world(path: str) -> Dict[str, List[Dict[str, Any]]]:
    data = load_json(path)
    data.setdefault("major_ports", [])
    data.setdefault("villages", [])
    data.setdefault("harbor_masters", [])
    return data

def harbor_master_for(port: str, world: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    for hm in world.get("harbor_masters", []):
        if hm.get("port") == port:
            return hm
    return None

# -------------------------
# Pygame title screen (PNG background)
# -------------------------
def title_screen_graphics_image(img_path: str, window_size=(1280, 720), show_centered_title=True):
    try:
        import pygame, os
    except ModuleNotFoundError:
        print("Pygame not installed. Run: pip install pygame"); press_enter(); return

    # Resolve path
    abspath = os.path.abspath(img_path)
    if not os.path.isfile(abspath):
        print("\n⚠️  Title image not found at:", abspath); press_enter(); return

    pygame.init()

    # Try native pygame loader first
    bg = None
    load_err = None
    try:
        bg = pygame.image.load(abspath).convert_alpha()
    except Exception as e:
        load_err = e

    # Fallback: Pillow -> RGBA -> pygame Surface
    if bg is None:
        try:
            from PIL import Image
            im = Image.open(abspath).convert("RGBA")   # strips weird modes/bit depths
            mode = im.mode  # "RGBA"
            data = im.tobytes()
            size = im.size
            bg = pygame.image.fromstring(data, size, mode)  # already alpha-capable
        except Exception as e2:
            print("\n⚠️  Could not load title image with pygame or Pillow.")
            print("Pygame error:", load_err)
            print("Pillow error:", e2)
            press_enter()
            return

    # Optionally resize window to image size
    if window_size is None:
        W, H = bg.get_width(), bg.get_height()
    else:
        W, H = window_size

    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("The Straits Project — Title")

    # Letterbox
    bw, bh = bg.get_width(), bg.get_height()
    r = min(W / bw, H / bh)
    scaled = pygame.transform.smoothscale(bg, (int(bw*r), int(bh*r)))
    sx, sy = scaled.get_width(), scaled.get_height()
    ox = (W - sx) // 2
    oy = (H - sy) // 2

    # Fonts/colors
    TITLE_GOLD = (220, 170, 60)
    SHADOW     = (0, 0, 0)
    PROMPT_G   = (220, 170, 60)

    def get_font(name, size, bold=False):
        try: return pygame.font.SysFont(name, size, bold=bold)
        except Exception: return pygame.font.Font(None, size)

    title_font  = get_font("Georgia", 72, bold=True)
    prompt_font = get_font("Verdana", 28)

    title_surface = title_font.render("THE STRAITS PROJECT", True, TITLE_GOLD)
    title_shadow  = title_font.render("THE STRAITS PROJECT", True, SHADOW)
    title_rect    = title_surface.get_rect(center=(W//2, int(H*0.18)))

    prompt = prompt_font.render("[ Press Enter ]", True, PROMPT_G)
    prompt_rect = prompt.get_rect(midbottom=(W//2, H - 28))

    # Show
    clock = pygame.time.Clock()
    running = True
    print("\n✅ Loaded title image:", abspath)

    while running:
        screen.fill((0,0,0))
        screen.blit(scaled, (ox, oy))
        # Centered title overlay (disable if your PNG already has perfect title)
        if show_centered_title:
            screen.blit(title_shadow, (title_rect.x + 2, title_rect.y + 3))
            screen.blit(title_surface, title_rect)
        screen.blit(prompt, prompt_rect)
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

# -------------------------
# Game State
# -------------------------
class GameState:
    def __init__(self, role: str, world: Dict[str, Any]):
        self.role = role
        self.gold = 30
        self.spices = 0
        self.ship_health = 100
        self.morale = 50
        self.day = 1

        self.world = world
        self.current_location: str = "At Sea"
        self.current_location_type: str = "sea"

        # One-time event flags (e.g., "harbormaster_intro|Malacca Harbor")
        self.once_flags: List[str] = []

        # Role adjustments
        if role == "Portuguese Conquistador":
            self.gold += 10
            self.morale += 5
        elif role == "Arab Muslim Dāʿī":
            self.spices += 2
            self.morale += 10
        elif role == "Chinese Trader":
            self.gold += 15
            self.spices += 5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "gold": self.gold,
            "spices": self.spices,
            "ship_health": self.ship_health,
            "morale": self.morale,
            "day": self.day,
            "current_location": self.current_location,
            "current_location_type": self.current_location_type,
            "once_flags": self.once_flags
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any], world: Dict[str, Any]) -> "GameState":
        obj = cls(d.get("role", "Portuguese Conquistador"), world)
        obj.gold = int(d.get("gold", 0))
        obj.spices = int(d.get("spices", 0))
        obj.ship_health = int(d.get("ship_health", 100))
        obj.morale = int(d.get("morale", 50))
        obj.day = int(d.get("day", 1))
        obj.current_location = d.get("current_location", "At Sea")
        obj.current_location_type = d.get("current_location_type", "sea")
        obj.once_flags = list(d.get("once_flags", []))
        return obj

    def apply_effect(self, effect: Dict[str, Any]):
        self.gold = max(0, self.gold + int(effect.get("gold", 0)))
        self.spices = max(0, self.spices + int(effect.get("spices", 0)))
        self.ship_health = max(0, min(100, self.ship_health + int(effect.get("ship_health", 0))))
        self.morale = max(0, min(100, self.morale + int(effect.get("morale", 0))))

    def is_game_over(self) -> bool:
        if self.ship_health <= 0:
            print("\n⚓ Your ship has been wrecked by misfortune at sea.")
            return True
        if self.morale <= 0:
            print("\n⚓ Your crew has lost all spirit and deserted you.")
            return True
        return False

    def status_text(self) -> str:
        return (
            f"Day {self.day}\n"
            f"Role: {self.role}\n"
            f"Location: {self.current_location} ({self.current_location_type})\n"
            f"Gold: {self.gold} | Spices: {self.spices}\n"
            f"Ship Health: {self.ship_health} | Morale: {self.morale}"
        )

# -------------------------
# IO: Save / Load
# -------------------------
def save_game(state: GameState):
    ensure_dirs()
    with open(SAVE_PATH, "w", encoding="utf-8") as f:
        json.dump(state.to_dict(), f, ensure_ascii=False, indent=2)
    print("\n💾 Game saved to slot 1.")

def load_game(world: Dict[str, Any]) -> Optional[GameState]:
    if not os.path.exists(SAVE_PATH):
        print("\nNo save found in slot 1.")
        return None
    with open(SAVE_PATH, "r", encoding="utf-8") as f:
        d = json.load(f)
    print("\n📂 Loaded save from slot 1.")
    return GameState.from_dict(d, world)

# -------------------------
# Event Engine
# -------------------------
class EventEngine:
    def __init__(self, events_data: Dict[str, Any]):
        self.events = events_data

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

    def _resolve_event(self, event: Dict[str, Any], state: GameState, once_key: Optional[str] = None):
        clear()
        title = event.get("id", "Event").replace("_", " ").title()
        print(f"— {title} —\n")
        print(event.get("description", "An event occurs.") + "\n")

        options = event.get("options", {})
        if not options:
            print("[DEV] Event missing options; skipping.]")
            return

        keys_sorted = sorted(options.keys(), key=lambda k: str(k))
        for k in keys_sorted:
            print(f"{k}) {options[k].get('text', '...')}")

        choice = input("\n> ").strip()
        if choice not in options:
            print("You hesitate, and time slips by...")
        else:
            effect = options[choice].get("effect", {})
            state.apply_effect(effect)
            print("\nOutcome applied.")
        if once_key:
            state.once_flags.append(once_key)
        press_enter()

    def _context_for_event(self, state: GameState) -> Dict[str, Any]:
        hm = harbor_master_for(state.current_location, state.world) if state.current_location_type == "major_port" else None
        ctx = {
            "current_port": state.current_location,
            "harbormaster_name": hm["name"] if hm else "the harbormaster",
            "harbor_fee": hm["fees"] if hm else 8
        }
        return ctx

    def trigger_random(self, pool_name: str, state: GameState):
        pool = self.events.get(pool_name, [])
        if not pool:
            print(f"\n(No events available for {pool_name.replace('_', ' ')})")
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

# -------------------------
# Menus
# -------------------------
def main_menu() -> str:
    clear()
    print("=" * 35)
    print("       THE STRAITS PROJECT")
    print("=" * 35)
    print("\n1) Start")
    print("2) Load (slot 1)")
    print("3) Quit")
    return input("\n> ").strip()

def choose_role() -> str:
    clear()
    print("Choose your background:\n")
    print("1) Portuguese Conquistador")
    print("2) Arab Muslim Dāʿī")
    print("3) Chinese Trader")
    mapping = {"1": "Portuguese Conquistador", "2": "Arab Muslim Dāʿī", "3": "Chinese Trader"}
    return mapping.get(input("\n> ").strip(), "Portuguese Conquistador")

def list_destinations(world: Dict[str, Any], kind: str) -> List[str]:
    return [entry["name"] for entry in world.get(kind, [])]

def choose_from_list(names: List[str], loc_type: str) -> Tuple[Optional[str], Optional[str]]:
    clear()
    print(f"Choose destination ({loc_type.replace('_',' ')}):\n")
    for idx, n in enumerate(names, start=1):
        print(f"{idx}) {n}")
    print(f"{len(names)+1}) Cancel")
    sel = input("\n> ").strip()
    try:
        k = int(sel)
    except ValueError:
        return None, None
    if 1 <= k <= len(names):
        return names[k-1], loc_type
    return None, None

def travel_menu(world: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    clear()
    print("Make landfall:\n")
    print("1) Major Ports")
    print("2) Villages")
    print("3) Cancel")
    top = input("\n> ").strip()
    if top == "1":
        return choose_from_list(list_destinations(world, "major_ports"), "major_port")
    if top == "2":
        return choose_from_list(list_destinations(world, "villages"), "village")
    return None, None

def action_menu(state: GameState) -> str:
    clear()
    print(state.status_text())
    print("\nWhat will you do?\n")
    print("1) Sail on (at sea)")
    print("2) Make landfall (travel to port/village)")
    print("3) Check status")
    print("4) Save (slot 1)")
    print("5) Quit")
    return input("\n> ").strip()

# -------------------------
# Loop
# -------------------------
def handle_landfall(state: GameState, engine: EventEngine):
    if engine.trigger_special_if_any(state):
        return
    if state.current_location_type == "major_port":
        engine.trigger_random("harbor_events", state)
    elif state.current_location_type == "village":
        engine.trigger_random("village_events", state)
    else:
        engine.trigger_random("harbor_events", state)

def run_game(state: GameState, engine: EventEngine):
    while True:
        if state.is_game_over():
            press_enter()
            break
        selection = action_menu(state)
        if selection == "1":
            state.current_location, state.current_location_type = "At Sea", "sea"
            engine.trigger_random("sea_events", state)
            state.day += 1
        elif selection == "2":
            dest, dest_type = travel_menu(state.world)
            if dest and dest_type:
                state.current_location, state.current_location_type = dest, dest_type
                handle_landfall(state, engine)
                state.day += 1
            else:
                print("\nYou remain at sea.")
                press_enter()
        elif selection == "3":
            clear()
            print(state.status_text())
            press_enter()
        elif selection == "4":
            save_game(state)
            press_enter()
        elif selection == "5":
            print("\nFarewell, Captain. Until next voyage.")
            break
        else:
            print("\nI didn’t catch that.")
            press_enter()

# -------------------------
# Entry
# -------------------------
def start_new_game(engine: EventEngine, world: Dict[str, Any]):
    role = choose_role()
    state = GameState(role, world)
    print(f"\nYou set sail as a {role}.")
    press_enter()
    run_game(state, engine)

def main():
    ensure_dirs()
    try:
        events_data = load_events(EVENTS_PATH)
        world = load_world(WORLD_PATH)
    except FileNotFoundError as e:
        print(f"Missing data file: {e}")
        sys.exit(1)

    # Use the generated PNG exactly; centered overlay title
    title_screen_graphics_image(os.path.join(ROOT_DIR, "assets", "title_straits.png"))

    engine = EventEngine(events_data)

    while True:
        choice = main_menu()
        if choice == "1":
            start_new_game(engine, world)
        elif choice == "2":
            state = load_game(world)
            if state:
                press_enter()
                run_game(state, engine)
            else:
                press_enter()
        elif choice == "3":
            print("\nGoodbye.")
            break
        else:
            print("\nInvalid option.")
            press_enter()

if __name__ == "__main__":
    main()
