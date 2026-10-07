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

# chronicle: open, filter, scroll, close — same paths as the input handlers
d.chronicle["open"] = True
d.draw()
d.on_button("flt:VoteResult")
assert d.chronicle["filter"] == "VoteResult"
d.chronicle["scroll"] = 10
d.draw()
d.on_button("flt:all")
assert d.chronicle["filter"] is None
d.chronicle["open"] = False

# auto_play: weeks advance on the clock alone, no action pause — and
# interrupt banners dismiss themselves, no space-press needed
d.toggle_auto()                    # the 'a' key — flushes any pending action pause
w0 = d.state.week
for _ in range(6):
    d.step(5.0)
    if d.banner and d.state.phase != "over":
        d.step(3.0)                  # past AUTO_BANNER_SECONDS
        assert d.banner is None, "auto_play left a banner blocking the run"
assert d.state.week > w0 and not d.action_pause, "auto_play didn't advance"
print(f"pyg smoke ok: week={d.state.week} phase={d.state.phase} events={len(d.state.log)}")
