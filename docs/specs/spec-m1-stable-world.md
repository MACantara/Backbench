# Spec: M1 — Stable world

Long runs stay interesting. Milestone spec: three items — **fiscal escalation** (the only new sim machinery), **invariant monitoring** (the health table made real), **first balance pass** (tuning driven by it). Milestone done-when (verbatim): *the invariant table holds across the 50-seed sweep; insolvency recurs instead of firing once and going silent.*

## Why

Two observations from the 1100-week runs converge on the same failure shape — a channel runs away and the world dies quietly:

- **The debt meter dies insolvent.** `crisis_armed` re-arms only below `DEBT_WARN`, so once `debt > DEBT_WARN` permanently, `DebtCrisis` fires exactly once — observed debt 1151 with a single crisis event. Real insolvency is a *spiral*: repeated crises, forced austerity, governments falling on the books.
- **The health table is aspirational.** The roadmap's long-run-health table lists seven areas to watch; `check_sweep.py` measures exactly one (government survival). Every other channel — party structure, elections, economy, legislation, careers — is unmonitored, which is how duopoly lock-in and 893 eternal laws shipped unnoticed.

Fix the known silent channel, then instrument the table so the *next* silent failure is caught instead of discovered.

## Item A — Fiscal escalation

Insolvency becomes a *state*, not an event. While `debt > DEBT_CRISIS`, the country is in receivership:

### Recurring crises

- `Treasury.crisis_armed` → `Treasury.last_crisis_week` + `Treasury.crises` (count). While `debt > DEBT_CRISIS` and a government sits: every `DEBT_CRISIS_EVERY` weeks → `DebtCrisis` fires again — brand hit + forced `confidence_vote`, same as the first. The cooldown bounds the spiral (no weekly collapse chains); the *repeat* is the escalation — each forced confidence is another chance to fall. Event text counts the recurrence ("second insolvency this parliament").
- Below `DEBT_WARN`, nothing changes: no inflation drag, no crisis eligibility — solvency is still a real escape.

### Forced austerity — receivership captures the agenda

- While `debt > DEBT_CRISIS`, the government's weekly bill is **forced austerity** — it cannot legislate its program while insolvent. `table_bill` branches on the level; no flag to desync.
- `Bill.austerity: bool = False` marks it. An austerity bill: positive-cost-savings (`cost = -AUSTERITY_SAVING`, net revenue while in force) positioned market-ward on the economic axis, with a *negative services effect* (`law_effect` extension: austerity → `{"services": -…}`) — the cuts hurt a dial voters feel. Named from an austerity pool ("Public Finances Emergency Act").
- **The dilemma is load-bearing and free**: the `fiscal` vote term is `cost × debt_pressure` — a *negative*-cost bill under deep debt is attractive to everyone fiscally, but whips and ideology fight it (a left coalition's own whip may break over `COALITION_WHIP_TOL` — the governing party can't even whip its own rescue). Pass → the cuts law enters the registry, upkeep drops, services sag, mood pays it back at the polls. Fail → debt compounds, the next crisis arrives on schedule. The spiral is emergent; the exits are legible.
- `AusterityFailed`-flavored signal comes free via the existing `VoteResult` — no new event type needed for the failure path.

### What this is not

- Not a bailout mechanic, not debt restructuring, not an IMF — receivership here is *agenda capture + recurring confidence*, the smallest model that makes insolvency recur with teeth.
- The hysteresis flag's old job (no same-week re-fire) is subsumed by the cooldown.

## Item B — Invariant monitoring

Extend `checks/check_sweep.py` from one metric to the roadmap's full table — per-seed tallies over long runs, printed as a band-checked summary. The table (bands are measured-first-then-asserted; see Item C):

| Area | Metric | Current state |
|------|--------|----------------|
| Party system | median seat-ENP at end; `PartyFormed`/`PartyDissolved`/`Secession` counts | measured in check_party_dynamism only |
| Elections | largest-party seat share; incumbent turnover | unmeasured |
| Government | survival median/p10/p90 (existing); `ConfidenceLost` rate | partially measured |
| Economy | % weeks each indicator pinned at a bound; debt median + max | unmeasured — the 1151 outlier must die |
| Legislation | laws in force at end; cumulative effect share vs indicator | unmeasured — the 893-law ratchet |
| Careers | `Promoted`/`MinisterSacked`/`Retired` counts; max minister tenure | unmeasured |
| Player | week reached before `phase == "over"` (passive player) | weak until the M6 bot; measure anyway |

Each row gets an assertion band loose enough to survive honest variance but tight enough to catch a dead channel (e.g. "no seed above N parties at end" isn't assertable on hegemonic seeds — median across seeds is). The output prints the table so a balance pass reads it directly, no re-runs.

## Item C — First balance pass

Process, not code: run the invariant table → list every violated band → tune `params.py` → re-run until green. Findings and the tuning rationale get recorded in the spec's Results section (appended during implementation — the table is useless if the tuning that consumed it isn't written down). Known suspects going in: `DEBT_*` economics (the whole point of Item A), law-effect saturation (893-law ratchet), party birth/death asymmetry.

## Events & params

- `DebtCrisis` — unchanged shape, now recurring (`crises` count in data).
- `BillTabled`/`LawEnacted` on austerity bills get `austerity=True` — the chronicle should read "the government is *forced* to table cuts."
- New params: `DEBT_CRISIS_EVERY` (crisis cooldown), `AUSTERITY_SAVING`, `AUSTERITY_SERVICES_CUT`, austerity name pool. All in `params.py`.

## Deferred

- Player-facing budget bills and voluntary austerity (P4 budget power).
- Receivership *institutions* — an external board with its own agenda is a character, not a rule; the level-gate is the honest abstraction here.
- The M6 spectator bot for the player row — the invariant measures survival span only until it exists.
- Bankruptcy default, bailouts, creditor politics — receivership is already the right amount of abstraction.

## Success criteria

- Insolvent worlds show *repeated* `DebtCrisis` events on the cooldown — the meter never goes permanently silent (fixture: debt pinned past CRISIS → ≥3 crises over 60 weeks).
- Forced austerity: while insolvent every tabled bill is an austerity bill (cost < 0, services-negative); passing one measurably improves weekly flow; a failed one leaves the spiral running.
- `check_sweep.py` prints and asserts the full seven-area table; long-run debt max is sane (no 1151-class outliers — austerity exits actually work).
- The balance pass lands real tuning with a written rationale, not a shrug — at least one violated band found and fixed in this milestone.
- Deterministic by seed; no I/O in `sim/`; all tunables in `params.py`.
