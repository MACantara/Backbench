# Backbench

A living fictional country that runs on classical AI — where you build a career inside politics the world generates itself.

No LLMs, no network, no cloud. You have the main role — the game is driven by your actions: what you campaign on, who you court, when you strike. The world stays alive around you (elections, coalitions, schisms, realignments run on their own logic), but this is a game to be played, not a simulation to watch. Campaign, keep your seat, climb to minister, challenge the leader, survive to become PM.

Every other actor is a classical algorithm: ~10,000 voter agents in a 2D ideological space, ~120 MP agents with ambition/loyalty/grudges/utility functions, parties that form, split, and die on their own. Every outcome is deterministic by seed and decomposes into legible causes — drama is emergent, not scripted.

## Requirements

- Python 3.12+
- `pip install numpy pygame` — pygame only needed for the graphical driver

## Run the game

```bash
python driver/pyg.py              # graphical driver (recommended)
python driver/pyg.py 42           # seeded run
python driver/terminal.py         # plain terminal driver
python driver/terminal.py 42
```

In the graphical driver: weeks auto-run (Space pauses, +/- speed), interrupt events pause with a banner. Click a seat to inspect its MP.

In the terminal driver each week you pick **2 actions** from the menu (campaign, speech, lobby, media, scheme, dig dirt, promise). Before committing you can:

- `inspect <mp_id>` — an MP's stats, relationships, seat safety
- `why` — breakdown of the last vote: who voted yes/no and which utility terms drove it

Events marked `***` are interrupts — coalition collapses, scandals, elections.

## How a run goes

```
campaign (~8 weeks) -> election (FPTP, 120 districts) -> coalition formation
-> governing (~40 weeks of bills + confidence votes) -> next campaign -> ...
```

Game over when you lose your seat or get expelled. Score = offices held x terms survived x legacy.

## Checks

No test framework — each `checks/check_*.py` is a runnable assertion script that fails loudly if the logic breaks:

```bash
python checks/check_worldgen.py     # world generation, determinism
python checks/check_election.py     # district elections, FPTP
python checks/check_parliament.py   # vote utility, whips
python checks/check_government.py   # coalition formation, confidence
python checks/check_parties.py      # schism, founding, dissolution
python checks/check_player.py       # actions move outcomes, career
python checks/check_e2e.py          # 200-week full cycle
python checks/check_sweep.py        # 50-seed tuning sweep (~1 min)
```

## Layout

```
sim/        pure state machine — no I/O, no prints
  params.py     every tunable constant (tuning = touch this file)
  state.py      dataclasses: Voter, MP, Party, Bill, Event, GameState
  worldgen.py   seeded world construction
  election.py   district voting, FPTP, polls
  parliament.py bill tabling, per-MP vote utility terms, whips
  government.py coalition formation, confidence votes
  parties.py    cohesion, defections, schisms, dissolutions
  actions.py    the player's 2 weekly actions
  career.py     portfolios, leadership challenges, scoring, expulsion
  inspect.py    explainability: why did an MP vote that way
  tick.py       the weekly pipeline: tick(state, actions) -> events
driver/
  terminal.py   thin shell over the sim core — replaceable (Textual later)
checks/         assertion scripts, one per subsystem
docs/
  specs/        design contracts per phase (spec-p1, spec-p2, spec-p3-*, capability-map-p3)
  ideas/        original concept one-pager
```

## Design notes

- **Events are first-class.** `tick()` returns typed `Event` objects — drivers can pause on them, inspect them, log them. That's what makes a real-time-with-pause UI possible later without touching the sim.
- **Explainability is a feature.** Vote utility is decomposed into named terms (policy distance, whip, solidarity, district opinion) so `why` can answer "why did the government fall."
- **Everything is seeded.** Same seed, same world. Deterministic replays make tuning possible.
- **Tuning lives in `params.py`.** Half of this game's development is "run 50 seeds, move a weight." All knobs in one file.
