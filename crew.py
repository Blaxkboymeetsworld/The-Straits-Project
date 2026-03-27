#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
crew.py — Crew recruitment, traits, occupations, language bonuses,
           morale effects, and slave-cargo-to-recruit mechanic.
"""

import random
import json
import os
from typing import Dict, List, Any, Optional, Set, Tuple

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT_DIR, "data")

# ─────────────────────────────────────────
# Trait mutual exclusivity
# ─────────────────────────────────────────

# Maps a trait_id to the set of trait_ids it cannot coexist with.
# The table is symmetric — if A blocks B, B blocks A.
TRAIT_EXCLUSIONS: Dict[str, Set[str]] = {
    "xenophobic":    {"worldly", "polyglot", "inspiring"},
    "worldly":       {"xenophobic"},
    "polyglot":      {"xenophobic"},
    "inspiring":     {"xenophobic"},
    # zealot blocks worldly unless the interfaith_respect bypass is present
    "zealot":        {"worldly"},
    "coward":        {"calm_under_fire", "intimidating"},
    "calm_under_fire": {"coward"},
    "intimidating":  {"coward"},
    "womanizer":     {"pious"},
    "pious":         {"womanizer"},
    "insubordinate": {"inspiring", "prideful"},
    "prideful":      {"insubordinate"},
    "gossip":        {"worldly"},
    "kleptomaniac":  {"sharp_trader"},
    "sharp_trader":  {"kleptomaniac"},
}

# Pairs that are exempt from the zealot↔worldly exclusion
# when a specific flag has been set (e.g. interfaith_respect event).
ZEALOT_WORLDLY_BYPASS_FLAG = "interfaith_respect_zealot"


def validate_trait_compatibility(
    trait_ids: List[str],
    bypass_flags: Optional[List[str]] = None
) -> bool:
    """
    Returns True if the given list of trait IDs contains no mutual exclusions.
    bypass_flags: list of special flags that lift specific exclusions.
    """
    if bypass_flags is None:
        bypass_flags = []

    id_set: Set[str] = set(trait_ids)
    for tid in trait_ids:
        blocked = TRAIT_EXCLUSIONS.get(tid, set())
        for other in blocked:
            if other not in id_set:
                continue
            # Check bypass
            if (
                {tid, other} == {"zealot", "worldly"}
                and ZEALOT_WORLDLY_BYPASS_FLAG in bypass_flags
            ):
                continue
            return False
    return True


def filter_incompatible_traits(
    candidates: List[Dict[str, Any]],
    existing_trait_ids: List[str],
    bypass_flags: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    From a list of candidate trait dicts, remove any that would conflict
    with the already-assigned existing_trait_ids.
    """
    if bypass_flags is None:
        bypass_flags = []
    result = []
    for t in candidates:
        tid = t["id"]
        test_list = existing_trait_ids + [tid]
        if validate_trait_compatibility(test_list, bypass_flags):
            result.append(t)
    return result

# Regions whose crews feel no cultural shock re: slavery in this world
SOUTHEAST_ASIAN_REGIONS = {"Southeast Asia"}
# These origins produce "stark" morale shock when a slave is recruited
HIGH_SHOCK_REGIONS = {"Europe", "East Asia", "Ottoman"}
# Moderate shock
MID_SHOCK_REGIONS = {"Indian Ocean", "Persian Gulf", "East Africa"}


