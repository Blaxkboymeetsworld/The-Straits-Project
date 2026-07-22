"""Cross-file integrity check for The Straits Project data files."""
import json
import sys

failures = []
warnings = []

def fail(msg):   failures.append(msg)
def warn(msg):   warnings.append(msg)
def ok(msg):     print(f"  [OK]  {msg}")

# ── Load all files ────────────────────────────────────────────────────
with open("data/crew_data.json",     encoding="utf-8") as f: cd = json.load(f)
with open("data/quests.json",        encoding="utf-8") as f: qd = json.load(f)
with open("data/world.json",         encoding="utf-8") as f: wd = json.load(f)
with open("data/npc_knowledge.json", encoding="utf-8") as f: nk_raw = json.load(f)
with open("data/events.json",        encoding="utf-8") as f: ed = json.load(f)

nk = {n["id"]: n for n in nk_raw.get("npcs", [])}

# ═══════════════════════════════════════════════════════════════════
print("=== crew_data.json ===")

occ_ids = set()
for occ in cd["occupations"]:
    for key in ("id","name","description","base_combat","base_navigation","base_trade","special"):
        if key not in occ:
            fail(f"occupation {occ.get('id','?')} missing key: {key}")
    occ_ids.add(occ["id"])
ok(f"{len(occ_ids)} occupations, all have required keys")

trait_ids = set()
for t in cd["positive_traits"] + cd["negative_traits"]:
    for key in ("id","name","description","stat_mods"):
        if key not in t:
            fail(f"trait {t.get('id','?')} missing key: {key}")
    trait_ids.add(t["id"])
ok(f"{len(trait_ids)} traits (pos+neg), all have required keys")

weapons_ids = set(cd["weapons"].keys())
for w_id, w in cd["weapons"].items():
    for key in ("name","cost","description","type","damage"):
        if key not in w:
            fail(f"weapon '{w_id}' missing key: {key}")
ok(f"{len(weapons_ids)} weapons, all have required keys")

# TRAIT_EXCLUSIONS in crew.py — all referenced ids must exist in data
TRAIT_EXCLUSION_IDS = {
    "xenophobic","worldly","polyglot","inspiring","zealot","coward","calm_under_fire",
    "intimidating","womanizer","pious","insubordinate","prideful","gossip",
    "kleptomaniac","sharp_trader",
}
for tid in TRAIT_EXCLUSION_IDS:
    if tid not in trait_ids:
        fail(f"crew.py TRAIT_EXCLUSIONS references trait '{tid}' not found in data")

# Occupation ids used in has_occupation() calls throughout codebase
OCCUPATION_REFERENCES = [
    "cook","navigator","carpenter","physician","merchant","interpreter",
    "gunner","soldier","mercenary","scout","priest",
    # "imam" and "monk" are not separate ids — crew_data uses "priest" for all spiritual roles
]
for oc in OCCUPATION_REFERENCES:
    if oc not in occ_ids:
        fail(f"Python code references occupation '{oc}' not in crew_data.json")
ok("all Python-referenced occupation ids exist in crew_data.json")

# recruitable_archetypes — must be a dict
archetypes = cd["recruitable_archetypes"]
if not isinstance(archetypes, dict):
    fail("recruitable_archetypes is not a dict")
else:
    ok(f"{len(archetypes)} recruitable archetypes present")

# ═══════════════════════════════════════════════════════════════════
print()
print("=== world.json ===")

all_port_names = {p["name"] for p in wd["major_ports"] + wd["villages"]}

