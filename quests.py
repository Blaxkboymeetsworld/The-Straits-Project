#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
quests.py — Timed quest system. Lords give quests, player completes them
             within a time window, disposition tracks relationship to rulers.
"""

import json
import os
import random
from typing import Dict, List, Any, Optional, Tuple

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT_DIR, "data")


def load_quests() -> List[Dict[str, Any]]:
    path = os.path.join(DATA_DIR, "quests.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("quests", [])


def load_mamluk_arc() -> List[Dict[str, Any]]:
    path = os.path.join(DATA_DIR, "quests.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("mamluk_arc", [])


class ActiveQuest:
    """An in-progress quest with a deadline."""

    def __init__(self, quest_data: Dict[str, Any], accepted_on_day: int = 1):
        self.id = quest_data["id"]
        self.title = quest_data["title"]
        self.giver_port = quest_data["giver_port"]
        self.giver_name = quest_data["giver_name"]
        self.giver_title = quest_data["giver_title"]
        self.description = quest_data["description"]
        self.target_port = quest_data["target_port"]
        self.target_character = quest_data.get("target_character")
        self.time_limit_days = quest_data["time_limit_days"]
        self.reward_gold = quest_data["reward_gold"]
        self.reward_disposition = quest_data["reward_disposition"]
        self.reward_item = quest_data.get("reward_item")
        self.failure_disposition = quest_data["failure_disposition"]
        self.lore = quest_data.get("lore", "")
        self.quest_type = quest_data.get("quest_type", "main")
        self.quest_tier = quest_data.get("quest_tier", 1)
        self.completion = quest_data.get("completion")
        self.accepted_on_day = accepted_on_day
        # Non-expiring adventure quests use time_limit_days: 0
        tlimit = quest_data["time_limit_days"]
        self.deadline = 999999 if tlimit == 0 else accepted_on_day + tlimit
        self.completed = False
        self.failed = False
        self.contact_found = False  # set True when player finds target_character at port

    def days_remaining(self, current_day: int) -> int:
        return self.deadline - current_day

    def is_expired(self, current_day: int) -> bool:
        if self.quest_type == "adventure" or self.deadline == 999999:
            return False
        return current_day > self.deadline and not self.completed

    def status_line(self, current_day: int) -> str:
        remaining = self.days_remaining(current_day)
        status = "✓ COMPLETE" if self.completed else ("✗ FAILED" if self.failed else f"{remaining}d left")
        destination = f"(resolve at {self.giver_port})" if self.completion == "at_giver" else f"→ {self.target_port}"
        return f"  [{status}] '{self.title}' {destination}  (from {self.giver_name})"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "giver_port": self.giver_port,
            "giver_name": self.giver_name,
            "giver_title": self.giver_title,
            "description": self.description,
            "target_port": self.target_port,
            "target_character": self.target_character,
            "time_limit_days": self.time_limit_days,
            "reward_gold": self.reward_gold,
            "reward_disposition": self.reward_disposition,
            "reward_item": self.reward_item,
            "failure_disposition": self.failure_disposition,
            "lore": self.lore,
            "quest_type": self.quest_type,
            "quest_tier": self.quest_tier,
            "completion": self.completion,
            "accepted_on_day": self.accepted_on_day,
            "deadline": self.deadline,
            "completed": self.completed,
            "failed": self.failed,
            "contact_found": self.contact_found,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ActiveQuest":
        pseudo_data = {
            "id": d["id"], "title": d["title"],
            "giver_port": d["giver_port"], "giver_name": d["giver_name"],
            "giver_title": d["giver_title"], "description": d["description"],
            "target_port": d["target_port"], "target_character": d["target_character"],
            "time_limit_days": d["time_limit_days"], "reward_gold": d["reward_gold"],
            "reward_disposition": d["reward_disposition"], "reward_item": d["reward_item"],
            "failure_disposition": d["failure_disposition"], "lore": d.get("lore", ""),
            "quest_type": d.get("quest_type", "main"), "quest_tier": d.get("quest_tier", 1),
            "completion": d.get("completion"),
        }
        obj = cls(pseudo_data, d["accepted_on_day"])
        obj.deadline = d["deadline"]
        obj.completed = d["completed"]
        obj.failed = d["failed"]
        obj.contact_found = d.get("contact_found", False)
        return obj


# Minimum faction reputation tier required per quest "tier" label.
# Quest data can carry a "req_rep_tier" int field (-5 to 5). Default 0.
QUEST_TIER_LABELS: Dict[int, str] = {
    0: "Dockworkers & minor tradesmen",
    1: "Guild merchants & ship captains",
    2: "Senior merchants & officers",
    3: "Orang Kaya, Fidalgo, junior beys",
    4: "Rulers, Bendahara, Viceroy, Zamorin",
    5: "Inner circle — by invitation only",
}

# 5-quest milestone scenes per faction (keyed by faction_id)
MILESTONE_SCENES: Dict[str, str] = {
    "malacca_sultanate": (
        "A senior officer of the Bendahara's household finds you at your anchorage.\n"
        "He says nothing complimentary — only that your name has been spoken in the right rooms.\n"
        "\"Do not mistake attention for trust. But you have our attention.\""
    ),
    "estado_da_india": (
        "A Fidalgo of the Estado, greying and precise, meets you at the harbor master's office.\n"
        "He reviews your record without expression. Then:\n"
        "\"You are becoming useful to the Crown. Useful men are remembered. Useful men are also watched.\""
    ),
    "ming_dynasty": (
        "Wei Chongde receives a sealed letter that was not addressed to him.\n"
        "He reads it, says nothing, hands it to you.\n"
        "It is from a factor in Quanzhou: your name appears in a ledger that very few people see."
    ),
    "hadrami_silsila": (
        "An elder of the Silsila — old, white-bearded, unhurried — greets you in Aden\n"
        "as if he expected you. He speaks for three minutes and says little directly.\n"
        "What he does say: \"The network remembers those who carry its water faithfully.\""
    ),
    "kingdom_of_calicut": (
        "The Zamorin's trade commissioner receives you standing, which is an honour.\n"
        "\"Five tasks,\" he says. \"A man who completes five tasks is either reliable or lucky.\n"
        "We prefer reliable. Come back when you have a sixth.\""
    ),
    "sultanate_of_bantam": (
        "A senior Orang Kaya sends a boy with a folded cloth — good Javanese work.\n"
        "No note. No explanation.\n"
        "Old Liang, if present, says: \"That cloth costs more than your ship.\""
    ),
}


class QuestManager:
    """Manages active quests, completions, and port dispositions."""

    def __init__(self):
        self.active: List[ActiveQuest] = []
        self.completed_ids: List[str] = []
        self.failed_ids: List[str] = []
        # Disposition per port ruler (0–100, default 50)
        self.disposition: Dict[str, int] = {}
        # Lore throttle: track how many times each lore string has been shown
        self.lore_shown_count: Dict[str, int] = {}

    def get_disposition(self, port_name: str) -> int:
        return self.disposition.get(port_name, 50)

    def adjust_disposition(self, port_name: str, delta: int):
        current = self.disposition.get(port_name, 50)
        self.disposition[port_name] = max(0, min(100, current + delta))

    def disposition_label(self, port_name: str) -> str:
        d = self.get_disposition(port_name)
        if d >= 80: return "Warmly disposed"
        if d >= 60: return "Friendly"
        if d >= 45: return "Neutral"
        if d >= 25: return "Wary"
        return "Hostile"

    def available_quests_at_port(
        self,
        port_name: str,
        all_quests: List[Dict[str, Any]],
        faction_manager: Any = None,
        state: Any = None,
    ) -> List[Dict[str, Any]]:
        """
        Return quests available at this port that haven't been taken yet,
        filtered by faction reputation tier if faction_manager is provided.
        """
        from faction import port_to_faction
        taken_or_done = set(q.id for q in self.active) | set(self.completed_ids) | set(self.failed_ids)
        result = []
        state_role  = getattr(state, "role", None)     if state else None
        state_year  = getattr(state, "year", 1)        if state else 1
        state_flags = getattr(state, "once_flags", []) if state else []

        for q in all_quests:
            if q.get("giver_port") != port_name:
                continue
            if q["id"] in taken_or_done:
                continue

            # Protagonist lock
            proto_lock = q.get("protagonist_lock")
            if proto_lock and state_role and state_role != proto_lock:
                continue

            # Available years gate
            avail_years = q.get("available_years")
            if avail_years and state_year not in range(avail_years[0], avail_years[-1] + 1):
                continue

            # requires_quest: prior quest must be completed
            req_quest = q.get("requires_quest")
            if req_quest and req_quest not in self.completed_ids:
                continue

            # requires_world_event: a once_flag must be set
            req_event = q.get("requires_world_event")
            if req_event and req_event not in state_flags:
                continue

            # Quest tier gating (global reputation_tier vs quest_tier)
            # Tier 1: rep 0+ (always), Tier 2: rep 1+, Tier 3: rep 3+
            QUEST_TIER_MIN_REP = {1: 0, 2: 1, 3: 3}
            qt = q.get("quest_tier", 1)
            player_rep = getattr(state, "reputation_tier", 0) if state else 0
            if player_rep < QUEST_TIER_MIN_REP.get(qt, 0):
                continue

            # Faction rep tier gating (faction-specific)
            req_tier = q.get("req_rep_tier", 0)
            if req_tier > 0 and faction_manager is not None:
                faction_id = port_to_faction(port_name)
                if faction_id:
                    player_tier = faction_manager.get_rep(faction_id)
                    if player_tier < req_tier:
                        continue

            # Role lock
            req_role = q.get("requires_role")
            if req_role and state_role != req_role:
                continue

            result.append(q)
        return result

    def lore_throttled(self, lore_text: str, max_shows: int = 2) -> bool:
        """
        Returns True if this lore text has been shown max_shows times already.
        Call before displaying lore, then call record_lore_shown() if displaying.
        """
        count = self.lore_shown_count.get(lore_text, 0)
        return count >= max_shows

    def record_lore_shown(self, lore_text: str):
        self.lore_shown_count[lore_text] = self.lore_shown_count.get(lore_text, 0) + 1

    def check_expirations(self, current_day: int) -> List[ActiveQuest]:
        """Check and mark failed quests. Returns list of newly-failed quests."""
        newly_failed = []
        for q in self.active:
            if not q.completed and not q.failed and q.is_expired(current_day):
                q.failed = True
                self.failed_ids.append(q.id)
                self.adjust_disposition(q.giver_port, q.failure_disposition)
                newly_failed.append(q)
        return newly_failed

    def check_port_arrival(
        self,
        port_name: str,
        current_day: int,
        state: Any,
        clear_fn,
        press_enter_fn
    ):
        """
        Called on arrival at a port. Checks if any active quest has this as
        the target port, and if so, attempts to resolve it.

        Quests with completion == "at_giver" instead resolve at the
        giver_port itself — no separate target_port travel required.
        """
        for q in self.active:
            if q.completed or q.failed:
                continue
            if q.contact_found:
                continue

            if q.completion == "at_giver":
                if q.giver_port != port_name:
                    continue
                clear_fn()
                print("═" * 50)
                print(f"  QUEST — '{q.title}'")
                print("═" * 50)
                if q.target_character:
                    print(f"\n  {q.target_character} is here at {q.giver_port}.")
                    print(f"\n  After some asking around the docks and market lanes,\n"
                          f"  you find them and settle the matter — the information\n"
                          f"  {q.giver_name} needed is now in hand.")
                else:
                    print(f"\n  Your task here is done. You gather the information {q.giver_name}\n"
                          f"  required, right where you stand.")
                q.contact_found = True
                press_enter_fn()
                continue

            if q.target_port != port_name:
                continue
            # Quest resolution
            clear_fn()
            print("═" * 50)
            print(f"  QUEST — '{q.title}'")
            print("═" * 50)

            if q.target_character:
                print(f"\n  You are here to find: {q.target_character}")
                print(f"\n  After some asking around the docks and market lanes,\n"
                      f"  you locate {q.target_character}.")
                print(f"\n  [Press Enter to meet them]")
                press_enter_fn()
                _resolve_character_meeting(q, state, self, clear_fn, press_enter_fn)
            else:
                # No specific character, just completing the delivery/intelligence quest
                print(f"\n  Your task here is done. You gather the information {q.giver_name}\n"
                      f"  required and prepare to return.")
                print(f"\n  Quest contact found. Return to {q.giver_port} to complete.")
                q.contact_found = True
                press_enter_fn()

    def check_return_to_giver(
        self,
        port_name: str,
        current_day: int,
        state: Any,
        clear_fn,
        press_enter_fn
    ):
        """Called on arrival — check if any completed-contact quest is being returned here."""
        for q in self.active:
            if q.completed or q.failed:
                continue
            if q.giver_port != port_name:
                continue
            if not q.contact_found:
                continue
            # Return and completion
            clear_fn()
            print("═" * 50)
            print(f"  QUEST COMPLETE — '{q.title}'")
            print("═" * 50)
            print(f"\n  You return to {q.giver_name} with the news they sought.")
            print(f"\n  The reward: {q.reward_gold} gold.")
            if q.reward_item:
                print(f"  You also receive: {q.reward_item.replace('_',' ').title()}")
                state.items.append(q.reward_item)
            # Lore cap: suppress after 3 total displays (acceptance + completions)
            if q.lore:
                lore_count = getattr(state, "seen_lore_flags", {}).get(q.id, 0)
                if lore_count < 3:
                    lang = getattr(state, "lang", "en")
                    lore_text = getattr(q, f"lore_{lang}", q.lore) if lang != "en" else q.lore
                    print(f"\n  ─ Historical Note ─\n  {lore_text}\n")
                    if hasattr(state, "seen_lore_flags"):
                        state.seen_lore_flags[q.id] = lore_count + 1

            state.gold += q.reward_gold
            self.adjust_disposition(port_name, q.reward_disposition)
            q.completed = True
            self.completed_ids.append(q.id)
            self.active.remove(q)

            # Global reputation and assignment tracking
            if hasattr(state, "reputation_tier"):
                state.reputation_tier = min(5, state.reputation_tier + 1)
            if hasattr(state, "assignments_completed"):
                state.assignments_completed += 1

            # Faction rep increase on quest completion
            from faction import port_to_faction
            faction_id = port_to_faction(port_name)
            if faction_id and hasattr(state, "factions"):
                state.factions.adjust_rep(faction_id, +1)
                state.factions.adjust_disposition(faction_id, +5)
                # 5-quest milestone check
                milestone_key = state.factions.record_faction_quest(faction_id)
                if milestone_key and faction_id in MILESTONE_SCENES:
                    print()
                    print("  ─" * 26)
                    print(f"\n  {MILESTONE_SCENES[faction_id]}\n")
                    print("  ─" * 26)

            press_enter_fn()
            break

    def quest_board_menu(
        self,
        port_name: str,
        all_quests: List[Dict[str, Any]],
        current_day: int,
        state: Any,
        clear_fn,
        press_enter_fn
    ):
        """Show available and active quests at this port."""
        faction_manager = getattr(state, "factions", None)
        # Merge main quests + mamluk arc for availability check
        mamluk_arc = load_mamluk_arc()
        combined_quests = all_quests + [
            q for q in mamluk_arc
            if q.get("type") != "world_event" and q.get("giver_port") is not None
        ]
        available = self.available_quests_at_port(port_name, combined_quests, faction_manager, state)

        while True:
            clear_fn()
            print("═" * 50)
            print(f"  AUDIENCES & MISSIONS — {port_name}")
            print(f"  Disposition: {self.disposition_label(port_name)} ({self.get_disposition(port_name)})")
            print("═" * 50)

            # Active quests
            if self.active:
                print(f"\n  Active quests:\n")
                for q in self.active:
                    print(q.status_line(current_day))

            # Available from this port
            if available:
                print(f"\n  Available from {port_name}:\n")
                for i, q in enumerate(available, 1):
                    diff = q.get("difficulty", "moderate").upper()
                    print(f"  [{i}] '{q['title']}' ({diff}) — {q['giver_name']}, {q['giver_title']}")
                    if q.get("completion") == "at_giver":
                        print(f"       → Resolve at {q['giver_port']}")
                    else:
                        print(f"       → Go to {q['target_port']}  within {q['time_limit_days']} days")
                    print(f"       Reward: {q['reward_gold']} gold\n")
            else:
                print("\n  No new missions available here at this time.\n")

            print("  [1–N] Accept a mission  |  [Q] Leave\n")
            choice = input("  > ").strip().upper()

            if choice == "Q":
                break
            elif choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(available):
                    q_data = available[idx]
                    aq = ActiveQuest(q_data, current_day)
                    self.active.append(aq)
                    available.pop(idx)
                    clear_fn()
                    print(f"\n  '{q_data['title']}'\n")
                    lang = getattr(state, "lang", "en")
                    desc_text = q_data.get(f"description_{lang}", q_data["description"]) if lang != "en" else q_data["description"]
                    print(f"  {desc_text}\n")
                    lore_id = q_data.get("id", "")
                    lore_count = getattr(state, "seen_lore_flags", {}).get(lore_id, 0)
                    if q_data.get("lore") and lore_count < 3:
                        lore_text = q_data.get(f"lore_{lang}", q_data["lore"]) if lang != "en" else q_data["lore"]
                        print(f"  ─ Context ─\n  {lore_text}\n")
                        if hasattr(state, "seen_lore_flags"):
                            state.seen_lore_flags[lore_id] = lore_count + 1
                    print(f"  You have {q_data['time_limit_days']} days.")
                    press_enter_fn()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active": [q.to_dict() for q in self.active],
            "completed_ids": self.completed_ids,
            "failed_ids": self.failed_ids,
            "disposition": self.disposition,
            "lore_shown_count": self.lore_shown_count,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "QuestManager":
        qm = cls()
        qm.active = [ActiveQuest.from_dict(aq) for aq in d.get("active", [])]
        qm.completed_ids = d.get("completed_ids", [])
        qm.failed_ids = d.get("failed_ids", [])
        qm.disposition = d.get("disposition", {})
        qm.lore_shown_count = d.get("lore_shown_count", {})
        return qm


def _resolve_character_meeting(
    quest: ActiveQuest,
    state: Any,
    qm: QuestManager,
    clear_fn,
    press_enter_fn
):
    """Narrative resolution when player meets the target character."""
    clear_fn()
    tc = quest.target_character
    print(f"\n  {tc} meets you in a tea house off the harbor lane.")
    print(
        f"\n  He is guarded at first, but when you produce {quest.giver_name}'s seal,\n"
        f"  something shifts behind his eyes. He speaks carefully. He confirms what\n"
        f"  {quest.giver_name} needed to know. The matter is settled — for now.\n"
    )
    print(f"\n  Return to {quest.giver_port} to report. The reward awaits.\n")
    quest.contact_found = True
    press_enter_fn()
