# Spec P2 — Graphical Driver ("See the Simulation")

Second driver for the existing sim core, in pygame. The sim is untouched: everything below consumes `tick(state, actions) -> list[Event]` and reads `GameState`. Confirmed intent: hemicycle parliament is the home screen, ideology/district map one keypress away, weeks auto-run with hard pauses for interrupts and player actions, mouse-driven action panel with click-to-target MPs.

## Architecture

```
driver/
  terminal.py   existing driver — must keep working
  pyg.py        pygame driver: run(seed) entry point
  pyg_render.py pure draw functions: (state, view_state) -> surfaces
```

- `pyg.py` owns the loop: clock, input, pause/interrupt state, and a per-week event queue for animations.
- `pyg_render.py` is pure drawing — no sim mutation, no input. Keeps rendering testable headless.
- `sim/` gains **no** pygame imports. Party colors are presentation data — they live in `driver/`, not `params.py`.

## Window and views

- Window: 1280×720 fixed. 60 FPS render, decoupled from sim speed.
- Two views, Tab toggles:
  - **PARLIAMENT (home):** hemicycle of 120 seats — concentric arcs, Westminster-style, government parties right of the aisle, opposition left. Player's seat ringed in white. Empty seats (dissolved parties) render as dim outlines.
  - **MAP:** left = 12×10 district grid colored by seat holder (brightness = margin); right = ideology scatter — sampled ~1500 voters as 1px alpha dots, party platforms as lettered markers, MPs as 3px dots. Player highlighted in both.
- Persistent side panel (right ~300px, both views): week counter, phase, poll bars, player stats card, scrolling event feed (last ~10 events, interrupts in red).

## Animation and time

- Auto-run: one week per 1.5s of wall time while running. Space toggles pause. +/- adjust speed (0.5x/1x/2x/4x).
- Vote animation: when a `VoteResult` event arrives, seats cascade green/yes or red/no over ~0.8s (staggered by seat index) — then settle.
- Interrupts (`ConfidenceLost`, `CoalitionFormed`, `PartyFormed`, `Defection`, `PartyDissolved`, `Scandal`, `ElectionCalled`, `ElectionResult`, `SeatLost`): auto-pause + banner overlay until Space/click dismisses.
- Election: districts on the map view resolve in order during a ~3s sequence; seats in the hemicycle update to match.

## Interaction

- **Click any seat** → MP inspect card (name, party, pos, stats, relationships, seat safety) — same data as `inspect.py`'s `explain_mp`, rendered as a panel. Works while running or paused.
- **Action pause:** when `available_actions` applies, auto-pause and show the action panel: button per action kind. Targeted actions (`lobby`, `dig_dirt`) enter "pick a target" mode — click a seat. `speech`/`promise` ask axis via two small buttons (economic/social). After 2 picks, resume.
- **why-button** on the panel renders `explain_vote` output for the most recent vote.
- Escape or Q quits; F12 saves a screenshot to `shots/` (cheap debugging aid).

## Dependencies

- `pygame-ce` (or `pygame`) — first non-stdlib/numpy dependency. Pin a published version ≥7 days old.
- Fonts: pygame's built-in `Font(None, size)`. No font files, no assets.

## Verification

- `checks/check_pyg_smoke.py`: run with `SDL_VIDEODRIVER=dummy`, drive ~30 weeks through the driver with scripted inputs, assert no exceptions and that view state updates (seat colors change after an election).
- Existing checks must stay green — the sim isn't touched.
- Manual acceptance: launch `python driver/pyg.py`, watch one full campaign→govern cycle without reading a terminal line.

## Out of scope

- New sim mechanics (media layer, factions, deals — Phase 3)
- Save/load, difficulty/scenarios (Phase 4)
- Sound, sprites, art assets
- Web/pygame-editor versions
- Touch/controller support; keyboard+mouse only
