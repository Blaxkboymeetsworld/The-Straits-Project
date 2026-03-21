#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
time_system.py — Day/night cycle, travel time between ports,
                  port availability by time of day (think M&B Warband's
                  simple but meaningful time system).
"""

import random
from typing import Dict, Any, Optional, Tuple

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
}

# Fill in reverse directions automatically (roughly symmetric)
_FILLED: Dict[Tuple[str, str], int] = {}
for (a, b), days in TRAVEL_TIMES.items():
    _FILLED[(a, b)] = days
    _FILLED[(b, a)] = days
TRAVEL_TIMES = _FILLED

DEFAULT_TRAVEL_TIME = 6  # fallback if route not in table

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
