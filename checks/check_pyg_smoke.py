"""Headless smoke check: the pygame driver runs weeks without a display."""
import os
import sys
from pathlib import Path

os.environ["SDL_VIDEODRIVER"] = "dummy"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from driver.pyg import Driver

d = Driver(seed=3, headless=True)
saw_election = saw_seats = False
for _ in range(35):
    d.banner = None
    d.paused = False
    d.action_pause = False
    d.advance()
    d.step(0.5)            # drive animations
    d.view = "map" if d.state.week % 2 else "parliament"
    d.draw()               # draw path must not throw either
    saw_election |= any(e.type == "ElectionResult" for e in d.events)
    saw_seats |= bool(d.seat_rects)

assert d.state.week >= 30, f"expected ~35 weeks, got {d.state.week}"
assert len(d.events) > 0, "no events collected"
assert saw_election, "35 weeks without an election"
assert saw_seats, "no hit-test geometry registered"
print(f"pyg smoke ok: week={d.state.week} phase={d.state.phase} events={len(d.state.log)}")
