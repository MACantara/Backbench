# Backbench

A living fictional country that runs on classical AI — where you build a career inside politics the world generates itself.

No LLMs, no network, no cloud. You have the main role — the game is driven by your actions: what you campaign on, who you court, when you strike. The world stays alive around you (elections, coalitions, schisms, realignments run on their own logic), but this is a game to be played, not a simulation to watch. Campaign, keep your seat, climb to minister, challenge the leader, survive to become PM.

Every other actor is a classical algorithm: ~10,000 voter agents in a 2D ideological space, ~120 MP agents with ambition/loyalty/grudges/utility functions, parties that form, split, and die on their own. Every outcome is deterministic by seed and decomposes into legible causes — drama is emergent, not scripted.

## Requirements

- Python 3.12+
- `pip install numpy pygame` — pygame only needed for the graphical driver

## Run the game

```bash
python driver/pyg.py                       # graphical driver (recommended)
python driver/pyg.py 42                    # seeded run
python driver/pyg.py --scenario outsider   # pick a starting situation
python driver/pyg.py --fullscreen
python driver/terminal.py                  # plain terminal driver
python driver/terminal.py 42 --spectate    # the bot plays, you watch
python driver/terminal.py --load           # resume a save
```

Scenarios set the opening deal: `standard`, `safe_seat`, `marginal`, `outsider` (start independent), `duopoly`, `fragmented`, `constructive` (German-model confidence). A `Scenario` instance can also raise `district_magnitude` — multi-member districts allocated by largest remainder instead of FPTP.

In the graphical driver: weeks auto-run (**Space** pauses, **+/-** speed, **A** toggles bot auto-play — interrupt banners dismiss themselves so a spectator run never stalls), elections reveal district-by-district on the map. Every command is a button in the side panel — pause, auto, speed, map/house toggle, log, save, load, screenshot, quit — and the keys still work too (**Tab** view, **C** chronicle, **F5**/**F9** save/load — manual or autosave, whichever is newer; the run autosaves every 4 weeks — **Q**/**Esc** quits). Click a seat to inspect its MP. The window is resizable.

In the terminal driver each week you pick **2 actions** from the menu (campaign, speech, lobby, media, scheme, dig dirt, promise, court, leak — more unlock with office). Before committing you can:

- `inspect <mp_id>` — an MP's stats, relationships, seat safety
- `inspect bench` — the judicial bench: doctrine, ages, who appointed whom
- `why` — breakdown of the last vote: who voted yes/no and which utility terms drove it
- `save` / `load` — write or resume a run from `saves/`

Events marked `***` are interrupts — coalition collapses, scandals, elections.

## How a run goes

```
campaign (~8 weeks) -> election (120 districts) -> coalition formation
-> governing (~40 weeks of bills + confidence votes) -> next campaign -> ...
```

Pick an ambition at the start (win a majority, found a party that outlives you, survive four terms, author three laws, become PM) or run an open career. Game over when you lose your seat or get expelled — the epilogue retells the career, and score = offices held × terms survived × legacy.

The world it plays inside: a written constitution with named articles and a bench of individual justices who can strike laws (and whom a PM appoints), constitutional amendments at two-thirds, a press corps with warmth you can court and leaks you can route, scandals with dossiers and October surprises, factions that secede, private member's bills, floor-crossing, party founding, and leadership challenges.

## Checks

No test framework — each `checks/check_*.py` is a runnable assertion script that fails loudly if the logic breaks:

```bash
python checks/check_worldgen.py     # world generation, determinism
python checks/check_election.py     # district elections, FPTP + multi-member
python checks/check_parliament.py   # vote utility, whips
python checks/check_government.py   # coalition formation, confidence
python checks/check_persist.py      # save/load round-trip, reference identity
python checks/check_prose.py        # cosmetic prose never touches the sim rng
python checks/check_scenarios.py    # scenario presets, param isolation
python checks/check_spectate.py     # the bot plays legal weeks and survives
python checks/check_e2e.py          # 200-week full cycle
python checks/check_sweep.py        # 50-seed tuning sweep (~1 min)
```

## Layout

```
sim/        pure state machine — no I/O, no prints
  params.py     every tunable constant (tuning = touch this file)
  state.py      dataclasses: Voter, MP, Party, Bill, Event, GameState
  worldgen.py   seeded world + scenario construction
  naming.py     country names, name packs, party archetypes
  prose.py      cosmetic text on a forked rng — never the sim stream
  persist.py    JSON save/load with identity-preserving id tables
  election.py   district voting, FPTP/largest-remainder, polls
  parliament.py bill tabling, per-MP vote utility terms, whips
  government.py coalition formation, confidence, collapse
  parties.py    cohesion, defections, schisms, dissolutions
  actions.py    the player's 2 weekly actions
  career.py     portfolios, challenges, scoring, ambitions, epilogue
  bot.py        spectator policy — a legible rule list
  inspect.py    explainability: why did an MP vote that way
  tick.py       the weekly pipeline: tick(state, actions) -> events
driver/
  pyg.py        graphical driver — map, chronicle, election night, spectate
  terminal.py   thin shell over the sim core — replaceable (Textual later)
checks/         assertion scripts, one per subsystem
docs/
  specs/        design contracts per milestone (spec-p1 … spec-m6)
  ideas/        original concept one-pager
```

## Design notes

- **Events are first-class.** `tick()` returns typed `Event` objects — drivers can pause on them, inspect them, log them. That's what makes a real-time-with-pause UI possible without touching the sim.
- **Explainability is a feature.** Vote utility is decomposed into named terms (policy distance, whip, solidarity, district opinion) so `why` can answer "why did the government fall."
- **Everything is seeded.** Same seed, same world — and a save file resumes byte-identically to uninterrupted play, so a seed plus a save reproduces a run. Cosmetic prose draws on a separate forked rng so rewording can never change the politics.
- **Tuning lives in `params.py`.** Half of this game's development is "run 50 seeds, move a weight." All knobs in one file.
