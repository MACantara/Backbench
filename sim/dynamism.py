"""Party-system dynamism: niche entry and revival — the birth channel.
Parties die on wipeouts; this is where they get born: into measured gaps."""
from __future__ import annotations

import numpy as np

from . import params as p
from .naming import party_name_for, revival_name
from .state import GameState, Party, dist


def _district_cells(state: GameState) -> dict[int, tuple[int, int]]:
    """District → grid cell, recovered from its centroid. District ids are
    relabeled sequentially at worldgen, so the cell must be recomputed from
    voter positions — the centroid always lies inside its own cell."""
    v = state.voters
    gx, gy = p.DISTRICT_GRID
    cells = {}
    for d in range(int(v.district.max()) + 1):
        cent = v.pos[v.district == d].mean(axis=0)
        cells[d] = (min(int((cent[0] + 1) / 2 * gx), gx - 1),
                    min(int((cent[1] + 1) / 2 * gy), gy - 1))
    return cells


def _unserved_clusters(state: GameState) -> list[list[int]]:
    """Adjacent groups of districts whose centroids sit far from every platform,
    largest first. Districts tile the ideology grid — adjacency is cell adjacency."""
    v = state.voters
    cells = _district_cells(state)
    by_cell = {cell: d for d, cell in cells.items()}
    plats = [pt.platform for pt in state.parties.values()]
    far = {d for d, cell in cells.items()
           if min(dist(tuple(v.pos[v.district == d].mean(axis=0)), pl)
                  for pl in plats) >= p.DYNAMIC_GAP_DIST}
    clusters = []
    while far:
        seed = far.pop()
        cluster, fringe = [seed], [seed]
        while fringe:
            cx, cy = cells[fringe.pop()]
            for nb in (by_cell.get((cx - 1, cy)), by_cell.get((cx + 1, cy)),
                       by_cell.get((cx, cy - 1)), by_cell.get((cx, cy + 1))):
                if nb is not None and nb in far:
                    far.discard(nb)
                    cluster.append(nb)
                    fringe.append(nb)
        clusters.append(cluster)
    return sorted(clusters, key=len, reverse=True)


def _new_party(state: GameState, name: str, platform, kind: str, districts: int) -> None:
    pid = max(state.parties, default=-1) + 1
    state.parties[pid] = Party(id=pid, name=name, platform=platform, seated=False,
                               founded_week=state.week)
    state.emit("PartyFormed",
               f"{name} declares for the election, contesting {districts} unserved districts.",
               party=pid, kind=kind, districts=districts)


def niche_entry(state: GameState) -> None:
    """Campaign-opening declarations: parties form where the map is unserved.
    A gap overlapping a grave produces a revival, not a fresh face."""
    if not state.parties:
        return
    cap = p.PARTY_COUNT_RANGE[1] + 2
    v = state.voters
    taken = {pt.name for pt in state.parties.values()}
    np_rng = np.random.default_rng(int(state.rng.random() * 2**63))
    entries = 0
    for cluster in _unserved_clusters(state):
        if (entries >= p.DYNAMIC_ENTRIES_PER_ELECTION or len(state.parties) >= cap
                or len(cluster) < p.DYNAMIC_GAP_MIN_SEATS):
            break
        mask = np.isin(v.district, cluster)
        platform = tuple(np.clip(v.pos[mask].mean(axis=0)
                                 + np_rng.normal(0, p.PARTY_PLATFORM_JITTER, 2), -1, 1))
        # re-check coverage — an earlier entrant this cycle may serve this gap
        if min(dist(platform, pt.platform) for pt in state.parties.values()) < p.DYNAMIC_GAP_DIST:
            continue
        grave = next((g for g in state.graves
                      if dist(g.platform, platform) < p.DYNAMIC_GAP_DIST), None)
        name = revival_name(grave.name, taken) if grave is not None else None
        if name is not None:
            _new_party(state, name, platform, "revival", len(cluster))
        else:
            _new_party(state, party_name_for(platform, state.rng, taken),
                       platform, "entry", len(cluster))
        entries += 1
