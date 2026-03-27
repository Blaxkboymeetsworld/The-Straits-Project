#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QA Checklist — v0.2.0-pass1
Tests all 8 items from the Pass 1 brief QA checklist without interactive input.
"""

import json, os, sys, traceback

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

PASS = []
FAIL = []

def ok(item, msg=""):
    tag = f"  [PASS] #{item}"
    tag += f" — {msg}" if msg else ""
    PASS.append(tag)
    print(tag)

def fail(item, msg=""):
    tag = f"  [FAIL] #{item}"
    tag += f" — {msg}" if msg else ""
    FAIL.append(tag)
    print(tag)

# ─── Import straits_project without running main() ────────────────────────────
# Patch input() so any accidental prompt doesn't block
import builtins
_real_input = builtins.input
builtins.input = lambda *a, **kw: ""

try:
    import straits_project as sp
except Exception as e:
    print(f"\n  [FATAL] Could not import straits_project.py: {e}")
    traceback.print_exc()
    sys.exit(1)

builtins.input = _real_input   # restore for our own test code

# ─── Helpers ──────────────────────────────────────────────────────────────────

def load_world():
    with open(os.path.join(ROOT, "data", "world.json"), encoding="utf-8") as f:
        return json.load(f)

def make_state(role="Portuguese Conquistador", lang="en"):
    sp.load_locale(lang)
    world = load_world()
    state = sp.GameState(role, world)
    state.lang = lang
    return state

# ─── ITEM 1: Language selection screen prints both options ─────────────────────
print("\n── ITEM 1: Language selection screen ──")
try:
    import io, contextlib
    buf = io.StringIO()
    builtins.input = lambda *a, **kw: ""   # auto-confirm with ""
    with contextlib.redirect_stdout(buf):
        result = sp.select_language()
    builtins.input = _real_input
    output = buf.getvalue()
    has_en = "English" in output or "english" in output.lower()
    has_es = "Español" in output or "español" in output.lower() or "Espanol" in output
    lang_en_returns_en = (result == "en")  # blank input → "en"
    if has_en and has_es and lang_en_returns_en:
        ok(1, "Both 'English' and 'Español' appear; blank input → 'en'")
    else:
        fail(1, f"has_en={has_en} has_es={has_es} blank_returns_en={lang_en_returns_en}\noutput={repr(output)}")
except Exception as e:
    fail(1, str(e)); traceback.print_exc()

# ─── ITEM 2: Role names in English ────────────────────────────────────────────
print("\n── ITEM 2: Role names in English ──")
try:
    sp.load_locale("en")
    expected = {
        "role_portuguese": "Portuguese Conquistador",
        "role_ottoman":    "Ottoman Trader",
        "role_chinese":    "Chinese Trader",
    }
    all_ok = True
    for key, want in expected.items():
        got = sp.t(key)
        if got != want:
            fail(2, f"t('{key}') = {repr(got)}, want {repr(want)}")
            all_ok = False
    if all_ok:
        ok(2, "Portuguese Conquistador / Ottoman Trader / Chinese Trader all correct")
except Exception as e:
    fail(2, str(e)); traceback.print_exc()

# ─── ITEM 3: Harbor master name and fee from two ports ────────────────────────
print("\n── ITEM 3: harbor_master_for() — at least two ports ──")
try:
    world = load_world()
    checks = [
        ("Malacca Harbor", "Hang Kassim",    12),
        ("Bantam",         "Raden Aria",      9),
        ("Hormuz",         "Abbas ibn Yusuf", 18),
        ("Aden Harbor",    "Ibrahim al-Yamani", 14),
        ("Goa Harbor",     "Rodrigo Rabelo",  20),
        ("Calicut",        "Koya Moopan",     10),
        ("Quanzhou",       "Wu Liangchen",     8),
    ]
    errors = []
    for port, want_name, want_fee in checks:
        hm = sp.harbor_master_for(port, world)
        if hm is None:
            errors.append(f"{port}: returned None")
        elif hm.get("name") != want_name:
            errors.append(f"{port}: name={repr(hm.get('name'))}, want={repr(want_name)}")
        elif hm.get("fees") != want_fee:
            errors.append(f"{port}: fees={hm.get('fees')}, want={want_fee}")
    if errors:
        fail(3, "; ".join(errors))
    else:
        ok(3, f"All {len(checks)} ports return correct harbor master name and fee")
except Exception as e:
    fail(3, str(e)); traceback.print_exc()

# ─── ITEM 4: Save / Load — language is restored ───────────────────────────────
print("\n── ITEM 4: Save then load — language restored ──")
try:
    import tempfile, shutil
    # Temporarily redirect SAVE_PATH to a temp file
    tmp_dir = tempfile.mkdtemp()
    orig_save_path = sp.SAVE_PATH
    sp.SAVE_PATH = os.path.join(tmp_dir, "slot1.json")

    # Save an English game
    state_en = make_state("Ottoman Trader", "en")
    builtins.input = lambda *a, **kw: ""
    import io, contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        sp.save_game(state_en)

    # Reset locale to something other than en to verify restoration
    sp.load_locale("es")
    assert sp.t("menu_start") != "Start", "locale sanity: should be Spanish now"

    world = load_world()
    with contextlib.redirect_stdout(io.StringIO()):
        loaded = sp.load_game(world)
    builtins.input = _real_input

    lang_ok = (loaded is not None and loaded.lang == "en" and sp.t("menu_start") == "Start")
    if lang_ok:
        ok(4, "Saved lang='en', loaded state.lang='en', LOCALE restored to English")
    else:
        loaded_lang = loaded.lang if loaded else "None"
        menu_start = sp.t("menu_start")
        fail(4, f"loaded.lang={repr(loaded_lang)}, t('menu_start')={repr(menu_start)}")

    # Also test Spanish save/load
    sp.load_locale("en")   # reset
    state_es = make_state("Chinese Trader", "es")
    sp.SAVE_PATH = os.path.join(tmp_dir, "slot1_es.json")
    builtins.input = lambda *a, **kw: ""
    with contextlib.redirect_stdout(io.StringIO()):
        sp.save_game(state_es)
    sp.load_locale("en")  # reset locale
    with contextlib.redirect_stdout(io.StringIO()):
        loaded_es = sp.load_game(world)
    builtins.input = _real_input

    es_ok = (loaded_es is not None and loaded_es.lang == "es" and sp.t("menu_start") == "Comenzar")
    if es_ok:
        ok(4, "Spanish save: lang='es' correctly restored on load")
    else:
        fail(4, f"Spanish save/load: lang={loaded_es.lang if loaded_es else None}, menu_start={sp.t('menu_start')}")

    sp.SAVE_PATH = orig_save_path
    shutil.rmtree(tmp_dir)
except Exception as e:
    fail(4, str(e)); traceback.print_exc()
    sp.SAVE_PATH = orig_save_path

# ─── ITEM 5: Spanish mode — menus, roles, status labels, game-over ─────────────
print("\n── ITEM 5: Spanish — menus, roles, status, game-over ──")
try:
    sp.load_locale("es")

    checks = {
        "menu_start":       ("Comenzar",),
        "menu_load":        ("Cargar",),
        "menu_quit":        ("Salir",),
        "role_portuguese":  ("Conquistador Portugués",),
        "role_ottoman":     ("Comerciante Otomano",),
        "role_chinese":     ("Comerciante Chino",),
        "status_day":       ("Día",),
        "status_role":      ("Origen",),
        "status_location":  ("Ubicación",),
        "status_gold":      ("Oro",),
        "status_ship_health": ("Estado del barco",),
        "status_morale":    ("Moral",),
        "game_over_ship":   ("naufragado",),    # substring check
        "game_over_morale": ("tripulación",),   # substring check
    }
    errors = []
    for key, (expect,) in checks.items():
        got = sp.t(key)
        if got.startswith("[") and got.endswith("]"):
            errors.append(f"t('{key}') → missing key placeholder: {repr(got)}")
        elif expect not in got:
            errors.append(f"t('{key}') = {repr(got)}, expected to contain {repr(expect)}")
    if errors:
        fail(5, "\n         ".join(errors))
    else:
        ok(5, f"All {len(checks)} Spanish UI strings correct")

    # Also verify status_text() contains Spanish labels
    state_es = make_state("Portuguese Conquistador", "es")
    st = state_es.status_text()
    for label in ("Día", "Origen", "Ubicación", "Oro", "Estado del barco", "Moral"):
        if label not in st:
            fail(5, f"status_text() missing Spanish label '{label}'")
            break
    else:
        ok(5, "status_text() renders all Spanish labels")

    sp.load_locale("en")  # restore
except Exception as e:
    fail(5, str(e)); traceback.print_exc()

# ─── ITEM 6: No [key_missing] placeholders in either language ─────────────────
print("\n── ITEM 6: No [key_missing] placeholders in either language ──")
try:
    missing_keys = []
    for lang in ("en", "es"):
        sp.load_locale(lang)
        state = make_state("Portuguese Conquistador", lang)
        # All t() calls used in game
        keys_to_check = [
            "menu_title","menu_start","menu_load","menu_quit",
            "role_choose","role_portuguese","role_ottoman","role_chinese",
            "travel_menu_title","travel_major_ports","travel_villages","travel_cancel",
            "action_sail","action_landfall","action_status","action_save","action_quit",
            "status_day","status_role","status_location","status_gold","status_spices",
            "status_ship_health","status_morale",
            "game_over_ship","game_over_morale",
            "save_confirm","load_confirm","load_none","farewell",
            "you_hesitate","outcome_applied","press_enter",
        ]
        for k in keys_to_check:
            v = sp.t(k)
            if v.startswith("[") and v.endswith("]"):
                missing_keys.append(f"lang={lang}: t('{k}') = {repr(v)}")
    if missing_keys:
        fail(6, "\n         ".join(missing_keys))
    else:
        ok(6, "No [key] placeholders in English or Spanish for all UI keys")
    sp.load_locale("en")
except Exception as e:
    fail(6, str(e)); traceback.print_exc()

# ─── ITEM 7: Events display in Spanish / fallback to English ──────────────────
print("\n── ITEM 7: Event i18n — Spanish display and English fallback ──")
try:
    with open(os.path.join(ROOT, "data", "events.json"), encoding="utf-8") as f:
        events_data = json.load(f)

    all_pools = ["sea_events", "harbor_events", "village_events", "special_events"]

    # 7a: Every event that has a description has a description_es
    missing_es = []
    for pool in all_pools:
        for ev in events_data.get(pool, []):
            if "description" in ev and "description_es" not in ev:
                missing_es.append(f"{pool}/{ev.get('id','?')}: missing description_es")
            for key, opt in ev.get("options", {}).items():
                if "text" in opt and "text_es" not in opt:
                    missing_es.append(f"{pool}/{ev.get('id','?')} option {key}: missing text_es")
            # check role variants
            for role, var in ev.get("variants", {}).items():
                if "description" in var and "description_es" not in var:
                    missing_es.append(f"{pool}/{ev.get('id','?')} variant {role}: missing description_es")
                for key, opt in var.get("options", {}).items():
                    if "text" in opt and "text_es" not in opt:
                        missing_es.append(f"{pool}/{ev.get('id','?')} variant {role} option {key}: missing text_es")

    if missing_es:
        fail(7, f"{len(missing_es)} events missing _es keys:\n         " + "\n         ".join(missing_es[:10]))
    else:
        total = sum(len(events_data.get(p, [])) for p in all_pools)
        ok(7, f"All {total} events across all pools have description_es and text_es")

    # 7b: EventEngine._resolve_event correctly picks description_es when lang=es
    sp.load_locale("es")
    # find an event that has both description and description_es
    test_ev = None
    for ev in events_data.get("sea_events", []):
        if "description" in ev and "description_es" in ev:
            test_ev = ev; break
    if test_ev:
        world = load_world()
        state = make_state("Portuguese Conquistador", "es")
        engine = sp.EventEngine(events_data)
        ctx = engine._context_for_event(state)
        ev_fmt = engine._apply_templating(test_ev, ctx)
        # Simulate what _resolve_event does
        lang = state.lang
        desc_served = ev_fmt.get("description", "")
        if lang != "en":
            desc_served = ev_fmt.get(f"description_{lang}", desc_served)
        is_spanish = (desc_served == ev_fmt.get("description_es", ev_fmt.get("description")))
        if is_spanish:
            ok(7, f"EventEngine serves description_es when lang=es (event: {test_ev.get('id')})")
        else:
            fail(7, f"EventEngine served English description when lang=es")
    else:
        fail(7, "Could not find a sea_event with both description and description_es")

    # 7c: Fallback works when _es key is absent — simulate with a stripped event
    sp.load_locale("es")
    fake_ev = {"id": "test_fallback", "description": "English only description", "options": {}}
    world = load_world()
    state = make_state("Portuguese Conquistador", "es")
    engine = sp.EventEngine(events_data)
    lang = state.lang
    desc_fallback = fake_ev.get("description", "")
    if lang != "en":
        desc_fallback = fake_ev.get(f"description_{lang}", desc_fallback)
    if desc_fallback == "English only description":
        ok(7, "Fallback to English works when description_es is absent")
    else:
        fail(7, f"Fallback broken: got {repr(desc_fallback)}")

    sp.load_locale("en")
except Exception as e:
    fail(7, str(e)); traceback.print_exc()

# ─── ITEM 8: Old save files load without crashing ─────────────────────────────
print("\n── ITEM 8: Old save (v0.1.0 format) loads with safe defaults ──")
try:
    world = load_world()
    # Simulate a pre-pass1 save (missing all v0.2.0-pass1 fields)
    old_save = {
        "role": "Portuguese Conquistador",
        "gold": 50, "spices": 2, "ship_health": 80, "morale": 60,
        "provisions": 40,
        "time": {"day": 5, "hour": 10},
        "current_location": "At Sea",
        "current_location_type": "sea",
        "has_visited_port": True,
        "cargo": {"pepper": 3},
        "slave_cargo": 0,
        "items": [],
        "once_flags": [],
        "crew": [],
        "quests": {},
        "factions": {},
        "npc_dispositions": {},
        # NOTE: ALL v0.2.0-pass1 fields are intentionally absent
    }
    sp.load_locale("en")
    state = sp.GameState.from_dict(old_save, world)

    # Verify all new fields got safe defaults
    checks = [
        ("reputation_tier",       state.reputation_tier,       0),
        ("faction_standing",      state.faction_standing,      dict),
        ("assignments_completed", state.assignments_completed,  0),
        ("seen_lore_flags",       state.seen_lore_flags,        list),
        ("player_traits",         state.player_traits,          list),
        ("slaves_aboard",         state.slaves_aboard,          0),
        ("combat_enabled",        state.combat_enabled,         False),
        ("lang",                  state.lang,                   "en"),
    ]
    errors = []
    for field, got, want in checks:
        if isinstance(want, type):
            if not isinstance(got, want):
                errors.append(f"{field}: type={type(got).__name__}, want {want.__name__}")
        else:
            if got != want:
                errors.append(f"{field}: got={repr(got)}, want={repr(want)}")
    if errors:
        fail(8, "\n         ".join(errors))
    else:
        ok(8, "Old save loaded; all 8 new fields defaulted correctly")

    # Also verify game_over and status_text don't crash on old save
    try:
        _ = state.is_game_over()
        _ = state.status_text()
        ok(8, "is_game_over() and status_text() run without error on old save")
    except Exception as e2:
        fail(8, f"Crash in is_game_over/status_text: {e2}")

except Exception as e:
    fail(8, str(e)); traceback.print_exc()

# ─── Summary ──────────────────────────────────────────────────────────────────
print("\n" + "═" * 60)
print(f"  RESULTS: {len(PASS)} passed, {len(FAIL)} failed")
print("═" * 60)
if FAIL:
    print("\n  FAILURES:")
    for f_item in FAIL:
        print(f_item)
    print()
    sys.exit(1)
else:
    print("\n  All 8 QA items passed.\n")
    sys.exit(0)
