"""Check: press relations — warmth, routed leaks, sponsored polls."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

import sim.params as p
from sim.actions import Action, apply_action
from sim.election import poll, publish_poll
from sim.state import dist
from sim.tick import tick
from sim.worldgen import new_game


def _governing(seed: int):
    s = new_game(seed)
    for _ in range(120):
        tick(s)
        if s.phase == "governing" and s.government.pm is not None:
            return s
    raise AssertionError(f"seed {seed} never formed a government")


def main() -> None:
    # court: warmth accrues toward your party and decays if you stop
    s = _governing(4)
    me = s.mps[s.player_id]
    o = s.outlets[0]
    o.warmth.clear()   # drift may already have warmed it toward the player
    apply_action(s, Action("court", target=o.id))
    w1 = o.warmth[me.party]
    assert w1 == p.COURT_WARMTH
    apply_action(s, Action("court", target=o.id))
    assert o.warmth[me.party] == min(1.0, w1 + p.COURT_WARMTH)
    apply_action(s, Action("court", target=o.id))
    apply_action(s, Action("court", target=o.id))
    apply_action(s, Action("court", target=o.id))
    apply_action(s, Action("court", target=o.id))
    apply_action(s, Action("court", target=o.id))
    apply_action(s, Action("court", target=o.id))
    assert o.warmth[me.party] == 1.0, "warmth should cap at 1.0"
    for _ in range(20):
        tick(s)   # no courting — the board forgets (drift may hold the floor)
    w_after = o.warmth.get(me.party, 0.0)
    assert w_after < 1.0 - p.COURT_WARMTH, "warmth never decayed"

    # routed leaks: the venue reads its warmth to the SUBJECT party —
    # warm buries the pickup weight, cold leads the knife in
    s2 = _governing(5)
    t = next(m for m in s2.mps.values()
             if m.id != s2.player_id and m.party in s2.parties
             and s2.parties[m.party].leader != m.id)
    t.dossier = 0.9
    t.scandal_weeks = 0   # a mid-burn target can't take a fresh detonation
    warm_o, cold_o = s2.outlets[0], s2.outlets[1]
    warm_o.warmth[t.party] = 1.0
    cold_o.warmth.clear()
    n = len(s2.log)
    apply_action(s2, Action("leak", target=t.id, outlet=warm_o.id))
    ev = next(e for e in s2.log[n:]
              if e.type in ("ScandalBreaks", "Expelled"))
    assert ev.data.get("routed") == warm_o.id, "the venue didn't stamp the story"

    # sponsored polls: the published number flatters the sponsor's friends
    s3 = _governing(10)
    big = max(s3.parties.values(), key=lambda pt: len(pt.members))
    sponsor = min(s3.outlets,
                  key=lambda x: dist(x.slant, big.platform))
    bias = None
    for _ in range(12):   # rotation may or may not hit the friendly outlet
        s3.week += 1
        publish_poll(s3)
        if s3.last_poll["outlet"] == sponsor.id:
            bias = (s3.last_poll["shares"].get(big.id, 0.0)
                    - poll(s3).get(big.id, 0.0))
            break
    assert bias is not None and bias > 0.02, \
        "a friendly outlet's poll should flatter its near party"
    assert s3.last_poll["week"] == s3.week, "the published poll must be stamped"

    # the snap gate reads the published number, not the oracle
    s4 = _governing(11)
    gov = set(s4.government.parties)
    seat_share = sum(len(s4.parties[i].members) for i in gov) / len(s4.mps)
    s4.government.weeks_in_office = sum(p.SNAP_WINDOW) // 2
    # a flattering lie: published share well above seats, oracle mediocre
    s4.last_poll = {"shares": {i: seat_share + p.SNAP_POLL_EDGE + 0.05
                             if i == next(iter(gov)) else 0.0
                             for i in gov},
                    "week": s4.week, "outlet": None}
    called = False
    for _ in range(400):
        from sim.government import strategic_call
        strategic_call(s4)
        if any(e.type == "ElectionCalled" and e.data.get("snap")
               and e.data["reason"] == "strategic"
               for e in s4.log):
            called = True
            break
        s4.week += 1     # keep the stamp fresh enough to read
        s4.last_poll["week"] = s4.week
    assert called, "a published surplus never tempted the PM into a snap"

    print("press ok: court warmth, routed leaks, sponsored polls, snap gate")


if __name__ == "__main__":
    main()
