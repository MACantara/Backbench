# Roadmap

## North star

**A living fictional country that runs on classical AI — where you build a career inside politics the world generates itself.**

You have the main role: the game loop is driven by your actions — what you campaign on, who you court, when you strike. The world stays alive around you (elections, coalitions, schisms, realignments run on their own logic), but the game is *played*, not watched — auto-play exists only to observe and tune the simulation, not as the intended experience. Three pillars, equal weight: the career climb (backbencher to PM), the emergent drama (betrayals and collapses nobody scripted), and strategic depth (whipping and kingmaking against worthy opponents). A run succeeds when the world does something unscripted, it mattered to your career, and the why traces to legible algorithmic causes — not a scripted twist, not an LLM, not a dice roll.

Constraints: classical AI only, local, deterministic by seed, self-consistent without a player. Audience: me. Out of scope forever: LLMs, real-world data, multiplayer, online services.

**Market context** (Oct 2026): emergent politics sims exist — UK Politics Simulator (20k NPC career sim, closed commercial), Lawmaker (modelled voters, but multiplayer), Democracy 3/4 (bloc voters, you are the government not a career MP), Absolute Majority (LLM-driven). The gap this occupies: fully *local* + *deterministic* + *legible* + open code, and parties that genuinely form, split, and die.

## How this roadmap is organized

Two axes, deliberately separate:

- **Phases** (below) catalog subsystems — what exists and what could exist, grouped by theme. They are a map, not a queue.
- **Milestones** (next section) sequence the remaining work by player-facing value. The lesson of the 1100-week runs: the sim is deepening faster than the career is playable. World-side features that don't create new player decisions wait — more interacting systems just mean more chances for a quiet feedback loop to kill the country (observed: duopoly by week 300, 893 eternal laws, one-shot debt crisis).

Dependencies still rule: anything can be pulled forward when a milestone needs it (save/load is independent — take it the moment long sessions get annoying; event writing improves incrementally, not at the end).

### The feature gate

Nothing is committed until it survives a "does the game need this?" pass — now concrete. A proposed mechanic answers five questions:

1. What behavior does it introduce?
2. What can the player observe about it?
3. What can the player do in response?
4. What consequences can follow?
5. Can the player make meaningfully different decisions because it exists?

Can't answer 1–2: not ready. Can't answer 3–5: spectator complexity — the world gets richer while the game stays watched.

## Milestones

The build queue. Items live in the phase catalog, tagged `[M1]`–`[M6]`.

| # | Objective | Scope |
|---|-----------|-------|
| **M1 — Stable world** (done) | Long runs stay interesting | Fiscal escalation, invariant monitoring (below), first balance pass |
| **M2 — Playable career** (done) | Advancement is attainable and legible | Career ladder, appointment logic, "why wasn't I picked" |
| **M3 — Strategic politics** | The player moves parliamentary outcomes | Kingmaking, conscience votes, abstention/attendance, independents, deals & favors, decisive explanations |
| **M4 — Full political lifecycle** | Decisions have lasting consequences | Budget power, legislative legacy, opposition role, cross the floor, scandal as a weapon |
| **M5 — Institutional depth** | Institutions constrain and shape power | Constitution, court appointments, press relations |
| **M6 — Replayability & presentation** | Runs are replayable, inspectable, shareable | Save/load, scenarios, goals, better writing, election night, spectator mode |

Done-when, per milestone:

- **M1**: the invariant table holds across the 50-seed sweep; insolvency recurs instead of firing once and going silent.
- **M2**: an honest run can reach ministerial office — 1100 weeks, 23 terms, zero promotions is the failure being fixed.
- **M3**: a hung parliament hands the player a real negotiation, and a whipped division is a real decision with readable stakes.
- **M4**: an AI government can repeal the player's flagship law; losing supply is a crisis, not a footnote.
- **M5**: a `LawStruck` cites its article; a bench a PM packed keeps ruling after their term ends.
- **M6**: a seed plus a save file reproduces a run; the chronicle reads like political history.

