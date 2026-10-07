# Spec M6: Replayability & presentation

The last milestone. The world simulates; now a run must be replayable
(save, restore, reproduce exactly), shapeable (scenarios and starting
situations, a book that can be written differently), purposeful (an arc
the player chooses, not a score alone), readable (the chronicle should
read like political history), and watchable (an election night, a bot
that can survive long enough to spectate). Nothing here adds a new
mechanic to the loop — M6 is the game made durable and legible.

Done-when (roadmap): **a seed plus a save file reproduces a run; the
chronicle reads like political history.**

Scope: save/load, scenarios & difficulty, goals beyond score, better
writing, election night, spectator mode, driver polish. The web driver
is deferred past M6 (the roadmap itself hedges it — "only if 'just me'
ever widens" — and it's a whole new runtime on the last milestone).

## 1. Save/load — reproducibility is a file

The honest cost nobody priced: `GameState` is a dataclass tree with a
*reference web*. `Deal.bill`, `Bill.repeals`, `Bill.amends`,
`Bill.entrenches`, `CourtCase.law`, `Government.amend_move`, and
`current_bill` hold live objects, and identity is load-bearing —
`d.bill is bill` gates promise bookkeeping, `challengeable` keys on
`id()`. A naive `asdict` would fork the web; on load, a deal on the
pending bill would point at a *copy* and silently never resolve.

New module `sim/persist.py` — pure functions, no file I/O (drivers own
the filesystem):

```python
def to_json(state: GameState) -> str
def from_json(text: str) -> GameState
```

- **Field-driven encoding** via `dataclasses.fields()` — new fields land
  in the format automatically; only reference fields need the id table.
- **The id table**: laws serialize by index into `state.laws`; articles
  by their real `id`; live Bill objects (`current_bill`, `amend_move`,
  every `deal.bill`) into a side table keyed by position, refs elsewhere
  emitted as `{ "#bill": n }` / `{ "#law": n }` / `{ "#article": n }`.
  Rehydration fixes the refs so identity semantics survive the trip.
- **rng**: `state.rng.getstate()` round-trips as a list; `prose_rng`
  (below) the same. Voters' ndarrays go through `.tolist()`.
- **Versioning**: `"format": 1` on the envelope; `from_json` refuses a
  foreign version cleanly — saves are allowed to die between milestones,
  they must never *silently* lie.
- Rejected: `pickle` — it preserves identity free, but every dataclass
  churn during development invalidates all saves, and the done-when
  needs a save a human can diff when a reproduction diverges.
- Drivers: `save`/`load` at the terminal prompt and pyg keys; files live
  in `saves/`, named by seed + week.

## 2. Scenarios & difficulty — the same world, dealt differently

`new_game(seed, scenario=None)`; a `Scenario` is a bundle of named
overrides applied at worldgen, plus a params profile name:

```python
@dataclass
class Scenario:
    name: str
    player_seat: str = "median"   # "safe" | "marginal" | "median"
    player_party: str | None = None  # "largest" | "smallest" | "outsider"
    party_pool: list | None = None   # pins generate_parties' archetype draw
    constructive_confidence: bool = False
    district_magnitude: int = 1
    params: dict = field(default_factory=dict)  # last-resort overrides
```

- `generate_parties(rng, np_rng, party_pool=None)` — the `party_pool=`
  hook the party-variety spec explicitly left open. A scenario ships a
  pinned system ("two-party", "fragmented", "the duopoly that broke").
- Starting situations read as worldgen picks: `safe` seats the player in
  the strongest-margin district for a major party; `marginal` the
  thinnest; `outsider` starts the player independent (M4's `found` is
  the career now). A scenario with `player_party` picks which pool the
  player draws from.
- **Constructive no-confidence** (the German model) as a stability knob:
  with `constructive_confidence` set, a lost confidence division falls
  the government only if the motion carried a viable successor slate;
  otherwise the government survives wounded. Implemented as a
  `collapse` guard reading the vote — the sim stays honest (the loser
  stays PM, brand bleeding), not a rules patch.
- **District magnitude** — the risky item. `magnitude > 1` allocates a
  district's seats by largest remainder over the party tally instead of
  winner-take-all: `resolve_election` gains a multi-seat path, candidate
  draws pull the top-N hopefuls per party, seat counts feed formation
  unchanged. Profoundly changes the party math (proportionality keeps
  small parties alive — the duopoly death spiral loosens). Ships behind
  the scenario flag; if the sweep can't absorb it, it lands documented
  experimental, not silently shipped.

## 3. Goals beyond score — a chosen arc, not a fixed ending

```python
@dataclass
class Ambition:
    kind: str         # "pm" | "majority" | "founder" | "survivor" | "reformer"
    met: bool = False
    failed: bool = False
    detail: str = ""
```

- `state.ambition` — picked at game start (terminal/scenario field; pyg
  start screen gets the same pick), or `None` for the sandbox career.
- The catalog is checkable and mechanical: `pm` (hold the office),
  `majority` (your party alone takes >50% of seats at an election),
  `founder` (a party you founded contests a later election without you),
  `survivor` (hold your seat N terms), `reformer` (author N enacted
  laws — `legacy_bills` already counts them).
- Resolution is an event: `AmbitionMet` / `AmbitionFailed`. A met arc
  doesn't end the run — the epilogue at game-over records it, alongside
  a career retelling (offices held, laws authored, justices still seated
  under `appointed_by`) that costs nothing but reads like a headline.
- `final_score` unchanged; a met ambition banks a small `score_terms`
  entry so the summary honors it without warping the incentive to play.

## 4. Better writing — the chronicle reads like history

Two mechanical changes unlock it:

- **`state.prose_rng = random.Random(seed ^ 0x5EED)`** — a cosmetic RNG
  forked at worldgen, consumed only by text. Any template draw must ride
  this stream: drawing prose choices off `state.rng` would make *the
  writing change the politics*, and it would corrupt every seeded check
  that counts on the mechanical stream. Persist saves/loads it.
- **`sim/prose.py`**: a template pool per event type —
  `render(state, kind, **slots) -> str` picks `templates[rng % len]` and
  formats the named actors already on the event (author names, clause
  names, party names). `emit` keeps its signature; call sites swap a
  fixed string for `prose.render(...)`. Three+ templates for the loud
  types — `LawEnacted`, `VoteResult`, `ScandalBreaks`, `Headline`,
  `ElectionResult`, `CoalitionFormed` — then the chronic repeaters the
  sweep flagged.
- **Echo tier**: player-action echoes (events carrying `action=`, plus
  the "You …" emissions) get classified `echo=True` at emit time; the
  pyg chronicle gains an "echoes" filter tier and terminal collapses
  them to a one-line digest per week. The 600-of-900 "You give a speech"
  problem dies here.
- **Naming texture** (the party-variety deferrals, landing):
  `state.country` gets a generated name — "the Republic of X" as the
  chronicle dateline (terminal header, pyg banner, save names); a
  regional flavor pack (a seed-drawn naming dialect) shifts party/
  district flavor without touching mechanics; the pyg map finally reads
  `AXIS_LABELS`/`POLE_LABELS` instead of raw axes.

## 5. Election night — dramaturgy on data that exists

`resolve_election` already walks districts one at a time with winner,
margin, and incumbent retention computed — it just never says so for
retained seats. One new emit inside the loop:

```python
state.emit("DistrictResult", "...",
           district=d, winner=winner, prev=prev_winner,
           margin=margin, flipped=not retained, incumbent=inc_id)
```

Then drivers dramatize: the election tick's `DistrictResult`s buffer and
reveal sequentially — pyg steps them on a timer (map seats fill as calls
land, a running seat bar, callouts on flips and "projection: plurality
likely X" once a fraction is in); terminal already prints events in
order — a live "called: N/113 seats — X leads 40" running line replaces
the current dump. The sim's truth doesn't change; only the telling.

## 6. Spectator mode — a player worth watching

The passive player dies ~week 174 losing their seat; a watchable run
needs a policy. `sim/bot.py` — pure function, no mutation:

```python
def auto_actions(state: GameState) -> list[Action]
```

Two picks a week from a rule list, in priority order: `vote` with the
whip on a pending division; `constituency`/`campaign` when the seat is
marginal; `lobby` while eligible and unpicked for promotion; `court` a
hostile outlet; `deal`/`amend` opportunistically on a live bill; PM
duties (`appoint`, `budget`, `amendment`) when holding the office. Its
draws ride `state.rng` deliberately — the bot *is* a player, and its
choices belong in the stream (a seeded spectator run still reproduces).

Drivers: terminal `--spectate` flag and a pyg mode feed `auto_actions`
to the action prompt; the pyg auto toggle gets a `bot` option so
watching doesn't mean a dead MP. The sweep can run bot-driven runs when
it wants the "does a played game stay healthy" column — M1's invariant
table finally gets runs that don't die at the first re-election.

## 7. Driver polish — small and overdue

- pyg fullscreen flag + resizable window.
- Reachability pass: chronicle, why-overlay, map, action panel, bench
  view — every surface reachable without hunting; the new M6 surfaces
  (scenario pick, ambition pick, save/load, election night) get homes in
  both drivers.

## Never

LLM-generated anything — the game's identity is classical AI; templates
stay hand-written. Web driver (deferred, above). Real-world political
data. Multiplayer. And the standing deferrals stay deferred:
by-elections, AI leaking *your* dirt back, outlet ownership (no money),
fabricated stories (no truth layer), per-MP warmth, a Head of State,
coordinated AI rebellion, AI-initiated deals.

## Params

```
AMBITION_TERMS     = 8     # "survivor": terms to hold the seat
AMBITION_LAWS      = 3     # "reformer": authored laws to pass
AMBITION_SCORE     = 10    # a met arc's bonus on the final tally
CONSTRUCTIVE_CONF  = False # scenario flag: falls need a named successor
DISTRICT_MAGNITUDE = 1     # seats per district; >1 = largest remainder
PROSE_SEED_KEY     = 0x5EED# cosmetic rng salt — never the mechanical stream
BOT_LOBBY_W        = 0.6   # the bot's hunger for promotion
BOT_MARGINAL       = 0.55  # seat-safety below this triggers defending
```

## Success criteria

- `check_persist.py` — the anchor: tick N weeks → save → tick M vs an
  uninterrupted N+M run produce identical event streams (same seed, same
  log); `deal.bill is state.current_bill` still holds after a load; a
  save mid-negotiation resumes the formation week; `format` mismatch
  refuses cleanly.
- `check_scenarios.py` — each preset produces its advertised start
  (safe-seat player sits a high-margin district, outsider starts
  independent); `party_pool=` pins the generated system; constructive
  confidence keeps a successorless government standing where the default
  falls; a `district_magnitude=2` run seats multiple members per
  district if it ships.
- `check_goals.py` — a `pm` ambition fires `AmbitionMet` on appointment
  and `AmbitionFailed` on game-over unmet; sandbox runs (`None`) never
  emit either; `survivor` counts terms correctly.
- `check_prose.py` — a template type renders ≥2 distinct texts across N
  emits; two identical-seed runs differ in prose but are identical in
  every non-text event field (the cosmetic stream never touches
  mechanics); echoes classify `echo=True`.
- `check_spectate.py` — the bot plays legal actions only, survives
  materially longer than the passive baseline (median week roughly
  doubles), and the invariant table still holds over bot-driven runs.
- Election night: every district emits `DistrictResult` with winner,
  margin, flip flag; the driver reveal is smoke-checked.
- `check_sweep.py` stays green — `prose_rng` provably leaves the
  mechanical stream untouched; the save round-trip check is the
  done-when, literally.

## Open questions

- Does `Scenario.params` last-resort override knob invite a balance
  swamp? It's power meant for us, not gameplay — keep it, but the named
  fields should cover everything a player-facing scenario needs.
- Should `Ambition` be offered once (start) or re-offered on failure
  (mid-run re-pick)? Once is cleaner and more roguelike; a failed arc
  just ends. Revisit if the "no arc" run feels shapeless.
- Bot competence ceiling: should it ever deal, defect, or leak — i.e.,
  play *well*? For spectate-tuning the bar is plausible-survival, not
  mastery; keep the rule list legible over clever.
- District magnitude is the item most likely to eat the schedule — it's
  specced with an explicit experimental fallback so the milestone isn't
  hostage to it.
