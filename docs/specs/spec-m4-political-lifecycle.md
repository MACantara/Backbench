# Spec M4: Full political lifecycle

Decisions have lasting consequences. The world already generates laws, budgets,
dossiers, and defections — M4 makes them *owned*: statutes have authors who
watch them repealed, budgets are real fiscal bills the player votes on, the
opposition benches are a playable position, the player can cross the floor, and
dirt becomes a timed weapon.

Done-when (roadmap): **an AI government can repeal the player's flagship law;
losing supply is a crisis, not a footnote.**

Scope: legislative legacy (repeal/sunset/authorship), budget power (supply as
a real bill), opposition role (scrutiny/amendments/self-preservation), cross
the floor (defect/found/independent), scandal as a weapon (timed leaks).

## 1. Legislative legacy

The registry is append-only — nothing political ever removes a law (only the
courts strike). Three mechanisms make the statute book a living instrument.

- **`Bill.repeals: Law | None`.** A repeal bill is a normal bill whose enact
  removes its target: `LawRepealed` names the statute and its `enacted_by`
  parties — dismantling someone's record is a brand event for *them*. If the
  law's `author` is the player, the event says so — that's the flagship dying.
- **`Law.author: int | None`** — the PM's id at enact time (None for a private
  member's bill → the tabling MP). `legacy_bills` counts laws the player
  authored (as PM or privately), so score already means "things I built".
- **AI repeal logic.** In `table_bill`, at `REPEAL_P` per week the government
  tables a repeal of the *most hostile* standing law — max `dist(law.pos,
  gov_platform)` — excluding laws passed **this term** (a government doesn't
  repeal its own session's work, but inherited statutes are fair game even
  when a predecessor shared a party — coalitions re-share core partners, so
  authorship-exclusion would gate repeal to ~never). Repeal bill
  `pos = gov_platform` (repealing IS the government's agenda — a mirror
  position empirically loses the coalition's own whip); the law's authors
  defend through their policy/district terms.
- **Sunset.** Statutes past `SUNSET_WEEKS` roll `SUNSET_P` weekly to lapse
  (`LawLapsed` — the book quietly prunes itself). The 893-law ratchet never
  reforms; `debt_max` watch item gets worse before better — flag for the
  balance pass.
- **Retable (cheap).** Failed ordinary bills sit in `state.failed` with a
  week stamp; past `RETABLE_CD` weeks and still agenda-aligned, `RETABLE_P`
  re-tables one ("returns with a revised…"). No repeats of the same failure.

## 2. Budget power — supply as a real bill

Today `BUDGET_EVERY_WEEKS` fires `confidence_vote` with a bare `Bill` —
immediate, no fiscal content, the player can't vote on it (the M3 pending
cadence never sees it). Supply becomes real:

- `Bill(budget=True, confidence=True)` carries a **posture**: `tax`/`spend`
  multipliers derived from the coalition agenda's economic axis (market
  governments cut, left governments spend, debt pressure tightens everyone).
- **Cadence**: on budget weeks `table_bill` produces the budget bill into
  `state.current_bill` — pending like everything else, divided next week,
  fully legible via `explain_bill`, open to `vote`/`deal`. This is the
  milestone's payoff for M3's cadence.
- **Enacted**: `treasury.posture = (tax, spend)` applies until the next
  budget — `revenue()` reads `tax`, `upkeep()` reads `spend`, and `spend`
  nudges the `services` dial weekly (austerity starves services voters feel).
- **Lost**: `res is False` on a confidence bill routes the collapse path —
  the *same* machinery `confidence_vote` uses, extracted so both the
  pending-cadence budget and forced-crisis votes share it. The event text
  names it: "Government loses supply" — a dissolution/formation follows, and
  a government with no supply can table no new business while caretaker.
- **Player as PM**: a `budget` action (0=austerity / 1=balanced / 2=stimulus)
  sets the posture before the budget week — the player writes their own
  supply bill and owns the result.
- `confidence_vote` stays as the *forced* path (debt crises demand immediate
  confidence); it shares the collapse helper.

## 3. Opposition role

Out of power shouldn't be dead time. Three small weapons plus the deferred
term the scandal spec called for.

- **`selfpreservation` vote term** — an MP with a burning scandal distances
  from the party line: `terms["selfpres"] = -W_SELFPRES * whip` when
  `scandal_weeks > 0` and whipped. Named, inspectable, makes a scandal-hit
  backbencher countable against their own whip.
