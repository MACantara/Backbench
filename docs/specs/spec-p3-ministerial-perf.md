# Spec: ministerial-perf (Phase 3)

Ministers do things in office — competence becomes a lived fact, not a hiring signal.

## Why

`mp.competence` decides *who gets appointed* and then goes inert. A 0.9-competence Finance minister and a 0.2-competence one are indistinguishable in office — portfolios are labels. Real politics runs on **valence** (Stokes): voters reward governments for competence beyond ideology, and PMs manage ministers — underperformers get sacked in reshuffles. The sim already has the valence channel (`mood` → `retro` term in vote scoring) and the accountability event (`MinisterSacked`, scandal-only); what's missing is performance flowing through them.

## Mechanics

### Ministry ↔ indicator map

Rename the portfolio list so each ministry owns one conditions dial — five ministries, five indicators:

```
Finance  → growth
Labour   → unemployment      (replaces "Justice" — no justice indicator exists)
Interior → crime
Health   → services
Foreign  → inflation         (trade credibility / supply chains)
```

`PORTFOLIO_INDICATOR` in `params.py`. Justice's crime coverage is absorbed by Interior; "Justice" disappears from `PORTFOLIOS`.

The portfolio list is a **data table**, not a fixed five — each entry is `(name, indicator)` so later phases append rows (patronage posts with `indicator=None`, party-flavored ministries) without touching the assignment or performance machinery.

### Performance push

Weekly, in `conditions_lifecycle` (after law effects, before shocks — ministers are continuous pressure, not events):

- For each government MP holding a portfolio: their indicator moves by `(competence - 0.5) * PORTFOLIO_EFFECT`, in the *good* direction (up for growth/services, down for unemployment/inflation/crime), scaled by distance-to-bound like law effects (diminishing near bounds).
- Mean competence is 0.5 → expected zero net — a minister is only as good as they are *above average*. A dud minister visibly erodes their dial.

### Track record

`MP.perf: float` — accumulates the signed improvement of their indicator while in office (their own push plus the world's, honestly attributed: record what happened on their watch). Sacking a minister freezes their record; it's the career-ladder input later.

### Performance sackings and reshuffles

- A minister with `weeks in office >= MINISTER_TENURE` and `perf < MINISTER_SACK_RECORD` gets sacked by the PM: `MinisterSacked` event with `reason="performance"` (scandal sacks keep `reason="scandal"`), `portfolio=None`, small party-brand hit (the PM bleeds a little credibility admitting a bad pick).
- A vacant portfolio while a government stands gets refilled the same week — `Reshuffle`-flavored `Promoted` event — using the existing seat-weighted appointment logic extracted into `_appoint(state, party_id, ministry)`.
- `assign_portfolios` keeps forming fresh cabinets at each formation (reshuffles happen *within* terms via performance/scandal vacancies).

## Events

- `MinisterSacked` gains `reason: "performance" | "scandal"`.
- `Promoted` gains `reason="reshuffle"` on mid-term refills.
- Optional chronicle line on sackings: "Health minister sacked as services deteriorate." — the indicator in the text, legible cause.

## Params

```
PORTFOLIO_EFFECT = 0.004       # weekly indicator push at competence 1.0
MINISTER_TENURE = 16           # weeks before a record is judged
MINISTER_SACK_RECORD = -0.06   # accumulated indicator loss that gets you fired
MINISTER_SACK_BRAND = 0.03     # brand hit when the PM admits a bad pick
```

## Deferred

- **Portfolio expansion** — the table stays five effect-ministries here; Phase 4+ grows it along three lanes: (a) *patronage posts* (`indicator=None`) — ministries that exist to buy loyalty, feeding `STAY_PORTFOLIO` and the `_will_join` haggling hook already flagged in `government.py`; (b) *bigger cabinets* — portfolio count scaling with coalition size (a real Gamson extension: more partners, more jobs to split); (c) *party-flavored ministries* — Agriculture for an agrarian partner, Justice for a GAL-TAN one — ministries parties actually *demand* in bargaining, which is what makes kingmaking negotiate something real.
- **Player-facing reshuffles** — when the player is PM, picking and firing ministers is Phase 4 (needs the career ladder to put players in the chair).
- **Per-party indicator attribution** — voters punishing *the party holding Health* for the services collapse is a finer clarity-of-responsibility model; the party-level `mood × responsibility` channel already carries most of it. Refinement, later.
- **PM competence** — a strong PM amplifying the whole cabinet is a second-order effect; portfolio-level performance first.
- **MINORITY_GOVT_PENALTY** — still a dead constant; minority-governor effectiveness is a different mechanism than ministerial competence.

## Success criteria

- A competent minister measurably improves their indicator vs a dud (fixture: same conditions seed, competence 0.9 vs 0.2 → divergence on that ministry's dial).
- A failing minister is sacked mid-term and the portfolio refills — `MinisterSacked reason="performance"` and `Promoted reason="reshuffle"` fire.
- Scandal sackings keep working with `reason="scandal"`.
- `MP.perf` accumulates on incumbents and freezes on removal.
- Long runs: sackings are occasional, not weekly; a government of high-competence ministers shows a better `mood` drift than a dud cabinet (directional, noisy).
- Deterministic by seed; no new I/O; all tunables in `params.py`.
