# Spec M2 — Playable Career

Milestone spec (see `ROADMAP.md` milestones). Scope: **career ladder, appointment logic, "why wasn't I picked"**. Done-when: an honest run can reach ministerial office — the measured failure is 1100 weeks of honest play, 23 terms, zero promotions while AI MPs collect 115.

## Objective

The climb becomes a strategic problem instead of a fixed-stat lottery. Three moves, each boring on its own: a movable standing currency, a junior rung layer, and an appointment score the player can read and move.

## Diagnosis

`_appoint` picks argmax of `competence + loyalty + seniority_norm × SENIORITY_W` — all worldgen-fixed draws. The player is eligible (they're a party member) but the same argmax wins every vacancy, forever. Meanwhile `lobby`/`scheme` build `relationships` that feed `vote_terms["rel"]` and `leadership_challenge` — but appointment never reads them. Actions exist; the ladder doesn't see them. And there are no rungs: 5 cabinet posts in a ~150-seat parliament, so promotion means beating the whole party at once, invisibly.

## Mechanics

### Standing — the movable currency

- `MP.standing` (float, clipped [-1, 1], weekly decay toward 0 via `STANDING_DECAY`). Accrues for **all** MPs — the world keeps generating its own climbers; the player's edge is deliberateness, not asymmetry.
- Earned on observable behavior: **whip fidelity** — in `resolve_vote`, a whipped MP (nonzero `whip_direction`) who votes with the line gains `STANDING_WHIP_YES`, against loses `STANDING_WHIP_NO` (free votes don't move it; confidence votes count — loyal soldiering is standing); **party service** — the `constituency` action adds `STANDING_SERVICE`; **office** — holding a junior or cabinet post pays a small weekly trickle.
- Lost on: `MinisterSacked`/`scandal sack` (−`STANDING_SACK_HIT`), active scandal weeks, whip rebellions.

### Junior rungs — the ladder needs low rungs

- `MP.junior: str | None`, `MP.junior_weeks: int`. Per-party posts: `JUNIOR_POSTS` (Whip, Spokesperson, Committee Chair) — they exist in **opposition parties too**, so the climb isn't hostage to your party governing.
- Appointed by party leadership on the same decomposed score as cabinet picks; filled at each new parliament and refilled same-week when vacated (promotion to cabinet vacates a junior slot — someone else climbs; the ladder visibly moves). Vacate on defection/retirement; `Government.sacked` gates both levels.
- Payoff: the standing trickle + a `rung` term in the cabinet score (`min(junior_weeks / RUNG_CAP, 1) × RUNG_W`) — proven juniors get picked.

### Decomposed appointment score

`_appoint` becomes named terms, same discipline as `vote_terms`:

- `record` — competence + ministerial perf where applicable (the merit ceiling; stays fixed — ability isn't earned, only proven)
- `standing` — `STANDING_W × standing`
- `backing` — `BACKING_W × relationships[party leader]` — the leader picks; lobby/scheme now pay into the climb
- `seniority` — unchanged term
- `rung` — junior service

AI candidates are scored identically — no player carve-out.

### Legibility — why wasn't I picked

- `Promoted`/junior-appointment events carry the winner's term dict in `data`.
- When the player was an eligible candidate and lost: `CareerEvent` "Passed over for Finance — Ines Marlow picked (you ranked 4 of 12): her record +0.9, your standing +0.5" — winner's top terms vs the player's, plus rank. A rank you can watch improve is a game; an invisible argmax is not.
- `explain_mp` gains a candidacy line for the player: their terms and predicted rank for the next vacancy in their party.
- `update_score` counts a `junior` term (+1 per election survived in post) — the ladder pays even below cabinet.

### Already works, kept honest

- `leadership_challenge` already reads `relationships` — lobbying colleagues pays at the top rung too. Add a small `standing` term to challenger support (members back proven climbers). Provoking a challenge is deliberately not player-reachable yet — that's M3 strategic politics.

## Boundaries

- Always: `params.py` for every constant; named terms for the appointment score; `state.emit` for legibility (drivers get passed-over events for free); standing accrues inside `resolve_vote`/lifecycles, not in action handlers.
- Ask first: player-as-leader choosing junior appointments (belongs to M3/M4 player-agency surfaces).
- Never: player-only mechanics (AI MPs must earn standing and climb the same ladder); a second hidden currency duplicating `relationships`; competence growth (the merit ceiling stays fixed — that's what separates careers); leadership-coup actions (M3).

## Success criteria

- `checks/check_ladder.py`: a scripted climber policy (lobby the party leader, constituency work, never rebel) reaches a junior post then a cabinet portfolio across N seeds — while a passive-player control reaches none or near-none. The delta is the game.
- `check_careers`/`check_player`/`check_ministerial` stay green; standing decays, whip fidelity moves it in a forced fixture.
- `check_sweep` career row extends: junior posts filled, ladder churn (promotions vacating juniors → refills).
- The done-when: an honest run *can* reach office — measurable, not hoped.

## Deferred on purpose

- Conscience-vote action (M3 — `player_vote` hook already exists), kingmaking (M3), abstention/attendance (M3).
- Player-as-leader appointment choices; provoking leadership challenges; patronage posts (the portfolio table already appends).
- Competence/experience growth arcs; by-elections (still deferred from P3 careers).