for p in wd["major_ports"] + wd["villages"]:
    pname = p.get("name", "?")
    for req_key in ("name","specialty_goods","base_prices","recruitable_pool","weapons_available","culture","language","religion"):
        if req_key not in p:
            fail(f"port/village '{pname}' missing key: {req_key}")
    for w_ref in p.get("weapons_available", []):
        if w_ref not in weapons_ids:
            fail(f"port '{pname}' weapons_available references unknown weapon: {w_ref}")
    for archetype in p.get("recruitable_pool", []):
        if archetype not in archetypes:
            fail(f"port '{pname}' recruitable_pool references unknown archetype: {archetype}")

    ruler = p.get("ruler")
    if ruler is not None:
        if not isinstance(ruler, dict):
            fail(f"port/village '{pname}' ruler is not a dict: {type(ruler).__name__}")
        else:
            for rk in ("name","title","faction","disposition"):
                if rk not in ruler:
                    fail(f"port/village '{pname}' ruler missing key: {rk}")
            if "disposition" in ruler and not isinstance(ruler["disposition"], int):
                fail(f"port/village '{pname}' ruler disposition is not an int: {ruler['disposition']!r}")

    hm_shape = p.get("harbor_master")
    if hm_shape is not None:
        if not isinstance(hm_shape, dict):
            fail(f"port/village '{pname}' harbor_master is not a dict: {type(hm_shape).__name__}")
        else:
            if "name" not in hm_shape:
                fail(f"port/village '{pname}' harbor_master missing key: name")
            if "fees" not in hm_shape:
                fail(f"port/village '{pname}' harbor_master missing key: fees")
            elif not isinstance(hm_shape["fees"], (int, dict)):
                fail(f"port/village '{pname}' harbor_master fees is not an int or dict: {hm_shape['fees']!r}")

for p in wd["major_ports"]:
    pname = p.get("name", "?")
    hm = p.get("harbor_master")
    if not hm:
        fail(f"major port '{pname}' missing harbor_master")
    elif "name" not in hm or "fees" not in hm:
        fail(f"major port '{pname}' harbor_master missing 'name' or 'fees'")

ok(f"{len(wd['major_ports'])} major ports: keys, weapons, archetypes, harbor_master checked")
ok(f"{len(wd['villages'])} villages checked")

# TRAVEL_TIMES in time_system.py — ports in that table should exist in world.json
# (we can't import time_system here safely, but we can grep)
import re, pathlib
ts_text = pathlib.Path("time_system.py").read_text(encoding="utf-8")
travel_port_refs = re.findall(r'"([\w\s]+)":\s*\{', ts_text)
for ref in travel_port_refs:
    ref = ref.strip()
    if ref and ref not in all_port_names and ref not in ("At Sea",) and "_" not in ref:
        warn(f"time_system.py TRAVEL_TIMES key '{ref}' not found in world.json")
ok("time_system.py TRAVEL_TIMES keys cross-referenced against world.json")

# PORT_HARBOR_MASTERS in straits_project.py
PORT_HARBOR_MASTERS = {
    "Malacca Harbor": "hang_kassim_malacca",
    "Bantam":         "raden_aria_bantam",
    "Hormuz":         "abbas_ibn_yusuf_hormuz",
    "Quanzhou":       "wu_liangchen_quanzhou",
    "Aden Harbor":    "ibrahim_al_yamani_aden",
    "Goa Harbor":     "rodrigo_rabelo_goa",
    "Calicut":        "koya_moopan_calicut",
}
for port, npc_id in PORT_HARBOR_MASTERS.items():
    if port not in all_port_names:
        fail(f"PORT_HARBOR_MASTERS port '{port}' not in world.json")
    if npc_id not in nk:
        fail(f"PORT_HARBOR_MASTERS npc_id '{npc_id}' not in npc_knowledge.json")
ok("PORT_HARBOR_MASTERS: all 7 ports and npc_ids cross-reference correctly")

# PORT_FACTION in faction.py — spot-check named ports
FACTION_PORT_REFS = [
    "Malacca Harbor","Goa Harbor","Calicut","Hormuz","Quanzhou","Bantam","Aden Harbor",
]
for ref in FACTION_PORT_REFS:
    if ref not in all_port_names:
        fail(f"faction.py PORT_FACTION key '{ref}' not in world.json")
ok("faction.py PORT_FACTION port keys all in world.json")

# ═══════════════════════════════════════════════════════════════════
print()
print("=== npc_knowledge.json ===")

