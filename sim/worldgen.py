"""Seeded world generation: voters, districts, starting parliament and parties."""
from __future__ import annotations

import random

import numpy as np

from . import params as p
from .naming import generate_parties, mp_name, mp_names
from .state import (Conditions, GameState, Hopeful, MP, Outlet, Party, Voters,
                    dist)

_OUTLET_ADJ = "Meridian Capital Northern Coastal Civic Free Daily Union".split()
_OUTLET_NOUN = "Herald Tribune Post Wire Gazette Sentinel".split()


def _district_of(pos: np.ndarray, grid: tuple[int, int]) -> np.ndarray:
    """Grid cells over ideology space — districts are ideologically coherent regions."""
    gx, gy = grid
    cx = np.clip(((pos[:, 0] + 1) / 2 * gx).astype(int), 0, gx - 1)
    cy = np.clip(((pos[:, 1] + 1) / 2 * gy).astype(int), 0, gy - 1)
    return cx * gy + cy


def make_voters(rng: random.Random, np_rng: np.random.Generator,
                centers: np.ndarray) -> Voters:
    n = p.N_VOTERS
    # mixture of a few ideological clusters → regional polarization for free;
    # cluster masses are a Dirichlet draw — some countries get a hegemonic
    # party, others a fragmented system where coalitions live on a knife-edge
    masses = np_rng.dirichlet(np.ones(len(centers)))
    weights = rng.choices(range(len(centers)), weights=masses.tolist(), k=n)
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


def make_hopeful(rng: random.Random, np_rng: np.random.Generator,
                 parties: dict[int, Party], n_districts: int,
                 name: str | None = None, age: int | None = None) -> Hopeful:
    """One aspiring politician: stats rolled, leaning toward the nearest platform."""
    plat = np.asarray(rng.choice(list(parties.values())).platform)
    hpos = tuple(np.clip(plat + np_rng.normal(0, p.MP_POS_JITTER, 2), -1, 1))
    stat = lambda k: min(1, max(0, rng.gauss(p.MP_STAT_MEANS[k], p.MP_STAT_SD)))
    return Hopeful(
        name=name or mp_name(rng), pos=hpos,
        ambition=stat("ambition"), loyalty=stat("loyalty"),
        competence=stat("competence"), integrity=stat("integrity"),
        district=rng.randrange(n_districts),
        party=min(parties.values(), key=lambda pt: dist(hpos, pt.platform)).id,
        age=age if age is not None else rng.randint(*p.HOPEFUL_AGE),
    )


def make_outlets(rng: random.Random, np_rng: np.random.Generator,
                 parties: dict[int, Party]) -> list[Outlet]:
    """The press: slants anchored near party poles, one guaranteed centrist."""
    count = rng.randint(*p.OUTLET_COUNT)
    anchors = [pt.platform for pt in parties.values()]
    rng.shuffle(anchors)
    if p.OUTLET_CENTRIST:
        anchors[rng.randrange(min(count, len(anchors)))] = (0.0, 0.0)  # used slot
    outlets = []
    for i in range(count):
        anchor = np.asarray(anchors[i % len(anchors)])
        slant = tuple(np.clip(anchor + np_rng.normal(0, p.OUTLET_SLANT_JITTER, 2), -1, 1))
        outlets.append(Outlet(
            id=i, name=f"The {rng.choice(_OUTLET_ADJ)} {rng.choice(_OUTLET_NOUN)}",
            slant=slant, reach=rng.uniform(*p.OUTLET_REACH),
            sensationalism=rng.random(), focus_axis=i % 2))
    return outlets


def new_game(seed: int) -> GameState:
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)
    # the party system comes first — the electorate clusters around its anchors
    specs = generate_parties(rng, np_rng)
    voters = make_voters(rng, np_rng, np.array([pl for _, pl in specs]))
    n_districts = int(voters.district.max()) + 1

    parties = {
        i: Party(id=i, name=name, platform=platform)
        for i, (name, platform) in enumerate(specs)
    }

    # one incumbent per district, anchored near the district centroid
    mps: dict[int, MP] = {}
    names = mp_names(rng, n_districts + p.N_HOPEFULS)
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
            age=rng.randint(*p.MP_AGE_WORLDGEN),
            seniority=rng.randint(*p.MP_SENIORITY_WORLDGEN),
        )
        party.members.add(d)
    for pt in parties.values():
        pt.leader = min(pt.members, key=lambda m: mps[m].ambition * -1) if pt.members else None

    # the pipeline: hopefuls below minimum age, leaning toward their nearest party
    hopefuls = [make_hopeful(rng, np_rng, parties, n_districts, name=names[n_districts + i])
                for i in range(p.N_HOPEFULS)]

    # player: an MP in a middling district (near the median centroid)
    med = np.argsort(np.linalg.norm(centroids, axis=1))[n_districts // 2]
    conds = {f: float(np.clip(v + np_rng.normal(0, p.COND_JITTER_SD), -1, 1))
             for f, v in p.COND_BASE.items()}
    return GameState(
        rng=rng, week=0, phase="campaign", voters=voters, mps=mps, parties=parties,
        hopefuls=hopefuls, outlets=make_outlets(rng, np_rng, parties),
        conditions=Conditions(**conds),
        player_id=int(med), weeks_to_election=p.CAMPAIGN_WEEKS,
    )
