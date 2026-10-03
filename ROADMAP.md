# Roadmap

## North star

**A living fictional country that runs on classical AI — where you build a career inside politics the world generates itself.**

You have the main role: the game loop is driven by your actions — what you campaign on, who you court, when you strike. The world stays alive around you (elections, coalitions, schisms, realignments run on their own logic), but the game is *played*, not watched — auto-play exists only to observe and tune the simulation, not as the intended experience. Three pillars, equal weight: the career climb (backbencher to PM), the emergent drama (betrayals and collapses nobody scripted), and strategic depth (whipping and kingmaking against worthy opponents). A run succeeds when the world does something unscripted, it mattered to your career, and the why traces to legible algorithmic causes — not a scripted twist, not an LLM, not a dice roll.

Constraints: classical AI only, local, deterministic by seed, self-consistent without a player. Audience: me. Out of scope forever: LLMs, real-world data, multiplayer, online services.

**Market context** (Oct 2026): emergent politics sims exist — UK Politics Simulator (20k NPC career sim, closed commercial), Lawmaker (modelled voters, but multiplayer), Democracy 3/4 (bloc voters, you are the government not a career MP), Absolute Majority (LLM-driven). The gap this occupies: fully *local* + *deterministic* + *legible* + open code, and parties that genuinely form, split, and die.

## Phases

Phases are ordered by dependency and player-facing value, not chronology guarantees. Each phase lists why it exists and what "done" looks like. Anything listed here is a candidate — nothing is committed until it survives a "does the game need this?" pass.

## Phase 1 — Playable core (built)

The spec implemented end to end. Terminal driver, all checks green, 10 commits on `main`.

- [x] Seeded worldgen: 120 FPTP districts, ~10k voter agents in 2D ideology space, ~120 MP agents
- [x] Elections: spatial voter scoring, turnout, incumbency, polls
- [x] Parliament: weekly bills, per-MP vote utility with named terms, party whips
- [x] Government: coalition formation, confidence votes, term ends -> next election
- [x] Dynamic parties: cohesion tracking, defections, schisms, dissolution
- [x] Player layer: 2 actions/week, career (portfolios, leadership challenges, expulsion), hidden stats, scoring
- [x] Terminal driver + inspector (`inspect <mp_id>`, `why`)

Known gap to keep an eye on: governments lean too stable (median survival = full term). Tune `params.py` if playtests feel calm.

## Phase 2 — See the simulation (built)

The terminal prints text; the game *thinks* in geometry and networks. This phase made the invisible visible. Driver-only work — the sim core is untouched (that was the point of the architecture).

- [x] **Pygame driver** (`driver/pyg.py` + `pyg_render.py`) — real window, replacing the planned Textual step: we went straight to graphics.
- [x] **Hemicycle seat chart** — parliament as an arc of colored dots, parties sorted left-to-right by platform, coalition members tagged, player ringed, PM crowned.
- [x] **Ideology map** — sampled voter point cloud, party platform markers, MP dots; Tab to toggle.
- [x] **District map** — 12x10 grid colored by seat holder, brightness = margin, player district ringed.
- [x] **Hybrid time** — auto-run weeks (1.5s, speeds 0.5–4x), interrupt banners hard-pause, weekly action panel with click-to-target MPs, click any seat to inspect, `why?` overlay explains the last vote term-by-term.
- [x] **Election reveal** — districts resolve one by one on the map when an election lands.
- [x] **Event chronicle** — C opens a scrollable full-history overlay with week stamps and per-type filter buttons; A toggles auto-play so the sim runs hands-free.

Done when met: a coalition collapse is *watchable* — vote cascade, banner pause, party colors rearranging.

## Phase 3 — The country deepens

The north star says the world is the star — so the next phase is everything that makes the country feel alive *without the player touching it*. Auto-play should already be worth watching at the end of this phase.

