"""Headless smoke check: the pygame driver runs weeks without a display."""
import os
import sys
from pathlib import Path

os.environ["SDL_VIDEODRIVER"] = "dummy"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from driver.pyg import Driver

d = Driver(seed=3, headless=True)
for _ in range(15):
    d.banner = None
    d.paused = False
    d.advance()
    d.draw()          # draw path must not throw either

assert d.state.week >= 10, f"expected ~15 weeks, got {d.state.week}"
assert len(d.events) > 0, "no events collected"
print(f"pyg smoke ok: week={d.state.week} phase={d.state.phase} events={len(d.state.log)}")
