#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
systems.py — Foundational mechanics used across all modules.

  roll_check(base_chance, modifiers)  — unified probability resolver
  dialogue_exchange(script, state)    — multi-turn scripted conversation engine
  IBU_MALAM_APPEARANCES               — data for recurring non-interactive figure
  LORE_FRAGMENTS                      — sea-travel urban legend pool
"""

import random
from typing import Any, Dict, List, Optional, Tuple


# ─────────────────────────────────────────
# roll_check
# ─────────────────────────────────────────

def roll_check(base_chance: float, modifiers: List[float] = None) -> bool:
    """
    Unified probability resolver. Returns True (success) or False (failure).

    base_chance : float in [0.0, 1.0]
    modifiers   : list of floats to add/subtract (e.g. +0.15, -0.10)

    Result is clamped to [0.05, 0.95] — nothing is guaranteed or impossible.
    """
    if modifiers is None:
        modifiers = []
    total = base_chance + sum(modifiers)
    clamped = max(0.05, min(0.95, total))
    return random.random() < clamped


# ─────────────────────────────────────────
# Dialogue exchange engine
# ─────────────────────────────────────────

def dialogue_exchange(script: Dict[str, Any], state: Any) -> Dict[str, Any]:
    """
    Walk through a scripted multi-turn dialogue.

    Script format:
    {
        "start": "node_id",
        "nodes": {
            "node_id": {
                "speaker": "Rui Brandão",
                "text": "Captain. A word.",
                "choices": [
                    {
                        "key": "A",
                        "text": "She stays. End of discussion.",
                        "outcome": "favorable",
                        "effects": {"morale": -2},           # applied to state
                        "next": "node_end"                    # or None = terminal
                    },
                    ...
                ]
            },
            "node_end": {
                "speaker": None,
                "text": "The matter is settled.",
                "choices": []   # empty = terminal node
            }
        }
    }

    Returns a result dict:
    {
        "outcome": "favorable" | "neutral" | "negative" | None,
        "effects_applied": [{"morale": -2}, ...]
    }
    """
    nodes = script.get("nodes", {})
    current_id = script.get("start")
    final_outcome = None
    effects_applied = []

    while current_id and current_id in nodes:
        node = nodes[current_id]
        speaker = node.get("speaker")
        text = node.get("text", "")
        choices = node.get("choices", [])

        # Print the node
        print()
        if speaker:
            print(f"  {speaker}: \"{text}\"")
        else:
            print(f"  {text}")

        if not choices:
            # Terminal node — just display and exit
            break

        # Display choices
        print()
        for ch in choices:
            print(f"  [{ch['key']}] {ch['text']}")
        print()

        # Get player input
        valid_keys = {ch["key"].upper() for ch in choices}
        while True:
            raw = input("  > ").strip().upper()
            if raw in valid_keys:
                break
            print("  (Invalid choice — try again)")

        # Find chosen branch
        chosen = next(ch for ch in choices if ch["key"].upper() == raw)
        outcome = chosen.get("outcome")
        effects = chosen.get("effects", {})
        next_id = chosen.get("next")

        if outcome:
            final_outcome = outcome

        # Apply effects to state if provided
        if effects and state is not None and hasattr(state, "apply_effect"):
            state.apply_effect(effects)
            effects_applied.append(effects)

        current_id = next_id

    return {"outcome": final_outcome, "effects_applied": effects_applied}


# ─────────────────────────────────────────
# Ibu Malam — recurring non-interactive figure
# ─────────────────────────────────────────

# Each entry: trigger_key (once_flag id), age_description, line, context note
IBU_MALAM_APPEARANCES: List[Dict[str, Any]] = [
    {
        "trigger": "ibu_malam_first_port",
        "age": "an old woman",
        "context": "first_port",
        "line": (
            "In the doorway of a warehouse at the edge of the harbour, "
            "an old woman watches your ship make fast. She does not move. "
            "By the time you look again, she is gone."
        ),
    },
    {
        "trigger": "ibu_malam_malacca_fall",
        "age": "a young woman, perhaps seventeen",
        "context": "fall_of_malacca",
        "line": (
            "In the smoke, as the city burns around her, a young woman — "
            "perhaps seventeen — stands in the open street and watches you "
            "specifically. She is unbothered. The fire does not reach her. "
            "She speaks in {protagonist_language}: \"You arrived.\" "
            "She turns away before you can answer."
        ),
    },
    {
        "trigger": "ibu_malam_after_crew_death",
        "age": "a middle-aged woman",
        "context": "crew_death",
        "line": (
            "Dockside at the next port, a middle-aged woman stands alone "
            "among the unloading crews. She looks directly at you — not "
            "past you, not near you — then walks into the crowd and is gone "
            "before you reach the gangplank."
        ),
    },
    {
        "trigger": "ibu_malam_hormuz_mehmed",
        "age": "a woman of indeterminate age",
        "context": "hormuz_ottoman",
        "role": "Ottoman Trader",
        "line": (
            "A woman of indeterminate age speaks to you in Ottoman Turkish "
            "at the Hormuz waterfront — which she should not know here. "
            "She says: \"The route west closes before you reach it.\" "
            "When you turn to question her, she has already gone."
        ),
    },
    {
        "trigger": "ibu_malam_quanzhou_chen",
        "age": "an elderly woman",
        "context": "quanzhou_chinese",
        "role": "Chinese Trader",
        "line": (
            "In the Quanzhou market, an elderly woman recedes into the crowd "
            "as you pass. She does not speak. But Old Liang goes pale. "
            "He will not say what he saw."
        ),
    },
]


def get_ibu_malam_appearance(
    trigger: str,
    state: Any,
    protagonist_language: str = "Portuguese"
) -> Optional[str]:
    """
    Returns the Ibu Malam line for this trigger if it hasn't fired yet,
    else None. Marks the trigger as seen in state.once_flags.
    """
    if trigger in state.once_flags:
        return None

    for entry in IBU_MALAM_APPEARANCES:
        if entry["trigger"] != trigger:
            continue
        # Role filter
        if "role" in entry and entry.get("role") != state.role:
            return None
        # Mark as seen
        state.once_flags.append(trigger)
        line = entry["line"].format(protagonist_language=protagonist_language)
        return f"\n  ─ ─ ─\n  {line}\n  ─ ─ ─"

    return None


# ─────────────────────────────────────────
# Urban legends / lore fragments
# ─────────────────────────────────────────

LORE_FRAGMENTS: List[str] = [
    (
        "Old sailors say Admiral Zheng He's treasure fleet still sails these waters "
        "in fog, crewed by men who do not know they are dead."
    ),
    (
        "The crocodile king of Patani remembers every debt. "
        "He has never forgotten one in three hundred years."
    ),
    (
        "There is an Orang Laut navigator who can read the current three days "
        "ahead by the colour of the water. He has never been wrong. "
        "He does not tell you how he knows."
    ),
    (
        "A Portuguese sailor married a Pontianak south of Pulau Tioman. "
        "He cannot die, but he also cannot sleep. "
        "He has been seen on three different ships in the same week."
    ),
    (
        "At the bottom of the Gulf of Hormuz there is a pearl that shows "
        "the diver one true vision. Every man who has brought it to the surface "
        "has put it back."
    ),
    (
        "The woman in the doorway at Malacca — the one who did not run — "
        "has been seen at Calicut, at Aden, at Bantam. Always watching. "
        "Always a different age."
    ),
    (
        "There is a chart drawn by a blind cartographer in Quanzhou that "
        "shows every reef between here and the Banda Sea. He drew it from memory. "
        "He has never been to sea."
    ),
    (
        "Somewhere in the Java Sea there is an island that appears for three days "
        "after every monsoon and is not on any map. The Bugis call it "
        "Pulau Bayang — the Shadow Island."
    ),
    (
        "A Tamil merchant at Calicut swears he bought a bolt of silk from a trader "
        "who had been dead six months. The silk was still warm."
    ),
    (
        "The Banda nutmeg trees do not grow where blood has not been spilled first. "
        "The oldest trees are very old."
    ),
]


def maybe_trigger_lore(state: Any, chance: float = 0.10) -> Optional[str]:
    """
    10% chance on sea travel to return a lore fragment.
    No player options. No mechanical effect. Returns text or None.
    """
    if not roll_check(chance):
        return None
    fragment = random.choice(LORE_FRAGMENTS)
    return f"\n  ─ A sailor mutters ─\n  \"{fragment}\"\n"