for npc_id, npc in nk.items():
    if "fallback" not in npc:
        fail(f"npc '{npc_id}' missing 'fallback' key")
    if "knowledge" not in npc:
        fail(f"npc '{npc_id}' missing 'knowledge' list")
    for i, entry in enumerate(npc.get("knowledge", [])):
        for req in ("topic","response"):
            if req not in entry:
                fail(f"npc '{npc_id}' knowledge[{i}] missing '{req}'")
        if "aliases" in entry and not isinstance(entry["aliases"], list):
            fail(f"npc '{npc_id}' knowledge[{i}] aliases is not a list")
        if entry.get("min_disposition", 0) > 0 and "locked_response" not in entry:
            warn(f"npc '{npc_id}' knowledge[{i}] (topic={entry.get('topic')}) has min_disposition but no locked_response")
        if entry.get("min_reputation", 0) > 0 and not entry.get("reputation_faction"):
            fail(f"npc '{npc_id}' knowledge[{i}] has min_reputation but no reputation_faction")
    port = npc.get("port", "")
    if port and port not in all_port_names:
        fail(f"npc '{npc_id}' port '{port}' not in world.json")

ok(f"{len(nk)} NPCs: fallback, knowledge entries, gate fields, port refs all checked")

# ═══════════════════════════════════════════════════════════════════
print()
print("=== events.json ===")

for pool in ("sea_events","harbor_events","village_events","special_events","lore_fragments"):
    if pool not in ed:
        fail(f"events.json missing top-level pool: {pool}")
ok("all required event pools present")

for i, frag in enumerate(ed.get("lore_fragments", [])):
    if not isinstance(frag, str):
        fail(f"lore_fragments[{i}] is not a string")
ok(f"{len(ed.get('lore_fragments',[]))} lore fragments, all strings")

VALID_EFFECT_KEYS = {"gold","spices","ship_health","morale","provisions"}
for pool_name in ("sea_events","harbor_events","village_events","special_events"):
    for ev in ed.get(pool_name, []):
        ev_id = ev.get("id","?")
        if "id" not in ev:
            fail(f"{pool_name} event missing 'id'")
        for opt_key, opt in ev.get("options", {}).items():
            if "text" not in opt:
                fail(f"event '{ev_id}' option '{opt_key}' missing 'text'")
            for eff_key in opt.get("effect", {}) or {}:
                if eff_key not in VALID_EFFECT_KEYS:
                    warn(f"event '{ev_id}' option '{opt_key}' effect has unrecognized key: {eff_key}")
        npc_ref = ev.get("npc_id")
        if npc_ref and npc_ref != "harbor_master" and npc_ref not in nk:
            fail(f"event '{ev_id}' npc_id '{npc_ref}' not in npc_knowledge.json")

ok("all event options have 'text'; effect keys valid; npc_id cross-refs OK")

# harbormaster_intro_special must have npc_id = harbor_master
hm_special = next((e for e in ed.get("special_events",[]) if e.get("id") == "harbormaster_intro_special"), None)
if not hm_special:
    fail("harbormaster_intro_special event missing from special_events")
elif hm_special.get("npc_id") != "harbor_master":
    fail(f"harbormaster_intro_special npc_id = '{hm_special.get('npc_id')}', expected 'harbor_master'")
else:
    ok("harbormaster_intro_special has npc_id='harbor_master'")

# ═══════════════════════════════════════════════════════════════════
print()
print("=== quests.json ===")

for key in ("quests","mamluk_arc"):
    if key not in qd:
        fail(f"quests.json missing top-level key: {key}")
ok("quests.json has 'quests' and 'mamluk_arc' keys")

REQUIRED_QUEST_KEYS        = ("id","title","description","giver_name","giver_port","reward_gold","reward_disposition")
REQUIRED_WORLD_EVENT_KEYS  = ("id","title","reward_gold","reward_disposition")   # no giver/description for triggered world events
all_quest_ids = set()
quest_port_refs = []