def load_crew_data() -> Dict[str, Any]:
    path = os.path.join(DATA_DIR, "crew_data.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ─────────────────────────────────────────
# CrewMember
# ─────────────────────────────────────────

class CrewMember:
    """Represents a single member of the player's crew."""

    def __init__(
        self,
        name: str,
        ethnicity: str,
        native_tongue: str,
        other_languages: List[str],
        occupation: str,
        occupation_data: Dict[str, Any],
        religion: str,
        world_region: str,
        positive_traits: List[Dict[str, Any]],
        negative_traits: List[Dict[str, Any]],
        wage: int,
        was_enslaved: bool = False,
    ):
        self.name = name
        self.ethnicity = ethnicity
        self.native_tongue = native_tongue
        self.other_languages = other_languages
        self.occupation = occupation
        self.occupation_data = occupation_data
        self.religion = religion
        self.world_region = world_region
        self.positive_traits = positive_traits
        self.negative_traits = negative_traits
        self.wage = wage
        self.was_enslaved = was_enslaved
        self.alive = True

    @property
    def all_languages(self) -> List[str]:
        return [self.native_tongue] + self.other_languages

    @property
    def all_trait_ids(self) -> List[str]:
        return [t["id"] for t in self.positive_traits + self.negative_traits]

    def has_trait(self, trait_id: str) -> bool:
        return trait_id in self.all_trait_ids

    def speaks(self, language: str) -> bool:
        return language in self.all_languages

    def short_summary(self) -> str:
        pos = ", ".join(t["name"] for t in self.positive_traits) or "—"
        neg = ", ".join(t["name"] for t in self.negative_traits) or "—"
        langs = ", ".join(self.all_languages)
        return (
            f"  {self.name} [{self.ethnicity}] — {self.occupation}\n"
            f"    Languages: {langs}\n"
            f"    Religion: {self.religion}\n"
            f"    Traits (+): {pos}\n"
            f"    Traits (−): {neg}\n"
            f"    Wage: {self.wage} gold/port\n"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "ethnicity": self.ethnicity,
            "native_tongue": self.native_tongue,
            "other_languages": self.other_languages,
            "occupation": self.occupation,
            "occupation_data": self.occupation_data,
            "religion": self.religion,
            "world_region": self.world_region,
            "positive_traits": self.positive_traits,
            "negative_traits": self.negative_traits,
            "wage": self.wage,
            "was_enslaved": self.was_enslaved,
            "alive": self.alive,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CrewMember":
        obj = cls(
            name=d["name"],
            ethnicity=d["ethnicity"],
            native_tongue=d["native_tongue"],
            other_languages=d["other_languages"],
            occupation=d["occupation"],
            occupation_data=d["occupation_data"],
            religion=d["religion"],
            world_region=d["world_region"],
            positive_traits=d["positive_traits"],
            negative_traits=d["negative_traits"],
            wage=d["wage"],
            was_enslaved=d.get("was_enslaved", False),
        )
        obj.alive = d.get("alive", True)
        return obj


# ─────────────────────────────────────────
# Name generation (historically plausible)
# ─────────────────────────────────────────

NAMES_BY_ETHNICITY: Dict[str, List[str]] = {
    "Malay": ["Ahmad", "Yusuf", "Hamid", "Ismail", "Zainal", "Razak", "Osman", "Hamzah"],
    "Javanese": ["Suryanto", "Prasetyo", "Wibowo", "Santoso", "Gunawan", "Wahyu", "Slamet"],
    "Tamil": ["Murugan", "Annamalai", "Subramaniam", "Selvam", "Rajan", "Karuppiah"],
    "Gujarati": ["Thakor", "Premji", "Manilal", "Bhimji", "Dharamshi", "Lakhaji"],
    "Portuguese": ["Fernão", "Álvaro", "Diogo", "Gonçalo", "Rui", "Lopo", "Afonso", "Bastião"],
    "Konkani": ["Vasco", "Simão", "Cristóvão", "Domingos", "António", "Bartolomeu"],
    "East African": ["Salim", "Omar", "Bakr", "Jabir", "Rashid", "Idris", "Musa"],
    "Goan": ["Caetano", "Inácio", "Jerónimo", "Francisco", "Sebastião"],
    "Nair": ["Namboothiri", "Varma", "Menon", "Pillai", "Unni", "Raman", "Kesavan"],
    "Mapilla": ["Ibrahim", "Koya", "Hasan", "Moosakunju", "Alavi", "Kunhi"],
    "Arab": ["Abdullah", "Khalid", "Suleiman", "Tariq", "Nasir", "Faris", "Jabir"],
    "Persian": ["Dariush", "Kamran", "Bahram", "Farhad", "Arash", "Rostam", "Kourosh"],
    "Baluchi": ["Nadir", "Hammal", "Ghazan", "Badan", "Sardar", "Jumma"],
    "Turkish": ["Mehmed", "Hasan", "Ibrahim", "Selim", "Yusuf", "Musa", "Sinan"],
    "Chinese (Hokkien)": ["Chen Wei", "Lin Bao", "Huang Fa", "Wu Qian", "Cai Long", "Xu Ming"],
    "Chinese (Fujian)": ["Lim Ah Kow", "Tan Beng", "Ong Siew", "Koh Teck", "Goh Bak"],
    "Chinese (Hakka)": ["Wong Ah Seng", "Lee Chun", "Chan Yew", "Lau Pak"],
    "Chinese (diaspora)": ["Wee Kok", "Teo Ah", "Yeo Bak", "Phua Eng"],
    "Sundanese": ["Asep", "Deden", "Ujang", "Aep", "Dudung", "Abah"],
    "Bugis": ["Daeng Mattola", "Pua Rani", "Daeng Sitaba", "Arung Palakka"],
    "Orang Laut": ["Awang", "Panglima", "Radi", "Kulup", "Seman", "Buyong"],
    "Malay (Patani)": ["Wan Ali", "Nik Hassan", "Tengku Yusof", "Che Mat"],
    "Siamese": ["Prapha", "Thong", "Sirichai", "Noppadon", "Somchai"],
    "Ternatan": ["Baab", "Kolano", "Kaicil", "Manuru", "Sangaji"],
    "Papuan": ["Korwa", "Mansoben", "Numberi", "Ullo", "Womsiwor"],
}


def generate_name(ethnicity: str) -> str:
    names = NAMES_BY_ETHNICITY.get(ethnicity, ["Unknown"])
    return random.choice(names)


# ─────────────────────────────────────────
# Trait assignment
# ─────────────────────────────────────────

def assign_traits(
    crew_data: Dict[str, Any],
    force_clean: bool = False
) -> Tuple[List[Dict], List[Dict]]:
    """
    Assign traits to a recruitable character, respecting mutual exclusivity.
    ~1/5 chance of no negative traits (as spec'd).
    """
    all_pos = crew_data["positive_traits"]
    all_neg = crew_data["negative_traits"]

    # Build positive traits respecting exclusivity
    num_pos = random.randint(1, 3)
    available_pos = list(all_pos)
    random.shuffle(available_pos)
    pos: List[Dict] = []
    for candidate in available_pos:
        if len(pos) >= num_pos:
            break
        current_ids = [t["id"] for t in pos]
        if validate_trait_compatibility(current_ids + [candidate["id"]]):
            pos.append(candidate)

    if force_clean or random.random() < 0.20:  # 1 in 5 have no negatives
        neg: List[Dict] = []
    else:
        num_neg = random.randint(1, 2)
        existing_ids = [t["id"] for t in pos]
        compatible_neg = filter_incompatible_traits(all_neg, existing_ids)
        random.shuffle(compatible_neg)
        neg = compatible_neg[:num_neg]

    return pos, neg


# ─────────────────────────────────────────
# Recruit generation
# ─────────────────────────────────────────

def generate_recruit(archetype_key: str, crew_data: Dict[str, Any]) -> Optional[CrewMember]:
    archetypes = crew_data.get("recruitable_archetypes", {})
    archetype = archetypes.get(archetype_key)
    if not archetype:
        return None

    occupations_data = {o["id"]: o for o in crew_data.get("occupations", [])}
    occ_key = random.choice(archetype["typical_occupations"])
    occ_data = occupations_data.get(occ_key, {"id": occ_key, "name": occ_key.title()})

    religion = random.choice(archetype["typical_religions"])
    wage_lo, wage_hi = archetype["wage_range"]
    wage = random.randint(wage_lo, wage_hi)
    name = generate_name(archetype["ethnicity"])
    pos, neg = assign_traits(crew_data)

    return CrewMember(
        name=name,
        ethnicity=archetype["ethnicity"],
        native_tongue=archetype["native_tongue"],
        other_languages=archetype.get("other_languages", []),
        occupation=occ_key,
        occupation_data=occ_data,
        religion=religion,
        world_region=archetype["world_region"],
        positive_traits=pos,
        negative_traits=neg,
        wage=wage,
        was_enslaved=archetype.get("was_enslaved", False),
    )


# ─────────────────────────────────────────
# Crew Manager
# ─────────────────────────────────────────

class CrewManager:
    """Holds the full roster of crew members and provides aggregate bonuses."""

    def __init__(self):
        self.members: List[CrewMember] = []

    def add(self, member: CrewMember):
        self.members.append(member)

    def remove(self, member: CrewMember):
        if member in self.members:
            self.members.remove(member)

    def alive_members(self) -> List[CrewMember]:
        return [m for m in self.members if m.alive]

    def count(self) -> int:
        return len(self.alive_members())

    def total_wages(self) -> int:
        return sum(m.wage for m in self.alive_members())

    def has_occupation(self, occ: str) -> bool:
        return any(m.occupation == occ for m in self.alive_members())

    def has_trait(self, trait_id: str) -> bool:
        return any(m.has_trait(trait_id) for m in self.alive_members())

    def has_language(self, lang: str) -> bool:
        return any(m.speaks(lang) for m in self.alive_members())

    def has_region(self, region: str) -> bool:
        return any(m.world_region == region for m in self.alive_members())

    def trade_bonus(self, port_language: str, port_culture: str) -> float:
        """
        Returns a trade discount multiplier (e.g. 0.85 = 15% off).
        Factors in native speakers, polyglots, worldly travelers, interpreters.
        """
        bonus = 0.0

        # Native speaker at this port's language
        native_speakers = [m for m in self.alive_members() if m.native_tongue == port_language]
        if native_speakers:
            bonus += 0.15

        # Non-native but speaks the language
        elif self.has_language(port_language):
            bonus += 0.08

        # Polyglot trait (partial bonus even without the language)
        if self.has_trait("polyglot"):
            bonus += 0.08

        # Worldly trait
        if self.has_trait("worldly"):
            bonus += 0.10

        # Interpreter occupation
        if self.has_occupation("interpreter"):
            bonus += 0.05

        # Sharp trader trait
        if self.has_trait("sharp_trader"):
            bonus += 0.05

        return min(bonus, 0.40)  # cap at 40% discount

    def morale_per_day_bonus(self) -> int:
        bonus = 0
        if self.has_occupation("cook"):
            bonus += 2
        if self.has_occupation("priest"):
            bonus += 1
        if self.has_trait("inspiring"):
            bonus += 2
        return bonus

    def daily_morale_drain(self) -> int:
        """Negative traits that drain morale at sea per day."""
        drain = 0
        for m in self.alive_members():
            if m.has_trait("seasick"):
                drain += 1
        return drain

    def travel_speed_bonus(self) -> int:
        """Days shaved from travel (used by day/night cycle)."""
        bonus = 0
        if self.has_occupation("navigator"):
            bonus += 1
        if self.has_trait("navigator"):
            bonus += 1
        return bonus

    def combat_rating(self) -> int:
        base = 5
        for m in self.alive_members():
            base += m.occupation_data.get("base_combat", 0) // 3
            if m.has_trait("strong"):
                base += 2
            if m.has_trait("quick"):
                base += 1
            if m.has_trait("coward"):
                base -= 2
        return max(1, base)

    def check_for_incidents(self) -> List[str]:
        """
        Called on port arrival. Returns list of incident strings triggered by
        negative traits (drunkard, violent, gambler, kleptomaniac).
        """
        incidents = []
        for m in self.alive_members():
            if m.has_trait("drunk") and random.random() < 0.20:
                incidents.append(f"⚠  {m.name} ({m.ethnicity}) got into a brawl at a waterfront establishment. Fine incoming.")
            if m.has_trait("violent") and random.random() < 0.10:
                incidents.append(f"⚠  {m.name} started a fight. The watch is involved.")
            if m.has_trait("gambler") and random.random() < 0.15:
                incidents.append(f"⚠  {m.name} lost badly at dice. He is asking to borrow from ship's funds.")
            if m.has_trait("kleptomaniac") and random.random() < 0.10:
                incidents.append(f"⚠  {m.name} was found with goods from the cargo hold he didn't purchase.")
        return incidents

    def roster_display(self):
        if not self.members:
            print("  (No crew aboard)")
            return
        for m in self.alive_members():
            print(m.short_summary())

    def to_list(self) -> List[Dict[str, Any]]:
        return [m.to_dict() for m in self.members]

    @classmethod
    def from_list(cls, data: List[Dict[str, Any]]) -> "CrewManager":
        cm = cls()
        for d in data:
            cm.add(CrewMember.from_dict(d))
        return cm


# ─────────────────────────────────────────
# Recruitment interface
# ─────────────────────────────────────────

def present_recruits(
    pool_keys: List[str],
    crew_data: Dict[str, Any],
    num_available: int = 4
) -> List[CrewMember]:
    """Generate a pool of available recruits for the player to browse."""
    recruits = []
    sample_keys = random.choices(pool_keys, k=num_available)
    for key in sample_keys:
        recruit = generate_recruit(key, crew_data)
        if recruit:
            recruits.append(recruit)
    return recruits


def recruitment_menu(
    port_data: Dict[str, Any],
    crew_data: Dict[str, Any],
    crew_manager: CrewManager,
    state: Any,
    clear_fn,
    press_enter_fn
):
    """Full recruitment UI for a port."""
    pool_keys = port_data.get("recruitable_pool", [])
    if not pool_keys:
        print("\nNo one here is looking for work.")
        press_enter_fn()
        return

    recruits = present_recruits(pool_keys, crew_data, num_available=4)

    while True:
        clear_fn()
        print("═" * 50)
        print(f"  RECRUITMENT — {port_data['name']}")
        print("═" * 50)
        print(f"  Your gold: {state.gold}  |  Current crew: {crew_manager.count()}\n")
        print("  Available to hire:\n")

        for i, r in enumerate(recruits, 1):
            print(f"  [{i}] {r.short_summary()}")

        print("  [R] Refresh (pay 2 gold to see new faces)")
        print("  [Q] Leave the docks\n")

        choice = input("  Hire [1–4], R, or Q: ").strip().upper()

        if choice == "Q":
            break
        elif choice == "R":
            if state.gold >= 2:
                state.gold -= 2
                recruits = present_recruits(pool_keys, crew_data, num_available=4)
                print("\n  (You buy a round and word spreads — new faces appear.)")
            else:
                print("\n  Not enough gold to buy drinks.")
            press_enter_fn()
        elif choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(recruits):
                recruit = recruits[idx]
                if state.gold >= recruit.wage:
                    state.gold -= recruit.wage
                    crew_manager.add(recruit)
                    recruits.pop(idx)
                    print(f"\n  {recruit.name} joins your crew. ({recruit.occupation.replace('_',' ').title()})")
                    press_enter_fn()
                else:
                    print(f"\n  Not enough gold. {recruit.name} wants {recruit.wage} gold signing fee.")
                    press_enter_fn()
            else:
                print("\n  Invalid selection.")
                press_enter_fn()


# ─────────────────────────────────────────
# Slave cargo mechanic
# ─────────────────────────────────────────

def slave_recruit_event(
    state: Any,
    crew_manager: CrewManager,
    crew_data: Dict[str, Any],
    clear_fn,
    press_enter_fn
):
    """
    Offer to recruit a slave from cargo to the crew.
    Triggers morale reactions scaled by crew region origins.
    """
    if state.slave_cargo <= 0:
        print("\n  You have no enslaved persons in cargo.")
        press_enter_fn()
        return

    clear_fn()
    print("═" * 50)
    print("  A MATTER OF CONSCIENCE")
    print("═" * 50)
    print(
        "\n  You consider the figure in the hold — a man or woman taken in war or raid,\n"
        "  a commodity by the ledger's reckoning. If you free them and offer a place\n"
        "  on your crew, they may prove loyal. Your crew will have opinions.\n"
    )
    print(f"  Enslaved persons in cargo: {state.slave_cargo}")
    print(
        "\n  [Y] Free one and offer them a place on your crew"
        "\n  [N] Leave things as they are\n"
    )
    choice = input("  > ").strip().upper()

    if choice != "Y":
        return

    # Generate a freed slave recruit
    freed = generate_recruit("african_slave_freed", crew_data)
    if not freed:
        return

    freed.was_enslaved = True
    crew_manager.add(freed)
    state.slave_cargo -= 1

    # Calculate morale impact by crew composition
    high_shock_count = sum(
        1 for m in crew_manager.alive_members()
        if m.world_region in HIGH_SHOCK_REGIONS and m != freed
    )
    mid_shock_count = sum(
        1 for m in crew_manager.alive_members()
        if m.world_region in MID_SHOCK_REGIONS and m != freed
    )
    neutral_count = sum(
        1 for m in crew_manager.alive_members()
        if m.world_region in SOUTHEAST_ASIAN_REGIONS and m != freed
    )

    print(f"\n  {freed.name} is freed and joins your crew.")
    print(f"\n  ─ CREW REACTION ─")

    morale_change = 0

    if high_shock_count > 0:
        shock = -(high_shock_count * 4)
        morale_change += shock
        print(
            f"\n  ⚠  Times are desperate: The crew questions your decision to recruit.\n"
            f"     {high_shock_count} crew member(s) from Europe, China, or the Middle East\n"
            f"     regard this as a breach of the natural order. Morale: {shock}"
        )

    if mid_shock_count > 0:
        shock = -(mid_shock_count * 2)
        morale_change += shock
        print(
            f"\n  {mid_shock_count} crew member(s) from the Indian Ocean world are unsettled\n"
            f"     but say nothing aloud. Morale: {shock}"
        )

    if neutral_count > 0:
        print(
            f"\n  {neutral_count} crew member(s) from this part of the world take no\n"
            f"     particular notice. Men change hands. The sea is what it is."
        )

    state.morale = max(0, state.morale + morale_change)
    print(f"\n  Net morale change: {morale_change}  |  Current morale: {state.morale}")
    press_enter_fn()
