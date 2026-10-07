# Spec M8: The bot plays the game

The spectator bot is a survivor, not a player. It votes the whip, does
casework, lobbies the leader, and fills quiet weeks with voters — it
never touches the toolkit that makes or ends careers: no attacks, no
dirt, no leaks, no bills of its own, no floor-crossing, no ambition.
Auto-play therefore spectates a career no human would actually play,
and its failures tell us nothing about the game a player faces. M8
turns the bot into a real playtester: it declares an ambition, plays
toward it with the full action menu, takes computed risks, and leaves
a decision trace so a dead run is tuning data, not a mystery.

Done-when: **a spectated run reads like a career — an ambition
declared, the full toolkit used, risks taken and paid for — and every
run ends with a reviewable box score (office reached, cause of death,
rules fired) per seed.**

Scope: bot policy only. No new mechanics — the sim's action surface
already does everything; the bot has to be willing to use it.

## 1. Persona — the bot declares an ambition

Today spectate runs skip the ambition pick entirely
(`terminal.py` gates it on `not spectate`; pyg auto-play stalls on the
week-0 choice). The bot declares one like a player:

- `bot_pick_ambition(state) -> str | None` chooses via `state.rng`,
  weighted by feasibility — `founder` is silly when the party is a
  good home, `pm` is natural from a safe seat, `survivor` from a
  marginal one. Draws ride `state.rng`, same as any future bot draw.
- The ambition sets a **strategy profile** — a priority ordering over
  the rules below. `pm` climbs the ladder and plays coalition
  politics; `reformer` tables and amends; `founder` builds a bloc and
  walks; `survivor` keeps the seat; `majority` leads the party toward
  a one-party house. `None` (sandbox) stays available for manual
  runs — the bot always declares, because a declared arc is
  measurable: met/failed is data.

## 2. Rule pipeline — priorities, not a fixed list

`auto_actions` becomes an ordered pipeline of small rules
`(state, ctx) -> Action | None`, sharing one context (`menu`, `spent`,
the `take` budget check, computed helpers). Order:

1. **Threats** — seat danger (existing marginal-seat rule), dossier
   heat (below), party collapse (§4).
2. **Duties** — `vote`, `pick_offer`, and the PM's desk
   (`appoint`, `budget`, `amendment`) — unchanged rules.
3. **Ambition plays** — the profile's signature moves.
4. **Relationships** — lobby/scheme/court/deal, target chosen by the
   profile (ladder rival, coldest outlet, swing voter for a pending
   bill).
5. **Filler** — speech/constituency/campaign, unchanged.

A rule fires at most one action; the pipeline walks until points run
out or no rule fits. Same `Action`, same `available_actions` gate,
same `ACTION_POINTS` — the bot is still bound by the player's economy.

## 3. The full toolkit, gated by the odds a player reads

Every kind the bot never touches gets a rule gated by the same
expressions `explain_action` surfaces and `apply_action` rolls
against — the bot plays the numbers, not vibes:

- `attack` (opposition): when the computed land-chance clears
  `BOT_ATTACK_MIN`, or the government is already weak.
- `media`: when a warm outlet exists and the gaffe risk is
  acceptable; skipped under dossier heat.
- `dig_dirt`: on a ladder rival blocking promotion or a vulnerable
  minister — a target with a reason, not a random MP.
- `leak`: routed by venue like a player — friendly desk for a safe
  leak, hostile desk when swinging at a strong target; dossier on the
  target required.
- `promise`: when the seat is marginal near an election — and only
  promises the bot's position can honor, because kept promises score
  and broken ones punish. This is a test of whether the promise
  economy is fair.
- `table`: reformer profile, or when the party platform sits far from
  the bot's position on an axis it cares about.
- `platform`: as leader, when the platform drifts off the bot's
  ground.
- `challenge`: a statute whose `legal_risk` is high and whose repeal
  serves the arc.
- `decline_offers`: when no offer seats the bot's party and a bad
  coalition costs more than waiting.

**Dossier heat is the risk budget.** Dirty ops (`dig_dirt`, `leak`,
`scheme`, repeat `media`) fire only while `player.dossier <
BOT_DIRTY_CEILING` — except when the payoff is exceptional
(`BOT_ATTACK_SURE`-class odds). Risk-taking is a slider, not a ban: a
playtest that never risks tests nothing, and a bot that dies to
scandal every seed is exactly the tuning signal the ceiling exists to
surface.

## 4. Party lifecycle — cross the floor or go down with it

The bot gets the same read `_stay_utility` gives the AI. Below
`BOT_STAY_UTILITY` (a bot-tuned param seeded from
`PARTY_FORM_STAY_UTILITY`):

- **Found** when the preview's follower count is non-trivial — walk
  with a bloc, not alone. Required for the `founder` profile.
- **Defect** to the nearest compatible party when the seat is also
  failing — the party is a bad home *and* a bad vehicle.
- **Stay** otherwise — and a comfortable member of a sinking party is
  a documented bot limitation, the same judgment a player makes.

`parties.py`'s carve-outs (the player excluded from AI secession and
lone-founder paths) stay exactly as they are — the bot exercises
`defect`/`found` through the action menu, the human path, not through
the AI lifecycle.

## 5. Decision trace — failed runs become tuning data

`auto_actions(state, trace=None)` takes an optional list; when passed,
each `take` appends `(week, rule, kind, key inputs)` — the gate value
that fired (seat_safety, dossier, stay_utility, land-chance). Defaults
to `None`; no mutation, no driver changes, sim stays pure.

A new `checks/check_bot.py` runs the seeded suite spectate-style and
prints the box score per seed: weeks survived, peak office, ambition
picked/met, game-over cause, final score, rule-fire counts. The
aggregate table is the tuning surface:

- every seed dying by scandal → `BOT_DIRTY_CEILING` too high
- every seed dying in seat loss while climbing → marginal-seat guard
  too low
- ambitions never met → the arc is unachievable, tune the game not
  the bot
- a kind never fired across all seeds → a dead rule or a dead feature

## 6. Drivers

- Terminal spectate picks ambition through the bot instead of
  skipping the question.
- Pyg auto-play resolves the week-0 ambition row via the bot's pick
  instead of waiting on a click.

## 7. Checks

`checks/check_bot.py`: ambition always declared; budget never
exceeded; same seed → same action trace (determinism); the suite
observes every toolkit kind firing at least once across seeds (a dead
rule fails loudly); runs terminate in a real game-over or a long-run
cap.

## Atomic commits

1. `docs: m8 player bot spec`
2. `feat: bot ambition + rule pipeline` — persona, profiles,
   pipeline reorg, dossier-heat budget; existing rules ported
3. `feat: bot uses full toolkit` — attack/media/dirt/leak/promise/
   table/platform/challenge/decline_offers rules with odds gates
4. `feat: bot defects and founds` — stay-utility rule, defect target
   choice, follower-count founding gate
5. `feat: bot decision trace + check_bot` — trace parameter, box
   score check
6. `polish: ambition auto-pick + docs` — driver wiring, README/
   ROADMAP touch-up
