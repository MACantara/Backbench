# Spec M11: Evolve — the player can reposition

Every AI MP drifts toward their district weekly (`MP_DISTRICT_PULL`,
exempting the player — "the player's ideology is theirs to manage"),
but no action anywhere writes `player.pos`. The comment is a fiction:
you can drag the electorate to you (`campaign`, `speech`), pull the
party line (`platform`), or start over (`found`) — but you can never
move yourself. Meanwhile your district random-walks
(`VOTER_DRIFT_SD`), your faction's centroid recomputes around you,
and the challenge-vote's first term is `-dist(voter, candidate)`.
Repositioning is an electoral lever, a faction lever, and a
leadership lever — and it's the one lever the player doesn't have.

Done-when: **the player can slide their position toward a chosen
anchor at a credibility price that scales with the distance jumped —
cheap to evolve, expensive to flip — and the bot repositions when
its seat is lost on ground, not on turnout.**

Scope: the `evolve` action, its cost model, legibility, bot use.
Out of scope: AI repositioning strategy (they keep ambient drift —
they have no agency to spend), a free-position picker in the UI
(drivers offer named anchors; `Action.pos` is already general).

## 1. The action

`evolve` joins the always-available picks (it matters most in
campaign phase, but MPs reposition in office too):

```python
new = clip(pos + EVOLVE_STEP * (action.pos - pos), -1, 1)
```

A lerp, not a jump — `EVOLVE_STEP = 0.15` of the gap per action, so
repositioning converges asymptotically: spamming gives shrinking
steps and the price meter reads real distance. `action.pos` supplies
the anchor; `None` defaults to the district centroid.

Driver anchors (the UI names the move, the sim only needs the point):
- **toward district** — the median-voter reposition, the electoral one
- **toward party** — trimming to the line, the career one
- pyg: two buttons on the action row like `defect`; terminal:
  `evolve district|party`

## 2. The price — you can't launder a flip

Two meters notice, in different currencies:

- **The district** (`EVOLVE_BETRAYAL_W = 0.2` per unit moved, on
  `v.betrayal`): a slide across the space accumulates ~`0.2 × gap`
  of district mistrust — lerp steps can't dodge it, the sum equals
  the distance covered. Scale check: a defection is 0.35; a full
  reposition ~0.6 move costs ~0.12 — real, survivable, honest.
- **The party** (`EVOLVE_STANDING_W = 0.5` on the platform-distance
  delta): trimming *toward* the line pays standing — the whip notes
  a trimmer; drifting *away* costs — the whip notes a wobbler. Same
  formula both directions: `standing += W × (d_old − d_new)`.

The event is honest about the direction: `"You edge toward your
district (+0.09) — the voters notice (+0.02 mistrust), the whip
notes the trim."`

Faction membership rides free — centroids recompute on their own
cadence; slide far enough and you wake in a different wing, which
the next challenge preview will show.

## 3. Legibility

- `explain_action("evolve")`: the anchor, the step distance this
  action would actually move (`EVOLVE_STEP × gap`), the projected
  betrayal cost, and the standing direction — stated numbers, the
  same expressions `apply_action` applies.
- The district card / party card already show positions — your slide
  is visible on both by inspection, no new surface needed.
- `explain_mp` prints `pos` already; a `CareerEvent` per move keeps
  the chronicle honest: the record shows *when* you moved.

## 4. The bot repositions when the ground is the problem

`_r_seat_defense` currently campaigns on a bad forecast regardless
of *why* it loses. New gate: when the projection is losing **and**
`dist(player.pos, district centroid) > BOT_EVOLVE_GAP (0.5)`, the
ground — not the ground game — is the problem: take `evolve` toward
the centroid instead of another knock. A player-shaped move: you
knock doors when the seat is close, you reposition when it's not
your seat anymore.

## 5. Checks

`check_actions` or a new `check_evolve.py`: pos moves by the lerp;
betrayal accrues ∝ actual distance (two halving moves ≈ one move's
sum); standing gains toward the line and loses away; `explain_action`
shows the same numbers apply uses; the bot takes `evolve` under a
forced losing-forecast with a position gap; `available_actions`
includes it every phase; determinism holds.

## Atomic commits

1. `docs: m11 evolve spec`
2. `feat: evolve action — costed repositioning`
3. `feat: driver anchors + explain`
4. `feat: bot repositioning gate`
5. `polish: checks + sweep`
