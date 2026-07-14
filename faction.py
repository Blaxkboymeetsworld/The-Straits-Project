#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
faction.py — Faction reputation, dialogue flags, and ending conditions.
             Tracks per-faction standing and narrative flags that unlock
             branching outcomes (letter of marque, pirate legacy, etc.).
"""

from typing import Any, Dict, List, Optional, Tuple

# ─────────────────────────────────────────
# Faction definitions
# ─────────────────────────────────────────

FACTIONS: Dict[str, Dict[str, Any]] = {
    "malacca_sultanate": {
        "id": "malacca_sultanate",
        "name": "Malacca Sultanate",
        "home_port": "Malacca Harbor",
        "disposition": 50,
    },
    "estado_da_india": {
        "id": "estado_da_india",
        "name": "Estado da India",
        "home_port": "Goa Harbor",
        "disposition": 50,
    },
    "ming_dynasty": {
        "id": "ming_dynasty",
        "name": "Ming Dynasty",
        "home_port": "Quanzhou",
        "disposition": 45,
    },
    "chen_zuyi_ghost": {
        "id": "chen_zuyi_ghost",
        "name": "The Ghost of Chen Zuyi",
        "home_port": "Malacca Harbor",
        "disposition": 30,
        "notes": (
            "A shadow network of smugglers and ex-pirates operating in "
            "Chen Zuyi's old territory through the Strait of Malacca."
        ),
    },
    "sultanate_of_bantam": {
        "id": "sultanate_of_bantam",
        "name": "Sultanate of Bantam",
        "home_port": "Bantam",
        "disposition": 50,
    },
    "kingdom_of_calicut": {
        "id": "kingdom_of_calicut",
        "name": "Kingdom of Calicut",
        "home_port": "Calicut",
        "disposition": 40,
    },
    "hadrami_silsila": {
        "id": "hadrami_silsila",
        "name": "Hadrami Silsila",
        "description": (
            "A transoceanic network of Hadrami Arab scholar-merchants whose diaspora "
            "stretches from the Hadramawt and Aden to Calicut, Malacca, and the Java Sea. "
            "They carry faith, learning, and spice-trade capital in equal measure, binding "
            "the Indian Ocean world through kinship, Sufi silsila, and debt."
        ),
        "color_tag": "olive",
        "home_ports": ["Aden Harbor", "Calicut", "Malacca Harbor"],
        "rival_factions": ["estado_da_india"],
        "ally_factions": ["malacca_sultanate", "kingdom_of_calicut"],
        "exclusive_goods": ["frankincense", "coffee", "aloes_wood"],
        "disposition": 45,
    },
    # ── Minor factions (not tracked in main rep display) ──────────────
    "karimi_merchants": {
        "id": "karimi_merchants",
        "name": "Karimi Merchant Brotherhood",
        "description": (
            "A residual network of medieval Red Sea spice merchants, now fragmented "
            "by Portuguese disruption of the Aden route. Minor but still influential "
            "in Aden and Hormuz; they remember when the world trade flowed their way."
        ),
        "home_ports": ["Aden Harbor", "Hormuz"],
        "disposition": 40,
        "minor": True,
    },
}


# ─────────────────────────────────────────
# Tiered reputation constants
# ─────────────────────────────────────────

# Positive reputation tiers (0–5)
REP_POSITIVE_LABELS: Dict[int, str] = {
    0: "Unknown",
    1: "Noted",
    2: "Familiar",
    3: "Well Received",
    4: "Trusted",        # Overridden per-faction by REP_TIER4_TITLE below
    5: "Trusted Insider",  # Overridden per-faction by REP_INSIDER_TITLE below
}

# Culture-specific tier 4 titles — carry weight of obligation and trust
REP_TIER4_TITLE: Dict[str, str] = {
    "malacca_sultanate":   "Sahabat",            # Malay: close friend with weight of obligation
    "estado_da_india":     "Homem de confiança",  # Portuguese: man of trust
    "hadrami_silsila":     "Rafiq",              # Sufi commercial brotherhood: companion of the road
    "karimi_merchants":    "Rafiq",
    "ming_dynasty":        "Zhiji (知己)",        # Chinese: one who truly knows you
    "sultanate_of_bantam": "Sahabat",
    "kingdom_of_calicut":  "Nambiar",            # Nair honorific: trusted associate
    "chen_zuyi_ghost":     "Saudara Dalam",       # Malay: inner brother
}

# Negative reputation tiers (0 to −5, stored as negative ints)
REP_NEGATIVE_LABELS: Dict[int, str] = {
    0:  "Unremarkable",
    -1: "Suspected",
    -2: "Unwelcome",
    -3: "Barred",
    -4: "Marked",
    -5: "Hunted",
}

# Insider title per faction (displayed at tier 5)
REP_INSIDER_TITLE: Dict[str, str] = {
    "malacca_sultanate":    "Orang Dalam",
    "estado_da_india":      "Quase da Casa",
    "ming_dynasty":         "Zìjǐrén",
    "sultanate_of_bantam":  "Orang Dalam",
    "kingdom_of_calicut":   "Nāṭukārar",
    "hadrami_silsila":      "Ibn al-Silsila",
    "chen_zuyi_ghost":      "Saudara",
    "karimi_merchants":     "Rafīq al-Karīmī",
}

# Ports → faction mapping for quest gating
PORT_FACTION: Dict[str, str] = {
    "Malacca Harbor":     "malacca_sultanate",
    "Goa Harbor":         "estado_da_india",
    "Calicut":            "kingdom_of_calicut",
    "Hormuz":             "karimi_merchants",
    "Aden Harbor":        "hadrami_silsila",
    "Bantam":             "sultanate_of_bantam",
    "Quanzhou":           "ming_dynasty",
    "Ternate":            "malacca_sultanate",   # under Sultanate influence
    "Keelung Outpost":    "ming_dynasty",
    "Banda Islands":      "hadrami_silsila",
    "Bali":               "sultanate_of_bantam",
    "Pulau Tioman":       "chen_zuyi_ghost",
    "Patani":             "malacca_sultanate",
    "Cham Coast":         "ming_dynasty",
}


def port_to_faction(port_name: str) -> Optional[str]:
    """Return the primary faction_id for a port, or None."""
    return PORT_FACTION.get(port_name)


# ─────────────────────────────────────────
# FactionManager
# ─────────────────────────────────────────

class FactionManager:
    """
    Tracks per-faction dispositions and named dialogue flags that gate
    narrative endings.  Flags are set via _apply_dialogue_flag(); the
    public entry point is apply_flag().
    """

    def __init__(self):
        self.dispositions: Dict[str, int] = {
            fid: data["disposition"] for fid, data in FACTIONS.items()
        }
        self.flags: List[str] = []
        # Tiered reputation: -5 (Hunted) to +5 (Insider). Default 0 (Unknown/Unremarkable).
        self.reputation_scores: Dict[str, int] = {fid: 0 for fid in FACTIONS}
        # Named rival captains: list of {name, faction_id, bounty, encounters}
        self.rival_captains: List[Dict[str, Any]] = []
        # Track quests completed per faction for milestone scenes
        self.quests_completed_per_faction: Dict[str, int] = {fid: 0 for fid in FACTIONS}
        # Milestone flags per faction (keyed by "milestone_{faction_id}")
        # stored in self.flags

    # ── Disposition ──────────────────────────────────────────────────

    def get_disposition(self, faction_id: str) -> int:
        return self.dispositions.get(faction_id, 50)

    def adjust_disposition(self, faction_id: str, delta: int):
        current = self.dispositions.get(faction_id, 50)
        self.dispositions[faction_id] = max(0, min(100, current + delta))

    def disposition_label(self, faction_id: str) -> str:
        val = self.get_disposition(faction_id)
        if val >= 80:
            return "Allied"
        elif val >= 60:
            return "Friendly"
        elif val >= 40:
            return "Neutral"
        elif val >= 20:
            return "Suspicious"
        else:
            return "Hostile"

    # ── Tiered reputation ─────────────────────────────────────────────

    def get_rep(self, faction_id: str) -> int:
        return self.reputation_scores.get(faction_id, 0)

    def adjust_rep(self, faction_id: str, delta: int):
        current = self.reputation_scores.get(faction_id, 0)
        self.reputation_scores[faction_id] = max(-5, min(5, current + delta))

    def rep_label(self, faction_id: str) -> str:
        score = self.get_rep(faction_id)
        if score >= 5:
            return REP_INSIDER_TITLE.get(faction_id, REP_POSITIVE_LABELS[5])
        if score == 4:
            return REP_TIER4_TITLE.get(faction_id, REP_POSITIVE_LABELS[4])
        if score >= 1:
            return REP_POSITIVE_LABELS.get(score, "Noted")
        if score <= -1:
            return REP_NEGATIVE_LABELS.get(score, "Suspected")
        return "Unremarkable"

    def rep_tier(self, faction_id: str) -> int:
        """Returns integer from -5 to 5."""
        return self.get_rep(faction_id)

    def is_barred(self, faction_id: str) -> bool:
        return self.get_rep(faction_id) <= -3

    def is_marked(self, faction_id: str) -> bool:
        return self.get_rep(faction_id) <= -4

    def is_hunted(self, faction_id: str) -> bool:
        return self.get_rep(faction_id) <= -5

    def port_access_modifier(self, port_name: str) -> Tuple[bool, str]:
        """
        Returns (can_dock_openly, reason_string) for a given port.
        Checks the port's primary faction reputation.
        """
        faction_id = port_to_faction(port_name)
        if not faction_id:
            return True, ""
        score = self.get_rep(faction_id)
        if score <= -5:
            return False, f"You are HUNTED by the {FACTIONS[faction_id]['name']}. Named captains have your bounty."
        if score <= -3:
            return False, f"You are BARRED from {port_name}. You cannot dock openly."
        if score <= -2:
            return True, f"You are UNWELCOME here. Some facilities refused."
        if score <= -1:
            return True, f"The {FACTIONS[faction_id]['name']} regards you with suspicion. Prices 20% worse."
        return True, ""

    def price_modifier_at_port(self, port_name: str) -> float:
        """Returns a price multiplier (1.0 = normal, >1.0 = worse for player)."""
        faction_id = port_to_faction(port_name)
        if not faction_id:
            return 1.0
        score = self.get_rep(faction_id)
        if score <= -4:
            return 1.40   # Marked — heavy penalty
        if score <= -2:
            return 1.20   # Unwelcome — 20% worse
        if score <= -1:
            return 1.10   # Suspected
        if score >= 5:
            return 0.75   # Trusted Insider — 25% improvement
        if score >= 4:
            return 0.80   # Culture-specific tier — 20% improvement
        if score >= 3:
            return 0.85   # Well Received — 15% improvement
        if score >= 2:
            return 0.90   # Familiar — 10% improvement
        if score >= 1:
            return 0.95   # Noted — 5% improvement
        return 1.0

    def record_faction_quest(self, faction_id: str) -> Optional[str]:
        """
        Record completion of a quest for this faction.
        Returns a milestone scene key if the 5th quest was just completed,
        else None.
        """
        if faction_id not in self.quests_completed_per_faction:
            self.quests_completed_per_faction[faction_id] = 0
        self.quests_completed_per_faction[faction_id] += 1
        count = self.quests_completed_per_faction[faction_id]
        milestone_flag = f"milestone_{faction_id}"
        if count == 5 and milestone_flag not in self.flags:
            self.flags.append(milestone_flag)
            return milestone_flag
        return None

    # ── Named rivals ──────────────────────────────────────────────────

    def add_rival(self, name: str, faction_id: str, bounty: int = 0):
        """Register a named rival captain."""
        for r in self.rival_captains:
            if r["name"] == name:
                r["encounters"] = r.get("encounters", 0) + 1
                r["bounty"] = max(r["bounty"], bounty)
                return
        self.rival_captains.append({
            "name": name,
            "faction_id": faction_id,
            "bounty": bounty,
            "encounters": 1,
        })

    def get_rivals_for_faction(self, faction_id: str) -> List[Dict[str, Any]]:
        return [r for r in self.rival_captains if r["faction_id"] == faction_id]

    # ── Flags ────────────────────────────────────────────────────────

    def has_flag(self, flag: str) -> bool:
        return flag in self.flags

    def _apply_dialogue_flag(self, flag: str, state: Any = None):
        """
        Record a dialogue flag and apply any side-effects.
        All flags — including letter_of_marque — are appended to
        self.flags so that check_ending_conditions can inspect them.
        Idempotent: calling twice has no additional effect.
        """
        if flag in self.flags:
            return

        if flag == "letter_of_marque":
            # A privateering licence granted by the Estado da India.
            # check_ending_conditions looks for this flag to determine
            # whether the Portuguese-privateer ending branch is available.
            self.flags.append(flag)
            self.adjust_disposition("estado_da_india", +15)
            self.adjust_disposition("malacca_sultanate", -10)
            if state is not None and "cartaz" not in state.items:
                state.items.append("cartaz")

        # ── Quest completion flags ────────────────────────────────────
        elif flag == "quest_zamorin_letter":
            # Player delivered a letter to/from the Zamorin of Calicut.
            self.flags.append(flag)
        elif flag == "quest_viceroy_dispatch":
            # Player completed a dispatch mission for the Viceroy at Goa.
            self.flags.append(flag)
        elif flag == "quest_hokkien_fleet":
            # Player assisted or intercepted the Hokkien merchant fleet.
            self.flags.append(flag)
        elif flag == "quest_ottoman_convoy":
            # Player interacted with an Ottoman trade convoy.
            self.flags.append(flag)

        # ── Narrative / audience flags ────────────────────────────────
        elif flag == "royal_audience_malacca":
            # Player gained a formal audience with the Malacca Sultanate.
            self.flags.append(flag)
        elif flag == "cannon_purchase":
            # Player acquired Mamluk/heavy artillery through Aden contacts.
            self.flags.append(flag)
            self.adjust_disposition("hadrami_silsila", +8)

        # ── Hadrami / Aden network flags ──────────────────────────────
        elif flag == "dialogue_ottomans":
            # Player gathered intelligence on Ottoman naval intentions via Hadrami contacts.
            self.flags.append(flag)
            self.adjust_disposition("hadrami_silsila", +5)

        elif flag == "intel_aden_politics":
            # Player learned of Tahirid/Mamluk power dynamics at Aden Harbor.
            self.flags.append(flag)

        elif flag == "ottoman_cannon_purchase":
            # Legacy flag — kept for save-game compatibility. Prefer cannon_purchase.
            self.flags.append(flag)
        elif flag == "taiwan_hidden_harbor":
            # Player discovered the hidden harbor on the Taiwan coast.
            self.flags.append(flag)

        # ── Crew unlock flags ─────────────────────────────────────────
        elif flag == "crew_hokkien_unlock":
            # Hokkien sailor recruitment pool unlocked.
            self.flags.append(flag)
        elif flag == "crew_network_keelung":
            # Player tapped into the Keelung trading network.
            self.flags.append(flag)

        else:
            self.flags.append(flag)

    def apply_flag(self, flag: str, state: Any = None):
        """Public entry point for setting a dialogue flag."""
        self._apply_dialogue_flag(flag, state)

    # ── Ending conditions ─────────────────────────────────────────────

    def check_ending_conditions(self, state: Any) -> Optional[str]:
        """
        Returns an ending-branch ID if the player qualifies, else None.
        Should be called at major narrative checkpoints.
        """
        # Portuguese privateering ending
        if (
            "letter_of_marque" in self.flags
            and self.get_disposition("estado_da_india") >= 65
        ):
            return "ending_portuguese_privateer"

        # Chen Zuyi ghost network ending
        if self.get_disposition("chen_zuyi_ghost") >= 75:
            return "ending_pirate_legacy"

        # Hadrami network ending — deep ties to the Silsila and Aden intel gathered
        if (
            self.get_disposition("hadrami_silsila") >= 70
            and "intel_aden_politics" in self.flags
            and "dialogue_ottomans" in self.flags
        ):
            return "ending_arab_network"

        # Merchant prince ending — high standing with multiple trading powers
        trading_high = sum(
            1
            for fid in ("malacca_sultanate", "ming_dynasty", "sultanate_of_bantam")
            if self.get_disposition(fid) >= 70
        )
        if trading_high >= 2 and state.gold >= 500:
            return "ending_merchant_prince"

        return None

    # ── Summary display ───────────────────────────────────────────────

    def faction_summary(self):
        """Print reputation summary. Minor factions shown in a separate section."""
        major = {fid: d for fid, d in FACTIONS.items() if not d.get("minor")}
        minor = {fid: d for fid, d in FACTIONS.items() if d.get("minor")}

        print("\n  FACTION STANDING")
        print("  " + "─" * 40)
        for fid, data in major.items():
            score = self.get_rep(fid)
            rep   = self.rep_label(fid)
            score_str = f"+{score}" if score > 0 else str(score)
            print(f"  {data['name']:<28} {rep} ({score_str})")

        if minor:
            print("\n  Minor Factions")
            print("  " + "─" * 40)
            for fid, data in minor.items():
                score = self.get_rep(fid)
                rep   = self.rep_label(fid)
                score_str = f"+{score}" if score > 0 else str(score)
                print(f"  {data['name']:<28} {rep} ({score_str})")

        if self.rival_captains:
            print("\n  Named Rivals")
            print("  " + "─" * 40)
            for r in self.rival_captains:
                faction_name = FACTIONS.get(r["faction_id"], {}).get("name", r["faction_id"])
                print(f"  {r['name']:<28} [{faction_name}]  (encounters: {r.get('encounters',1)})")
        print()

    # ── Serialisation ─────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dispositions": dict(self.dispositions),
            "flags": list(self.flags),
            "reputation_scores": dict(self.reputation_scores),
            "rival_captains": list(self.rival_captains),
            "quests_completed_per_faction": dict(self.quests_completed_per_faction),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FactionManager":
        obj = cls()
        obj.dispositions.update(d.get("dispositions", {}))
        obj.flags = list(d.get("flags", []))
        obj.reputation_scores.update(d.get("reputation_scores", {}))
        obj.rival_captains = list(d.get("rival_captains", []))
        obj.quests_completed_per_faction.update(d.get("quests_completed_per_faction", {}))
        return obj