- **`attack` action** (opposition player only): parliamentary scrutiny —
  succeeds with probability scaled by `-mood` and the worst minister's `perf`;
  on a hit, government parties bleed brand and the player banks
  `ATTACK_STANDING` (opposition profile is party service); on a whiff, a
  small own-brand cost. Attacking a popular government should mostly whiff.
- **`amend` action**: move the pending bill's `pos` by `AMEND_STEP` toward
  the player's pos — one amendment per bill (`bill.amended` flag). Real
  procedural power: dragging a bill away from a coalition partner's platform
  can break their own whip line. Works on the backbench and in government.
- **`table` action** (non-government player only): a private member's bill —
  `Bill(pos≈player.pos)`, divided *immediately* (PMBs don't occupy the
  government agenda slot). It won't carry a whip; a genuinely popular bill
  can still pass, and if it does the player is its `author` — legacy from
  the backbenches.

## 4. Cross the floor

The player is currently the only MP who can never leave their party.

- **`defect` action**: `target` = party id (or none → sit independent).
  Westminster rules: the receiving party can't refuse. Costs ride existing
  machinery — old party members' relationships burn (`DEFECT_REL_HIT`), the
  district's `betrayal` rises (`DEFECT_BETRAYAL`), `standing` resets to 0
  (party-internal currency doesn't transfer), `junior`/`faction` strip.
  A portfolio dies with the party tie — defecting ministers fall to the
  backbench immediately, not next tick.
- **Defecting PM forfeits the premiership** — you can't lead a coalition
  you walked out of; `government.pm` reverts to the old party's leader.
- **`found` action**: `_found(state, player_id, followers)` — followers are
  old-party members with `rel > FOUND_REL_MIN` and low `_stay_utility`
  (they choose to walk; you don't hand-pick). The founder is leader; the
  vehicle is named by the existing convention. Founding from no party is
  allowed (an independent launches a vehicle).
- AI symmetry stays where it is — AI defection-to-existing-party is a
  candidate follow-up but not required this milestone; the point is the
  *player's* franchise.

## 5. Scandal as a weapon

`dig_dirt` grows dossiers; the leak roll decides timing. Weaponization = the
player chooses the moment.

- **`leak` action**: target an MP whose dossier exceeds `LEAK_MIN_DOSSIER`;
  the dossier detonates now — the same `ScandalBreaks` path a natural leak
  takes (election-window multiplier applies — October surprises are a play).
- **`LEAK_TRACE_P`**: a traced release burns the target's relationship with
  the player and marks the player (`+LEAK_CAUGHT_DIRT` dossier) — leaking is
  deniable but not free. Dirt too small to ignite can't be leaked at all
  (visible in `explain_mp`, so targeting is informed).
- Deferred: trading silence (favors-for-dirt needs the M6 economy), AI
  weaponizing the player's dirt (AI leaks need rival-MP motive modeling —
  the player's own `dossier` visibility already makes "is my dirt
  survivable" a readable decision).

## Boundaries

**Always**: `params.py` for every constant; named vote/appointment terms;
`state.emit` for every legibility surface; seeded RNG only; `tick()` is the
only mutation path drivers touch.

**Never**: constitutional amendment bills (need M5's constitution object);
court appointments; press relations; AI→player deal offers (M3 deferral
stands); money/bribery (no economy); per-provision bill drafting.

## Success criteria

- `check_legacy.py` — fixture: player-authored law in force; hostile AI
  government tables a repeal; passed repeal removes the law (effect + upkeep
  stop same week) and `LawRepealed` names it. Sunset lapses an aged law.
  Budget: enacted posture shifts `flow()` measurably; a lost budget runs the
  collapse path and names supply.
- `check_floor.py` — defect moves the player, costs apply (betrayal, rel
  burn, standing reset, portfolio stripped); defecting PM loses the office;
  `found` spawns a party with relationship-gated followers; `leak` detonates
  a dirty MP and the trace cost fires.
- `check_opposition.py` — `attack` whiffs on a good-mood government and lands
  on a slumping one; `selfpres` term appears in a burning MP's `vote_terms`;
  `amend` moves bill.pos once; a private bill can pass.
- The invariant sweep re-reads: `laws in force` should *fall* (repeal +
  sunset), `debt_max` watch item confirmed, government survival may dip
  (supply is now a real division the player can spoil).

## Open questions

- Should a repealed law's `enacted_by` parties take a brand *hit* (record
  dismantled) — or does repeal mainly vindicate the repealer? Currently
  specified as the former (symmetric with `LawStruck`).
- One amendment per bill is a convenience cap, not a principled one —
  revisit if amending feels like free agenda control.
