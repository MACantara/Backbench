"""Runnable check: scenario profiles deal the advertised world, the
party_pool pin lands, constructive confidence keeps a successorless
government standing, and param overlays don't leak between runs."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from sim import params as p
from sim.government import collapse
from sim.worldgen import SCENARIOS, Scenario, new_game


def _margin(s, d):
    v = s.voters
    plats = np.array([pt.platform for _, pt in sorted(s.parties.items())])
    near = np.linalg.norm(v.pos[:, None] - plats[None, :], axis=2).argmin(1)
    t = np.sort(np.bincount(near[v.district == d], minlength=len(plats)))
    return (t[-1] - t[-2]) / t.sum()


def main() -> None:
    # the defaults reproduce a standard deal
    a, b = new_game(0), new_game(0, "standard")
    assert np.array_equal(a.voters.pos, b.voters.pos)
    assert a.player_id == b.player_id

    # seat situations: safe picks a fatter margin than marginal
    safe = new_game(0, "safe_seat")
    marg = new_game(0, "marginal")
    ms, mm = (safe.mps[safe.player_id].district,
              marg.mps[marg.player_id].district)
    assert ms != mm or _margin(safe, ms) != _margin(marg, mm)
    assert _margin(safe, ms) >= _margin(marg, mm), \
        "safe seat not safer than the marginal pick"

    # outsider starts unaligned; the party that would have had them loses a member
    out = new_game(0, "outsider")
    assert out.mps[out.player_id].party is None
    assert all(out.player_id not in pt.members for pt in out.parties.values())

    # party_pool pins the cast
    duo = new_game(0, "duopoly")
    assert len(duo.parties) == 2, "duopoly didn't pin the system"
    assert {pt.name for pt in duo.parties.values()} <= {
        "Labour", "Social Democrats", "Workers' Party", "Union of Labour",
        "Socialist Party", "Conservative Party", "National Coalition",
        "People's Party", "Union Party", "The Union"}

    # params overlay applies at worldgen and is restored after
    before = p.PARTY_COUNT_RANGE
    two = new_game(0, Scenario("x", params={"PARTY_COUNT_RANGE": (2, 2)}))
    assert len(two.parties) == 2
    assert p.PARTY_COUNT_RANGE == before, "param overlay leaked"

    # constructive confidence: no successor slate, the wounded government stands
    s = new_game(0)
    s.phase = "governing"
    s.constructive_confidence = True
    pid = max(s.parties, key=lambda i: len(s.parties[i].members))
    for pt in s.parties.values():
        pt.members = set()
    s.parties[pid].members = set(s.mps)
    s.government.parties = {pid}
    s.government.pm = next(iter(s.parties[pid].members))
    s.government.collapses = 0
    collapse(s, "confidence")
    assert s.government.pm is not None, "constructive collapse emptied the office"
    assert s.phase == "governing"
    assert any(e.type == "ConfidenceHeld" for e in s.log)
    assert s.parties[pid].brand < 0, "survival cost no brand wound"

    # without the flag, the same situation falls
    s2 = new_game(0)
    s2.phase = "governing"
    for pt in s2.parties.values():
        pt.members = set()
    s2.parties[pid].members = set(s2.mps)
    s2.government.parties = {pid}
    s2.government.pm = next(iter(s2.parties[pid].members))
    collapse(s2, "confidence")
    assert s2.government.pm is None or s2.phase != "governing"
    assert any(e.type == "ConfidenceLost" for e in s2.log)

    # determinism: same seed + scenario reproduces the deal
    assert np.array_equal(new_game(3, "fragmented").voters.pos,
                          new_game(3, "fragmented").voters.pos)

    print("scenarios check OK")


if __name__ == "__main__":
    main()
