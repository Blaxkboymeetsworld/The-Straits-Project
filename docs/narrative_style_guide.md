# The Straits Project — Narrative Style Guide

This document establishes the tone, voice, register, and specific language practices for all text in *The Straits Project*. It applies to event descriptions, NPC dialogue, quest text, item descriptions, status messages, and all player-facing prose.

---

## Core register

**Elevated but not archaic.** The writing should feel like a well-researched historical novel from the literary end of the genre — Patrick O'Brian, or Hilary Mantel, or Derek Walcott's prose. Not like a Hollywood period film. Not like a textbook. Not like a fantasy game with pseudo-medieval flavoring.

**Precise rather than decorative.** The prose earns its complexity through accuracy and specificity. "A dhow low in the water with bales of Malabar pepper" is better than "a ship carrying exotic spices." Specificity creates world-texture; vagueness creates nothing.

**Morally observant, not morally instructive.** The text should notice moral weight — the violence of the cartaz system, the banality of the slave trade, the cruelty of a paranoid sultan — without telling the player how to feel about it. The events speak for themselves. The game's narrator does not editorialize.

---

## Narrative voice

### Events and descriptions

Events are written in third-person limited present tense, focused on what the player observes directly. The camera is at the player's position, not aerial.

**Example:**
> The harbormaster does not look at the letter. He tucks it under the pile on his left, where it will wait, and tells you the fee has increased since last season. He names a figure. His expression is that of a man who expects to be paid.

Not:
> The corrupt harbormaster demanded a bribe, showing how the Portuguese colonial system was oppressive.

### NPC dialogue (fallbacks and responses)

Direct speech. Present tense. Specific vocabulary appropriate to the character's cultural context. NPCs do not explain their world to the player; they speak from inside it.

**Good:**
> "Three days. The cartaz window is three days. After that I cannot help you." — harbor official

**Poor:**
> "As you may know, the Portuguese cartaz system requires ships to obtain permits. Unfortunately, the time for your permit has expired." — harbor official

The good example implies bureaucratic pressure without explaining the system. The poor example sounds like a tutorial.

### Quest text

Quest text is the one place where slightly more context is appropriate, since the player needs to understand what they are doing. Still: lean. One sentence of context, one sentence of task, one sentence of stakes.

**Example:**
> Tun Mutahir speaks carefully. A Gujarati merchant — one of his creditors — has vanished along with a shipment of tin. The merchant was last seen in Calicut. He does not ask you to make inquiries openly. He asks you to go to Calicut, find news of a man named Farid al-Surat, and return within the fortnight.

This gives: who's asking, what happened, where, what the task is, and the time pressure. No exposition about the political situation; the player learns that through lore.

### Lore text

Lore appears after events, in quest completion screens, and in NPC knowledge responses. It is the one place for historical depth. Still written in the same elevated register, not textbook style.

**Example:**
> The Indian Ocean trade in the early 16th century was sustained by credit networks between Gujarati merchants and local rulers. The disappearance of a factor was not merely personal — it could destabilize regional credit.

Two sentences. No footnotes. A window, not a lecture.

---

## Specific language practices

### Trade and commerce vocabulary

Use period-accurate terminology consistently:
- **cartaz** — not "permit" or "license"; this is the Portuguese term for their sea-toll document
- **factor** — not "agent" or "employee"; factors were the specific commercial agents of merchant houses
- **bahar** — the standard unit of weight for bulk trade goods (roughly 200 kg, but varying by port)
- **cruzado** — Portuguese gold coin; the standard of value for this world
- **xerafin** — Hormuz/Persian Gulf coin; widely circulated in the western Indian Ocean
- **calain/calaim** — Malaccan tin coin; petty transactions
- **proa** — outrigger canoe (generic Southeast Asian small vessel)
- **lanchara** — a large rowing vessel with sail (Portuguese term for the regional fast galley)
- **junk** — Chinese or Southeast Asian merchant vessel
- **nao** — Portuguese large sailing ship (caravel is smaller and earlier; nao is the type at Malacca)
- **fidalgo** — Portuguese noble; one with claims to gentle birth and honor
- **casado** — married Portuguese settler; distinct from temporary military personnel

