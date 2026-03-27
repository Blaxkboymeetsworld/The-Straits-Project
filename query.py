#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
query.py — Text query system for The Straits Project v0.3.0

Roadwarden-style free-text NPC queries with:
- Fuzzy keyword / alias matching
- Disposition gates (port-level)
- Faction reputation gates (per-entry)
- Graceful fallback responses
"""

import json
import os
from typing import Dict, Any, Optional, List

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR  = os.path.join(ROOT_DIR, "data")
NPC_KNOWLEDGE_PATH = os.path.join(DATA_DIR, "npc_knowledge.json")

# ── Port → queryable NPC IDs (ordered: harbor master first) ──────────
PORT_NPCS: Dict[str, List[str]] = {
    "Malacca Harbor": ["hang_kassim_malacca", "tun_mutahir_malacca"],
    "Bantam":         ["raden_aria_bantam"],
    "Hormuz":         ["abbas_ibn_yusuf_hormuz", "mustafa_al_rumi_hormuz"],
    "Quanzhou":       ["wu_liangchen_quanzhou"],
    "Aden Harbor":    ["ibrahim_al_yamani_aden", "amir_salim_tahiri_aden"],
    "Goa Harbor":     ["rodrigo_rabelo_goa"],
    "Calicut":        ["koya_moopan_calicut"],
}

# ── Tavern informant per port (first match used) ─────────────────────
TAVERN_NPC: Dict[str, str] = {
    "Malacca Harbor": "hang_kassim_malacca",
    "Bantam":         "raden_aria_bantam",
    "Hormuz":         "abbas_ibn_yusuf_hormuz",
    "Quanzhou":       "wu_liangchen_quanzhou",
    "Aden Harbor":    "ibrahim_al_yamani_aden",
    "Goa Harbor":     "rodrigo_rabelo_goa",
    "Calicut":        "koya_moopan_calicut",
}

_knowledge_cache: Optional[Dict[str, Any]] = None


def _load() -> Dict[str, Any]:
    global _knowledge_cache
    if _knowledge_cache is None:
        with open(NPC_KNOWLEDGE_PATH, encoding="utf-8") as f:
            raw = json.load(f)
        _knowledge_cache = {npc["id"]: npc for npc in raw.get("npcs", [])}
    return _knowledge_cache


def get_npc_disposition(npc_id: str, state) -> int:
    """Return the current port-level disposition for this NPC's home port."""
    npc = _load().get(npc_id, {})
    port_name = npc.get("port", "")
    return state.quests.get_disposition(port_name) if port_name else 0


def text_query(npc_id: str, query_text: str, state) -> str:
    """
    Match query_text against this NPC's knowledge entries.

    Matching: any alias/topic that appears as a substring of query,
    or query appears as a substring of the alias/topic.
    First match wins.

    Returns the appropriate response string.
    """
    db = _load()
    npc = db.get(npc_id)
    if not npc:
        return "He looks at you blankly."

    query = query_text.lower().strip()
    if not query:
        return npc.get("fallback_unknown", "He says nothing.")

    matched = None
    for entry in npc.get("knowledge", []):
        keys = [entry["topic"]] + entry.get("aliases", [])
        if any(k in query or query in k for k in keys):
            matched = entry
            break

    if not matched:
        return npc.get("fallback_unknown", "He looks at you blankly.")

    # ── Disposition gate ──────────────────────────────────────────────
    disp = get_npc_disposition(npc_id, state)
    if disp < matched.get("min_disposition", 0):
        return matched.get(
            "locked_response",
            "He studies you a moment. 'I wouldn't know anything about that.'"
        )

    # ── Faction reputation gate ───────────────────────────────────────
    req_rep = matched.get("min_reputation", 0)
    rep_faction = matched.get("reputation_faction")
    if rep_faction and req_rep > 0:
        if state.factions.get_rep(rep_faction) < req_rep:
            return matched.get(
                "locked_response",
                "He glances around. 'Not something I discuss with strangers.'"
            )

    return matched["response"]


# ── Interactive query loop ────────────────────────────────────────────

def query_npc_menu(
    npc_id: str,
    state,
    clear_fn,
    press_enter_fn,
    intro_line: str = "",
):
    """
    Full conversation loop with a named NPC.
    Player types free-text questions; press Enter on blank line to leave.
    """
    db = _load()
    npc = db.get(npc_id, {})
    npc_name = npc.get("name", npc_id)
    npc_role  = npc.get("role", "")

    clear_fn()
    print("═" * 52)
    label = f"{npc_name}  —  {npc_role}" if npc_role else npc_name
    print(f"  {label}")
    if intro_line:
        print(f"\n  {intro_line}")
    print("═" * 52)
    print(
        "\n  Ask him anything: routes, prices, local politics, faction affairs,\n"
        "  or the names of men worth knowing.\n"
        "  (Press Enter on an empty line to step away.)\n"
    )

    while True:
        raw = input("  You: ").strip()
        if not raw:
            break
        response = text_query(npc_id, raw, state)
        print(f"\n  {npc_name}: \"{response}\"\n")

    press_enter_fn()


def speak_with_locals_menu(
    port_name: str,
    state,
    clear_fn,
    press_enter_fn,
):
    """
    Present the list of queryable NPCs at this port and let the player
    pick one to speak with.
    """
    db = _load()
    npc_ids = PORT_NPCS.get(port_name, [])
    available = [
        (nid, db[nid]) for nid in npc_ids if nid in db
    ]

    if not available:
        clear_fn()
        print("\n  There is no one here who will speak with you at length.")
        press_enter_fn()
        return

    while True:
        clear_fn()
        print("═" * 52)
        print(f"  LOCAL FIGURES — {port_name}")
        print("═" * 52)
        print()
        for i, (nid, npc) in enumerate(available, 1):
            disp = get_npc_disposition(nid, state)
            print(f"  [{i}] {npc['name']:<28} {npc.get('role','')}")
            print(f"       Disposition toward you: {disp}")
            print()
        print("  [Q] Back\n")

        choice = input("  > ").strip().upper()
        if choice == "Q":
            break
        elif choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(available):
                nid, npc = available[idx]
                query_npc_menu(nid, state, clear_fn, press_enter_fn)
            else:
                print("\n  No such person.")
                press_enter_fn()
        else:
            print("\n  No such person.")
            press_enter_fn()


def tavern_query_menu(
    port_name: str,
    state,
    clear_fn,
    press_enter_fn,
):
    """
    Tavern version: one informant NPC, presented as 'a sailor at the bar'.
    Falls back to generic if no NPC configured for this port.
    """
    npc_id = TAVERN_NPC.get(port_name)
    if not npc_id:
        clear_fn()
        print("\n  No one here seems to know much about anything.")
        press_enter_fn()
        return

    db = _load()
    npc = db.get(npc_id, {})
    npc_name = npc.get("name", "a man at the bar")

    query_npc_menu(
        npc_id,
        state,
        clear_fn,
        press_enter_fn,
        intro_line=f"You sit down beside {npc_name}. He has the look of someone who pays attention.",
    )
