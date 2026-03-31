# The Straits Project — World Bible

This document maps the historical world of 1511–1526 onto the game's port system, faction framework, and economic logic. Everything here should be treated as canonical game-world fact unless overridden by a specific design decision.

---

## The Indian Ocean System

The world the player navigates is not a collection of independent ports. It is a single, interdependent trade system held together by two forces: monsoon winds and credit networks.

**The monsoon calendar governs everything.** The northeast monsoon (roughly November–March) carries ships from India and Arabia eastward to Malacca and beyond. The southwest monsoon (roughly May–September) carries them back. Ships from the Persian Gulf and Red Sea cannot reach Malacca in a single season — they must winter in Gujarat, which is why Gujarati merchants became the dominant carriers of western goods to Malacca. The Strait of Malacca itself has local winds that are less seasonal; the South China Sea above it has its own cycle.

**Credit networks replaced physical currency over most distances.** Gujarati and Hadrami merchants used *hundis* (letters of credit) across the ocean. A Malaccan merchant could purchase goods from a Gujarati ship captain with a letter redeemable in Cambay. This is why the destruction of trust (the Portuguese cartaz system, Albuquerque's seizures) was so devastating: it shattered the credit infrastructure that made long-distance trade possible.

---

## Malacca Harbor

**Historical date:** Conquered by Albuquerque, July–August 1511. The game's Year 1 (1511) opens immediately after the conquest.

**Geographic situation:** Located on the narrowest point of the Malacca Strait, where all traffic between the Indian Ocean and the South China Sea must pass. No natural deep harbor — ships anchor in the roadstead. The town sits on a hill (Bukit Cina on the east bank, the main settlement on the west). The Malacca River divides the city; the bridge over it was the military key to the conquest.

**Portuguese fortress:** Built on the site of the great mosque, using stone from Malay tombstones and shells for lime. By 1512 it had two wells and artillery on all sides. It is the power center of the Portuguese Indian Ocean in the game.

**Population after conquest (Pires' account):** Mixed and recovering. Many merchants returned quickly because Malacca's geographic advantage is permanent. Gujaratis, Klings (Tamil merchants), Javanese, Malays, Chinese, Bengalis all present. The native Malay population was reduced; the conquered king (Sultan Mahmud) was at Bintan with a rump court. Portuguese soldiers and officials occupied the hill.

**Key social divisions:**
- *Casados* — married Portuguese settlers; the permanent colonial population
- *Soldados* — soldiers of the garrison
- *Cristãos novos* — converso (Jewish-origin) merchants and factors; present but liminal
- Kling merchants (Tamil Hindus/Muslims) — most commercially powerful after conquest; their leader Nina Chatu held the bendahara office until his death
- Chinese community — present since before the conquest; grew rapidly after Portuguese secured the strait
- Malay population — reduced but present; suspicious of the Portuguese; many ties to Sultan Mahmud in exile

**Trade goods flowing through Malacca (game-relevant):**
- East → West: cloves (Maluku), nutmeg and mace (Banda), sandalwood (Timor/Solor), camphor (Borneo), pepper (Sumatra/Banten), tin (Malayan peninsula), Chinese porcelain and silk, benzoin, gold
- West → East: cotton textiles (Gujarat, Coromandel), opium (Aden), horses (Arabia/Persia), coral (Mediterranean via Gujarat), copper (Arabian Peninsula), rose water, dyes

**Harbor master in game:** Hang Kassim — a Malay harbor official who survived the conquest by accommodating the Portuguese. His cooperation is calculated, not loyal; he supplies information to both sides. He knows the Malay community's mood and can warn of unrest.

**Tun Mutahir (Bendahara):** Historical figure; killed by Sultan Mahmud before the conquest. In the game he exists in the pre-conquest timeline (Years before game start) as a source of backstory and lore. NPCs who knew him speak of him with grief.

---

## Goa Harbor

**Historical date:** Conquered by Albuquerque, November 1510 (second capture; first was March 1510, then retaken by Bijapur, then reconquered).

**Geographic situation:** The island of Goa, split from the mainland by a river channel; excellent natural harbor on the Mandovi River. Portuguese headquarters for the Estado da India; the Governor (Viceroy from 1526) resides here.

**Political situation:** The Hindu population of Goa (Konkani-speaking) supported the Portuguese against the Muslim Bijapur Sultanate. Bijapur still controls the mainland around Goa and periodically threatens to retake it. The game should treat this threat as a constant low-level tension rather than open war during Years 1–5.

**Portuguese power center:** All cartazes (safe-passage licenses) are issued from Goa. Tribute from subordinate ports flows to Goa. The factor (treasury official) based here handles customs revenue from the entire Estado.

**Dom Afonso de Albuquerque:** Governor-General until his death in December 1515. In game Years 1–4, he is the supreme Portuguese authority; his death (Year 4/5 boundary) is a significant in-game event. He is in Goa or at sea, but his authority is felt everywhere.

**Ruler noted in world.json:** Dom Afonso de Albuquerque — with death note flagging his 1515 death as a turning point.

**Trade:** Goa is the main node for the Gujarat-Portugal axis. Horses from Arabia and Persia (via Hormuz) transit through Goa to the Vijayanagara empire and Deccan sultans; this horse trade is enormously profitable. Spices come in from Malacca; textiles go out from Gujarat.

**Harbor master:** Rodrigo Rabelo — a Portuguese casado (married settler) of mixed Goan descent; his mother was likely Konkani. He knows the street life of Goa and the unofficial trade that the official system ignores.

---

## Hormuz

**Geographic situation:** An island at the mouth of the Persian Gulf. Extreme aridity — no freshwater on the island. Water shipped from mainland (Nabandah/Bandar-e Khamir) or from the island of Qeshm. Heat so severe that merchants reportedly lived underground in summer.

**Political situation (1511):** Hormuz is a tributary state under Portuguese suzerainty after Albuquerque's campaign of 1507–1508. The Shah (Shah Salghur in game) is nominally sovereign but the Portuguese maintain a fortress and demand annual tribute of 15,000 xerafins. The real power historically was Cogeatar (Khoja Atar), who had the chancellery; by 1511 a new political equilibrium had been reached.

**Strategic significance:** Every ship traveling between India, Arabia, East Africa, and the Persian Gulf must pass through the Strait of Hormuz. Control here means leverage over Gulf trade: horses, pearls, dates, silk, and the luxury goods of Persia.

**Key goods:** Persian Gulf pearls (from the Bahrain banks, certified by the Shah's jeweler — as in quest q_hormuz_pearl_merchant); horses (sent to India); dates; silk from Persia; copper.

**Harbor master:** Abbas ibn Yusuf — a Hadrami Arab merchant who serves as harbor master under the Portuguese umbrella. His family has traded here for generations; he knows the Persian Gulf's politics and the Ottoman threat from Egypt/the Red Sea.

**Ottoman presence:** Mustafa al-Rumi (in game) is an Ottoman agent at Hormuz. Historically, Ottoman interest in the Indian Ocean intensified after the Mamluk defeat at Diu (1509) — the first Portuguese-Muslim naval engagement in the Gulf. The Ottomans were trying to establish a Red Sea fleet to counter the Portuguese; Hormuz was a key intelligence post. This becomes more significant in Years 5–6 (see game_timeline.md).

---

## Aden Harbor

**Geographic situation:** At the mouth of the Red Sea, on a volcanic peninsula. Natural harbor protected by cliffs; excellent strategic position. Commands all traffic between the Indian Ocean and the Red Sea/Mediterranean trade route.

**Political situation:** Aden was controlled by the Tahirid dynasty (a local Arab dynasty) in the early 16th century, under nominal Rasulid and then Mamluk suzerainty. The Ottomans were expanding into the Red Sea; Aden fell to Ottoman forces in 1538, but Ottoman pressure was felt earlier. In the game's timeline, Aden is independent but under threat.

**Trade significance:** Everything moving between the Indian Ocean and Egypt/Europe passed through Aden. The spice route: Malacca → Calicut → Aden → Cairo → Venice. Aden's harbor master collected dues on this entire flow. Albuquerque attempted to take Aden in 1513 and failed; the city was too strongly fortified.

**Key goods:** Coffee (already traded in small quantities); pepper (from Malabar and Malacca); opium; Arabian horses (going to India); textiles from Gujarat; gold and slaves from East Africa.

**Harbor master:** Ibrahim al-Yamani — a Yemeni Arab. His loyalties are local: he serves the Tahirid governor but has his own relationships with Hadrami and Egyptian merchants.

**Tahirid Governor:** Amir Salim al-Tahiri — the game's political power at Aden. He holds a precarious position: the Mamluks are weakening, the Ottomans are expanding, and the Portuguese are threatening from the sea. He needs intelligence and may use the player as an unofficial channel.

**Hadrami network:** The Hadhramaut (southern Yemen coast) produced a diaspora of Muslim merchants who spread across the Indian Ocean from East Africa to Malacca. The game's hadrami_figure contacts at Hormuz and Aden are part of this network: long-established, multilingual, with relationships across the entire system.

---

## Calicut

**Geographic situation:** The dominant pepper port of the Malabar (Kerala) coast. No natural harbor — ships anchor in the roadstead and use small boats (tongues). The beach landing is dangerous in the wrong season.

**Political situation:** The Zamorin (Samuthiri) of Calicut was the most powerful Hindu ruler on the Malabar coast and Albuquerque's most persistent enemy. Calicut had been the center of the Indian Ocean pepper trade for centuries; Portuguese attempts to monopolize pepper cut directly into the Zamorin's revenues. The Zamorin maintained a policy of war or near-war with the Portuguese throughout this period.

**In game Years 1–5:** The player can operate in Calicut but with Portuguese-faction penalties. The Zamorin's court is not inherently hostile to trade — just to Portuguese monopoly claims. A player with low Portuguese-faction or good Muslim-merchant relationships can navigate Calicut more freely.

**Key goods:** Pepper (Malabar's primary export); cardamom; rice; Indian textiles.

**Harbor master:** Koya Moopan — a Muslim Tamil merchant (Koya = honorific for senior Muslim trading families). The Koya Moopan tradition was the Zamorin's designated trading contact for Muslim merchants; Koya Moopan in the game is the man the Portuguese deliver cartazes to (quest q_goa_cartaz_delivery) and who provides intelligence.

**Zamorin:** Mana Vikraman — the ruling Zamorin. He is not a quest-giver in the game's current design but appears as a figure in NPC lore and knowledge entries.

---

## Bantam

**Geographic situation:** At the western tip of Java, commanding the Sunda Strait (the alternative route to the Malacca Strait). Not yet a major power in 1511 — Bantam's rise begins after the fall of the Hindu Sunda kingdom in the 1520s–1530s. In game Year 1 it is a secondary port.

**Political situation:** The Sunda Kingdom (Hindu) controls West Java. Islam is arriving from Demak and the north Java coast ports. The game's Bantam is at this cusp: the harbor master Raden Aria is a Muslim noble, but the hinterland is still Hindu Sundanese.

**Trade significance:** Bantam is the closest port to the Sunda Strait pepper-growing region. West Java pepper was an alternative to Malabar pepper. As Portuguese pressure on Malabar intensified, Bantam's importance grew.

**Key goods:** Pepper (primary); rice; timber; Javanese textiles.

**Political figures in game:** Maulana Hasanuddin (heir who becomes Sultan and defeats the Sunda kingdom), Sultan Hasanuddin (the future ruler), Maulana Yusuf (religious figure). These are historical figures whose rise is in the game's future (Years 5+).

---

## Quanzhou

**Geographic situation:** The major port of Fujian province, southern China. Not the capital of the Chinese state — Quanzhou's role was as the center of the overseas Chinese merchant community. By 1511 Quanzhou's official status had declined in favor of Guangzhou, but the Hokkien (Fujianese) diaspora that originated here was spread across Southeast Asia.

**Political situation:** Under the Ming Dynasty, which had banned private overseas trade (*haijin*). The Zheng He voyages (1405–1433) had ended; official Chinese presence in Southeast Asia was minimal. The Quanzhou merchants who appear in the game are operating outside the *haijin* prohibition, either through corruption or under the umbrella of Portuguese or Malay trade.

**The Chinese community at Quanzhou vs. abroad:** The game distinguishes between Quanzhou (the home port, official and restricted) and the overseas Chinese communities at places like Malacca, Bantam, and Patani. Abbot Mingzhi in the game represents the monastery-merchant hybrid common in Chinese coastal trade — temples served as storehouses and neutral meeting points.

**Harbor master:** Wu Liangchen — a Hokkien merchant who has obtained a position as harbor registrar. He navigates between official Ming prohibition and the practical reality that merchants will trade regardless.

**Prefect Chen Bao:** The official Chinese magistrate; he and Wu Liangchen have an uncomfortable mutual dependence.

---

## Secondary ports

**Patani:** A Muslim sultanate on the east coast of the Malay Peninsula (modern southern Thailand). During the 15th–16th centuries, Patani was a major alternative to Malacca after the conquest, particularly for Chinese traders seeking to avoid the Portuguese. Important for Chinese-Malay trade in game Years 3+.

**Ternate:** In the Maluku (Spice Islands). The origin of cloves. Sultan Baab Ullah's predecessors held clove monopoly rights. Portuguese established a presence at Ternate after Magellan's circumnavigation (1519–1521), building a fortress. In game Years 1–5, Ternate is a distant prize; the player may encounter Ternate goods but not visit the port directly in the base game.

**Pulau Tioman:** A small island off the Malay coast, used as a resupply and shelter stop on the South China Sea route. No significant political power; important as a waypoint. A "neutral ground" between Chinese and Malay maritime spheres.

---

## Faction overview

**Estado da India (Portuguese):** The official Portuguese empire in Asia. Goa is the capital; Malacca the eastern anchor. The cartaz system is their primary economic tool. Their military advantage is naval artillery; their disadvantage is small numbers and long supply lines. Albuquerque's death in 1515 creates a succession crisis.

**Muslim merchant network:** The informal alliance of Gujarati, Hadrami, and Tamil Muslim merchants who had dominated Indian Ocean trade before the Portuguese. After Malacca's fall they re-routed trade through Aden, Calicut, and Patani. Not a unified faction but a shared interest group.

**Javanese pates:** The north Java coastal cities (Demak, Gresik, Tuban, Surabaya) were Muslim and commercially powerful. They organized the armada that tried to retake Malacca (defeated 1511) and continued sponsoring piracy against Portuguese shipping. Java remains a hostile power throughout the game.

**Chinese imperial/merchant:** The Ming state officially prohibits private trade but cannot enforce it. The overseas Chinese community (Hokkien diaspora) operates commercially in Southeast Asia with tacit acceptance. Not a political faction in the game but a cultural-commercial network with enormous commercial weight.

**Malay sultans in exile:** Sultan Mahmud at Bintan; various Malay nobles scattered through the peninsula and Sumatra. They represent the displaced legitimate authority and can activate Malay loyalists against Portuguese Malacca. The ex-sultan's faction becomes increasingly relevant in Years 3–5.

---

## Economic logic of the game world

**Why goods are expensive:** Distance, risk, monsoon timing, and tolls. A sack of cloves is worth roughly ten times its Ternate price by the time it reaches Malacca; twenty times in Gujarat; forty times in Cairo.

**Why the Portuguese are hated:** They demand cartazes (tolls) on top of existing port duties. They seize non-licensed ships. Their fortress cannon can destroy any merchant vessel. They have upended century-old credit networks by establishing monopoly claims.

**Why merchants still come:** Malacca's geographic position is non-negotiable. The Strait cannot be avoided. The Portuguese have better artillery than anyone and (initially) a reputation for enforcing their own merchants' contracts fairly. Some merchants, like Nina Chatu, calculated that cooperation produced more profit than resistance.

**What the player can exploit:** Information asymmetry. The player can learn, through NPC knowledge queries, what goods are scarce at which ports, which factions are about to move, where Portuguese inspections are lax. Trade intelligence is as valuable as cargo.