Do not use:
- "ship" as a generic (specify by type when possible)
- "spices" as a vague category (specify: pepper, cloves, nutmeg, mace, cardamom, cinnamon)
- "Muslim" as a monolith (specify nationality and school where relevant: Gujarati Sunni, Hadrami, Shi'a Persian, etc.)

### Names and honorifics

Maintain the honorific systems of each culture in dialogue:
- **Portuguese:** Dom (noble male), Dona (noble female), Padre (priest), Frei (Franciscan friar). Common men have first name + father's surname or place-name.
- **Malay:** Tun (highest nobility), Raja (prince/ruler), Hang (warrior class), Daeng (Bugis noble). Do not use generic "Sultan" for non-sultans.
- **Arabic/Hadrami:** Shaykh (learned elder or tribal leader), Mawlana/Maulana (religious scholar), Said/Sayyid (descendant of the Prophet), Amir (commander). Ibn = "son of."
- **Chinese:** No honorific in casual address; formal address uses official title. Abbot for monastery heads. The Hokkien nickname prefix "Ah-" for familiar address of inferiors.
- **Tamil:** Koya (honorific for senior Muslim trading families in Malabar/Malacca). Moopan (elder/headman).

### Numbers and weights

- Spell out numbers under ten; use numerals from 10 upward in narrative prose
- In trade contexts, use the period-accurate measurement: "three bahars of pepper" not "600 kilograms"
- Money: "sixty cruzados" in narrative; can use numerals in game mechanics (60 cruzados)

### Violence and coercion

The game world is violent. Describe violence with economy — the act, the consequence, no lingering. The historical sources do this well: "he stabbed him three or four times and the man fell dead." That is the model.

Coercion (slavery, extortion, cartaz enforcement) should be described accurately without sanitizing or dwelling. The slave market at Malacca is a market: goods, prices, human beings treated as inventory. The text describes this as the characters in the world see it, which is to say, as normal. Player discomfort is appropriate; authorial horror is not appropriate.

---

## Language by character type

### Portuguese officials and soldiers

Formal, hierarchical. Rank matters. Orders are given; compliance is expected. When threatened, they invoke the King of Portugal, God, or both. When corrupt, they are businesslike about it — corruption here is systematic, not shameful.

Register: Formal period-English that implies Portuguese originals. Short declarative sentences when giving orders; longer constructions when justifying. Religious framing for violence and conquest.

> "The King of Portugal requires this harbor to be licensed. The fee is forty cruzados. You will pay now, or your vessel will be held for inspection."

### Malay nobles and officials

Indirect. Status-conscious. Everything passes through intermediaries; direct requests are rare. Emotional weight is carried by understatement. A compliment on your cargo means you are being considered for a transaction. An inquiry about your next port means you are being assessed.

Register: Courtly. Long clauses with subordinate qualifications. Silence and pause are meaningful. The kris is never mentioned directly — it is implied.

> "Your vessel is well-loaded, I see. And you plan to sail where, after Malacca? One wonders if Calicut is on your route. There is a man there who might find certain goods more interesting than the current price suggests."

### Arab/Hadrami merchants

Formal courtesy first, business after. Extensive indirect honorifics before arriving at the point. Religious framing (bismillah, inshallah, mashallah) is organic, not decorative. Negotiations are long; patience is expected.

Register: Elaborate courtesy; then precision about commercial terms. Do not rush to the point. The point arrives when the point arrives.

> "May God increase your prosperity. I see you have come from the east. The men of Malacca say the clove price holds firm. My cousin in Hormuz would pay well for a cargo certified by a trustworthy hand. Are you, perhaps, trustworthy?"

### Chinese merchants (Hokkien dialect culture)

Practical. Commercially acute. Direct in private; circumspect in public (because of the haijin prohibition). The monastery or temple is the neutral meeting ground. Relationships (guanxi) matter more than contracts.

Register: Economical. Few words. Numbers are precise. Concession is framed as favor. Obligation is implied, not stated.

> "Three months ago you carried a cargo for my cousin. He said nothing bad. This is better than saying something good. I have a proposal."

### Ottoman agents

Courtly, political. They are operating in a region where they are guests (or spies), so their manner is correct and slightly over-formal. They are gathering information under commercial cover; their questions are always slightly off-center from the topic they claim to be about.

Register: Formal courtesy; educated vocabulary (Persian and Arabic loanwords in their Turkish thinking); political awareness that surfaces despite the commercial cover.

> "A profitable season, yes? The Portuguese have many ships here. One wonders how many they have at Hormuz also. Purely an idle curiosity."

### East African / Swahili merchants

Confident navigators; connected to the Hadrami network but distinct from it. Their knowledge is the East African coast: what the wind is doing, where the water is good, which communities are safe to approach. They carry ivory, ambergris, gold dust, and occasionally slaves.

Register: Direct but unhurried. Navigation as moral authority — they know the sea; others need to catch up. Religious framing (Swahili Muslims) is present but worn lightly.

> "I have crossed to Hormuz eleven times. I know which way the wind goes in October. You do not. If you want to arrive before the pepper season ends, you will listen."

---

## What to avoid

### Period-inappropriate concepts
- "Colonialism" as a character's self-awareness (nobody used this word or concept; the Portuguese had different frameworks)
- "Racism" as an operative concept in this world (ethnicity mattered enormously, but through different categories than modern racial thinking)
- Anachronistic sympathy performances (characters do not apologize for slavery, do not express proto-abolitionist thoughts)
- Anachronistic disgust performances (Portuguese characters do not feel guilt about conquest; they feel pride, duty, and religious zeal)

### Tonal errors
- **Ironic detachment** — this is not a game that winks at the player about how bad historical things were
- **Romantic primitivism** — Southeast Asian or African characters are not noble savages; they are sophisticated people operating complex political economies
- **Orientalism** — the "mysterious East" framing; Malacca is mysterious to Portuguese characters, not to the reader
- **Melodrama** — emotional moments earn their weight through understatement, not intensity
- **Explained irony** — if something is ironic, show it; do not comment on it

### Generic fantasy vocabulary
- "Quest" does not appear in dialogue
- "Loot," "dungeon," "adventure" are anachronistic in this register
- Avoid any construction that would feel at home in a Tolkien-adjacent fantasy game

---

## Spanish/Latin American register (translation)

All text has parallel `_es` keys. The Spanish register should be:
- **Latin American Spanish**, not Castilian — this is a linguistic and cultural choice, not a geographic one; it avoids the period Castilian register that would feel archaic
- **Literary but accessible** — the same elevated-but-not-archaic quality as the English
- **Not anglicized** — do not translate English idioms directly; find the equivalent Spanish construction

Specific trade terms should be maintained in Spanish in their period-appropriate forms where they exist (e.g., *cartaz* is the same word; *cruzado* has a Spanish equivalent *cruzado* as well; *fidalgo* translates naturally).

The Spanish versions of honorifics: Don (noble male), Doña (noble female), Padre, Fray (Franciscan). Arabic honorifics remain in Arabic in Spanish text, as they would in the actual period.
