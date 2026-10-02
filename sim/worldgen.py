"""Seeded world generation: voters, districts, starting parliament and parties."""
from __future__ import annotations

import random

import numpy as np

from . import params as p
from .state import GameState, MP, Party, Voters, dist

_FIRST = "Ash Brook Cole Dawn Elm Fern Gale Hale Iris Jade Kite Lark Moss Nell Onyx Pine Reed Sage Teal Wren".split()
_LAST = "Barton Croft Dale Ellis Frost Grange Holt Ingram Marsh North Pace Quill Rook Shore Vale West York".split()


def _names(rng: random.Random, n: int) -> list[str]:
    pool = [f"{a} {b}" for a in _FIRST for b in _LAST]
    return rng.sample(pool, n)


def _district_of(pos: np.ndarray, grid: tuple[int, int]) -> np.ndarray:
    """Grid cells over ideology space — districts are ideologically coherent regions."""
    gx, gy = grid
    cx = np.clip(((pos[:, 0] + 1) / 2 * gx).astype(int), 0, gx - 1)
    cy = np.clip(((pos[:, 1] + 1) / 2 * gy).astype(int), 0, gy - 1)
    return cx * gy + cy


def make_voters(rng: random.Random, np_rng: np.random.Generator) -> Voters:
    n = p.N_VOTERS
    # mixture of a few ideological clusters → regional polarization for free
    centers = np.array([pl for _, pl in p.STARTING_PARTIES])
    weights = rng.choices(range(len(centers)), k=n)
    pos = centers[weights] + np_rng.normal(0, p.VOTER_POS_SD, (n, 2))
    pos = np.clip(pos, -1, 1)
    cell = _district_of(pos, p.DISTRICT_GRID)
    # relabel occupied cells to sequential district ids
    uniq, district = np.unique(cell, return_inverse=True)
    clipped = lambda a: np.clip(a, 0, 1)
    return Voters(
        pos=pos,
        turnout=clipped(np_rng.normal(p.TURNOUT_MEAN, p.TURNOUT_SD, n)),
        loyalty=clipped(np_rng.normal(p.LOYALTY_MEAN, p.LOYALTY_SD, n)),
        betrayal=np.zeros(n),
        salience=np.clip(np_rng.normal(p.SALIENCE_BASE, p.SALIENCE_SD, (n, 2)), 0.1, None),
        district=district.astype(int),
        last_party=np.full(n, -1),
    )


def new_game(seed: int) -> GameState:
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)
    voters = make_voters(rng, np_rng)
    n_districts = int(voters.district.max()) + 1

    parties = {
        i: Party(id=i, name=name, platform=platform)
        for i, (name, platform) in enumerate(p.STARTING_PARTIES)
    }

    # one incumbent per district, anchored near the district centroid
    mps: dict[int, MP] = {}
    names = _names(rng, n_districts)
    centroids = np.array([voters.pos[voters.district == d].mean(axis=0) for d in range(n_districts)])
    for d in range(n_districts):
        centroid = tuple(np.clip(centroids[d] + np_rng.normal(0, p.MP_POS_JITTER, 2), -1, 1))
        party = min(parties.values(), key=lambda pt: dist(centroid, pt.platform))
        # an MP blends party platform with district character
        pos = tuple(np.clip(0.65 * np.asarray(party.platform) + 0.35 * np.asarray(centroid)
                            + np_rng.normal(0, p.MP_POS_JITTER / 2, 2), -1, 1))
        stat = lambda k: min(1, max(0, rng.gauss(p.MP_STAT_MEANS[k], p.MP_STAT_SD)))
        mps[d] = MP(
            id=d, name=names[d], pos=pos,
            ambition=stat("ambition"), loyalty=stat("loyalty"),
            competence=stat("competence"), integrity=stat("integrity"),
            district=d, party=party.id,
        )
        party.members.add(d)
    for pt in parties.values():
        pt.leader = min(pt.members, key=lambda m: mps[m].ambition * -1) if pt.members else None

    # player: an MP in a middling district (near the median centroid)
    med = np.argsort(np.linalg.norm(centroids, axis=1))[n_districts // 2]
    return GameState(
        rng=rng, week=0, phase="campaign", voters=voters, mps=mps, parties=parties,
        player_id=int(med), weeks_to_election=8,
    )
