# Spec: courts (Phase 3)

A court reviews laws in the registry — extreme statutes get challenged, sit in a docket, and are struck or upheld after a delay. The bench is abstract; verdicts are rules, not dice.

## Why

`state.laws` is append-only: once a bill passes, its weekly indicator push and upkeep cost run forever — nothing checks whether the law *should* stand. Real parliaments legislate under a shadow: a radical statute invites litigation, and losing in court is a specific, legible kind of defeat (different from losing a vote — you won parliament and lost anyway). The machinery this builds — docket, delay, verdict, removal — is exactly what the next module (`constitution`) needs: articles replace the abstract risk formula, and Phase 4 court appointments replace the abstract disposition. Courts first, because the others are its object and its composition.

## Mechanics

### Legal risk

`legal_risk(law)` — a pure derived score, legible formula, no stored drift:

```
risk = RISK_EXTREMITY_W * |law.pos|               # radical statutes invite review
     + RISK_COST_W      * (law.cost / norm)       # expensive ones more so
     + RISK_MARGIN_W    * (1 - law.margin)        # thin mandates are contestable
```

Computed on demand (fixture, events, inspect) — the number is *visible*: `LawEnacted` carries `risk=` in its data so the chronicle can show a law was born contested. The `constitution` module later replaces this formula with per-article violations; the docket machinery doesn't care which oracle produced the score.

### The challenge — the venue for losers

Weekly scan (`courts_lifecycle`, in the always-on tail — courts don't dissolve with parliament): the highest-risk *unchallenged* law meeting all gates opens a case:

- `legal_risk(law) >= CHALLENGE_RISK_MIN`
- an **opposition** party exists with `dist(platform, law.pos) >= CHALLENGE_DIST` — the most hostile one files (`challenger=` on the event). A coalition partner doesn't sue its own government; if the filer joins government or dissolves mid-case, the case proceeds — courts don't care who filed.
- `len(state.docket) < COURT_DOCKET_MAX` — the bench has finite capacity; the riskiest unchallenged case goes first.

`ReviewOpened` event: challenger, law, risk, due week.

### The docket

`state.docket: list[CourtCase]` — `(law, due_week, challenger)`. `due_week = week + REVIEW_WEEKS`: the statute sits pending for a real interval, staying in force meanwhile (injunctions deferred). `law.reviewed` flips at verdict — res judicata: a law is challenged at most once, ever, keeping the registry honest and the docket bounded.

### The verdict — a rule, not a roll

Per-seed `state.court_activism` (0..1, drawn at worldgen from `state.rng`) is the bench's character — deferential courts let almost everything stand, activist courts police hard:

```
strike if risk_at_filing >= COURT_STRIKE_BASE - COURT_ACTIVISM_W * (court_activism - 0.5)
```

The verdict reads the risk snapshot stamped on the `CourtCase` at filing — the statute *as challenged*, not as decayed (upkeep costs fade weekly; a filed case can't cool off under the line by waiting).

No RNG at decision time. The same statute survives on one world and falls on another — institutional character is the uncertainty, not a per-case coin. A `CourtCase` whose law left the registry another way (future repeal) resolves as moot.

### Strike consequences

- The `Law` leaves `state.laws` — weekly indicator effect stops immediately (courts run before `conditions_lifecycle`), upkeep stops the same week (fiscal relief rides free — treasury reads the registry).
- `law.enacted_by: set[int]` — stamped at `enact` (`state.government.parties` at passage): the strike blames the **authors**, even if they've since lost office. Your flagship Act getting struck under a successor government is exactly the emergent drama this module exists for. Surviving authors take `COURT_BRAND_HIT`; the media subject resolves to them (falling back to current government if all are gone).
- `LawStruck` event. `LawUpheld` on the survive path — a validated law is now immune, a small vindication.

## Events

- `ReviewOpened` — a case is filed (challenger, law, risk, due).
- `LawStruck` — the bench removes it (law, authors, risk). `_NEWS` row: broadsheet fare, negative for the authors.
- `LawUpheld` — survives review (law, authors). Mild, positive.

## Params

```
RISK_EXTREMITY_W = 0.6         # radicalism is the main invitation
RISK_COST_W      = 0.3         # expensive statutes draw scrutiny
RISK_MARGIN_W    = 0.2         # thin mandates are contestable
CHALLENGE_RISK_MIN = 0.45      # below this the courts stay out
CHALLENGE_DIST   = 0.5         # opposition hostility needed to file
REVIEW_WEEKS     = 12          # a case sits pending a real interval
COURT_DOCKET_MAX = 2           # bench capacity — cadence stays rare
COURT_STRIKE_BASE  = 0.6       # risk an average court strikes at
COURT_ACTIVISM_W = 0.4         # per-seed disposition swing
COURT_BRAND_HIT  = 0.04        # author brand bleed on a strike
```

## Deferred

- **Constitutional articles** — the next module: `legal_risk` becomes "violates Article 4 — equal franchise", strikes cite the article. The risk formula is the interim oracle.
- **Court appointments (P4)** — `court_activism` becomes a derived lean over a bench of appointed justices who age and retire like MPs; `courts_lifecycle`'s verdict line reads the bench instead of the scalar.
- **Injunctions** — a challenged law's effect suspended during review; currently pending laws stay in force (the common case).
- **Player-initiated challenges** — the player as opposition leader filing suit needs the leader surface (P4).
- **Provision-level strikes** — needs richer bill structure; whole-law only here.
- **Amendment/repeal interplay** — P4 legislative legacy; a repealed law leaves the registry the same way a struck one does (moot-case guard covers it).

## Success criteria

- An extreme, costly, thin-margin law gets challenged; a moderate centrist law never does (fixture: gates fire on engineered statutes, silence on centrist ones).
- The delay is real: `ReviewOpened` → verdict lands `REVIEW_WEEKS` later, not same-week.
- Same law, different seeds: struck under an activist court, upheld under a tame one — verdict determined by `court_activism`, never by a roll.
- Strike removes the law from the registry: its weekly effect and upkeep stop that week; `law.reviewed` blocks re-challenge.
- Strikes are rare and cause-driven in long runs — a handful per term on radical governments, none on centrist ones; a struck author's brand bleeds even after leaving office.
- Deterministic by seed; no I/O in `sim/`; all tunables in `params.py`.
