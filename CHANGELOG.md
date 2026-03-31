# The Straits Project — Changelog

All notable changes to this project will be documented here.
Format: [version] — Title — Date
Changes: Added / Changed / Fixed / Flagged (future)

---

## [v0.2.0-pass2] — Source Synthesis & World Bible — 2026-03-30

### Added
- `docs/source_synthesis.md` — structured entry for each of the 6 primary sources (2
  text-extractable PDFs read in full; 4 image-based PDFs synthesized from training
  knowledge). Includes cross-source conflict table and resolution policy.
- `docs/world_bible.md` — canonical world reference: all 8 ports, faction overview,
  trade goods, economic logic, and political context for 1511–1526.
- `docs/encounter_geography.md` — port-by-port encounter plausibility reference with
  population mix, historically grounded encounter types, monsoon notes, and
  implausibility warnings. Includes quick-reference matrix.
- `docs/narrative_style_guide.md` — tone, voice, and register guidelines; character-type
  dialogue registers; period-accurate vocabulary list; translation conventions for `_es`.
- `docs/game_timeline.md` — 15-year game calendar mapped to historical events; year-by-year
  world state; world events at Years 1, 3, 5, 6; notes on future development windows.
- `docs/character_bibles/` — 13 named character files: camila_de_sousa, rui_barbosa,
  estevao, diogo, tome (Portuguese); mehmed_al_rumi, kemal (Ottoman); yusuf, baraka
  (Arab/Swahili); chen_mingzhi, old_liang, ah_kow, wei_chongde (Chinese). Each file
  covers who they are, what they know, how they speak, historical grounding.

### Flagged
- Tesseract OCR binary not installed on Windows; 4 image-based PDFs (Malay Annals,
  Ma Huan, Marvels of India, Décadas da Ásia) were synthesized from training knowledge,
  not direct OCR. See source_synthesis.md for per-source notes.
- Hang Tuah gap: *Hikayat Hang Tuah* is not in sources/; any Hang Tuah supernatural
  content must be flagged as folklore rather than historical record.
- Commentaries Vol 1 covers only 1503–1507 (Part I); the Malacca campaign (1511) is in
  Vol 2 which is not in sources/. Noted in source_synthesis.md.

---

## [v0.2.0-pass1] — Foundations — 2026

### Fixed
- `harbor_master_for()` now correctly reads harbor master data from within
  `major_ports` entries rather than the empty `harbor_masters` array in
  `world.json`. `EventEngine._context_for_event()` updated to use this function.
  Harbor master name and fee now display correctly at all ports.

### Changed
- Role renamed: Arab Muslim Dāʿī → Ottoman Trader (name was already present in
  `world.json`; `choose_role()` menu, `GameState` branch updated throughout)
- Ottoman Trader starting stats adjusted: gold +20, spices +3, morale +8
  (previously: gold +0, spices +2, morale +10)

### Added
- Internationalization (i18n) system: `LOCALE` global, `load_locale(lang)`,
  `t(key)` translation helper in `straits_project.py`
- Language selection screen at startup (hardcoded bilingual prompt; all
  subsequent text uses the locale system)
- `data/lang_en.json` — full English locale for all structural UI strings
- `data/lang_es.json` — full Latin American Spanish locale (neutral register)
- Language stored in save file as `"lang": "en"` or `"lang": "es"` and
  restored automatically on load
- `EventEngine._resolve_event()` serves `description_es` / `text_es` when
  Spanish is active, falls back to English if the key is absent
- `EventEngine._apply_templating()` templates both `description`/`description_es`
  and `text`/`text_es` fields
- All event text fields in `events.json` carry `_es` parallel key with full
  Spanish translation (sea_events, harbor_events, village_events, special_events
  including role variants)
- All quest text fields in `quests.json` carry `title_es`, `description_es`,
  and `lore_es` keys (standard quests and full Mamluk arc)
