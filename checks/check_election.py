"""Runnable check: elections resolve all districts, loyalty and proximity work."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from sim.election import poll, resolve_election
from sim.worldgen import new_game


def main() -> None:
    # determinism
    a, b = new_game(7), new_game(7)
    resolve_election(a)
    resolve_election(b)
    assert [m.party for m in a.mps.values()] == [m.party for m in b.mps.values()]

    # all districts filled, one MP each
    assert sorted(m.district for m in a.mps.values()) == list(range(120))
    seats = a.log[-1].data["seats"]
    assert sum(seats.values()) == 120

    # proximity test (scoring level): a voter at plat0 scores a plat0 candidate
    # above every other platform — zero noise so ordering is pure distance
    import sim.params as p
    from sim.election import _district_scores
    c = new_game(7)
    c.voters.pos[:] = c.parties[0].platform
    mask = c.voters.district == 0
    cand = {pid: c.parties[pid].platform for pid in c.parties}
    saved = p.VOTE_NOISE_SD
    p.VOTE_NOISE_SD = 0.0
    try:
        score, parties = _district_scores(c, mask, cand, [])
    finally:
        p.VOTE_NOISE_SD = saved
    assert (score[:, 0:1] > score[:, 1:]).all()

    # proximity test (election level): voters at plat0 → party 0 dominates.
    # Incumbents keep their worldgen positions, so a few far-flung seats flip —
    # that's the mechanic working, not a bug.
    c2 = new_game(7)
    c2.voters.pos[:] = c2.parties[0].platform
    resolve_election(c2)
    c_seats = c2.log[-1].data["seats"]
    assert c_seats.get(0, 0) > 100, c_seats

    # loyalty test: with loyalty high and last_party set, distant-but-loyal wins sometimes
    d = new_game(7)
    d.voters.last_party[:] = 4
    d.voters.loyalty[:] = 1.0
    resolve_election(d)
    assert d.log[-1].data["seats"].get(4, 0) > 0

    # independents: a party-less local can win and sits with party=None —
    # force fielding everywhere so proximity decides crowded districts
    ind = new_game(7)
    saved_p = p.INDEPENDENT_P
    p.INDEPENDENT_P = 1.0
    try:
        resolve_election(ind)
    finally:
        p.INDEPENDENT_P = saved_p
    ind_seats = ind.log[-1].data["seats"].get("ind", 0)
    ind_mps = [m for m in ind.mps.values() if m.party is None]
    assert ind_seats > 0 and len(ind_mps) == ind_seats, \
        f"independents fielded everywhere but seated none (seats={ind_seats})"

    # poll returns shares summing to 1
    s = poll(new_game(7))
    assert abs(sum(s.values()) - 1.0) < 1e-9

    print(f"election ok: seats={seats}, sweep={c_seats.get(0)}, loyal_nf={d.log[-1].data['seats'].get(4)}")


if __name__ == "__main__":
    main()
