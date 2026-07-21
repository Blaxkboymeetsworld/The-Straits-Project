# The Straits Project

A historical text-based RPG set in Southeast Asia and the Indian Ocean during the Age of Discovery. Year 1 = 1511. The game spans 15 years.

Tone: loosely historical, CK2-style human drama, whimsy and absurdity alongside genuine stakes. Every character has a reason for what they do. The world changes around you whether you participate or not.

---

## Three Protagonists

| Character | Role | Starting Position | Home Port |
|---|---|---|---|
| Tomé de Faro | Portuguese Conquistador | Indian Ocean, SE of Calicut | Goa Harbor |
| Mehmed Bey | Ottoman Trader | Arabian Sea, departing Hormuz | Aden Harbor |
| Chen Mingzhi | Chinese Trader | South China Sea, S of Quanzhou | Quanzhou |

Each character has a unique opening scene, crew, faction relationships, and role-specific quest variants. The same world events (Fall of Malacca, Fall of Mamluks, etc.) play out differently depending on who you are.

---

## File Structure

```
straits_project.py      — Main game loop, world events, port/sea menus
quests.py               — QuestManager, ActiveQuest, quest board UI
faction.py              — Faction definitions, reputation tiers, port→faction map
time_system.py          — Day/night cycle, travel times, TRAVEL_TIMES dict
economy.py              — Trade, haggling, price fluctuations
crew.py                 — CrewManager, traits, occupations, recruitment
systems.py              — roll_check(), dialogue_exchange(), Ibu Malam, lore fragments
combat.py               — Naval combat, personal combat, bodyguard intercept

data/
  quests.json           — All quest definitions (array of quest objects)
  world.json            — Ports (major_ports + villages), rulers, goods, prices
  events.json           — Random event pools (sea, harbor, village, special)
  routes.json           — Travel days + waterway descriptions between port pairs
  crew_data.json        — Occupations, traits, archetypes
  npc_knowledge.json    — NPC dialogue topics and responses
  lang_en.json          — English UI strings
  lang_es.json          — Spanish UI strings

docs/
  world_bible.md        — Canonical port reference, faction overview, trade goods
  narrative_style_guide.md — Tone, register, period vocabulary, what to avoid
  game_timeline.md      — 15-year historical calendar, world events by year
  source_synthesis.md   — All 7 source texts, cross-source conflicts resolved
  encounter_geography.md — Port-by-port encounter types and plausibility
  character_bibles/     — 13 named character files (see below)
```

---

## Key Systems

**Travel** — `time_system.py` / `TRAVEL_TIMES` dict. Port name strings must match exactly. Missing routes fall back to `DEFAULT_TRAVEL_TIME = 6` days. Add new routes to both `TRAVEL_TIMES` and `data/routes.json`.

**Quests** — defined in `data/quests.json`. Loaded by `quests.py`. Gated by `quest_tier` vs `state.reputation_tier`. Three-character siege quests use `requires_role` field (not yet enforced in code — see TO DO). Quest flow: available → accepted → contact_found → return to giver → complete.

**Factions** — `faction.py`. Six factions, 5 positive / 5 negative tiers. Culture-specific tier-4 names (Sahabat, Homem de confiança, Rafiq, Zhiji). Port→faction mapping in `PORT_FACTION` dict. Reputation shifts on quest complete/fail.

**World Events** — `_check_world_events()` in `straits_project.py`. Fires by day/year. All have role-variant text. Current events: Fall of Malacca (Year 1, days 1–90 phased), Albuquerque's Death (Year 5), Fall of Mamluks (Year 6). Each sets `once_flags` to prevent re-firing.

**Day/Night** — `TimeSystem` in `time_system.py`. Markets, officials, ship repair gated by hour. Port menu shows what is accessible. `press_enter()` uses `input()` — menu loops use `input("  > ").strip().upper()`.

---

## World Events Timeline

| Day / Year | Event | Effect |
|---|---|---|
| Day 1–30 | Fall of Malacca announcement | Role-variant scene, faction shifts |
| Day 30–45 | Malacca rumors (port visits, 50% chance) | Flavor text |
| Day 45–60 | Malacca formal announcement | Once-only scene, all roles |
| Day 75–90 | Malacca falls | Port control changes, price disruption |
| Year 5 | Albuquerque dies | Estado leadership gap |
| Year 6 | Fall of Mamluks | Ottoman rep +, Karimi network collapses |
| Year 15 | Bintan Raid | End-game, Malay faction dissolves |