- `GameState` expanded with new fields (all serialized; old saves load safely
  with sensible defaults): `reputation_tier`, `faction_standing`,
  `assignments_completed`, `seen_lore_flags`, `player_traits` (stub),
  `slaves_aboard`, `combat_enabled` (stub), `lang`
- TODO stub: combat system (v0.3) in `run_game()` at sea event resolution
- TODO stub: mini-games — Mahjong, Mancala, TBD (v0.4) in `tavern_menu()`
- TODO stub: player traits at character creation (v0.3) in `GameState.__init__()`
- `harbor_master_for(port_name, world)` utility function added

### Sources (PDFs in sources/ directory, not modified in this pass)
- Commentaries of Afonso de Albuquerque (Portuguese route)
- Décadas da Ásia — João de Barros (Estado politics) [Portuguese language]
- Yingya Shenglan — Ma Huan (Chinese route, Malacca at height)
- Kitāb ʿAjāʾib al-Hind — Buzurg ibn Shahriyar (Ottoman/Arab lore)
- Hikayat Hang Tuah (Malay NPC register, Hang Tuah chain)
- Suma Oriental — Tomé Pires (ground truth, all ports)

---

## [v0.3.0] — The Living World — 2026

### Added
- Goa Harbor added as major port with two minor factions:
  Konkani Merchant Network and Bijapur Remnant
- Goa temporal arc: raw Year 1, consolidating Year 2–4,
  Albuquerque death Year 5 world event
- Albuquerque death (Year 5, 1515) minor world event — all protagonists
- Ottoman Mamluk Arc: 7-quest sequential arc, Ottoman protagonist
  only, Years 4–7, includes off-map naval events resolving back
  to Southeast Asian faction consequences
- Fall of Mamluks world event: full scene for Mehmed,
  event marker for Tomé and Chen
- Karimi merchant network as minor faction (Aden/Hormuz),
  collapses Year 6
- Selman Reis as named NPC (Ottoman arc, Year 7)
- Mustafa al-Rumi expanded to Ottoman arc anchor character
- Price shift mechanic: Fall of Mamluks triggers Quanzhou
  pepper price change
- Chen Mingzhi single Mamluk-response quest (Prefect Chen Bao)
- Goa world.json entry with minor factions, temporal notes,
  Ibu Malam flag
- Text query system (Roadwarden-style): free-text input at
  named NPCs and port taverns; fuzzy keyword matching against
  npc_knowledge.json; reputation-gated responses; graceful
  fallback for unknown inputs
- npc_knowledge.json: knowledge base for all named NPCs
  covering people, places, prices, factions, rumors,
  historical events
- npc_knowledge.json: initial entries for all 7 harbor masters
  and named quest givers
- Text query fuzzy matching with alias system
- Disposition and reputation gates on NPC knowledge
- Graceful fallback responses for unknown queries
- Query prompt integrated into all named NPC interactions
  and port tavern scenes
- query.py: load_npc_knowledge(), text_query(), query_npc_menu(),
  speak_with_locals_menu(), tavern_query_menu()
- PORT_NPCS and TAVERN_NPC maps covering all 7 major ports
- Port action menu: option [N] "Speak with local figures"
- Tavern menu: option [5] "Ask someone a question (free-form)"

### Fixed
- v0.2.0 stress test failures (see test log)

### Flagged for Future (v0.4.0+)
- Carry forward all v0.2.0 flags
- Bintan raid world event (Year 15)
- Pati Unus assault on Malacca as witnessed event (Year 2)
- Sultan Mahmud's death at Kampar (late Year 15)
- Wei Chongde's child side quest (Year 7+)
- Mahjong, Mancala, Javanese dice game minigames

---

## [v0.2.0] — The Bones Update — March 2026