for list_name in ("quests","mamluk_arc"):
    for q in qd.get(list_name, []):
        q_id = q.get("id","?")
        is_world_event = q.get("type") == "world_event"
        keys_to_check = REQUIRED_WORLD_EVENT_KEYS if is_world_event else REQUIRED_QUEST_KEYS
        for rk in keys_to_check:
            if rk not in q:
                fail(f"quest '{q_id}' ({list_name}) missing key: {rk}")
        all_quest_ids.add(q_id)
        port = q.get("giver_port")
        if port:
            quest_port_refs.append((q_id, port))

ok(f"{len(all_quest_ids)} total quest ids collected from both lists")

# Port cross-refs (allow 'any', None, and multi-port strings separated by '/')
for q_id, port in quest_port_refs:
    if port == "any" or port is None:
        continue
    ports_in_quest = [p.strip() for p in port.split("/")]
    for p in ports_in_quest:
        if p and p not in all_port_names:
            warn(f"quest '{q_id}' port '{p}' not in world.json")

ok("quest port references cross-checked against world.json")

# target_port: null is only valid for completion == "at_giver" quests (resolved
# in place at the giver_port) or type == "world_event" (which never resolves
# via the giver_port/target_port quest flow at all — triggered directly by
# _check_world_events() in straits_project.py). Any other quest with a null
# target_port can never be completed: check_port_arrival has nothing to match
# it against, so it's permanently stuck once accepted.
for list_name in ("quests","mamluk_arc"):
    for q in qd.get(list_name, []):
        if (
            q.get("target_port") is None
            and q.get("type") != "world_event"
            and q.get("completion") != "at_giver"
        ):
            fail(f"quest '{q.get('id','?')}' ({list_name}) has target_port=null but completion != 'at_giver' — quest can never be completed")

ok("target_port=null only allowed with completion='at_giver' (or type='world_event')")

# completion == "deliver" requires a non-empty cargo_required and a non-null target_port
for list_name in ("quests","mamluk_arc"):
    for q in qd.get(list_name, []):
        if q.get("completion") == "deliver":
            q_id = q.get("id","?")
            if q.get("target_port") is None:
                fail(f"quest '{q_id}' ({list_name}) has completion='deliver' but target_port is null")
            cargo_req = q.get("cargo_required")
            if not cargo_req or not isinstance(cargo_req, dict):
                fail(f"quest '{q_id}' ({list_name}) has completion='deliver' but cargo_required is missing or empty")

ok("completion='deliver' quests all have non-empty cargo_required and non-null target_port")

# requires_quest chain — every referenced id must exist
for list_name in ("quests","mamluk_arc"):
    for q in qd.get(list_name, []):
        rq = q.get("requires_quest")
        if rq and rq not in all_quest_ids:
            fail(f"quest '{q['id']}' requires_quest '{rq}' does not exist in quests.json")

ok("requires_quest chain is fully self-consistent")

# protagonist_lock values must be valid role names
VALID_ROLES = {"Portuguese Conquistador","Ottoman Trader","Chinese Trader"}
for list_name in ("quests","mamluk_arc"):
    for q in qd.get(list_name, []):
        pl = q.get("protagonist_lock")
        if pl and pl not in VALID_ROLES:
            fail(f"quest '{q['id']}' protagonist_lock '{pl}' is not a valid role")
ok("protagonist_lock values all valid")

# available_years must be a list of ints or absent
for list_name in ("quests","mamluk_arc"):
    for q in qd.get(list_name, []):
        ay = q.get("available_years")
        if ay is not None:
            if not isinstance(ay, list) or not all(isinstance(y, int) for y in ay):
                fail(f"quest '{q['id']}' available_years is not a list of ints: {ay}")
ok("available_years fields are well-formed")

# ═══════════════════════════════════════════════════════════════════
print()
if warnings:
    print(f"=== WARNINGS ({len(warnings)}) ===")
    for w in warnings:
        print(f"  [WARN] {w}")
    print()

if failures:
    print(f"=== FAILURES: {len(failures)} ===")
    for fi in failures:
        print(f"  [FAIL] {fi}")
    sys.exit(1)
else:
    print(f"=== ALL CHECKS PASSED  ({len(warnings)} warnings) ===")
    sys.exit(0)