M3's end-state is the vertical slice of the north star: build influence → negotiate → decide → consequences → advance or lose ground. Playtest that loop before opening M5.

## Long-run health

Interacting feedback loops fail one way: a channel runs away and the world dies quietly. The fix is measurement, not hope — these invariants get checked in `checks/check_sweep.py` across seeds and long runs:

| Area | Watch | Warning sign |
|------|-------|--------------|
| Party system | Viable parties over time; `PartyFormed`/`Secession`/`PartyDissolved` counts | Every seed converges to the same structure |
| Elections | Seat margins, turnover | Permanent landslides or frozen results |
| Government | Duration, confidence defeats, coalition churn | Never falls, or always falling |
| Economy | Debt, inflation, unemployment, growth | Indicators pinned at their bounds |
| Legislation | Laws in force, cumulative effects | Registry grows without bound; law effects dominate indicators |
| Careers | Promotions, defections, retirements, succession | The same small group holds office forever |
| Player | Offices held, decisions taken, outcomes | Survives but never advances |

The target is a *plausible* country that produces interesting decisions — not a realistic one. Don't tune statistics toward a real country; tune them toward drama with legible causes. And determinism is the debugging aid, not the goal: a reproducible sim can still reproducibly produce bad politics.

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
- [x] **The treasury** — done (P3.6): `Treasury.debt` is the one stock; weekly `flow = revenue − upkeep − interest` where revenue reads growth/unemployment, upkeep is every law in force (costs decay — programs normalize into baseline, the interim release valve until repeal/strikes exist), interest compounds. `Bill.cost` is real — generated ∝ extremity, printed on `BillTabled`/`LawEnacted`. The constraint is political: a named `fiscal` term makes parliaments stingy as `debt/DEBT_WARN` rises (expensive bills stall exactly when they should — 83→37 yes votes under debt in the fixture). `debt > DEBT_WARN` drags inflation; `debt > DEBT_CRISIS` fires `DebtCrisis` (brand hit + forced confidence, hysteresis re-arm) — governments can fall on the books. Also shipped inside this branch: the coalition-whip fix (junior partners whipped *against* their own government's bills — now bound to the program unless a bill breaks `COALITION_WHIP_TOL`) and `BILL_PERSUASION` re-tuned for the restored ~realistic pass rate. Deferred on purpose: player budget bills (P4), fiscal meaning of repeal/strikes, `MINORITY_GOVT_PENALTY` dead-constant cleanup.
- [x] **Procedural parties and naming** — the same five parties every run contradicts the north star. Generate the starting party pool per seed (3–7 parties, spread platforms, generated names), ideology-flavored names for schism/founded parties, a bigger MP name library (the hopefuls pipeline churns through the current 340-combo pool), and *named bills*: bill position → policy-domain name pools ("Housing Regeneration Act", not "a bill at (+0.63, -0.21)") so the chronicle reads like political history. One naming utility serves all of it. Each run should be a genuinely different country. Ground the generators in real structure: platforms anchored on generated *cleavage lines* (Lipset–Rokkan — class, center–periphery, urban–rural) rather than random points, so parties represent constituencies, and names drawn from real party families (social democratic, liberal, agrarian, nationalist, green). Include named poles for the ideology space — economic (redistribution ↔ market) and GAL–TAN (libertarian ↔ authoritarian) — so map labels, faction wings, and inspect cards speak political science instead of coordinates.
- [x] **Party-system dynamism** — the 1100-week observation that rewrites Phase 3: every seed converges to a **two-party duopoly by ~week 300 and never recovers**. The lifecycle has only a death channel (electoral wipeout → `PartyDissolved`); the birth channels never fire — `PartyFormed`=0, `Secession`=0 in 1100 weeks because the gates are unreachable (`stay_utility` floor ~0.64 vs the 0.2 founding threshold; intra-party spread 0.06–0.23 vs the 0.45 faction gate). A living country needs party *births*: niche-party entry around unserved ideological space (Meguid — new parties enter when mainstream parties vacate it), recalibrated founding/faction thresholds, and reconstitution after wipeouts. Without it, generated variety dies by mid-game and Duverger wins after all.
- [x] **Snap elections** — a government that falls (`ConfidenceLost`) currently just re-forms in place; `ElectionCalled` only ever fires on schedule, so elections are metronomes. A fallen government should dissolve parliament into an early campaign — collapse needs electoral consequence, not just reshuffling.
- [x] **Fiscal escalation** `[M1]` — done (M1): insolvency is a state, not an event. `Treasury.last_crisis_week` + `crises` replace `crisis_armed`; while `debt > DEBT_CRISIS` a `DebtCrisis` re-fires every `DEBT_CRISIS_EVERY` weeks (brand hit + forced confidence — each repeat another chance to fall), persisting across governments, and a real solvency exit below `DEBT_WARN` re-arms the meter so relapse fires promptly. Receivership captures the agenda: insolvent governments table only **austerity bills** (negative cost, market-ward, services-cutting — the fiscal vote term makes them attractive exactly when the whip fights them); passing cuts pays debt down, failing leaves the spiral running. Fixture: crises recur through collapse→campaign→re-formation; a passed cuts law measurably relieves flow.
- [ ] **Independent MPs** `[M3]` — `MP.party` already allows `None`; add party-less candidates to FPTP so independents can win seats without founding one-person parties. The payoff is minority-government drama: a lone independent holding the balance of power. Design note: FPTP with no strategic voting keeps fragmentation artificially high — that's a deliberate anti-Duverger choice for multiparty drama, not an oversight; revisit only if landslides get one-sided.
- [ ] **Abstention and attendance** `[M3]` — the house is not always full. Today every MP votes every week and `u > 0` forces a binary choice. Add the real third state: torn MPs *abstain* (`|u|` below a margin — present but not voting, a weaker signal than defying the whip), and a weekly attendance roll — absenteeism rises in campaign season (MPs go home to fight their seats), during burning scandals, and late in careers. Consequence is the payoff: thin-majority governments can lose votes they should win, and a surprise Tuesday defeat is real parliamentary drama. A **quorum** rides on top as a thin rule — below ~half the house present, a division can't stand and the business stalls a week: mostly a formality, dramatic only when attendance craters (scandal weeks, election season), which is exactly when the mechanic earns it. Whip arithmetic stops being a formality — the substrate kingmaking and opposition play will exploit.
- [x] **Ministerial performance** — done (P3): portfolios are a data table (`PORTFOLIO_INDICATOR`: Finance→growth, Labour→unemployment, Interior→crime, Health→services, Foreign→inflation) — Justice became Labour since no justice dial exists, and the table appends rows for Phase 4 (patronage posts, bigger cabinets, party-flavored ministries). Weekly, each minister pushes their indicator by `(competence − 0.5) × PORTFOLIO_EFFECT` — above-average ministers help, duds visibly erode their dial — while `MP.perf` accumulates the actual on-watch delta (decayed, recency rules) and `portfolio_weeks` counts tenure. Past `MINISTER_TENURE`, a record below `MINISTER_SACK_RECORD` gets `MinisterSacked reason="performance"` plus a brand hit on the PM's party; `Government.sacked` bars re-hires until the next election (scandal-sacked join the same set), and *any* dark chair — sack, scandal, defection, retirement — is refilled same-week by the seat-weighted queue (`Promoted reason="reshuffle"`). Competence flows into the existing `mood → retrospective` channel: appointment → indicator → mood → voter judgment. Check: 21 performance sackings / 33 same-week refills over 4 seeds, competence 0.95 vs 0.05 diverges growth.
- [x] **The judiciary** — done (P3): `legal_risk(law)` is a legible derived score (extremity + cost + thin margin, stamped on `LawEnacted`) and the courts are the venue for losers — weekly, the most hostile *opposition* party drags the riskiest unchallenged statute into a capped docket (`ReviewOpened`), where it sits `REVIEW_WEEKS` in force before a verdict. Verdicts are a rule, never a roll: per-seed `court_activism` sets the strike line, so the same statute falls on an activist world and stands on a deferential one. `LawStruck` removes the `Law` — effect *and* upkeep stop the same week — and bleeds the **authoring** parties (`law.enacted_by`), even after they've left office; `LawUpheld` confers immunity (res judicata — one challenge per law ever). Observed cadence: 54 challenges / 16 strikes / 36 upheld over 4×250 weeks — smackdowns stay rare drama. Deferred on purpose: constitutional articles as the review object (next module), injunctions, player-filed suits, provision-level strikes. The bench itself starts abstract — a political bench with appointed justices is Phase 4 (see Court appointments).
- [ ] **The constitution** `[M5]` — what judicial review reviews *against*: a short generated set of entrenched articles per seed (electoral rules, rights provisions, structural limits — term length, majority thresholds, minister eligibility). `legal_risk` stops being an abstract score and becomes "violates Article 4 — equal franchise": strikes cite their article, fully inspectable. A ceremonial Head of State could revive here as the constitution's guardian (refusing assent, calling elections on violations) — earlier deferred as decorative, this gives it a job. Amendment needs a supermajority; the rules of the game are themselves contestable. Depends on courts — it IS the court's object of review.
- [x] **Policy salience** — subsumed by the media layer (P3.4): agenda-setting IS outlets pushing `focus_axis` salience into their audiences, and `speech` already contests the agenda. Nothing left to build here beyond tuning.

Done when: a played term feels like you're inside a living country — and when you peek via auto-play, the chronicle confirms the world moved on its own logic, not around you.

## Phase 4 — Your career inside it

The three pillars made playable: climb, drama, strategy. These are player-facing systems layered on the now-living world. Ordered by milestone — the career ladder leads because 23 terms of zero promotions means the climb pillar is hollow, and kingmaking leads M3 because the single highest-leverage decision in the game is currently a spectator moment.

- [x] **Career ladder** `[M2]` — done (M2): the climb is a strategic problem now. `MP.standing` is the movable currency — whip fidelity in `resolve_vote`, the `constituency` action, and office trickles earn it; sacks, rebellions, and burning scandal weeks burn it; it decays. Per-party junior posts (`JUNIOR_POSTS` — Whip/Spokesperson/Committee Chair) exist in **opposition parties too**, refilled same-week in-session; promotion to cabinet vacates a rung and someone climbs. `_appoint` is decomposed into named `appointment_terms` — `record`/`standing`/`backing`/`seniority`/`rung` — scored identically for AI, with `backing` reading the appointer's view of the candidate (lobby and scheme pay into the climb). Legibility: `Promoted` carries winner terms, a losing player gets a passed-over `CareerEvent` with rank and deciding terms, and `explain_mp` shows the cabinet-candidacy rank. Check: `check_ladder.py` — scripted climber reaches cabinet 6/8 seeds vs passive 1/8.
- [ ] **Kingmaking** `[M3]` — `form_government` is automatic; the pillar promises kingmaking but nothing makes coalition formation player-facing. When your party holds the balance after an election, *you* choose who governs — trade portfolios and policy concessions for your support, or deny everyone and force a minority. The single highest-leverage decision in the game and it's currently a spectator moment. Real coalition science applies to both the player UI and the AI logic: minimal winning and *connected* coalitions (Riker/Axelrod — ideologically adjacent partners, not grab-bags), and portfolio allocation ∝ seats contributed (Gamson's Law). The deal should outlive the handshake: partners resent concessions, your party can disagree with your choice, voters can punish you for propping up an unpopular government.
- [ ] **Vote your conscience** `[M3]` — the weekly division becomes a player decision. `resolve_vote` already takes `player_vote` (+1/−1/0) — wire it to an action: the whip calls, you vote yes, no, or abstain. Defying the whip costs relationships and party standing; abstaining is the readable middle signal, not a dodge. Consequences stay situational, not automatic — rebelling can burn party standing while buying constituency credit; backing a toxic bill can preserve leadership support at electoral cost. The payoff lands on the mechanics built around it: in thin divisions your vote actually swings outcomes — on ordinary bills, on confidence, on your own legislation. The vote screen needs the stakes legible before you commit (see Decisive explanations).
- [ ] **Deals and favors** `[M3]` — logrolled votes: promise an MP your vote on their bill for theirs on yours. The relationships dict and favor mechanics are placeholders waiting for this. The core of strategic depth — but it only becomes a currency once kingmaking and conscience votes give favors somewhere to be spent. Start small: an agreed benefit, a deadline, a counterparty, a record of whether the commitment was honored. Only grow the relationship machinery once the basic loop produces interesting betrayals.
- [ ] **Decisive explanations** `[M3]` — `why` already lists weighted terms; it should say which ones *decided* the outcome. "The MP rebelled: their faction's economic line and their constituency both pulled against the whip, and a burning scandal made the whip's price not worth paying — ideology alone wouldn't have flipped them." A ranked list of six weights is arithmetic, not an explanation; a choice you can't read the stakes of isn't strategic, it's a guess. Gates informed voting and kingmaking — add decisive-factor ranking to the vote explanation before the player is asked to bet a career on a division.
- [ ] **Opposition role** `[M4]` — today the player mostly matters in government. Shadow scrutiny, amendment attacks, coordinated rebellion — being out of power should be a playable position, not dead time. Includes the deferred whip-breaking term from the scandal spec: MPs with an active scandal distance themselves from the party line (a named `selfpreservation` vote term, not folded into whip blindly), so a burning backbencher can be *counted* against their own whip — rebellion with a legible cause.
- [ ] **Budget power** `[M4]` — the PM tables the annual budget as a bill parliament votes on: revenue (tax posture) vs spending (services voters feel vs debt the treasury counts). Opposition can vote the budget down — losing supply is a constitutional crisis, not just a failed bill. The player's tradeoffs are real because the treasury is real. Depends on the Phase 3 treasury.
- [ ] **Legislative legacy** `[M4]` — the law registry made playable: revive a bill that failed (re-table with a cooldown, whip harder this time), repeal or amend laws in force — AI governments do it on their own logic, the player does it as leader. Opposition repealing your flagship law mid-term is exactly the drama the north star wants; defending your record is a career stake beyond seat safety. At the apex: constitutional amendment bills — supermajority to change the rules themselves, entrenching your own advantage or undoing a rival's. Observed need: the registry hit **893 eternal laws** in 1100 weeks — add a world-side sunset/repeal lifecycle (statutes lapse or get repealed on their own logic) so the statute book stays a living instrument, not an append-only log; accumulated law effects already push indicators toward bounds long-run.
- [ ] **Cross the floor** `[M4]` — the player cannot defect or found a party: `_found` and secession walkers exclude `player_id`. "Found a party that outlives you" is impossible until this exists. Player defection via the same machinery (join another party, or walk out with whoever follows you), with real costs — your district's betrayal, burned relationships, and a party with your name on it that can also die.
- [ ] **Scandal as a weapon** `[M4]` — dig_dirt currently produces dossiers mechanically. Timing releases, trading silence, deciding when your own dirt is survivable.
- [ ] **Court appointments** `[M5]` — the bench made political: judicial vacancies are filled by the PM, justices age and retire through the same lifecycle machinery as MPs (the `remove_mp` pattern reused), and the bench's ideological lean shades `legal_risk` resolution — a court you packed keeps ruling on laws after your term ends. Institutional capture as legacy: legible (bench composition is inspectable), slow (vacancies are rare), and the opposition inherits or suffers your appointments. Depends on the Phase 3 judiciary existing first.
- [ ] **Press relations** `[M5]` — the outlet landscape made playable: choose which outlet gets your dirt (a friendly paper buries the story, a hostile one leads with it), court editorial boards for friendlier coverage, and read polls through their publishers — biased samples mean a friendly poll can flatter you. AI parties court outlets on their own logic; hostile outlets become a career threat to manage. At the far end: **acquire the outlet outright** — ownership bends its slant toward the owner. Caveat: there is no money in the game, so the price is paid in favors/influence (ties to Deals and favors) unless an economy ever exists; AI barons owning outlets is the world-side half. Stretch (needs a truth layer): fabricated stories.
- [ ] **Goals beyond score** `[M6]` — optional arcs layered on the open-ended career (win a majority as PM, found a party that outlives you, survive N terms) — roguelike structure without a fixed ending.
- [ ] **Save/load** `[M6]` — `GameState` is a dataclass tree; serialize to JSON. Cheap because determinism was designed in. Independent of everything above — pull it forward the moment long sessions get annoying.
- [ ] **Difficulty and scenarios** `[M6]` — starting situations (safe seat vs marginal, incumbent vs opposition), `params.py` profiles. Constitutional variants too: constructive no-confidence (German model — must name a successor to topple the government) as a stability knob, and alternative district magnitudes. Scenario presets pin generated party systems via the `party_pool=` override hook deferred from party-variety.
- [x] **Balance pass** `[M1, recurring]` — first pass done (M1): `check_sweep.py` now prints and asserts the seven-area invariant table (party system, elections, government, economy, legislation, careers, player). First-pass finding: `debt_max` across 50 seeds sat exactly at `DEBT_CRISIS=2.0` — threshold tuned to 1.8 so receivership is reachable but still rare (2 crises / 50 seeds). Bands and rationale recorded in `spec-m1-stable-world.md` §Results. Recurs after every milestone that changes the feedback loops.

