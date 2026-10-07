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
| **M3 — Strategic politics** (done) | The player moves parliamentary outcomes | Kingmaking, conscience votes, abstention/attendance, independents, deals & favors, decisive explanations |
| **M4 — Full political lifecycle** (done) | Decisions have lasting consequences | Budget power, legislative legacy, opposition role, cross the floor, scandal as a weapon |
| **M5 — Institutional depth** (done) | Institutions constrain and shape power | Constitution, court appointments, press relations |
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
- [x] **Independent MPs** `[M3]` — done (M3): `INDEPENDENT_P` fields a party-less local per district per election, positioned near (never exactly on) the centroid — pure-proximity candidates who win where every party sits far away. No label, no brand, no loyalty — voters score the person; betrayal sticks to the person too. `MP.party=None` threads the whole sim; election results report `"ind"` seats. ~2-5 seats a parliament — exactly the balance-of-power scale.
- [x] **Abstention and attendance** `[M3]` — done (M3): `|u| < ABSTAIN_MARGIN` abstains (present but not voting, half a rebel's standing price); a weekly attendance roll (rising at term end, in burning scandals, late in careers, plus a rare shared shock — flu/boycott weeks) drops the house below `QUORUM` → `DivisionStalled`, the pending bill carries to next week. Confidence divisions are three-line whips — whipped MPs can't abstain; the player still can (the franchise has a standing price).
- [x] **Ministerial performance** — done (P3): portfolios are a data table (`PORTFOLIO_INDICATOR`: Finance→growth, Labour→unemployment, Interior→crime, Health→services, Foreign→inflation) — Justice became Labour since no justice dial exists, and the table appends rows for Phase 4 (patronage posts, bigger cabinets, party-flavored ministries). Weekly, each minister pushes their indicator by `(competence − 0.5) × PORTFOLIO_EFFECT` — above-average ministers help, duds visibly erode their dial — while `MP.perf` accumulates the actual on-watch delta (decayed, recency rules) and `portfolio_weeks` counts tenure. Past `MINISTER_TENURE`, a record below `MINISTER_SACK_RECORD` gets `MinisterSacked reason="performance"` plus a brand hit on the PM's party; `Government.sacked` bars re-hires until the next election (scandal-sacked join the same set), and *any* dark chair — sack, scandal, defection, retirement — is refilled same-week by the seat-weighted queue (`Promoted reason="reshuffle"`). Competence flows into the existing `mood → retrospective` channel: appointment → indicator → mood → voter judgment. Check: 21 performance sackings / 33 same-week refills over 4 seeds, competence 0.95 vs 0.05 diverges growth.
- [x] **The judiciary** — done (P3): `legal_risk(law)` is a legible derived score (extremity + cost + thin margin, stamped on `LawEnacted`) and the courts are the venue for losers — weekly, the most hostile *opposition* party drags the riskiest unchallenged statute into a capped docket (`ReviewOpened`), where it sits `REVIEW_WEEKS` in force before a verdict. Verdicts are a rule, never a roll: per-seed `court_activism` sets the strike line, so the same statute falls on an activist world and stands on a deferential one. `LawStruck` removes the `Law` — effect *and* upkeep stop the same week — and bleeds the **authoring** parties (`law.enacted_by`), even after they've left office; `LawUpheld` confers immunity (res judicata — one challenge per law ever). Observed cadence: 54 challenges / 16 strikes / 36 upheld over 4×250 weeks — smackdowns stay rare drama. Deferred on purpose: constitutional articles as the review object (next module), injunctions, player-filed suits, provision-level strikes. The bench itself starts abstract — a political bench with appointed justices is Phase 4 (see Court appointments).
- [x] **The constitution** `[M5]` — done (M5): `make_constitution` writes a per-seed book of `Article` clauses — Fiscal (cost cap) and Mandate (margin floor) always, positional clauses fencing the poles far from the voter centroid. `legal_risk` sums per-article violations plus a residual extremity term; `ReviewOpened`/`LawStruck`/`LawEnacted` cite the worst-breached clause by name. **Constitutional amendment** shipped too: `Bill.amends`/`entrenches` rides the pending cadence at `AMEND_MAJORITY` (two-thirds of votes cast — abstentions burn the mover, 0-0 cannot carry), unreachable by judicial review; a government whose law was struck tables repeal of the citing clause at `AMEND_TABLE_P` — one swing per clause per government. Player-PM queues a repeal or entrenchment via `amendment` (materializes as next week's government business; lapses at every transition); a PMB may carry one. Player-initiated `challenge` files suit on any qualifying statute — the deferred p3-courts item, unblocked by the M4 player surface. Deferred on purpose: Head of State as the constitution's guardian, injunctions, provision-level strikes.
- [x] **Policy salience** — subsumed by the media layer (P3.4): agenda-setting IS outlets pushing `focus_axis` salience into their audiences, and `speech` already contests the agenda. Nothing left to build here beyond tuning.

Done when: a played term feels like you're inside a living country — and when you peek via auto-play, the chronicle confirms the world moved on its own logic, not around you.

## Phase 4 — Your career inside it

The three pillars made playable: climb, drama, strategy. These are player-facing systems layered on the now-living world. Ordered by milestone — the career ladder leads because 23 terms of zero promotions means the climb pillar is hollow, and kingmaking leads M3 because the single highest-leverage decision in the game is currently a spectator moment.

- [x] **Career ladder** `[M2]` — done (M2): the climb is a strategic problem now. `MP.standing` is the movable currency — whip fidelity in `resolve_vote`, the `constituency` action, and office trickles earn it; sacks, rebellions, and burning scandal weeks burn it; it decays. Per-party junior posts (`JUNIOR_POSTS` — Whip/Spokesperson/Committee Chair) exist in **opposition parties too**, refilled same-week in-session; promotion to cabinet vacates a rung and someone climbs. `_appoint` is decomposed into named `appointment_terms` — `record`/`standing`/`backing`/`seniority`/`rung` — scored identically for AI, with `backing` reading the appointer's view of the candidate (lobby and scheme pay into the climb). Legibility: `Promoted` carries winner terms, a losing player gets a passed-over `CareerEvent` with rank and deciding terms, and `explain_mp` shows the cabinet-candidacy rank. Check: `check_ladder.py` — scripted climber reaches cabinet 6/8 seeds vs passive 1/8.
- [x] **Kingmaking** `[M3]` — done (M3): when the player's party sits in a viable slate, `resolve_formation` pauses a week — `OfferMade` events enumerate every proposer's coalition with its price; `pick_offer`/`decline_offers` answer (silence takes the default, so autoplay isn't punished). The price is real: far partners drag the negotiated **agreement** (`government.platform`, a distinct object from the manifesto) and the proposer's members pay standing — AI pays identically. Declining sits the player's party out of slates *and* the minority fallback; a slate that dies during the bargaining week emits `OfferLapsed` and the table re-deals.
- [x] **Vote your conscience** `[M3]` — done (M3): bills tabled week W are divided week W+1 — the player reads the pending business all week, then the `vote` action casts aye/no/abstain. `VoteResult` records the player's column. The consequences were already priced: whip defiance burns standing, district exposure is a named term, and a stalled quorum carries the bill.
- [x] **Deals and favors** `[M3]` — done (M3), deliberately small: one promise shape — commit your vote on the pending division to a named MP (`deal` action). The counterparty banks `DEAL_REL` up front; `resolve_vote` judges the promise on the cast column — `DealKept` banks more + standing, `DealBroken` costs double. One promise per head; deals lapse on dissolution or a collapse.
- [x] **Decisive explanations** `[M3]` — done (M3): `explain_vote` marks each MP's *deciding* term (the one whose removal flips `u`); `explain_bill` projects the pending division noise-free — never touches `state.rng` — with the tally, the marginals, and each marginal's decider. The vote column now renders the *cast* ballot, so a whipped MP forced to a side never displays as an abstainer.
- [x] **Opposition role** `[M4]` — done (M4): opposition is a playable position — `attack` (scrutiny that whiffs against a popular government and lands on a weak one, scaled by `−mood` + worst-minister `perf`), `amend` (drags the pending bill's `pos` toward you once per bill — can break a partner's whip line), `table` (private member's bill, immediate division, player-authored, feeds `legacy_bills` and is repeal-able). The deferred whip-breaking term shipped as `selfpres`: during a burning-scandal week the MP distances themselves from the effective whip line — rebellion with a legible cause. Deferred on purpose: coordinated AI rebellion beyond the per-MP term.
- [x] **Budget power** `[M4]` — done (M4): the scheduled budget is a real `Bill(budget=True, confidence=True)` carrying a tax/spend **posture** derived from the coalition agenda, riding the pending-bill cadence (stakes readable via `explain_bill`, deal-able, amendable). Pass sets `Treasury.posture` — revenue/upkeep/services shift until the next budget; loss routes through the shared `collapse(…, "supply")` path — losing supply is a government fall, not a footnote. Player-as-PM picks the posture via the `budget` action. Crisis confidence votes still resolve same-tick.
- [x] **Legislative legacy** `[M4]` — done (M4): `Law.author` (the PM's id at enact, or the PMB sponsor) makes "your flagship law" a real object; AI governments table `Bill(repeals=law)` against inherited statutes at `REPEAL_P`, and `LawRepealed` names the dismantled authors (symmetric with `LawStruck`). Failed ordinary bills retable after `RETABLE_CD` at `RETABLE_P` (named `(Revisited)`; austerity/repeal/PMB excluded); statutes past `SUNSET_WEEKS` lapse at `SUNSET_P` — the statute book is a living instrument. Deferred on purpose: constitutional amendments (needs M5's constitution).
- [x] **Cross the floor** `[M4]` — done (M4): `defect` to a party or go independent — betrayal, relationship burn, standing reset, portfolio stripped; **a defecting PM forfeits the office** (legitimate successor from the largest coalition party, else collapse; stale caretaker PM during formation is not a live PM). `found` reuses `_found` with relationship- AND misery-gated followers who walk with you unpenalized; parties joined mid-term are marked `seated`.
- [x] **Scandal as a weapon** `[M4]` — done (M4): `leak` detonates a dirty MP's dossier on your schedule (election-window multiplier applies — October surprises are a play); `LEAK_TRACE_P` catch cost adds to *your* dossier and burns the relationship. Self-targeting rejected in both drivers. Deferred on purpose: trading silence, AI leaking your dirt back.
- [x] **Court appointments** `[M5]` — done (M5): `court_activism` survives only as the worldgen seed for a real `bench` of `BENCH_SIZE` justices — each with `pos`/`activism`/`age`/`appointed_by`. Verdicts are per-justice votes (`risk − doctrine-line + ideology distance`, majority carries) with the detail list on the event, so `explain_bench` shows *which* justices killed a law. Justices age on the MP hazard curve; vacancies fill through the PM — AI appoints a same-week loyalist, a player-PM picks from a `APPOINT_POOL` shortlist of visible tradeoffs (young ideologue vs old moderate), a caretaker fills nothing. `appointed_by` is the legacy trail — monotonic `justice_seq` ids keep citations unambiguous after departures.
- [x] **Press relations** `[M5]` — done (M5): `Outlet.warmth` per party — the `court` action buys goodwill (decays weekly; organic drift toward the nearest-slant party is capped below what courting buys) and softens that outlet's coverage hostility. `leak` takes an `outlet=` venue: warmth to the *subject* buries the pickup, cold leads it — and trace asymmetry keys on warmth to *your* party (`FRIENDLY_TRACE_MULT`/`HOSTILE_TRACE_MULT`: friends protect sources, enemies don't). Rotating outlets sponsor `PollShift` with an audience-affinity skew, stamped into `state.last_poll` — and `strategic_call` reads the *published* number, so a friendly poll can flatter a government into a doomed snap. Deferred on purpose: outlet ownership (no money in the game), fabricated stories (needs a truth layer), per-MP warmth.
- [x] **Goals beyond score** `[M6]` — done (M6): pickable `Ambition` arcs (pm, majority, founder, survivor, reformer) layered on the open-ended career — `AmbitionMet`/`AmbitionFailed` events, a `score_terms` entry for a met arc, and a career-retelling epilogue at game over. Sandbox (`None`) stays the default.
- [x] **Save/load** `[M6]` — done (M6): `sim/persist.py` JSON codec — field-driven encode plus a `#bill`/`#law`/`#article` id table, so the identity web (`deal.bill is current_bill`, amendment queues, docket refs) survives the round trip. RNG state included: a save resumes byte-identically to uninterrupted play. Terminal `save`/`load` + `--load`; pyg F5/F9.
- [x] **Difficulty and scenarios** `[M6]` — done (M6): `Scenario` presets (standard, safe_seat, marginal, outsider, duopoly, fragmented, constructive) via `new_game(seed, scenario=)` — starting seat, party-system pinning through `party_pool=`, constructive no-confidence (confidence falls need a named successor; the wounded government limps on at a brand bleed), and `district_magnitude` for multi-member districts on a largest-remainder allocation. Per-scenario param overlays scope to worldgen — no leakage between runs.
- [x] **Balance pass** `[M1, recurring]` — first pass done (M1): `check_sweep.py` now prints and asserts the seven-area invariant table (party system, elections, government, economy, legislation, careers, player). First-pass finding: `debt_max` across 50 seeds sat exactly at `DEBT_CRISIS=2.0` — threshold tuned to 1.8 so receivership is reachable but still rare (2 crises / 50 seeds). Bands and rationale recorded in `spec-m1-stable-world.md` §Results. Recurs after every milestone that changes the feedback loops.

Done when: you choose to act most weeks — not because the game demands input, but because the world gave you something to exploit.

## Phase 5 — Watchability and reach (optional)

The world is already watchable; this is presentation depth and sharing. All `[M6]`.

- [x] **Better writing** `[M6]` — done (M6): `sim/prose.py` template pools render election/vote/newcomer text with named actors on a forked `prose_rng` (`seed ^ PROSE_SEED_KEY`) — wording draws provably never touch the mechanical stream (check_prose corrupts the prose stream and verifies `state.rng` untouched). Generated country name is the dateline, regional name packs flavor parties and MPs, map poles read `AXIS_LABELS`/`POLE_LABELS`. Player-action echoes carry `echo=True` — terminal collapses them into a digest line, pyg files them under their own chronicle chip.
- [x] **Election night mode** `[M6]` — done (M6): `resolve_election` emits one `DistrictResult` per district (winners, previous holders, margin, flip flag, retained MPs). Pyg stages the reveal on a timer with flip callouts; terminal collapses the dump into a called-line plus named flips. The sim's truth doesn't change — only the telling.
- [x] **Spectator/analysis mode** `[M6]` — done (M6): `sim/bot.py::auto_actions` — a draw-free rule list (whip the vote, defend the seat, lobby, court hostile outlets, run the PM's desk) that survives where the passive player died at ~week 174: probe seeds reach the 600-week cap and a terminal spectator run ran 444 weeks. Terminal `--spectate`; pyg auto-play drives the bot.
- [x] **Driver polish** `[M6]` — done (M6): pyg fullscreen toggle + resizable window over a fixed logical canvas (mouse coords map back), hemicycle scales past 120 seats, save/load keys hinted on-screen. Terminal got `save`/`load`/`--load`, `inspect bench`, scenario flag, and the election-night summary.
- [ ] **Web driver** `[M6]` — same `tick()` contract, browser rendering. Enables sharing seeds and runs — only if "just me" ever widens.

## Explicitly not on the roadmap

- **LLM-generated anything** — the game's identity is classical AI. Dialogue and events stay algorithmic.
- **Real-world political data** — fictional country is a feature.
- **Multiplayer** — the MP-agent layer is the opponent.
