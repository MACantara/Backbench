# Spec P3.2 — Scandal lifecycle

Module id: `scandal-lifecycle` (per `docs/specs/capability-map-p3.md`). Today `mp.dossier` is write-only for AI MPs — `dig_dirt` piles material on them and nothing ever consumes it; the only reader is `check_expulsion`, an instant game-over for the player. This module gives dirt a lifecycle: it accumulates, simmers, surfaces (often at the worst moment), burns for weeks, and ends careers — AI ones too.

## Objective

Scandals should read as a story arc in the chronicle — leak → weeks of pressure → resignation or survival — not a single-line event. Careers should sometimes end in flames, and the vacancy machinery from `ai-careers` should get exercised hard.

## Mechanics

**Latent dirt (all MPs, all weeks):**
- AI MPs accumulate dossier on their own: `dossier += DIRTY_GROWTH * (1 - integrity)` per week — low-integrity MPs collect material; high-integrity ones stay mostly clean. dig_dirt and gaffes add on top as today.
- Dossier never decays — kompromat is forever.

**Surfacing:**
- Weekly leak probability scales with dossier size: `p = LEAK_BASE_P * dossier`, capped at `LEAK_MAX_P`.
- **October surprise:** when `weeks_to_election <= ELECTION_LEAK_WINDOW`, multiply by `LEAK_ELECTION_MULT` — dirt detonates when it hurts most.
- On surface: `ScandalBreaks` event (interrupt-tier) naming the MP and rough severity; the MP enters active scandal for `SCANDAL_WEEKS` (rolled 3–6).

**Active scandal (weekly while burning):**
- Party `brand` bleeds (`SCANDAL_BRAND_HIT`); a *minister's* scandal hits government parties harder.
- The MP's district feels it: voter `betrayal` rises in their district → `seat_safety` erodes at the next election.
- Party leader makes a rule-based call at leak time for members (not for themselves): if `dossier > SACK_THRESHOLD` → expel the member immediately to contain the damage (`Expelled` event; member removed via `remove_mp` → vacancy). Below threshold → ride it out.
- If the MP holds a portfolio: PM (leader) sacks them or defends them — `MinisterSacked` event (loses portfolio, keeps seat) vs continued brand bleed.
- Per-week resolution roll while active: `RESIGN_BASE_P + dossier * RESIGN_DOSSIER_W` → `Resigned` event → `remove_mp` → vacancy. Survive the duration → `ScandalWeathered`, small permanent brand scar, dossier reduced by `WEATHERED_BURN` (the material is spent).

**Player treatment:**
- Same lifecycle: dossier ≥ leak probabilities apply to the player too. When the player's scandal breaks, it's an interrupt with weeks of pressure — `Resigned` for the player = game over (`SeatLost`-equivalent ending). `check_expulsion` is removed — the instant-kill threshold is replaced by the lifecycle (dossier > SACK_THRESHOLD → the party expels the player → game over with a different epitaph).
- `dig_dirt` semantics unchanged (adds dossier) — but now it has teeth: dug material raises the victim's leak probability permanently. Timed *release* control (choose when to detonate) is Phase 4 "scandal as a weapon" — this module only makes dirt dangerous.

**Events:** `ScandalBreaks` (interrupt), `Expelled`, `MinisterSacked`, `Resigned`, `ScandalWeathered`.

## Boundaries

- Always: constants in `params.py`; `state.emit` for anything drivers show; `remove_mp` for all departures (leader succession and PM handoff ride free).
- Ask first: changing `check_expulsion` semantics — the player ending must stay *possible* but moves from instant to lifecycle.
- Never: dossier decay; scandal effects in the voter-ideology space (they hit brand + district betrayal, not positions); per-MP action menus for AI; player-controlled release timing (Phase 4).

## Success criteria

- `checks/check_scandals.py`: fixture a dirty low-integrity MP → scandal breaks within N weeks → either `Resigned` + vacant district or `ScandalWeathered`; fixture a minister past `SACK_THRESHOLD` → `Expelled`/`MinisterSacked` fires; a long unscripted run produces AI scandals with zero player input; a player past the expel path reaches game-over via the lifecycle (not instantly).
- `check_player.py`, `check_e2e.py`, `check_careers.py`, `check_parties.py` stay green — `check_player`'s expulsion assert needs updating to the lifecycle path.
- Vacancy frequency rises — revisit whether deferred by-elections now matter (the map's stated trigger).

## Open questions

- Multiple simultaneous scandals on one party — do brand hits compound linearly? Yes, capped at a per-week party bleed max to avoid death spirals.

## Deferred

- **Scandal-hit MPs voting differently** (distancing from their whip while defending themselves) — deferred to a later phase. Keep scandal out of `vote_utility` for now; brand + career stakes carry the drama. Revisit if the lifecycle plays flat.