---

## Ports

**Major Ports** (full menu: market, recruit, quests, weapons, repair, tavern):
Malacca Harbor, Goa Harbor, Calicut, Hormuz, Quanzhou, Aden Harbor, Bantam

**Villages** (limited menu):
Pulau Tioman, Patani, Ternate, Bali, Cham Coast

**Home port lockout**: locked until `state.assignments_completed >= 3`. Tagged `[LOCKED]` in travel list.

---

## Named Characters (Key)

| Character | Role | Port | Notes |
|---|---|---|---|
| Tomé de Faro | Protagonist | Goa | Portuguese captain |
| Camila de Faro | Crew / arc | — | Marriage arc Year 7 |
| Rui Brandão | Crew | — | Portuguese |
| Estêvão da Guiné | Crew | — | Luso-African; cultural hooks at every port |
| Mehmed Bey | Protagonist | Aden/Hormuz | Ottoman |
| Baraka | Crew | — | Morale system tied to slave freedom |
| Yusuf al-Halabi | Crew | — | Commercial anchor for Ottoman arc |
| Chen Mingzhi | Protagonist | Quanzhou | Chinese |
| Wei Chongde | Crew | — | Long reveal arc, fragments over 20–30 days |
| Old Liang | Crew | — | Chinese anchor |
| Ibu Malam | Recurring NPC | All ports | Non-interactive, appears at significant moments |
| Dom Afonso de Albuquerque | NPC | Goa | Active Years 1–4, dies Year 5 |
| Tun Mutahir | NPC | Malacca | Bendahara; disposition 50 |

Full character bibles in `docs/character_bibles/`.

---

## Quest Structure (data/quests.json)

Each quest object requires these fields:

```json
{
  "id": "q_unique_id",
  "title": "Display Title",
  "title_es": "Spanish Title",
  "giver_port": "Exact Port Name",
  "giver_name": "NPC Name",
  "giver_title": "NPC Title",
  "description": "English description text.",
  "description_es": "Spanish description text.",
  "target_port": "Exact Port Name",
  "target_character": "NPC Name or null",
  "time_limit_days": 10,
  "reward_gold": 50,
  "reward_disposition": 15,
  "reward_item": null,
  "failure_disposition": -15,
  "difficulty": "easy|moderate|hard",
  "quest_tier": 1,
  "lore": "Historical lore text (shown max 3 times).",
  "lore_es": "Spanish lore text."
}
```

Optional fields:
- `requires_role`: `"Portuguese Conquistador"` | `"Ottoman Trader"` | `"Chinese Trader"` — restricts quest to one protagonist (enforcement TO DO in `quests.py`)
- `available_from_day` / `available_to_day`: day-window gating (enforcement TO DO)

---

## TO DO (Known Open Items)

- [ ] `requires_role` field not yet enforced in `available_quests_at_port()` in `quests.py`
- [ ] `available_from_day` / `available_to_day` not yet enforced in quest availability
- [ ] Menu input guard: blank Enter in PowerShell bypasses menu selections
- [ ] Sailing destination picker: port name mismatch causing `DEFAULT_TRAVEL_TIME` fallback (all routes showing 5–7 days)
- [ ] Portuguese Day-1 fleet alert: pre-siege dispatch text for Tomé de Faro
- [ ] Hang Tuah event chain (stub exists, content not written)
- [ ] Wei Chongde reveal arc (fragments designed, full chain not implemented)

---

## Adding Content: Rules

**New quest** → add object to `data/quests.json`. Match port names exactly to `world.json`. Match `giver_name` to a named character or create a new minor NPC with title.

**New port** → add to `world.json` under `major_ports` or `villages`. Add routes to `data/routes.json` AND to `TRAVEL_TIMES` in `time_system.py`. Add to `PORT_FACTION` in `faction.py`.

**New world event** → write function `_world_event_name(state)` in `straits_project.py`. Add trigger condition to `_check_world_events()`. Use `state.once_flags` to prevent re-firing. Write role-variant text for all three protagonists.

**New NPC** → add to `data/npc_knowledge.json` with topics and responses. Connect via `npc_id` field on an event, or as a quest `target_character`.

**Never** rewrite existing working systems to add new content. Extend, don't replace.
