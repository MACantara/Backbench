"""Perf guard: district_centroid stays bitwise-identical to the masked
mean it replaces, and invalidates on pos_version bumps."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from sim.state import district_centroid
from sim.tick import tick
from sim.worldgen import new_game


def _assert_centroids(s) -> None:
    v = s.voters
    for d in range(int(v.district.max()) + 1):
        assert np.array_equal(district_centroid(v, d),
                              v.pos[v.district == d].mean(axis=0)), \
            f"district {d} centroid diverged"


def main() -> None:
    s = new_game(0)
    v = s.voters
    _assert_centroids(s)

    # write without a bump reads the memo; with a bump, fresh and exact
    before = district_centroid(v, 0).copy()
    v.pos[v.district == 0] += 0.01
    assert np.array_equal(district_centroid(v, 0), before)
    v.pos_version += 1
    assert np.array_equal(district_centroid(v, 0),
                          v.pos[v.district == 0].mean(axis=0))
    assert not np.array_equal(district_centroid(v, 0), before)

    # the real write path: drift mutates pos every week — centroids track it
    for _ in range(10):
        tick(s)
        _assert_centroids(s)
    print("perf ok")


if __name__ == "__main__":
    main()
