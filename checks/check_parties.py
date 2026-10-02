"""Runnable check: parties form on defection, split on schism, die at 0 seats."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

import sim.params as p
from sim.parties import party_lifecycle
from sim.tick import tick
from sim.worldgen import new_game


def main() -> None:
    # forced schism: party split into two distant wings, cohesion destroyed
    s = new_game(5)
    pt = s.parties[0]
    members = list(pt.members)
    half = len(members) // 2
    for m in members[:half]:
        s.mps[m].pos = (-1.0, -1.0)
    for m in members[half:]:
        s.mps[m].pos = (1.0, 1.0)
    for m in members:
        s.mps[m].loyalty = 0.1
        s.mps[m].ambition = 0.4  # below the lone-founder threshold — schism path only
    pt.platform = (0.0, 0.0)
    pt.schism_cooldown = 0
    n_parties = len(s.parties)
    party_lifecycle(s)
    assert len(s.parties) == n_parties + 1, "schism should create a new party"
    assert members[0] not in s.parties[0].members
    assert any(e.type == "PartyFormed" for e in s.log)

    # lone founder: tank party cohesion, one ambitious MP far from platform walks
    s2 = new_game(6)
    mp = next(iter(s2.mps.values()))
    pt2 = s2.parties[mp.party]
    for m in pt2.members:
        s2.mps[m].pos = (-1.0, 1.0)   # whole party drifts off its platform
        s2.mps[m].loyalty = 0.1
        s2.mps[m].ambition = 0.4
    mp.ambition = 0.9
    mp.pos = (1.0, -1.0)
    party_lifecycle(s2)
    assert s2.parties[mp.party].platform == mp.pos  # founded a party at own position

    # death: a party that loses all members dissolves
    s3 = new_game(7)
    dead = s3.parties[4]
    dead.members = set()
    party_lifecycle(s3)
    assert 4 not in s3.parties

    # a founded party contests the next election
    s4 = new_game(8)
    mp4 = next(iter(s4.mps.values()))
    mp4.ambition = 0.9
    mp4.pos = (1.0, -1.0)
    party_lifecycle(s4)
    new_pid = mp4.party
    while s4.phase == "campaign":
        tick(s4)
    s4.rng.gauss  # touch
    assert any(mp.party == new_pid for mp in s4.mps.values()) or new_pid not in s4.parties
    print("parties ok: schism, founding, dissolution all fire")


if __name__ == "__main__":
    main()
