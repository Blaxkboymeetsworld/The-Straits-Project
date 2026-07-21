#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
time_system.py — Day/night cycle, travel time between ports,
                  port availability by time of day (think M&B Warband's
                  simple but meaningful time system).
"""

import json
import os
import random
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

START_DATE = datetime(1511, 1, 1)  # canonical game start: January 1, 1511

_ROOT = os.path.dirname(os.path.abspath(__file__))
_ROUTES_PATH = os.path.join(_ROOT, "data", "routes.json")
_NAUTICAL_DATA_PATH = os.path.join(_ROOT, "data", "nautical_data.json")

# Rough travel times between ports in days (one-way)
# Reflects the actual geography of the Indian Ocean / Southeast Asia
TRAVEL_TIMES: Dict[Tuple[str, str], int] = {
    # Malacca as hub
    ("Malacca Harbor", "Bantam"):       3,
    ("Malacca Harbor", "Goa Harbor"):   8,
    ("Malacca Harbor", "Calicut"):      7,
    ("Malacca Harbor", "Hormuz"):       14,
    ("Malacca Harbor", "Quanzhou"):     12,
    ("Malacca Harbor", "Ternate"):      7,
    ("Malacca Harbor", "Pulau Tioman"): 1,
    ("Malacca Harbor", "Patani"):       2,
    # Goa to others
    ("Goa Harbor", "Calicut"):          2,
    ("Goa Harbor", "Hormuz"):           7,
    ("Goa Harbor", "Quanzhou"):         18,
    ("Goa Harbor", "Bantam"):           12,
    ("Goa Harbor", "Ternate"):          16,
    # Calicut to others
    ("Calicut", "Hormuz"):              6,
    ("Calicut", "Quanzhou"):            16,
    ("Calicut", "Bantam"):              10,
    # Hormuz to Quanzhou
    ("Hormuz", "Quanzhou"):             22,
    ("Hormuz", "Bantam"):               18,
    # Bantam to Ternate
    ("Bantam", "Ternate"):              4,
    ("Bantam", "Quanzhou"):             9,
    # Ternate to Quanzhou
    ("Ternate", "Quanzhou"):            11,
    # Villages
    ("Pulau Tioman", "Bantam"):         3,
    ("Pulau Tioman", "Quanzhou"):       11,
    ("Patani", "Quanzhou"):             10,
    ("Patani", "Bantam"):               5,
    ("Ternate", "Pulau Tioman"):        8,
    # New ports
    ("Aden Harbor", "Hormuz"):          4,
    ("Aden Harbor", "Calicut"):         5,
    ("Aden Harbor", "Goa Harbor"):      6,
    ("Aden Harbor", "Malacca Harbor"): 18,
    ("Bali", "Bantam"):                 3,
    ("Bali", "Ternate"):                4,
    ("Bali", "Malacca Harbor"):         5,
    ("Cham Coast", "Quanzhou"):         6,
    ("Cham Coast", "Malacca Harbor"):   5,
    ("Cham Coast", "Patani"):           4,
    # At-sea starting positions
    ("Indian Ocean, southeast of Calicut", "Malacca Harbor"): 8,
    ("Indian Ocean, southeast of Calicut", "Goa Harbor"):     3,
    ("Indian Ocean, southeast of Calicut", "Calicut"):        2,
    ("Indian Ocean, southeast of Calicut", "Hormuz"):         9,
    ("Indian Ocean, southeast of Calicut", "Quanzhou"):       18,
    ("Indian Ocean, southeast of Calicut", "Bantam"):         12,
    ("Indian Ocean, southeast of Calicut", "Aden Harbor"):    7,
    ("Arabian Sea, departing Hormuz", "Hormuz"):              1,
    ("Arabian Sea, departing Hormuz", "Aden Harbor"):         5,
    ("Arabian Sea, departing Hormuz", "Calicut"):             8,
    ("Arabian Sea, departing Hormuz", "Goa Harbor"):          9,
    ("Arabian Sea, departing Hormuz", "Malacca Harbor"):      16,
    ("South China Sea, south of Quanzhou", "Quanzhou"):       2,
    ("South China Sea, south of Quanzhou", "Malacca Harbor"): 10,
    ("South China Sea, south of Quanzhou", "Bantam"):         8,
    ("South China Sea, south of Quanzhou", "Patani"):         6,
}

# Fill in reverse directions automatically (roughly symmetric)
_FILLED: Dict[Tuple[str, str], int] = {}
for (a, b), days in TRAVEL_TIMES.items():
    _FILLED[(a, b)] = days
    _FILLED[(b, a)] = days
TRAVEL_TIMES = _FILLED

DEFAULT_TRAVEL_TIME = 6  # fallback if route not in table

# ── Route waypoints (loaded from routes.json) ────────────────────────────────
# Maps (origin, dest) → {waterway: str, at_sea: str}
ROUTE_WAYPOINTS: Dict[Tuple[str, str], Dict[str, str]] = {}

try:
    with open(_ROUTES_PATH, encoding="utf-8") as _f:
        _routes_data = json.load(_f)
    for _r in _routes_data.get("routes", []):
        _a, _b = _r["from"], _r["to"]
        _entry = {"waterway": _r["waterway"], "at_sea": _r["at_sea"]}
        ROUTE_WAYPOINTS[(_a, _b)] = _entry
        ROUTE_WAYPOINTS[(_b, _a)] = _entry
except (FileNotFoundError, KeyError):
    pass  # graceful fallback — no waypoints

# ── Nautical data (monsoon calendar, ship speed profiles, route distances) ──
# Loaded from data/nautical_data.json. Powers calculate_voyage() below.
# NOTE: calculate_voyage() is standalone and not called from anywhere else
# yet — see the __main__ test block at the bottom of this file.
try:
    with open(_NAUTICAL_DATA_PATH, encoding="utf-8") as _f:
        _NAUTICAL_DATA = json.load(_f)
except FileNotFoundError:
    _NAUTICAL_DATA = {"monsoon_calendar": {}, "ship_speed_profiles": {}, "route_distances": []}

_ROUTE_DISTANCES_NM: Dict[Tuple[str, str], int] = {}
for _rd in _NAUTICAL_DATA.get("route_distances", []):
    _rd_a, _rd_b, _rd_nm = _rd["from"], _rd["to"], _rd["nautical_miles"]
    _ROUTE_DISTANCES_NM[(_rd_a, _rd_b)] = _rd_nm
    _ROUTE_DISTANCES_NM[(_rd_b, _rd_a)] = _rd_nm

# Short archipelago hops treated as coastal (calm, sheltered water) rather
# than open ocean, per Prompt 2 spec.
_COASTAL_HOPS = {
    ("Malacca Harbor", "Kedah"), ("Kedah", "Malacca Harbor"),
    ("Ternate", "Tidore"), ("Tidore", "Ternate"),
    ("Gresik", "Bali"), ("Bali", "Gresik"),
}

# Each ocean system's monsoon_calendar entry carries two directional
# sub-systems (e.g. sw_monsoon / ne_monsoon) with opposite favorable
# windows. Direction is inferred from origin/dest membership in a small
# set of "anchor" ports representing the near/west (Indian Ocean) or
# north (South China Sea) end of the crossing — grounded in the real
# geography already in the Prompt 1 spec text ("SW monsoon favors
# Arabia/Africa -> India/eastward", "NE monsoon favors China -> SE Asia").
# Leaving FROM an anchor port uses the "outbound" sub-system; arriving
# AT an anchor port (i.e. sailing the return leg) uses the other one.
# Routes that don't touch an anchor port at all (most SE-Asia-internal
# hops) can't be resolved this way and fall back to the outbound
# sub-system as a documented default.
_OCEAN_ANCHOR_PORTS = {
    "indian_ocean": {"Hormuz", "Aden Harbor", "Calicut", "Goa Harbor"},
    "south_china_sea": {"Quanzhou"},
}
_OUTBOUND_MONSOON_SUBSYSTEM = {
    "indian_ocean": "sw_monsoon",       # Arabia/Africa -> India/eastward
    "south_china_sea": "ne_monsoon",    # China -> Southeast Asia
}
_RETURN_MONSOON_SUBSYSTEM = {
    "indian_ocean": "ne_monsoon",       # the return west
    "south_china_sea": "sw_monsoon",    # the return north
}


def _select_monsoon_subsystem(ocean_system: str, origin_port: str, dest_port: str) -> str:
    anchors = _OCEAN_ANCHOR_PORTS.get(ocean_system, set())
    origin_is_anchor = origin_port in anchors
    dest_is_anchor = dest_port in anchors
    if origin_is_anchor and not dest_is_anchor:
        return _OUTBOUND_MONSOON_SUBSYSTEM.get(ocean_system, "")
    if dest_is_anchor and not origin_is_anchor:
        return _RETURN_MONSOON_SUBSYSTEM.get(ocean_system, "")
    # Ambiguous (both or neither end is an anchor) — default to outbound.
    return _OUTBOUND_MONSOON_SUBSYSTEM.get(ocean_system, "")


def calculate_voyage(
    origin_port: str,
    dest_port: str,
    ocean_system: str,
    current_month: int,
    protagonist_role: str,
) -> Dict[str, Any]:
    """
    Voyage-time estimate built on data/nautical_data.json, wired into the
    travel flow in straits_project.py (see Prompt 3).

    Returns {"days": int, "monsoon_state": "favorable"|"unfavorable"|"transition",
    "blocked": bool, "subsystem": "sw_monsoon"|"ne_monsoon"}.
    If the route distance or ship profile isn't in the data, returns
    {"days": None, "monsoon_state": None, "blocked": True, "error": <reason>}
    rather than guessing a distance.
    """
    distance_nm = _ROUTE_DISTANCES_NM.get((origin_port, dest_port))
    if distance_nm is None:
        return {
            "days": None, "monsoon_state": None, "blocked": True,
            "error": f"no route_distances entry for {origin_port} <-> {dest_port}",
        }

    profile = _NAUTICAL_DATA.get("ship_speed_profiles", {}).get(protagonist_role)
    if profile is None:
        return {
            "days": None, "monsoon_state": None, "blocked": True,
            "error": f"no ship_speed_profile for protagonist_role {protagonist_role!r}",
        }

    ocean = _NAUTICAL_DATA.get("monsoon_calendar", {}).get(ocean_system)
    if ocean is None:
        return {
            "days": None, "monsoon_state": None, "blocked": True,
            "error": f"no monsoon_calendar entry for ocean_system {ocean_system!r}",
        }

    subsystem_key = _select_monsoon_subsystem(ocean_system, origin_port, dest_port)

    if current_month in ocean.get("transition_months", []):
        monsoon_state = "transition"
    else:
        subsystem = ocean.get(subsystem_key, {})
        monsoon_state = "favorable" if current_month in subsystem.get("favorable_months", []) else "unfavorable"

    is_coastal = (origin_port, dest_port) in _COASTAL_HOPS
    base_knots = profile["coastal_knots"] if is_coastal else profile["open_ocean_knots"]

    if monsoon_state == "unfavorable":
        effective_knots = base_knots * profile["upwind_penalty_multiplier"]
        blocked = True
    else:
        # "favorable" and "transition" both sail at full favorable speed;
        # transition just flags elevated storm weighting downstream.
        effective_knots = base_knots
        blocked = False

    days = max(1, round(distance_nm / (effective_knots * HOURS_PER_DAY)))

    return {"days": days, "monsoon_state": monsoon_state, "blocked": blocked, "subsystem": subsystem_key}


def next_favorable_month(ocean_system: str, origin_port: str, dest_port: str, current_month: int) -> Optional[int]:
    """
    Return the next month (1-12, strictly after current_month, wrapping
    around the year) that's favorable for this route's monsoon subsystem,
    or None if the ocean_system/subsystem isn't in the data. Used to let
    the player wait out an unfavorable monsoon rather than sail into it.
    """
    ocean = _NAUTICAL_DATA.get("monsoon_calendar", {}).get(ocean_system)
    if ocean is None:
        return None
    subsystem_key = _select_monsoon_subsystem(ocean_system, origin_port, dest_port)
    favorable = set(ocean.get(subsystem_key, {}).get("favorable_months", []))
    if not favorable:
        return None
    for offset in range(1, 13):
        candidate = ((current_month - 1 + offset) % 12) + 1
        if candidate in favorable:
            return candidate
    return None


# Monsoon multipliers by waterway and month (0=January, 11=December)
# Favorable: 0.7x | Adverse: 1.4x | Dangerous: 1.6x | Transition: 1.3x
WATERWAY_MONSOON: Dict[str, Dict[int, float]] = {
    "malacca_strait": {
        0: 1.4,  # January — NE monsoon adverse
        1: 1.4,  # February
        2: 1.4,  # March
        3: 1.3,  # April — transition
        4: 0.7,  # May — SW monsoon favorable
        5: 0.7,  # June
        6: 0.7,  # July
        7: 0.7,  # August
        8: 0.7,  # September
        9: 1.3,  # October — transition
        10: 1.4, # November — NE monsoon adverse
        11: 1.4, # December
    },
    "indian_ocean": {
        0: 0.7,  # January — NE monsoon favorable eastbound
        1: 0.7,  # February
        2: 0.7,  # March
        3: 1.3,  # April
        4: 0.7,  # May — SW monsoon favorable westbound
        5: 0.7,  # June
        6: 0.7,  # July
        7: 0.7,  # August
        8: 0.7,  # September
        9: 1.3,  # October
        10: 0.7, # November
        11: 0.7, # December
    },
    "arabian_sea": {
        0: 0.7,  # January — NE monsoon favorable
        1: 0.7,  # February
        2: 1.3,  # March
        3: 1.3,  # April
        4: 1.6,  # May — SW monsoon dangerous
        5: 1.6,  # June
        6: 1.4,  # July
        7: 1.4,  # August
        8: 1.3,  # September
        9: 1.3,  # October
        10: 0.7, # November — NE monsoon favorable
        11: 0.7, # December
    },
    "south_china_sea": {
        0: 0.7,  # January — NE monsoon favorable
        1: 0.7,  # February
        2: 1.3,  # March
        3: 1.3,  # April
        4: 1.4,  # May — SW monsoon adverse
        5: 1.4,  # June
        6: 1.4,  # July
        7: 1.4,  # August
        8: 1.3,  # September
        9: 1.3,  # October
        10: 0.7, # November — NE monsoon favorable
        11: 0.7, # December
    },
    "banda_sea": {
        0: 1.4,  # January
        1: 1.4,  # February
        2: 1.3,  # March
        3: 1.3,  # April
        4: 0.7,  # May
        5: 0.7,  # June
        6: 0.7,  # July
        7: 0.7,  # August
        8: 0.7,  # September
        9: 1.3,  # October
        10: 1.4, # November
        11: 1.4, # December
    },
    "malabar_coast": {
        0: 0.7,  # January — NE monsoon favorable
        1: 0.7,  # February
        2: 1.3,  # March
        3: 1.3,  # April
        4: 1.6,  # May — SW monsoon dangerous close to coast
        5: 1.6,  # June
        6: 1.4,  # July
        7: 1.4,  # August
        8: 1.3,  # September
        9: 1.3,  # October
        10: 0.7, # November
        11: 0.7, # December
    },
    "open_ocean": {
        0: 1.0, 1: 1.0, 2: 1.3, 3: 1.3, 4: 1.0, 5: 1.0,
        6: 1.0, 7: 1.0, 8: 1.3, 9: 1.3, 10: 1.0, 11: 1.0,
    },
}


def get_at_sea_description(origin: str, destination: str) -> str:
    """Return a descriptive location string for transit between two ports."""
    entry = ROUTE_WAYPOINTS.get((origin, destination))
    if entry:
        return entry["at_sea"]
    return f"At Sea, en route to {destination}"


def get_waterway(origin: str, destination: str) -> str:
    """Return the waterway region for a given route (for encounter filtering)."""
    entry = ROUTE_WAYPOINTS.get((origin, destination))
    if entry:
        return entry["waterway"]
    return "open_ocean"

# Hours of the day (simplified)
HOURS_PER_DAY = 24
DAWN_HOUR = 5
DUSK_HOUR = 19


class TimeSystem:
    """
    Tracks day, hour, and port restrictions by time of day.
    Like M&B Warband: daytime = markets and officials open,
    nighttime = reduced access, but certain characters only appear at night.
    """

    def __init__(self, day: int = 1, hour: int = 8):
        self.day = day
        self.hour = hour  # 0–23

    @property
    def is_day(self) -> bool:
        return DAWN_HOUR <= self.hour < DUSK_HOUR

    @property
    def is_night(self) -> bool:
        return not self.is_day

    @property
    def time_of_day_str(self) -> str:
        if 5 <= self.hour < 8:
            return "Dawn"
        elif 8 <= self.hour < 12:
            return "Morning"
        elif 12 <= self.hour < 15:
            return "Afternoon"
        elif 15 <= self.hour < 19:
            return "Evening"
        elif 19 <= self.hour < 22:
            return "Dusk"
        elif 22 <= self.hour or self.hour < 2:
            return "Night"
        else:
            return "Late Night"

    @property
    def display(self) -> str:
        ampm_hour = self.hour % 12 or 12
        ampm = "AM" if self.hour < 12 else "PM"
        return f"Day {self.day}  •  {ampm_hour}:00 {ampm}  ({self.time_of_day_str})"

    def advance_hours(self, hours: int):
        self.hour += hours
        while self.hour >= HOURS_PER_DAY:
            self.hour -= HOURS_PER_DAY
            self.day += 1

    def advance_to_dawn(self):
        """Fast-forward to next dawn (for resting in port)."""
        if self.hour >= DUSK_HOUR or self.hour < DAWN_HOUR:
            # Already night — advance to next day's dawn
            hours_to_dawn = (DAWN_HOUR + HOURS_PER_DAY - self.hour) % HOURS_PER_DAY
            self.advance_hours(hours_to_dawn)

    def travel(
        self,
        origin: str,
        destination: str,
        crew_speed_bonus: int = 0
    ) -> int:
        """
        Simulate travel between two locations.
        Returns the number of days elapsed.
        Storm/weather chance en route adds days.
        """
        base_days = TRAVEL_TIMES.get((origin, destination), DEFAULT_TRAVEL_TIME)
        actual_days = max(1, base_days - crew_speed_bonus)

        # Apply monsoon seasonal multiplier
        waterway = get_waterway(origin, destination)
        month = ((self.day - 1) % 365) // 30
        monsoon_mult = WATERWAY_MONSOON.get(waterway, WATERWAY_MONSOON["open_ocean"]).get(month, 1.0)
        actual_days = max(1, round(actual_days * monsoon_mult))

        # Random weather delay (15% chance of +1–3 day delay)
        if random.random() < 0.15:
            delay = random.randint(1, 3)
            actual_days += delay

        # Convert to hours
        hours = actual_days * HOURS_PER_DAY
        self.advance_hours(hours)
        return actual_days

    def port_access_status(self) -> Dict[str, bool]:
        """
        Returns what is accessible at the current time.
        Markets and officials close at night; the docks and certain
        characters are only accessible at certain hours.
        """
        return {
            "market_open":       self.is_day,
            "harbor_master":     self.is_day,
            "ruler_audience":    8 <= self.hour < 17,
            "recruitment":       self.is_day,
            "tavern":            self.hour >= 16 or self.hour < 2,
            "quest_board":       self.is_day,
            "ship_repair":       self.is_day,
            "night_market":      self.is_night and random.random() < 0.40,
            "dock_rumors":       True,  # always
        }

    def access_warning(self, feature: str) -> Optional[str]:
        status = self.port_access_status()
        warnings = {
            "market_open":   "The market is closed. Return at dawn.",
            "harbor_master": "The harbor master's office is dark. Come back in the morning.",
            "ruler_audience":"The palace is not receiving visitors at this hour.",
            "recruitment":   "The docks are quiet. Recruits will be here in the morning.",
            "quest_board":   "Officials are not available until morning.",
            "ship_repair":   "The shipwrights are not working at this hour.",
        }
        if feature in status and not status[feature]:
            return warnings.get(feature, f"{feature} not available right now.")
        return None

    def rest_until_dawn(self):
        """Rest the crew until dawn. Costs time, restores morale slightly."""
        self.advance_to_dawn()

    def to_dict(self) -> Dict[str, Any]:
        return {"day": self.day, "hour": self.hour}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TimeSystem":
        return cls(day=d.get("day", 1), hour=d.get("hour", 8))


if __name__ == "__main__":
    # Standalone sanity check for calculate_voyage() — Prompt 2.
    # Not wired into the game loop; run directly with `python time_system.py`.
    _TEST_ROUTES = [
        ("Malacca Harbor", "Aceh",      "indian_ocean",     "Portuguese Conquistador"),
        ("Malacca Harbor", "Ayutthaya", "south_china_sea",  "Chinese Trader"),
        ("Aden Harbor",    "Aceh",      "indian_ocean",     "Ottoman Trader"),
        ("Gresik",         "Bali",      "south_china_sea",  "Chinese Trader"),
    ]
    _FAVORABLE_MONTH = {"indian_ocean": 7, "south_china_sea": 12}    # Jul / Dec
    _UNFAVORABLE_MONTH = {"indian_ocean": 1, "south_china_sea": 7}   # Jan / Jul

    for _origin, _dest, _ocean, _role in _TEST_ROUTES:
        print(f"\n{_origin} -> {_dest}  ({_ocean}, {_role})")
        for _label, _month_map in (("favorable", _FAVORABLE_MONTH), ("unfavorable", _UNFAVORABLE_MONTH)):
            _month = _month_map[_ocean]
            _result = calculate_voyage(_origin, _dest, _ocean, _month, _role)
            print(f"  month={_month:>2} (expect {_label:11}) -> {_result}")