- [x] **AI careers** — done (P3.1): MPs age and accrue seniority, retire past ~55 (hazard ramps at 70), seats sit vacant until the next general election, party-leader and PM succession fire automatically, portfolios weight seniority, and a ~120-strong hopefuls pool ages into eligibility — young newcomers win their first seats via elections (`Retired`, `Newcomer`, `Promoted` events). Deferred on purpose: by-elections (revisit during scandal-lifecycle, when vacancies get frequent).
- [x] **Factions inside parties** — done (P3.3): wings detected on intra-party spread, named from ideology (`Union Labour-right`), whip their own line on distant bills (`fwhip` term, `FactionRebels` events), and secede as a bloc after sustained estrangement — replacing the ad-hoc schism path. MPs drift toward their district centroids (constituency pull), which is what makes wings emerge and move in unscripted play.
- [x] **Scandal lifecycle** — done (P3.2): dossiers are a four-stage arc for every MP — latent growth ∝ (1−integrity), probabilistic surfacing (leak rate ×3 inside the six-week election window — the October-surprise mechanic), a 3–6-week burn bleeding party brand and district betrayal, then resignation (real vacancy via `remove_mp`) or weathering (dossier scar + permanent brand scar). Past `SACK_THRESHOLD` leaders expel members outright; ministers get `MinisterSacked` or defended at doubled brand bleed. The player burns in the same lifecycle — the old instant expulsion trapdoor is gone (`ScandalBreaks`, `Expelled`, `Resigned`, `MinisterSacked`, `ScandalWeathered` events; dossier + BURNING now shown on the inspect card). Deferred on purpose: scandal effects in vote utility, timed dirt releases (Phase 4 "scandal as a weapon"), dossier decay — past dirt stays dangerous.
- [x] **Media layer** — done (P3.4): 3–4 generated outlets (editorial slant, reach, sensationalism, a guaranteed centrist) each lead with their most newsworthy story weekly — tabloids and broadsheets cover different weeks. Framing moves `brand` (hostile coverage amplifies damage, friendly damps) and `pub_pos` — the party's *perceived* position, which voters now score instead of the platform (candidate blend + `brand` finally a live voter term; both bounded and mean-reverting). Agenda-setting pushes axis salience into ideologically-affine audiences — echo chambers emerge free. `Headline` per week (silent on slow weeks), `PressCycle` interrupts multi-week frenzies; the inspect card shows the seen-vs-platform gap. Deferred on purpose: per-voter perception, fabricated stories, biased polls, outlet-routed dirt (Phase 4 Press relations).
- [x] **Country conditions** — done (P3.5): five national indicators (growth, unemployment, inflation, services, crime) drift mean-reverting with pairwise couplings and rare `Shock` events the press covers. Passed bills enter a **law registry** (`Law` records — name, position, margin, persistent weekly effect with diminishing returns near bounds) so legislation leaves marks on the country. `mood` (deviations from baseline) drives retrospective voting — a named `retro` term in both voter scorers, weighted by *clarity of responsibility* (PM's party takes the big share, juniors split the rest) — and on confidence bills, where coalition MPs defect measurably more in a slump (18 vs 1 defections in the engineered test). `LawEnacted`/`Shock` events; the inspect card shows indicators + mood. Deferred on purpose: treasury (revenue reads indicators), portfolio→indicator ministerial blame, repeal/strikes on the registry, mood→salience priming.
- [ ] **The treasury** — money that constrains legislation. `Bill.cost` is a dead field today; give the government a treasury: weekly revenue ∝ growth + employment (indicators feed it), bills spend from it, deficits accumulate debt → inflation drag, insolvency → crisis events (forced confidence vote, brand collapse). One number plus flows — a constraint, not a spreadsheet; a sector/trade/monetary web would bury legibility. Depends on country-conditions; the player-facing half is Phase 4 "Budget power".
- [ ] **Procedural parties and naming** — the same five parties every run contradicts the north star. Generate the starting party pool per seed (3–7 parties, spread platforms, generated names), ideology-flavored names for schism/founded parties, a bigger MP name library (the hopefuls pipeline churns through the current 340-combo pool), and *named bills*: bill position → policy-domain name pools ("Housing Regeneration Act", not "a bill at (+0.63, -0.21)") so the chronicle reads like political history. One naming utility serves all of it. Each run should be a genuinely different country. Ground the generators in real structure: platforms anchored on generated *cleavage lines* (Lipset–Rokkan — class, center–periphery, urban–rural) rather than random points, so parties represent constituencies, and names drawn from real party families (social democratic, liberal, agrarian, nationalist, green). Include named poles for the ideology space — economic (redistribution ↔ market) and GAL–TAN (libertarian ↔ authoritarian) — so map labels, faction wings, and inspect cards speak political science instead of coordinates.
- [ ] **Independent MPs** — `MP.party` already allows `None`; add party-less candidates to FPTP so independents can win seats without founding one-person parties. The payoff is minority-government drama: a lone independent holding the balance of power. Design note: FPTP with no strategic voting keeps fragmentation artificially high — that's a deliberate anti-Duverger choice for multiparty drama, not an oversight; revisit only if landslides get one-sided.
- [ ] **Abstention and attendance** — the house is not always full. Today every MP votes every week and `u > 0` forces a binary choice. Add the real third state: torn MPs *abstain* (`|u|` below a margin — present but not voting, a weaker signal than defying the whip), and a weekly attendance roll — absenteeism rises in campaign season (MPs go home to fight their seats), during burning scandals, and late in careers. Consequence is the payoff: thin-majority governments can lose votes they should win, and a surprise Tuesday defeat is real parliamentary drama. Whip arithmetic stops being a formality — the substrate kingmaking and opposition play will exploit.
- [ ] **Ministerial performance** — portfolios generate outcomes (economy up/down, crises) that reflect on competence and feed approval. Right now a portfolio is a title; under the north star a bad minister should *matter* to the country. This is *valence* in poli-sci terms — the non-positional competence dimension voters reward regardless of ideology (same channel `brand` and `integrity` already use).
- [ ] **The judiciary** — a court that reviews laws in the registry: legibility-first judicial review where extreme/costly laws carry visible `legal_risk`, get challenged, and are struck down (removed, effect reversed) or upheld after a delay. Rare, cause-driven, never a dice roll — a government getting smacked down by the bench is emergent drama. Whole-law strikes only; provision-level granularity needs richer bill structure (deeper future). Depends on the law registry. The bench itself starts abstract — a political bench with appointed justices is Phase 4 (see Court appointments).
- [ ] **The constitution** — what judicial review reviews *against*: a short generated set of entrenched articles per seed (electoral rules, rights provisions, structural limits — term length, majority thresholds, minister eligibility). `legal_risk` stops being an abstract score and becomes "violates Article 4 — equal franchise": strikes cite their article, fully inspectable. A ceremonial Head of State could revive here as the constitution's guardian (refusing assent, calling elections on violations) — earlier deferred as decorative, this gives it a job. Amendment needs a supermajority; the rules of the game are themselves contestable. Depends on courts — it IS the court's object of review.
- [x] **Policy salience** — subsumed by the media layer (P3.4): agenda-setting IS outlets pushing `focus_axis` salience into their audiences, and `speech` already contests the agenda. Nothing left to build here beyond tuning.

Done when: a played term feels like you're inside a living country — and when you peek via auto-play, the chronicle confirms the world moved on its own logic, not around you.

## Phase 4 — Your career inside it

The three pillars made playable: climb, drama, strategy. These are player-facing systems layered on the now-living world.

- [ ] **Deals and favors** — logrolled votes: promise an MP your vote on their bill for theirs on yours. The relationships dict and favor mechanics are placeholders waiting for this. The core of strategic depth.
- [ ] **Cross the floor** — the player cannot defect or found a party: `_found` and secession walkers exclude `player_id`. "Found a party that outlives you" is impossible until this exists. Player defection via the same machinery (join another party, or walk out with whoever follows you), with real costs — your district's betrayal, burned relationships, and a party with your name on it that can also die.
- [ ] **Kingmaking** — `form_government` is automatic; the pillar promises kingmaking but nothing makes coalition formation player-facing. When your party holds the balance after an election, *you* choose who governs — trade portfolios and policy concessions for your support, or deny everyone and force a minority. The single highest-leverage decision in the game and it's currently a spectator moment. Real coalition science applies to both the player UI and the AI logic: minimal winning and *connected* coalitions (Riker/Axelrod — ideologically adjacent partners, not grab-bags), and portfolio allocation ∝ seats contributed (Gamson's Law).
- [ ] **Vote your conscience** — the weekly division becomes a player decision. `resolve_vote` already takes `player_vote` (+1/−1/0) — wire it to an action: the whip calls, you vote yes, no, or abstain. Defying the whip costs relationships and party standing; abstaining is the readable middle signal, not a dodge. The payoff lands on the mechanics built below: in thin divisions your vote actually swings outcomes — on ordinary bills, on confidence, on your own legislation.
- [ ] **Opposition role** — today the player mostly matters in government. Shadow scrutiny, amendment attacks, coordinated rebellion — being out of power should be a playable position, not dead time. Includes the deferred whip-breaking term from the scandal spec: MPs with an active scandal distance themselves from the party line (a named `selfpreservation` vote term, not folded into whip blindly), so a burning backbencher can be *counted* against their own whip — rebellion with a legible cause.
- [ ] **Budget power** — the PM tables the annual budget as a bill parliament votes on: revenue (tax posture) vs spending (services voters feel vs debt the treasury counts). Opposition can vote the budget down — losing supply is a constitutional crisis, not just a failed bill. The player's tradeoffs are real because the treasury is real. Depends on the Phase 3 treasury.
- [ ] **Legislative legacy** — the law registry made playable: revive a bill that failed (re-table with a cooldown, whip harder this time), repeal or amend laws in force — AI governments do it on their own logic, the player does it as leader. Opposition repealing your flagship law mid-term is exactly the drama the north star wants; defending your record is a career stake beyond seat safety. At the apex: constitutional amendment bills — supermajority to change the rules themselves, entrenching your own advantage or undoing a rival's.
- [ ] **Scandal as a weapon** — dig_dirt currently produces dossiers mechanically. Timing releases, trading silence, deciding when your own dirt is survivable.
- [ ] **Court appointments** — the bench made political: judicial vacancies are filled by the PM, justices age and retire through the same lifecycle machinery as MPs (the `remove_mp` pattern reused), and the bench's ideological lean shades `legal_risk` resolution — a court you packed keeps ruling on laws after your term ends. Institutional capture as legacy: legible (bench composition is inspectable), slow (vacancies are rare), and the opposition inherits or suffers your appointments. Depends on the Phase 3 judiciary existing first.
- [ ] **Press relations** — the outlet landscape made playable: choose which outlet gets your dirt (a friendly paper buries the story, a hostile one leads with it), court editorial boards for friendlier coverage, and read polls through their publishers — biased samples mean a friendly poll can flatter you. AI parties court outlets on their own logic; hostile outlets become a career threat to manage. At the far end: **acquire the outlet outright** — ownership bends its slant toward the owner. Caveat: there is no money in the game, so the price is paid in favors/influence (ties to Deals and favors) unless an economy ever exists; AI barons owning outlets is the world-side half. Stretch (needs a truth layer): fabricated stories.
- [ ] **Goals beyond score** — optional arcs layered on the open-ended career (win a majority as PM, found a party that outlives you, survive N terms) — roguelike structure without a fixed ending.
- [ ] **Save/load** — `GameState` is a dataclass tree; serialize to JSON. Cheap because determinism was designed in.
- [ ] **Difficulty and scenarios** — starting situations (safe seat vs marginal, incumbent vs opposition), `params.py` profiles. Constitutional variants too: constructive no-confidence (German model — must name a successor to topple the government) as a stability knob, and alternative district magnitudes.
- [ ] **Balance pass** — playtest-driven tuning of `params.py`, informed by actually watching the sim run.

Done when: you choose to act most weeks — not because the game demands input, but because the world gave you something to exploit.

## Phase 5 — Watchability and reach (optional)

The world is already watchable; this is presentation depth and sharing.

- [ ] **Better writing** — event text from a larger template pool with named actors, so the chronicle reads like political history instead of status lines.
- [ ] **Election night mode** — districts resolve with projections and swing callouts during the reveal. The sim computes per-district; this is dramaturgy.
- [ ] **Spectator/analysis mode** — headless auto-play with visualizations, for tuning and for watching the machine grind.
- [ ] **Driver polish** — fullscreen mode, and a pass over whether every essential view is reachable without hunting (chronicle, why-overlay, map, action panel). As new Phase 3 systems land, their info needs a home too.
- [ ] **Web driver** — same `tick()` contract, browser rendering. Enables sharing seeds and runs — only if "just me" ever widens.

## Explicitly not on the roadmap

- **LLM-generated anything** — the game's identity is classical AI. Dialogue and events stay algorithmic.
- **Real-world political data** — fictional country is a feature.
- **Multiplayer** — the MP-agent layer is the opponent.
