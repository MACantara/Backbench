"""Party-system dynamism: niche entry and revival — the birth channel.
Parties die on wipeouts; this is where they get born: into measured gaps."""
from __future__ import annotations

import numpy as np

from . import params as p
from .naming import party_name_for
from .state import GameState, Party, dist


def _unserved_clusters(state: GameState) -> list[list[int]]:
    """Adjacent groups of districts whose centroids sit far from every platform,
    largest first. Districts tile the ideology grid — adjacency is cell adjacency."""
    v = state.voters
    gy = p.DISTRICT_GRID[1]
    n_districts = int(v.district.max()) + 1
    plats = [pt.platform for pt in state.parties.values()]
    far = {d for d in range(n_districts)
           if min(dist(tuple(v.pos[v.district == d].mean(axis=0)), pl)
                  for pl in plats) >= p.DYNAMIC_GAP_DIST}
    clusters = []
    while far:
        seed = far.pop()
        cluster, fringe = [seed], [seed]
        while fringe:
            c = fringe.pop()
            cx, cy = divmod(c, gy)
            for nb in (c - 1, c + 1, c - gy, c + gy):
                if nb in far and abs(divmod(nb, gy)[0] - cx) + abs(divmod(nb, gy)[1] - cy) == 1:
                    far.discard(nb)
                    cluster.append(nb)
                    fringe.append(nb)
        clusters.append(cluster)
    return sorted(clusters, key=len, reverse=True)


def _new_party(state: GameState, name: str, platform, kind: str, seats: int) -> None:
    pid = max(state.parties, default=-1) + 1
    state.parties[pid] = Party(id=pid, name=name, platform=platform,
                               founded_week=state.week)
    state.emit("PartyFormed",
               f"{name} declares for the election, contesting {seats} unserved districts.",
               party=pid, kind=kind, districts=seats)


def niche_entry(state: GameState) -> None:
    """Campaign-opening declarations: parties form where the map is unserved.
    A gap overlapping a grave produces a revival, not a fresh face."""
    if len(state.parties) >= p.PARTY_COUNT_RANGE[1] + 2:
        return
    v = state.voters
    taken = {pt.name for pt in state.parties.values()}
    np_rng = np.random.default_rng(int(state.rng.random() * 2**63))
    entries = 0
    for cluster in _unserved_clusters(state):
        if entries >= p.DYNAMIC_ENTRIES_PER_ELECTION or len(cluster) < p.DYNAMIC_GAP_MIN_SEATS:
            break
        mask = np.isin(v.district, cluster)
        platform = tuple(np.clip(v.pos[mask].mean(axis=0)
                                 + np_rng.normal(0, p.PARTY_PLATFORM_JITTER, 2), -1, 1))
        grave = next((g for g in state.graves
                      if dist(g["platform"], platform) < p.DYNAMIC_GAP_DIST), None)
        if grave is not None and f"Second {grave['name']}" not in taken:
            name = f"Second {grave['name']}"
            taken.add(name)
            _new_party(state, name, platform, "revival", len(cluster))
        else:
            _new_party(state, party_name_for(platform, state.rng, taken),
                       platform, "entry", len(cluster))
        entries += 1
