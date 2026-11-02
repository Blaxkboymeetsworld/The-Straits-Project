#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
economy.py — Internal economy with fluctuating prices, trade interface,
              slave market, and port-specific commodity availability.
"""

import random
from typing import Dict, Any, Optional, List, Tuple
from systems import roll_check, dialogue_exchange

# All tradeable goods with base flavor text
GOODS_CATALOG: Dict[str, Dict[str, Any]] = {
    "pepper":       {"name": "Black Pepper",      "unit": "sacks",   "bulky": False,
                     "desc": "The king of spices. Malabar and Sumatra grow it; Cairo, Venice, and China can't get enough."},
    "tin":          {"name": "Tin (ingots)",       "unit": "ingots",  "bulky": True,
                     "desc": "Mined in the Malay Peninsula. Bronze-casters and Indian buyers pay well for it."},
    "camphor":      {"name": "Camphor",            "unit": "chests",  "bulky": False,
                     "desc": "Crystal resin from Sumatran trees. Doctors, embalmers, and perfumers from China to Arabia want it."},
    "cloves":       {"name": "Cloves",             "unit": "sacks",   "bulky": False,
                     "desc": "Dried flower buds that grow only in Maluku. Worth a fortune by the time they reach the West."},
    "nutmeg":       {"name": "Nutmeg",             "unit": "sacks",   "bulky": False,
                     "desc": "Seed of a tree that grows only in the Banda Islands. Physicians swear by it."},
    "silk":         {"name": "Silk (bolts)",       "unit": "bolts",   "bulky": False,
                     "desc": "Chinese silk. Every court from Calicut to Cairo dresses in it."},
    "cotton":       {"name": "Cotton Cloth",       "unit": "bales",   "bulky": True,
                     "desc": "Indian cotton cloth. In the islands, merchants trade it for spices like currency."},
    "rice":         {"name": "Rice",               "unit": "sacks",   "bulky": True,
                     "desc": "Feeds every crew and every city. Cheap, heavy, always needed."},
    "opium":        {"name": "Opium",              "unit": "chests",  "bulky": False,
                     "desc": "Sold as medicine for pain and fever. Arab and Gujarati merchants carry it east."},
    "porcelain":    {"name": "Porcelain",          "unit": "crates",  "bulky": True,
                     "desc": "Chinese blue-and-white. Fragile, heavy, and a mark of wealth in every port."},
    "salt":         {"name": "Salt",               "unit": "sacks",   "bulky": True,
                     "desc": "Preserves fish and meat. Cheap wherever salt pans sit near the sea."},
    "gold_dust":    {"name": "Gold Dust",          "unit": "pouches", "bulky": False,
                     "desc": "Panned from Sumatran and Malay rivers. Good money anywhere."},
    "iron":         {"name": "Iron (bars)",        "unit": "bars",    "bulky": True,
                     "desc": "Bars for nails, tools, and weapons."},
    "turtle_shell": {"name": "Turtle Shell",      "unit": "pieces",  "bulky": False,
                     "desc": "Hawksbill shell, carved into combs and inlays. Chinese craftsmen buy it."},
    "slaves":       {"name": "Enslaved Persons",   "unit": "persons", "bulky": False},
    "frankincense": {"name": "Frankincense",       "unit": "pouches", "bulky": False,
                     "desc": "Arabian resin burned in temples, mosques, and churches across the ocean."},
    "coffee":       {"name": "Coffee (beans)",     "unit": "sacks",   "bulky": True,
                     "desc": "A bitter bean from the Yemeni highlands. Yemen and its Sufis drink it; almost no one beyond the Red Sea has heard of it."},
    "deer_hide":    {"name": "Deer Hide",          "unit": "bales",   "bulky": True,
                     "desc": "Hides for leather and armor. Chinese buyers take them."},
    "sulphur":      {"name": "Sulphur",            "unit": "barrels", "bulky": True,
                     "desc": "Yellow mineral for gunpowder and medicine."},
    "dried_fish":   {"name": "Dried Fish",         "unit": "barrels", "bulky": True,
                     "desc": "Salted and sun-dried. Cheap food for crews and port towns."},
    "songket":      {"name": "Songket (cloth)",    "unit": "bolts",   "bulky": False,
                     "desc": "Malay brocade woven with gold thread, worn at court and weddings."},
    "ivory":        {"name": "Ivory",              "unit": "tusks",   "bulky": True,
                     "desc": "Tusks for carving. Chinese workshops pay the best prices."},
    "aloes_wood":   {"name": "Aloes Wood (oud)",   "unit": "chests",  "bulky": False,
                     "desc": "Resin-soaked heartwood burned as the finest incense. Champa grows the best."},
    "mace":         {"name": "Mace",               "unit": "sacks",   "bulky": False,
                     "desc": "The red lace around the nutmeg seed. Rarer than nutmeg, and priced like it."},
    "silver":       {"name": "Silver (bars)",       "unit": "bars",    "bulky": False,
                     "desc": "Coin metal from the West. China values it above almost everything."},
    "bugis_cloth":  {"name": "Bugis Cloth",         "unit": "bolts",   "bulky": False,
                     "desc": "Checked sarong cloth woven in South Sulawesi."},
    "cham_ikat":    {"name": "Cham Ikat Cloth",     "unit": "bolts",   "bulky": False,
                     "desc": "Cloth tie-dyed in patterns before weaving, from the Cham coast."},
    "batik":        {"name": "Javanese Batik",      "unit": "bolts",   "bulky": False,
                     "desc": "Wax-resist dyed cloth from Java's north coast."},
    "ritual_cloth": {"name": "Ritual Offering Cloth", "unit": "bolts",   "bulky": False,
                     "desc": "Cloth woven for Balinese temple offerings. Means nothing outside the islands."},
    "kris":         {"name": "Javanese Kris",       "unit": "blades",  "bulky": False,
                     "desc": "The wavy-bladed Javanese dagger. Many owners believe each blade carries a spirit."},
    "gamelan_bronze":{"name": "Gamelan Bronze",      "unit": "pieces",  "bulky": False,
                     "desc": "Bronze gongs and keys from Javanese gamelan orchestras."},
    "lacquerware":  {"name": "Siamese Lacquerware", "unit": "crates",  "bulky": True,
                     "desc": "Siamese boxes and bowls coated in layer after layer of tree-sap lacquer."},
    "lontar":       {"name": "Lontar Manuscripts",  "unit": "bundles", "bulky": False,
                     "desc": "Palm-leaf books of Balinese scripture, law, and magic."},
    "beeswax":      {"name": "Beeswax",             "unit": "blocks",  "bulky": False,
                     "desc": "Wax for candles, metal-casting molds, and cloth dyeing."},
    "benzoin":      {"name": "Benzoin",             "unit": "chests",  "bulky": False,
                     "desc": "Sumatran tree resin burned as incense. Arabs and Chinese buy it as a cheaper rival to frankincense."},
    "musk":         {"name": "Musk",                "unit": "pods",    "bulky": False,
                     "desc": "Scent from the musk deer's gland. A few grains perfume a room; Arabia and Persia pay dearly."},
    "lac_dye":      {"name": "Lac Dye",             "unit": "sacks",   "bulky": False,
                     "desc": "Red dye made from insect resin. Persian and Arab weavers use it."},
    "rubies":       {"name": "Rubies",              "unit": "pouches", "bulky": False,
                     "desc": "Burmese rubies, the finest known. Small, light, and worth a fortune in India and Arabia."},
    "sapanwood":    {"name": "Sapanwood",           "unit": "bundles", "bulky": True,
                     "desc": "Red dyewood from Siam. China imports it by the shipload."},
    "teak":         {"name": "Teak Timber",         "unit": "logs",    "bulky": True,
                     "desc": "Hard, rot-resistant timber for shipbuilding."},
    "rattan":       {"name": "Rattan",              "unit": "bundles", "bulky": True,
                     "desc": "Climbing-palm cane for rope, furniture, and lashing cargo."},
    "sago":         {"name": "Sago",                "unit": "sacks",   "bulky": True,
                     "desc": "Starch from the sago palm. The daily bread of Maluku."},
    "bird_of_paradise":{"name": "Bird-of-Paradise Skins", "unit": "bundles", "bulky": False,
                     "desc": "Dried skins of a brilliant bird from beyond Maluku. Turkish and Persian nobles wear the plumes."},
    "cinnamon":     {"name": "Cinnamon",            "unit": "bundles", "bulky": False,
                     "desc": "Cassia bark from the Cham coast, cinnamon's rougher cousin."},
    "horses":       {"name": "Horses",              "unit": "head",    "bulky": True,
                     "desc": "Arabian and Persian horses. Indian kingdoms can't breed warhorses and pay fortunes for them."},
    "elephant":     {"name": "Elephant",            "unit": "head",    "bulky": True,
                     "desc": "A working elephant. Indian courts use them for war and ceremony."},
    "war_elephant": {"name": "War Elephant",        "unit": "head",    "bulky": True,
                     "desc": "A trained, armored war elephant."},
    "white_elephant":{"name": "White Elephant",      "unit": "head",    "bulky": True,
                     "desc": "A sacred white elephant. In Siam, owning one marks a king. Ruinous to keep."},
    "fighting_cock":{"name": "Fighting Cock",       "unit": "birds",   "bulky": False,
                     "desc": "A Balinese gamecock. Cockfights settle bets, pay temple dues, and honor the gods."},
}

# Price fluctuation: market events that shift prices up or down
MARKET_EVENTS = [
    {"desc": "A Portuguese fleet has blockaded the route from Aden. Spice prices spike.",
     "goods": ["pepper", "cloves", "nutmeg", "camphor"], "mod": 1.35},
    {"desc": "A bumper harvest in the interior has flooded the market with rice.",
     "goods": ["rice"], "mod": 0.60},
    {"desc": "News of war between Calicut and the Zamorin's rivals pushes up the price of iron.",
     "goods": ["iron"], "mod": 1.40},
    {"desc": "A large Chinese junk has just unloaded silk. Prices are depressed.",
     "goods": ["silk", "porcelain"], "mod": 0.70},
    {"desc": "Monsoon delays have cut tin supply from the interior mines.",
     "goods": ["tin"], "mod": 1.50},
    {"desc": "Wealthy pilgrims passing through have driven up the price of provisions.",
     "goods": ["rice", "salt", "cotton"], "mod": 1.20},
    {"desc": "A pirate raid on a spice fleet has made cloves and nutmeg scarce and expensive.",
     "goods": ["cloves", "nutmeg"], "mod": 1.60},
    {"desc": "Competition from local merchants has undercut the going rate for cotton.",
     "goods": ["cotton"], "mod": 0.75},
    {"desc": "Guild traders are price-fixing. All goods slightly elevated.",
     "goods": list(GOODS_CATALOG.keys()), "mod": 1.15},
    {"desc": "A glut of opium from the interior has depressed that market.",
     "goods": ["opium"], "mod": 0.65},
    {"desc": "Gold dust is particularly sought after here this season.",
     "goods": ["gold_dust"], "mod": 1.30},
    {"desc": "No particular disruption. The market is quiet.",
     "goods": [], "mod": 1.0},
]

MAX_CARGO = 50  # max cargo units per hold


# ─────────────────────────────────────────
# Trade zones and regional demand (gap-fill sell prices)
# ─────────────────────────────────────────

# Every world.json location belongs to one trade zone.
TRADE_ZONES: Dict[str, str] = {
    "Aden Harbor": "West",          "Hormuz": "West",
    "Goa Harbor": "West India",     "Calicut": "West India",
    "Pegu": "Bengal",
    "Malacca Harbor": "Straits",    "Aceh": "Straits",    "Kedah": "Straits",
    "Patani": "Straits",            "Pulau Tioman": "Straits",
    "Bantam": "Archipelago",        "Gresik": "Archipelago", "Bali": "Archipelago",
    "Makassar": "Archipelago",      "Ternate": "Archipelago", "Tidore": "Archipelago",
    "Ayutthaya": "Siam",            "Cham Coast": "Siam",
    "Quanzhou": "China",
}

# Undirected links between zones. Zone distance = fewest links between two zones.
ZONE_LINKS: List[Tuple[str, str]] = [
    ("West", "West India"), ("West India", "Bengal"), ("Bengal", "Straits"),
    ("Straits", "Archipelago"), ("Straits", "Siam"), ("Siam", "China"),
]

_ALL_ZONES: List[str] = ["West", "West India", "Bengal", "Straits", "Archipelago", "Siam", "China"]


def _zone_distance(zone_a: str, zone_b: str) -> int:
    """Fewest ZONE_LINKS hops between two zones (0 if same; 0 if either is unknown)."""
    if zone_a == zone_b or zone_a not in _ALL_ZONES or zone_b not in _ALL_ZONES:
        return 0
    neighbors: Dict[str, List[str]] = {z: [] for z in _ALL_ZONES}
    for a, b in ZONE_LINKS:
        neighbors[a].append(b)
        neighbors[b].append(a)
    frontier, seen, dist = [zone_a], {zone_a}, 0
    while frontier:
        dist += 1
        nxt = []
        for z in frontier:
            for n in neighbors[z]:
                if n == zone_b:
                    return dist
                if n not in seen:
                    seen.add(n)
                    nxt.append(n)
        frontier = nxt
    return 0


def _all_zones_except(*keep: str) -> List[str]:
    return [z for z in _ALL_ZONES if z not in keep]


# Where a good fetches a premium ("prized", x1.5) or has no buyers at all
# ("no_market", sells at 30% of origin price) when the port doesn't list it.
GOOD_DEMAND: Dict[str, Dict[str, List[str]]] = {
    "pepper":           {"prized": ["West", "China"],               "no_market": []},
    "cloves":           {"prized": ["West", "West India", "China"], "no_market": []},
    "nutmeg":           {"prized": ["West", "West India", "China"], "no_market": []},
    "mace":             {"prized": ["West", "West India", "China"], "no_market": []},
    "camphor":          {"prized": ["West", "China"],               "no_market": []},
    "benzoin":          {"prized": ["West", "China"],               "no_market": []},
    "aloes_wood":       {"prized": ["West", "China"],               "no_market": []},
    "frankincense":     {"prized": ["China", "West India"],         "no_market": []},
    "sapanwood":        {"prized": ["China"],                       "no_market": []},
    "silk":             {"prized": ["West", "West India"],          "no_market": []},
    "porcelain":        {"prized": ["West", "West India"],          "no_market": []},
    "cotton":           {"prized": ["Straits", "Archipelago"],      "no_market": []},
    "rubies":           {"prized": ["West", "West India"],          "no_market": []},
    "musk":             {"prized": ["West"],                        "no_market": []},
    "lac_dye":          {"prized": ["West"],                        "no_market": []},
    "bird_of_paradise": {"prized": ["West"],                        "no_market": []},
    "tin":              {"prized": ["West India", "West"],          "no_market": []},
    "turtle_shell":     {"prized": ["China"],                       "no_market": []},
    "ivory":            {"prized": ["China"],                       "no_market": []},
    "deer_hide":        {"prized": ["China"],                       "no_market": []},
    "horses":           {"prized": ["West India"],                  "no_market": ["China"]},
    "elephant":         {"prized": ["West India"],                  "no_market": ["West", "China"]},
    "war_elephant":     {"prized": ["West India"],                  "no_market": ["West", "China"]},
    "white_elephant":   {"prized": ["West India"],                  "no_market": ["West", "China"]},
    "coffee":           {"prized": [],                              "no_market": _all_zones_except("West")},
    "fighting_cock":    {"prized": [],                              "no_market": _all_zones_except("Archipelago")},
    "lontar":           {"prized": [],                              "no_market": _all_zones_except("Archipelago")},
    "ritual_cloth":     {"prized": [],                              "no_market": _all_zones_except("Archipelago")},
    "gamelan_bronze":   {"prized": [],                              "no_market": _all_zones_except("Archipelago")},
}

# good -> {"price": lowest positive base_price anywhere, "location": ..., "zone": ...}
# Built lazily from data/world.json on first use.
_GOOD_ORIGINS: Optional[Dict[str, Dict[str, Any]]] = None


def _good_origins() -> Dict[str, Dict[str, Any]]:
    """Load data/world.json once and record each good's cheapest source.
    (straits_project.load_world() can't be imported here without a circular
    import, so this reads the file directly, like load_crew_data_fn().)"""
    global _GOOD_ORIGINS
    if _GOOD_ORIGINS is None:
        import json, os
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "world.json")
        with open(path, "r", encoding="utf-8") as f:
            world = json.load(f)
        origins: Dict[str, Dict[str, Any]] = {}
        for loc in world.get("major_ports", []) + world.get("villages", []):
            for good, price in loc.get("base_prices", {}).items():
                if price > 0 and (good not in origins or price < origins[good]["price"]):
                    origins[good] = {"price": price, "location": loc["name"],
                                     "zone": TRADE_ZONES.get(loc["name"])}
        _GOOD_ORIGINS = origins
    return _GOOD_ORIGINS


def _random_noise() -> float:
    """Per-good market noise, shared by live prices and gap-fill sell prices."""
    return random.uniform(0.88, 1.12)


# ─────────────────────────────────────────
# Haggling system
# ─────────────────────────────────────────

# Portuguese-controlled ports (where Estado da India authority gives home-court advantage)
PORTUGUESE_CONTROLLED_PORTS = {"Goa Harbor", "Malacca Harbor", "Hormuz"}

# Muslim-majority trade ports (Ottoman advantage)
MUSLIM_PORTS = {
    "Malacca Harbor", "Calicut", "Hormuz", "Aden Harbor",
    "Bantam", "Patani", "Ternate",
}

# Ports east of (and including) Malacca — Chinese home waters
CHINESE_HOME_PORTS = {
    "Malacca Harbor", "Bantam", "Quanzhou", "Patani",
    "Cham Coast", "Ternate",
}

# Crew ethnicity → port culture pairings that trigger culture intervention
# Maps crew_ethnicity → list of port cultures they match
CULTURE_INTERVENTION_MAP: Dict[str, List[str]] = {
    "Mapilla":          ["Calicut"],
    "Persian":          ["Hormuz"],
    "Arab":             ["Aden Harbor", "Hormuz"],
    "Malay":            ["Malacca Harbor", "Patani", "Bantam"],
    "Javanese":         ["Bantam", "Bali"],
    "Tamil":            ["Calicut"],
    "Gujarati":         ["Calicut", "Hormuz", "Goa Harbor"],
    "Chinese (Hokkien)":["Quanzhou", "Malacca Harbor", "Patani"],
    "Chinese (Fujian)": ["Quanzhou"],
    "Turkish":          ["Hormuz", "Aden Harbor"],
    "Orang Laut":       ["Malacca Harbor", "Pulau Tioman"],
}

def get_haggle_odds(role: str, port_name: str) -> float:
    """
    Return base win-chance for haggling at a given port, role-adjusted.
    Implements the role/region matrix from the design spec.

    Portuguese Conquistador:
      Default 0.50; own controlled ports (Goa, Malacca, Hormuz) = 0.75

    Ottoman Trader:
      Muslim ports = 0.65; Portuguese-controlled ports = 0.40; default 0.50

    Chinese Trader:
      East-of-Malacca (including Malacca) = 0.70; west = 0.50
    """
    if role == "Portuguese Conquistador":
        return 0.75 if port_name in PORTUGUESE_CONTROLLED_PORTS else 0.50

    elif role == "Ottoman Trader":
        if port_name in PORTUGUESE_CONTROLLED_PORTS:
            return 0.40
        if port_name in MUSLIM_PORTS:
            return 0.65
        return 0.50

    elif role == "Chinese Trader":
        return 0.70 if port_name in CHINESE_HOME_PORTS else 0.50

    return 0.50


def haggle_check(state: Any, port_name: str) -> Dict[str, Any]:
    """
    Mechanical haggling check. Returns:
      {
        "success": bool,
        "odds": float,           # final probability used
        "margin": float,         # discount fraction if success (0.0 if fail)
        "flavor_key": str,       # key for narrative text lookup
      }

    Navigator modifier (applied to base odds):
      skilled navigator: +0.10
      basic navigator:   +0.05
      no navigator:       0.00

    Flavor keys:
      haggle_blowout_win        — win margin ≥ 20%
      haggle_close_win          — win margin < 20%
      haggle_merchant_theatrics — merchant resists dramatically (odds 40–55%, loss)
      haggle_close_loss         — narrow loss (odds > 55%, still lost)
      haggle_firm_refusal       — decisive loss (low odds)
    """
    base_odds = get_haggle_odds(state.role, port_name)

    # Navigator modifier
    nav_level = state.crew.navigator_skill_level()
    nav_mod = {"skilled": 0.10, "basic": 0.05, None: 0.00}[nav_level]
    final_odds = max(0.05, min(0.95, base_odds + nav_mod))

    from systems import roll_check
    success = roll_check(final_odds)

    if success:
        import random
        margin = random.uniform(0.10, 0.25)
        flavor_key = "haggle_blowout_win" if margin >= 0.20 else "haggle_close_win"
    else:
        margin = 0.0
        if 0.40 <= final_odds <= 0.55:
            flavor_key = "haggle_merchant_theatrics"
        elif final_odds > 0.55:
            flavor_key = "haggle_close_loss"
        else:
            flavor_key = "haggle_firm_refusal"

    return {
        "success": success,
        "odds": final_odds,
        "margin": margin,
        "flavor_key": flavor_key,
    }


def find_intervention_crew(crew_manager: Any, port_name: str) -> Optional[Any]:
    """
    Return the first alive crew member whose ethnicity matches the port culture,
    enabling a culture intervention dialogue.
    """
    for member in crew_manager.alive_members():
        match_ports = CULTURE_INTERVENTION_MAP.get(member.ethnicity, [])
        if port_name in match_ports:
            return member
    return None


def haggle(
    state: Any,
    crew_manager: Any,
    port_name: str,
    base_buy_price: int,
    clear_fn,
    press_enter_fn,
) -> int:
    """
    Run the haggling mini-sequence. Returns the final buy price for this
    transaction. May be lower (player wins), same (neutral), or unchanged.

    If an intervention crew member is present, fires a multi-turn dialogue first
    that can shift the odds.
    """
    clear_fn()
    print("═" * 52)
    print(f"  HAGGLING — {port_name}")
    print("═" * 52)
    print(f"\n  Base price: {base_buy_price} gold")

    win_chance = get_haggle_odds(state.role, port_name)
    intervention_member = find_intervention_crew(crew_manager, port_name)
    final_odds = win_chance

    if intervention_member:
        print(
            f"\n  {intervention_member.name} ({intervention_member.ethnicity}) steps forward.\n"
            f"  He knows this port, these people.\n"
        )
        print("  [1] Let him negotiate fully  (→ 50/50 odds)")
        print("  [2] Back him up              (→ slight improvement)")
        print("  [3] Override him             (→ keep base odds)")
        print()
        choice = input("  > ").strip()

        if choice == "1":
            final_odds = 0.50
            # Run the dialogue exchange
            script = _build_intervention_script(intervention_member, port_name)
            result = dialogue_exchange(script, state)
            print()
        elif choice == "2":
            final_odds = min(0.95, win_chance + 0.15)
            print(f"\n  You stand at his shoulder. The harbor master's eyes flick between you.")
        else:
            final_odds = win_chance
            print(f"\n  {intervention_member.name} steps back. You handle it your way.")

    # Run mechanical check
    result = haggle_check(state, port_name)
    # Override final_odds if intervention modified it
    if final_odds != get_haggle_odds(state.role, port_name):
        # Intervention occurred — re-run with modified odds but keep result structure
        pass
    odds_pct = int(final_odds * 100)
    print(f"\n  Odds: {odds_pct}% in your favor.")

    _HAGGLE_FLAVOR = {
        "haggle_blowout_win":        "The merchant throws up his hands — you have the better of him entirely.",
        "haggle_close_win":          "After a pause, the merchant concedes a little ground.",
        "haggle_merchant_theatrics": "The merchant performs his grief with great conviction. The price does not move.",
        "haggle_close_loss":         "You were close. The merchant holds, and you sense he knows it too.",
        "haggle_firm_refusal":       "The merchant regards you with the patience of a man who has no reason to bargain.",
    }
    print(f"\n  {_HAGGLE_FLAVOR.get(result['flavor_key'], '')}")

    if result["success"]:
        final_price = max(1, round(base_buy_price * (1.0 - result["margin"])))
        print(f"  Price: {final_price} gold  ({int(result['margin']*100)}% off)")
    else:
        final_price = base_buy_price
        print(f"  Price: {final_price} gold.")

    press_enter_fn()
    return final_price


def _build_intervention_script(member: Any, port_name: str) -> Dict[str, Any]:
    """Build a simple 2-node dialogue script for the culture intervention."""
    return {
        "start": "crew_speaks",
        "nodes": {
            "crew_speaks": {
                "speaker": member.name,
                "text": (
                    f"I know this house. "
                    f"Give us a fair price, as you would give a neighbor."
                ),
                "choices": [
                    {
                        "key": "A",
                        "text": "Let him finish. Say nothing.",
                        "outcome": "favorable",
                        "effects": {},
                        "next": "master_responds_well",
                    },
                    {
                        "key": "B",
                        "text": "Cut in: 'And we have coin ready today.'",
                        "outcome": "neutral",
                        "effects": {},
                        "next": "master_responds_neutral",
                    },
                ],
            },
            "master_responds_well": {
                "speaker": "Harbor Master",
                "text": (
                    "...He considers. Nods once. "
                    "\"For a man who knows the house. We can speak.\""
                ),
                "choices": [],
            },
            "master_responds_neutral": {
                "speaker": "Harbor Master",
                "text": "\"Today's price is today's price. Take it or leave.\"",
                "choices": [],
            },
        },
    }


class Economy:
    """Manages a port's live market, including fluctuations and trade."""

    def __init__(self, port_data: Dict[str, Any]):
        self.port_data = port_data
        self.port_name = port_data["name"]
        self.port_language = port_data["language"]
        self.base_prices: Dict[str, int] = port_data.get("base_prices", {})
        self.live_prices: Dict[str, int] = {}
        self.active_event: Optional[Dict[str, Any]] = None
        self.slave_market: bool = port_data.get("slave_market", False)
        self.slave_notes: Optional[str] = port_data.get("slave_notes")
        self._generate_live_prices()
        # Sell-only prices for goods this port doesn't list. Fixed for the
        # visit; kept out of live_prices so the buy menu never shows them.
        self.gap_sell_prices: Dict[str, int] = {}
        self._generate_gap_sell_prices()

    def _generate_gap_sell_prices(self):
        """Price unlisted goods from their origin price, zone distance and
        regional demand, with the same noise and market-event modifier as
        _generate_live_prices()."""
        origins = _good_origins()
        here = TRADE_ZONES.get(self.port_name)
        affected = self.active_event["goods"]
        mod = self.active_event["mod"]
        for good in GOODS_CATALOG:
            if good == "slaves" or self.live_prices.get(good, 0) > 0:
                continue
            origin = origins.get(good)
            if origin is None:
                continue  # effective_sell_price falls back to 1, as before
            demand = GOOD_DEMAND.get(good, {})
            if here in demand.get("no_market", []):
                raw = round(origin["price"] * 0.3)
            else:
                raw = origin["price"] * (1 + 0.25 * _zone_distance(origin["zone"], here))
                if here in demand.get("prized", []):
                    raw *= 1.5
            multiplier = _random_noise()
            if good in affected:
                multiplier *= mod
            self.gap_sell_prices[good] = max(1, round(raw * multiplier))

    def _generate_live_prices(self):
        """Apply a random market event to generate live prices."""
        self.active_event = random.choice(MARKET_EVENTS)
        affected = self.active_event["goods"]
        mod = self.active_event["mod"]
        random_noise = _random_noise

        for good, base in self.base_prices.items():
            if base == 0:
                self.live_prices[good] = 0
                continue
            multiplier = random_noise()
            if good in affected:
                multiplier *= mod
            self.live_prices[good] = max(1, round(base * multiplier))

    def effective_buy_price(self, good: str, trade_bonus: float) -> int:
        """Price player pays when buying (lower is better). Trade bonus reduces cost."""
        base = self.live_prices.get(good, 0)
        discounted = base * (1 - trade_bonus)
        return max(1, round(discounted))

    def effective_sell_price(self, good: str, crew_sell_bonus: float) -> int:
        """Price player receives when selling (higher is better). Crew bonus increases revenue."""
        base = self.live_prices.get(good, 0)
        if not base and good != "slaves":
            base = self.gap_sell_prices.get(good, 0)
        boosted = base * (1 + crew_sell_bonus)
        return max(1, round(boosted))

    def market_display(
        self,
        cargo: Dict[str, int],
        trade_bonus: float,
        sell_bonus: float
    ):
        """Print a formatted market table."""
        print(f"\n{'─'*56}")
        print(f"  MARKET — {self.port_name}")
        print(f"  {self.active_event['desc']}")
        print(f"{'─'*56}")
        print(f"  {'Good':<22} {'Buy':>6} {'Sell':>6} {'In Hold':>8}")
        print(f"  {'─'*22} {'─'*6} {'─'*6} {'─'*8}")

        for good, info in GOODS_CATALOG.items():
            if good not in self.live_prices or self.live_prices[good] == 0:
                continue
            if good == "slaves" and not self.slave_market:
                continue
            buy_p = self.effective_buy_price(good, trade_bonus)
            sell_p = self.effective_sell_price(good, sell_bonus)
            in_hold = cargo.get(good, 0)
            name_str = info["name"]
            print(f"  {name_str:<22} {buy_p:>6} {sell_p:>6} {in_hold:>8}")

        print(f"{'─'*56}")
        if trade_bonus == 0 and sell_bonus == 0:
            print("  (Hire crew with trade skills to unlock better prices)")
        print()

    def trade_menu(
        self,
        state: Any,
        crew_manager: Any,
        clear_fn,
        press_enter_fn
    ):
        """Full trade UI."""
        trade_bonus = crew_manager.trade_bonus(self.port_language, self.port_data.get("culture", ""))
        sell_bonus_val = 0.05 if crew_manager.has_trait("sharp_trader") else 0.0

        while True:
            clear_fn()
            cargo_used = sum(state.cargo.values())
            print(f"\n  Gold: {state.gold}  |  Cargo: {cargo_used}/{state.cargo_capacity()} units")
            if trade_bonus > 0:
                print(f"  ✦ Language/trade bonus active: -{int(trade_bonus*100)}% on buy prices")
            self.market_display(state.cargo, trade_bonus, sell_bonus_val)

            print("  [B] Buy goods")
            print("  [S] Sell goods")
            if self.slave_market:
                print("  [L] Slave market")
            print("  [Q] Leave market\n")

            top = input("  > ").strip().upper()

            if top == "Q":
                break
            elif top == "B":
                self._buy_menu(state, trade_bonus, clear_fn, press_enter_fn)
            elif top == "S":
                self._sell_menu(state, sell_bonus_val, clear_fn, press_enter_fn)
            elif top == "L" and self.slave_market:
                self._slave_market_menu(state, crew_manager, trade_bonus, clear_fn, press_enter_fn)
            else:
                print("\n  Invalid option.")
                press_enter_fn()

    def _buy_menu(self, state: Any, trade_bonus: float, clear_fn, press_enter_fn):
        available_goods = {
            g: self.effective_buy_price(g, trade_bonus)
            for g in self.live_prices
            if self.live_prices[g] > 0 and g != "slaves"
        }
        if not available_goods:
            print("\n  Nothing available to buy here.")
            press_enter_fn()
            return

        clear_fn()
        print(f"\n  BUY — {self.port_name}  (Gold: {state.gold})\n")
        goods_list = list(available_goods.items())
        for i, (g, price) in enumerate(goods_list, 1):
            info = GOODS_CATALOG.get(g, {})
            cargo_used = sum(state.cargo.values())
            in_hold = state.cargo.get(g, 0)
            print(f"  [{i}] {info.get('name', g):<22}  {price} gold/unit  (hold: {in_hold})")

        print("  [Q] Back\n")
        choice = input("  Buy which? > ").strip().upper()

        if choice == "Q":
            return
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(goods_list):
                good, price = goods_list[idx]
                cargo_used = sum(state.cargo.values())
                space = state.cargo_capacity() - cargo_used
                if space <= 0:
                    print("\n  Your hold is full.")
                    press_enter_fn()
                    return
                desc = GOODS_CATALOG.get(good, {}).get("desc")
                if desc:
                    print(f"\n  {desc}")
                qty_str = input(f"  How many {GOODS_CATALOG[good]['name']}? (max {min(space, state.gold // price)}): ").strip()
                if qty_str.isdigit():
                    qty = int(qty_str)
                    cost = qty * price
                    if qty <= 0:
                        pass
                    elif cost > state.gold:
                        print("\n  Not enough gold.")
                        press_enter_fn()
                    elif qty > space:
                        print(f"\n  Not enough cargo space. Max {space} units.")
                        press_enter_fn()
                    else:
                        state.gold -= cost
                        state.cargo[good] = state.cargo.get(good, 0) + qty
                        print(f"\n  Bought {qty} {GOODS_CATALOG[good]['name']} for {cost} gold.")
                        press_enter_fn()

    def _sell_menu(self, state: Any, sell_bonus: float, clear_fn, press_enter_fn):
        sellable = {g: qty for g, qty in state.cargo.items() if qty > 0 and g != "slaves"}
        if not sellable:
            print("\n  Nothing in the hold to sell.")
            press_enter_fn()
            return

        clear_fn()
        print(f"\n  SELL — {self.port_name}  (Gold: {state.gold})\n")
        goods_list = list(sellable.items())
        for i, (g, qty) in enumerate(goods_list, 1):
            sell_p = self.effective_sell_price(g, sell_bonus)
            info = GOODS_CATALOG.get(g, {})
            total = sell_p * qty
            print(f"  [{i}] {info.get('name', g):<22}  {sell_p} gold/unit  x{qty} = {total} gold")

        print("  [Q] Back\n")
        choice = input("  Sell which? > ").strip().upper()

        if choice == "Q":
            return
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(goods_list):
                good, in_hold = goods_list[idx]
                sell_p = self.effective_sell_price(good, sell_bonus)
                qty_str = input(f"  Sell how many? (max {in_hold}): ").strip()
                if qty_str.isdigit():
                    qty = int(qty_str)
                    if qty <= 0 or qty > in_hold:
                        print("\n  Invalid quantity.")
                        press_enter_fn()
                    else:
                        revenue = qty * sell_p
                        state.gold += revenue
                        state.cargo[good] -= qty
                        if state.cargo[good] == 0:
                            del state.cargo[good]
                        print(f"\n  Sold {qty} {GOODS_CATALOG[good]['name']} for {revenue} gold.")
                        press_enter_fn()

    def _slave_market_menu(
        self,
        state: Any,
        crew_manager: Any,
        trade_bonus: float,
        clear_fn,
        press_enter_fn
    ):
        """Slave market: buy (as cargo), sell, or recruit to crew."""
        clear_fn()
        print("═" * 50)
        print(f"  SLAVE MARKET — {self.port_name}")
        print("═" * 50)
        if self.slave_notes:
            print(f"\n  {self.slave_notes}")
        print(
            f"\n  This is a market where human lives are traded.\n"
            f"  Enslaved persons in your hold: {state.slave_cargo}\n"
        )
        buy_price = self.effective_buy_price("slaves", trade_bonus)
        sell_price = self.effective_sell_price("slaves", 0.0)
        print(f"  Buy price: {buy_price} gold/person")
        print(f"  Sell price: {sell_price} gold/person")
        print()
        print("  [B] Purchase enslaved persons (cargo)")
        print("  [S] Sell enslaved persons from cargo")
        print("  [R] Offer freedom and recruit from cargo to crew")
        print("  [Q] Leave\n")

        choice = input("  > ").strip().upper()

        if choice == "B":
            qty_str = input("  How many to purchase? ").strip()
            if qty_str.isdigit():
                qty = int(qty_str)
                cost = qty * buy_price
                if cost > state.gold:
                    print("\n  Not enough gold.")
                elif qty <= 0:
                    pass
                else:
                    state.gold -= cost
                    state.slave_cargo += qty
                    print(f"\n  Purchased {qty} enslaved person(s) for {cost} gold.")
            press_enter_fn()

        elif choice == "S":
            if state.slave_cargo <= 0:
                print("\n  No enslaved persons in cargo to sell.")
            else:
                qty_str = input(f"  Sell how many? (max {state.slave_cargo}): ").strip()
                if qty_str.isdigit():
                    qty = int(qty_str)
                    if 0 < qty <= state.slave_cargo:
                        revenue = qty * sell_price
                        state.gold += revenue
                        state.slave_cargo -= qty
                        print(f"\n  Sold {qty} enslaved person(s) for {revenue} gold.")
                    else:
                        print("\n  Invalid quantity.")
            press_enter_fn()

        elif choice == "R":
            from crew import slave_recruit_event
            slave_recruit_event(state, crew_manager, load_crew_data_fn(), clear_fn, press_enter_fn)


def load_crew_data_fn():
    """Lazy import to avoid circular deps."""
    import json, os
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "crew_data.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