Done when: you choose to act most weeks — not because the game demands input, but because the world gave you something to exploit.

## Phase 5 — Watchability and reach (optional)

The world is already watchable; this is presentation depth and sharing. All `[M6]`.

- [ ] **Better writing** `[M6]` — event text from a larger template pool with named actors, so the chronicle reads like political history instead of status lines. Includes the deferred naming texture: generated country names (a dateline for the chronicle), regional flavor name packs for party archetypes, and driver map pole labels reading `AXIS_LABELS`/`POLE_LABELS`. Observed need: **two-thirds of the chronicle is player-action echoes** ("You give a speech" ~600/900 events) — action echoes need their own tier/filter, and headlines need story variety (a thousand "X becomes law" leads is not a press). Can improve incrementally — don't wait for the rest of M6.
- [ ] **Election night mode** `[M6]` — districts resolve with projections and swing callouts during the reveal. The sim computes per-district; this is dramaturgy.
- [ ] **Spectator/analysis mode** `[M6]` — headless auto-play with visualizations, for tuning and for watching the machine grind. Observed need: the idle auto-player **dies at ~week 155** (loses their seat at the ~4th election, game over) — spectator mode needs a heuristic policy bot making plausible weekly decisions, or observation can't run past the first term. (Also serves M1: the invariant table needs long runs that don't die early.)
- [ ] **Driver polish** `[M6]` — fullscreen mode, and a pass over whether every essential view is reachable without hunting (chronicle, why-overlay, map, action panel). As new systems land, their info needs a home too.
- [ ] **Web driver** `[M6]` — same `tick()` contract, browser rendering. Enables sharing seeds and runs — only if "just me" ever widens.

## Explicitly not on the roadmap

- **LLM-generated anything** — the game's identity is classical AI. Dialogue and events stay algorithmic.
- **Real-world political data** — fictional country is a feature.
- **Multiplayer** — the MP-agent layer is the opponent.
