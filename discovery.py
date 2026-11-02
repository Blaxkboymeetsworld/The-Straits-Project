#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
discovery.py — What the player knows about the map.

Every location is UNKNOWN, RUMORED, or CHARTED for this game. The rutter
records each known location's status, the goods rumored there, and who
told you about it. Source lines are stored in English and Spanish so the
rutter reads correctly whichever language is active.
"""

from typing import Any, Dict, List, Optional

UNKNOWN = "unknown"
RUMORED = "rumored"
CHARTED = "charted"
_RANK = {UNKNOWN: 0, RUMORED: 1, CHARTED: 2}

SOURCE_COMMON = ("What every captain knows", "Lo que sabe todo capitán")
SOURCE_GRANDFATHER = ("Your grandfather's charts", "Las cartas de vuestro abuelo")
SOURCE_OWN_VOYAGE = ("Your own voyage", "Vuestro propio viaje")

# Starting knowledge per role. Anything not listed is UNKNOWN.
STARTING_KNOWLEDGE: Dict[str, Dict[str, List[str]]] = {
    "Portuguese Conquistador": {
        CHARTED: ["Goa Harbor", "Calicut", "Hormuz", "Aden Harbor", "Malacca Harbor"],
        RUMORED: ["Aceh", "Pegu", "Kedah", "Quanzhou"],
    },
    "Ottoman Trader": {
        CHARTED: ["Aden Harbor", "Hormuz", "Calicut", "Goa Harbor", "Aceh", "Malacca Harbor",
                  "Pegu", "Kedah"],
        RUMORED: ["Bantam", "Gresik", "Ternate", "Tidore", "Ayutthaya", "Quanzhou", "Patani"],
    },
    "Chinese Trader": {
        CHARTED: ["Quanzhou", "Malacca Harbor", "Ayutthaya", "Patani", "Cham Coast",
                  "Pulau Tioman", "Bantam", "Gresik", "Kedah"],
        RUMORED: ["Calicut", "Hormuz", "Aden Harbor", "Aceh", "Pegu", "Bali", "Makassar",
                  "Ternate", "Tidore"],
    },
}
# Chinese rumors of the far west come from the grandfather's charts.
GRANDFATHER_RUMORS = {"Calicut", "Hormuz", "Aden Harbor"}


class Rutter:
    """Per-game knowledge of locations: {name: {status, goods, source, source_es}}.
    Locations with no entry are UNKNOWN."""

    def __init__(self, entries: Optional[Dict[str, Dict[str, Any]]] = None):
        self.entries: Dict[str, Dict[str, Any]] = entries or {}

    # ── queries ──────────────────────────────────────────────────────
    def status(self, location: str) -> str:
        entry = self.entries.get(location)
        return entry["status"] if entry else UNKNOWN

    def is_known(self, location: str) -> bool:
        return self.status(location) != UNKNOWN

    def at_least(self, location: str, level: str) -> bool:
        return _RANK[self.status(location)] >= _RANK[level]

    def known_locations(self, level: str = RUMORED) -> List[str]:
        return [n for n, e in self.entries.items() if _RANK[e["status"]] >= _RANK[level]]

    # ── updates ──────────────────────────────────────────────────────
    def learn(self, location: str, level: str, source: tuple = SOURCE_COMMON,
              goods: Optional[List[str]] = None) -> bool:
        """Raise a location to `level` (never lowers it). Adds rumored goods
        and records the source when the status rises. Returns True if the
        status rose."""
        entry = self.entries.get(location)
        rose = _RANK[level] > _RANK[self.status(location)]
        if entry is None:
            entry = {"status": UNKNOWN, "goods": [], "source": source[0], "source_es": source[1]}
            self.entries[location] = entry
        if rose:
            entry["status"] = level
            entry["source"], entry["source_es"] = source
        for g in goods or []:
            if g not in entry["goods"]:
                entry["goods"].append(g)
        return rose

    def chart_on_arrival(self, location: str) -> None:
        """Arriving anywhere makes it CHARTED; keep the original source if known."""
        if self.status(location) == UNKNOWN:
            self.learn(location, CHARTED, SOURCE_OWN_VOYAGE)
        elif self.status(location) == RUMORED:
            self.entries[location]["status"] = CHARTED

    # ── construction / persistence ──────────────────────────────────
    @classmethod
    def for_role(cls, role: str) -> "Rutter":
        rutter = cls()
        start = STARTING_KNOWLEDGE.get(role, {})
        for name in start.get(CHARTED, []):
            rutter.learn(name, CHARTED, SOURCE_COMMON)
        for name in start.get(RUMORED, []):
            source = SOURCE_GRANDFATHER if (role == "Chinese Trader" and name in GRANDFATHER_RUMORS) else SOURCE_COMMON
            rutter.learn(name, RUMORED, source)
        return rutter

    @classmethod
    def all_charted(cls, location_names: List[str]) -> "Rutter":
        """For saves made before the discovery system: everything CHARTED."""
        rutter = cls()
        for name in location_names:
            rutter.learn(name, CHARTED, SOURCE_COMMON)
        return rutter

    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        return {n: dict(e, goods=list(e["goods"])) for n, e in self.entries.items()}

    @classmethod
    def from_dict(cls, d: Dict[str, Dict[str, Any]]) -> "Rutter":
        entries = {}
        for n, e in (d or {}).items():
            if e.get("status") in _RANK:
                entries[n] = {"status": e["status"], "goods": list(e.get("goods", [])),
                              "source": e.get("source", SOURCE_COMMON[0]),
                              "source_es": e.get("source_es", SOURCE_COMMON[1])}
        return cls(entries)
