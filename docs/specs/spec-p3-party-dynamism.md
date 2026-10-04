# Spec P3.8 — Party-system dynamism

Module id: `party-dynamism`. The 1100-week observation rewrote the phase: **every seed converges to a two-party duopoly by ~week 300 and never recovers.** The lifecycle has only a death channel — `PartyDissolved` fires on electoral wipeouts — while the birth channels are unreachable: `PartyFormed`=0 and `Secession`=0 in 1100 weeks because `stay_utility` floors at ~0.64 vs the 0.2 founding threshold, and intra-party spread runs 0.06–0.23 vs the 0.45 faction gate. Duverger wins after all — the deliberate anti-Duverger design (FPTP, no strategic voting, multiparty drama) needs a countervailing *entry* channel, not just lower barriers.

## Objective

The party system should *breathe*: parties die on wipeouts (works), parties are born where politics is unserved (missing), wings form and occasionally walk (gated too hard), and a wiped-out space attracts re-entry. Long-run seat-ENP (Laakso–Taagepera: `1/Σ share²`) should sit in a multiparty band across seeds — not a fixed count, but never locked at two. Every birth is legible: the event names the space it entered.

## Mechanics

**Niche entry — the missing birth channel:**
- During the **campaign phase** (before `resolve_election`, so entrants contest immediately via placeholder candidates), measure *coverage*: each district centroid's distance to the nearest party platform. Districts past `DYNAMIC_GAP_DIST` are unserved.
- If the largest unserved *cluster* (adjacent unserved districts sharing a region, ≥ `DYNAMIC_GAP_MIN_SEATS` districts) clears the bar, a new party declares: platform = the gap's voter centroid (+ small jitter), name via `party_name_for` — Meguid's niche entry: parties enter where mainstream parties vacated space. Emit `PartyFormed` with `kind="entry"` and the gap's size — already newsworthy (weight 1.5).
- Rate limit: at most `DYNAMIC_ENTRIES_PER_ELECTION` entrants per election, and only while `len(parties) < PARTY_COUNT_RANGE[1] + 2` — a hard ceiling so births can't run away.

**Reconstitution — wipeouts get heirs:**
- Keep a short memory of recently-dissolved parties (`state.graves`: name, platform, weeks-dead, capped list). When a gap overlaps a grave, the entrant is a *revival*: `"Second {dead name}"` via the ordinal fallback convention, `kind="revival"` — real convention (parties re-form), and legible: the chronicle reads "Second Homeland Party founded in the space the Homeland Party left."
- Revivals inherit nothing but the name's ideological address — no members, no brand (brand starts 0; a resurrection discount on the orphan voters' loyalty is honest but tunable via `REVIVAL_LOYALTY_W`).

**Faction gate recalibration — wings are normal, secession is rare:**
- `FACTION_SPREAD_MIN` 0.45 → ~0.18: wings form whenever a party spans real internal distance, which is most parties most of the time — real parties always have wings. The *rare* event stays downstream: `SECESSION_DIST` (0.5) + `SECESSION_WEEKS` (6) already gate the walkout, so raising wing frequency raises rebellion/rebel-whip texture without flooding the log with splits.
- Secession frequency is self-limiting (estranged wings that walk leave a more cohesive parent); target ~0–2 per term across seeds, not a quota.

**Founding path recalibration — misery must be reachable:**
- `_stay_utility` currently can't dip below ~0.5 in practice (proximity term `max(0, 1-dist)` ~0.25 + cohesion ~0.4 + portfolio bonus). Re-derive so a genuinely alienated MP scores low: portfolio absence penalized, intra-party distance weighted harder, faction-estrangement counted. Then `PARTY_FORM_STAY_UTILITY` retunes to catch ~0–1 founders per term — lone-founder "Surname List" vehicles (they'll mostly die next election, which is the correct fate of personal vehicles).
- The founder gate keeps `ambition > 0.6` — desperation requires ego.

**Anti-runaway guards:**
- Births only where a measured gap exists; deaths unchanged (wipeout → dissolve). Net drift is set by the gap threshold, not a target count — the system self-corrects: a crowded field has no gaps to enter.
- The Duverger asymmetry is now honest: fragmentation is bounded above by entry requirements and below by the birth channel.

## Boundaries

- Always: everything seeded from `state.rng`/`np_rng`; thresholds in `params.py`; `PartyFormed`/`Secession`/`PartyDissolved` events carry a `kind`/`cause` so inspect and media can say *why*; entries happen during campaign so they contest the imminent election.
- Ask first: `state.graves` (new state field — small); changing `FACTION_SPREAD_MIN` (a gameplay-visible retune — wings will appear where none did; measured spreads say 0.45 is unreachable so the current gate is dead code, but the target value is a judgment call).
- Never: player-facing founding changes (P4 "Cross the floor"); player dragged into AI secessions (already exempt); births mid-term (parties enter *electorally*); strategic-voting machinery (the anti-Duverger choice stands); LLM anything.

## Success criteria

- `checks/check_party_dynamism.py`: drive several seeds 300+ weeks — assert `PartyFormed` fires with `kind` populated; a killed party's space produces a `kind="revival"` entrant within a few elections; wings form on parties with spread ≥ the retuned gate; party count stays ≥3 through 300 weeks on most seeds (duopoly should be a possible *outcome*, not the attractor).
- Sweep measurement: seat-ENP across 20 seeds × 300 weeks — median ENP in a multiparty band (≥2.0, no ceiling assertion beyond the entry cap), and ≥1 `PartyFormed` per run on most seeds. Existing `check_sweep` must stay green — more entries means more competition; watch for destabilized government medians and adjust entry cadence, not the collapse mechanics.
- `check_factions.py`, `check_parties.py`, `check_election.py`, `check_e2e.py` stay green — retuned constants may need fixture updates (documented, not silent).

## Deferred

- Snap elections on collapse (separate `snap-elections` module — this one makes falls survivable for the system, that one makes them electoral).
- Independents contesting gaps (the `independents` module — a lone district's gap could spawn an independent rather than a party; the gap detector is shared substrate).
- Player-triggered new parties (P4 "Cross the floor" — the player should get the same entry machinery when they defect).
- Platform *drift* of living parties toward their members (parties currently never move; adaptive-position models are a later module — entry alone should already break the duopoly).
- Loyalty decay for orphaned voters (a dissolved party's `last_party` keeps pointing at the grave until they vote — revivals reclaiming them cheaply is tunable, not assumed).