### Added
- CHANGELOG.md
- roll_check() unified probability system with trait/occupation modifiers
- Trait mutual exclusivity validation function
- New traits: zealot, prideful, oath_breaker, haunted, womanizer, xenophobic
- Zealot conflict event (low morale + opposing zealot = crew crisis)
- Zealot cooperation event (both worldly = interfaith_respect trait gained)
- Trait acquisition mechanic (only current in-game method)
- Haggling system: role/region weighted odds, crew culture intervention dialogue
- Travel time display with navigator modifier (+4-6 days penalty without one)
- Supplies system: provisions consumed at sea, cook reduces drain rate
- All crew occupations given mechanical hooks (no occupation is passive)
- Dialogue engine: language/diplomacy events now run multi-turn exchanges
- Quest lore throttle: lore text shown max 2-3 times globally then suppressed
- Faction reputation system: bidirectional, per-faction, 5 positive / 5 negative tiers
- Negative reputation consequences: cold port → barred → marked → hunted
- Sneak-in mechanic for barred ports (disguise / bribe / false flag / force)
- Named rival captains system (accumulate across game, remember prior encounters)
- Tiered quest hierarchy by faction reputation (tradesmen → guilds → nobility → rulers)
- 5-quest milestone dialogue per faction (senior NPC acknowledgment)
- Bodyguard/soldier protection system for negative reputation events (60% injury/death chance)
- Social class system with Southeast Asian titles (Orang Kaya, Temenggung, Laksamana, etc.)
- Protagonist naming: Tomé de Faro (Portuguese), Mehmed Bey (Ottoman), Chen Mingzhi (Chinese)
- Portuguese opening crew: Camila de Faro, Rui Brandão, Simão, Estêvão da Guiné
- Portuguese opening scene: "A Woman on My Ship" — 4 choices, branching outcomes
- Ottoman opening crew: Yusuf al-Halabi, Ibrahim, Baraka
- Ottoman opening scene: Mehmed and Baraka's first exchange at sea
- Chinese opening crew: Old Liang, Ah Kow, Wei Chongde
- Chinese opening scene: Wei's credentials — 4 choices, loyalty outcome set
- Slave market interactions: buy / free one / free all / ignore
- Prisoner mechanic: ransom (soldiers/warriors, tiered value) or enslave
- Baraka morale system: +5 per slave freed, unique dialogue
- Game timeline: 15-year arc, Year 1 = 1511
- Fall of Malacca world event: Year 1, all protagonists, optional participation
- Fall of Mamluks world event: Year 6 (1516-17), shifts Ottoman faction power
- Ottoman-Portuguese conflict pressure: late-game escalation
- Camila de Faro marriage arc: Year 7 (mid-game), NPC or disposition-based match
- Ibu Malam recurring figure: non-interactive, random ages (first appearance: old woman / first port)
- Urban legend / lore fragment pool: 10% trigger on sea travel, no options required
- Naval combat: abstracted, stat-driven, single-round decisions
- Personal/boarding combat: 3-round text exchange, weapon/trait-fed rolls
- Luso-African crew member Estêvão da Guiné: full dialogue hooks at each port culture
- Wei Chongde long-form reveal arc: fragments across 20-30 in-game days

### Flagged for Future Release (v0.3.0+)
- Wei Chongde's child side quest (mid-game, Year 7+)
- Mahjong minigame (Chinese ports)
- Mancala minigame (Aden, Hormuz, East African-adjacent ports)
- Javanese dice game (Bantam)
- Full ability/attribute system
- Camila's children as mid-game NPCs

---

## [v0.1.0] — First Playable Build — August 2025

### Added
- Core game loop (sail / travel / status / save / quit)
- JSON event engine (sea, harbor, village, special event pools)
- Role-specific event variants via requires and variants fields
- Pygame title screen with PNG background
- Three starting roles: Portuguese Conquistador, Ottoman Trader, Chinese Trader
- Save/load single slot
- world.json: 7 major ports, 3 villages
- events.json: ~35 events across all pools
- quests.json: 6 quests with lore, givers, targets, time limits
- crew_data.json: 15 occupations, 15 positive traits, 15 negative traits, 28 archetypes
