# Spec P3.5 — Country conditions

Module id: `country-conditions` (per `docs/specs/capability-map-p3.md`). Today voters are purely spatial — there is no country to run, only opinion. `brand` is a media-driven reputation channel; nothing models *objective conditions* an electorate could judge a government on. Passed bills nudge `voters.pos` (persuasion) and vanish — no marks on the country. `Bill.cost` is written nowhere and read nowhere. This module adds the country itself: a small set of indicators that evolve on their own logic, a law registry so legislation leaves persistent marks, and retrospective voting so electorates reward and punish governments for results, not positions.

## Objective

Governments should sometimes fall because the economy tanked — a legible, non-ideological cause in the chronicle: *recession → polls sag → incumbent routed*. Legislation should accumulate into a visible legislative history that courts (P3 `courts`) and repeal mechanics (P4) can act on later.

## Mechanics

**Indicators (`Conditions` dataclass on `GameState`):**
- Five national indicators: `growth` (-1..1, contraction..boom), `unemployment` (0..1), `inflation` (0..1), `services` (0..1, public-service capacity — slow-moving), `crime` (0..1). Seeded near baseline at worldgen.
- Derived scalar `mood` (-1..1): `w·growth + w·services − w·unemployment − w·inflation − w·crime`, weights in `params.py`. `mood` is the number voters feel — shown in inspect.
- Weekly evolution: mean-reverting drift toward baseline + seeded noise + pairwise couplings (`growth↑ → unemployment↓`, `unemployment↑ → crime↑`, `services↑ → crime↓` slowly). A handful of explicit params — no coupled ODEs.
- **Shocks:** rare stochastic jumps (recession, boom, crime wave) — ~one per term. `Shock` event with direction; interrupts only for the big ones, media covers them for free.

**Law registry (`GameState.laws: list[Law]`):**
- `Law` dataclass: `name`, `pos`, `beneficiary_axis`, `cost`, `passed_week`, `margin`, `effect`.
- On a passed `VoteResult`, the bill enters the registry. `name` is a placeholder ("Week-42 Act") until the procedural-naming module lands; `cost` rides along for the treasury module.
- Each law carries a small constant weekly `effect` on one indicator, derived legibly from position: axis-0 right → `growth+`, axis-0 left → `services+`; axis-1 authoritarian → `crime−`, libertarian → `crime+`. Magnitude ∝ axis extremity — moderate laws barely move the country, radical ones move it visibly. Effect applies while the law is in force, inside the conditions lifecycle.
- Laws persist indefinitely until repealed (P4) or struck (P3 `courts`). The voter-persuasion nudge in `resolve_vote` stays — that's a different channel (the bill moves opinion AND the country).

**Retrospective voting:**
- In `_district_scores` and `poll`: a named additive term `retro = RETRO_WEIGHT * mood * share`, where `share` is the party's responsibility in the outgoing government. Parties outside the coalition get 0.
- **Clarity of responsibility:** the PM's party takes `RETRO_PM_SHARE` of the credit/blame; the remainder splits evenly across junior partners. A single-party majority is punished cleanly; coalition blame diffuses — the real-world pattern.
- `state.government` persists through `resolve_election` into the next formation, so the *outgoing* government is the one judged at the ballot — no special casing needed.
- **Confidence pressure:** `vote_terms` gains `retro` on confidence bills only — coalition backbenchers get `W_RETRO_CONF * mood` (negative in a slump). Mid-term collapse becomes possible for the same legible reason elections turn. This is the one change to `vote_utility` in the module — flagged, deliberate.

**Tick order:** `conditions_lifecycle(state)` runs in the lifecycle block immediately before `media_lifecycle` — indicator drift, law effects, and shock rolls settle before the press reads the week. Registry writes happen inside `resolve_vote` where the bill context lives.

**Events:** `Shock` (variant + direction + magnitude), `LawEnacted` (name, effect summary — for the chronicle and later court review). Indicator values surface via inspect, not event spam.

**Inspect:** `player_status` gains a country line (indicators + mood) and a laws-in-force count; the pygame driver gets the same readout — display only, no sim logic in driver.

## Boundaries

- Always: constants in `params.py`; `state.rng` only; effects legible (a law's indicator effect is visible on the law, `mood` decomposition inspectable); `retro` stays a named term in both voter scoring and `vote_terms`.
- Ask first: the `retro` term on confidence bills — it makes mid-term collapse mechanically possible; it's the module's core promise but it touches `vote_utility`.
- Never: per-district conditions (national only — a regional economy is a different game); monetary/fiscal policy levers (that's `treasury`); conditions writing to `brand` (brand is media's channel, retro is the objective channel — no double-counting in scoring); conditions moving voter *positions* (mood is valence, not ideology); automatic government policy responses.

## Success criteria

- `checks/check_conditions.py`: pass a far-axis-0 bill → the mapped indicator drifts the expected direction over N weeks; fixture a crashed `mood` → governing party's poll share drops vs an identical-mood-good control; coalition vs single-party government → PM-party `retro` term larger in the single-party case (clarity); bad-mood coalition MPs defect on a confidence vote where good-mood control doesn't; across seeds a `Shock` fires within a bounded window and appears in `Headline` coverage; same seed → identical indicator trajectory.
- `check_election.py`, `check_parliament.py`, `check_e2e.py`, `check_media.py` stay green — `retro` is additive and zero when there is no government.
- `check_sweep.py` stays healthy — target: mean term length drops a few weeks (recessions now fell governments) without p10 collapse.

## Open questions

- Should bad `mood` raise axis-0 salience (priming — voters attend to the economy when it hurts)? Deferred — outlets already move salience via `focus_axis`; a mood→salience channel is a cheap later add if elections don't feel responsive.
- Should opposition parties gain *positive* share when mood is bad? No — relative scoring already transfers the lost votes; explicit opposition credit would double-count.

## Deferred

- Treasury reads indicators for revenue (`treasury` module) — `conditions` is its dependency.
- Ministerial performance maps portfolios to indicators (a bad economy lands on the Chancellor).
- Repeal/strike mechanics on the registry (P4 legislative legacy / P3 courts).
- Named laws (procedural naming module fills `Law.name` properly).
- Per-district conditions — never; national mood only.
