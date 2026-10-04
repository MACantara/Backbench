# Spec: snap-elections (Phase 3)

Parliament can dissolve mid-term — the metronome breaks.

## Why

The 1100-week observation: `ElectionCalled` fires only on schedule (`weeks_in_office >= 40`), and a fallen government re-forms in place the next week — same parliament, no campaign, no voter judgment. Real parliaments don't work that way: when a government falls and no alternative majority exists, the house dissolves and the voters decide. Elections arriving only on a fixed cadence make the world feel clockwork instead of alive — collapses have no stakes.

## Mechanics

Three triggers, all legible, all funnel into the existing `phase="campaign"` path.

### 1. Dissolution on confidence loss (constructive no-confidence)

When `confidence_vote` fails, the question is no longer "re-form" but **"is there an alternative government?"** — the constructive no-confidence rule (Germany, Spain): the house can only dismiss a government it can replace.

- Extract the coalition-building algorithm from `form_government` into a dry-run probe: `_best_coalition(state) -> (proposer_id, coalition_set, bloc_seats)` — same `_will_join` + largest-first logic, no mutation.
- On `ConfidenceLost`: if the probe finds a **non-incumbent-overlapping** majority coalition (i.e., a coalition that isn't just the fallen government re-dressing itself), `phase="formation"` as today — the house chooses a successor in place.
- If no alternative majority exists → **dissolution**: `phase="campaign"`, `weeks_to_election=8`, `niche_entry` runs as at a scheduled call, emit `ElectionCalled` with `snap=True, reason="confidence"`.
- The minority fallback still exists at formation, but a minority government that *just* collapsed confidence doesn't count as a viable alternative for the probe — the probe only accepts majority blocs, and the incumbent coalition is excluded.

### 2. Deadlock dissolution

Repeated collapses without a stable re-formation mean the house is ungovernable (Israel 2019–21, Belgium 2010–11).

- `Government.collapses: int` — incremented on each `ConfidenceLost`, reset in `resolve_election`.
- After `SNAP_COLLAPSE_MAX` collapses since the last election, even a technically-viable alternative is denied: the house dissolves. `snap=True, reason="deadlock"`.

### 3. Strategic dissolution (incumbent timing advantage)

A PM riding high calls an early election to lock in a bigger majority — the political business cycle / scheduling power (Cox & McCubbins).

- In the governing phase, evaluated weekly: `weeks_in_office` inside a mid-term window (`SNAP_WINDOW`), government's combined poll share above `SNAP_POLL_MIN`, and a seeded chance `SNAP_CALL_P` → `ElectionCalled` with `snap=True, reason="strategic"`.
- Must be rare: the poll gate does most of the work (a government only gambles when it's winning); `SNAP_CALL_P` keeps it stochastic, not guaranteed.

## Events

- `ElectionCalled` gains `snap: bool` and `reason: "confidence" | "deadlock" | "strategic"` — scheduled calls emit `snap=False` (or omit). The sweep already counts `ElectionCalled`, so spans stay correct.
- Text: "Parliament dissolved — snap election called." / "The PM calls an early election to capitalize on the polls." / "No stable government can be formed — parliament dissolved."

## Params

```
SNAP_COLLAPSE_MAX = 2      # collapses since last election that force dissolution
SNAP_WINDOW = (20, 32)     # weeks_in_office range where a strategic call is allowed
SNAP_POLL_MIN = 0.55       # combined gov poll share needed to risk an early call
SNAP_CALL_P = 0.15         # per-week chance while the window + poll gate hold
```

## Deferred

- **Player "call early election" action** — when the player is PM, the strategic-dissolution path becomes a player lever. Phase 4 (needs the career ladder to put players in the chair first).
- **Caretaker conventions** — a dissolved parliament's government technically lingers as caretaker; the sim has no governing-phase behavior during campaign anyway, so nothing to model.
- **Fixed-term veto** — some systems (UK post-2011, Norway) forbid early dissolution entirely; a scenario/difficulty flag, Phase 4.
- **Opposition-triggered no-confidence motions** — a weekly random chance for the opposition to table one. Real, but needs the opposition-play surface (Phase 4) to mean anything.

## Success criteria

- A `ConfidenceLost` with no viable alternative produces `ElectionCalled snap=True` — the same parliament does not silently re-form.
- A `ConfidenceLost` with a viable alternative majority still re-forms in place (constructive rule preserved).
- `SNAP_COLLAPSE_MAX` consecutive collapses force dissolution even when coalition math permits.
- Natural runs: snap elections occur on some seeds without occurring on all — government lifespans in the sweep gain a short tail below the 40-week cap.
- Deterministic by seed; no new I/O; all tunables in `params.py`.
