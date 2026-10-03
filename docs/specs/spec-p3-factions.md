# Spec P3.3 — Factions inside parties

Module id: `factions` (per `docs/specs/capability-map-p3.md`). Today party membership is flat — cohesion is one scalar and schisms erupt with no visible middle act. This module gives parties *wings*: detected ideological blocs that whip separately, feud visibly, and can secede as a bloc. The schism machinery already exists; factions are the texture before the break.

## Objective

A divided party should read as divided *before* it splits: "the Labour-left" whipping against a coalition bill, a faction leader positioned as heir-apparent, and a secession event that the chronicle explains in advance rather than surprising you.

## Mechanics

**Faction detection (not authored):**
- When a party's intra-party position spread exceeds `FACTION_SPREAD_MIN` (reuse the existing spread computation from `party_lifecycle`), members split into wings along the axis of maximum variance — members above/below the member-mean on that axis. Two wings max for now; a third requires the spread to stay bimodal anyway.
- Each wing gets: `Faction` record — id, name, centroid pos, member ids, and a *de facto leader* (highest-ambition member — used by leadership challenges, no separate election machinery).
- **Hysteresis**: factions don't re-cluster weekly. Re-detect only when membership changes by >20% or every `FACTION_RECHECK_WEEKS` (~12). A wing smaller than `FACTION_MIN_SIZE` (3) dissolves back into the party.
- Naming: `{Party} {direction}` — direction derived from the wing's centroid relative to the party's on each axis ("left"/"right" economic, "libertarian"/"traditional" social → "Labour-left", "Conservative-moderate" for a near-platform wing).

**Faction effects:**
- **Faction whip**: when a faction's centroid is far enough from a bill (`FACTION_REBEL_DIST`), the faction whips *its own* direction instead of the party's. In `vote_utility` this surfaces as a named `fwhip` term replacing `whip` for faction members — the `why` overlay must show it, or factions are invisible.
- **Feuds**: a faction's distance from party platform contributes to cohesion already via member spread — no new mechanic needed; factions make the *cause* nameable.
- **Secession**: replaces the ad-hoc schism path. When a faction's centroid drifts past `SECESSION_DIST` from platform for `SECESSION_WEEKS` consecutive weeks, the whole wing walks — `_found` the new party with the faction leader as founder and all wing members as followers. Event: `Secession` ("The Labour-left secedes — 11 MPs form the Socialist Alliance."). Keep `schism_cooldown`; one secession per party per week. (Simplified during implementation: the party-cohesion condition was dropped — the wing's own estrangement is the legible cause.)
- **What makes wings move**: MPs drift toward their district centroid weekly (`MP_DISTRICT_PULL`) — constituency pressure. Parties holding ideologically scattered districts organically grow spread; coherent parties stay tight. Without this, wing formation and secession never fire in unscripted play (verified: 0 events in 10 seeds × 300 weeks before the drift existed).
- **Old schism path**: the current "farthest member + followers within 0.4" logic is *deleted*, not kept as fallback — factions are the only route to multi-MP splits. Lone-founder defections (`_stay_utility` path) stay unchanged.

**Player hooks:**
- `mp.faction` shown on the inspect card and MP tooltips.
- The player can belong to a wing; a player-led faction secession is a career lever (Phase 4 makes it an action — here it's world machinery only; if the player's faction secedes, the player stays with the old party by default and gets an event).

**Events:** `FactionEmerged` (wings detected), `FactionRebels` (faction whips against party line on a vote — throttle: once per faction per bill), `Secession`, `FactionDissolved` (wing drops below min size).

## Boundaries

- Always: new constants in `params.py`; `fwhip` must be a named utility term (AGENTS.md rule); `state.emit` for anything drivers show.
- Ask first: changes to `vote_utility` signature or the `detail` schema drivers consume.
- Never: factions inside the voter model; more than 2 wings per party (k>2 clustering is complexity for no payoff at 120 MPs); player-targetable faction actions (Phase 4).

## Success criteria

- `checks/check_factions.py`: fixture a party with bimodal members → wings emerge with names/centroids → forcing a distant bill produces `fwhip` in vote detail and a `FactionRebels` event → sustained distance produces `Secession` taking the whole wing, parent party keeps its other wing.
- `check_parties.py`, `check_e2e.py`, `check_careers.py` stay green; the sweep should show *more* government instability variance than the current all-40 flatline (factions make coalitions brittle in legible ways — worth watching, not a gate).

## Open questions

- Should faction leaders get ambition-boosted leadership challenges (the heir-apparent pattern)? Cheap: challengers who lead wings get a bonus in `leadership_challenge` member voting — include if it's ~10 lines, else defer.
- Independent MPs (separate module) must be faction-free — they have no party, no wings.
