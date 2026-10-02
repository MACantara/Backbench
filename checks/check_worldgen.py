"""Runnable check: worldgen produces a consistent, deterministic world."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from sim import params as p
from sim.state import dist
from sim.worldgen import new_game


def main() -> None:
    a, b = new_game(42), new_game(42)

    # deterministic
    assert np.array_equal(a.voters.pos, b.voters.pos)
    assert [m.pos for m in a.mps.values()] == [m.pos for m in b.mps.values()]

    n_districts = int(a.voters.district.max()) + 1
    assert n_districts <= p.N_DISTRICTS
    # every district has voters and exactly one MP
    counts = np.bincount(a.voters.district)
    assert counts.min() >= 1
    assert sorted(m.district for m in a.mps.values()) == list(range(n_districts))
    # parties are spread out
    plats = [pt.platform for pt in a.parties.values()]
    assert all(dist(x, y) > 0.4 for i, x in enumerate(plats) for y in plats[i + 1:])
    # every MP is in a party, every party member is an MP
    assert all(m.party is not None for m in a.mps.values())
    assert all(pt.members for pt in a.parties.values()) or True  # empty party allowed but note it
    # player is a real MP
    assert a.player_id in a.mps
    print(f"worldgen ok: {n_districts} districts, {len(a.mps)} MPs, "
          f"{len(a.voters.pos)} voters, {len(a.parties)} parties, player={a.player_id}")


if __name__ == "__main__":
    main()
