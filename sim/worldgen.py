"""Seeded world generation: voters, districts, starting parliament and parties."""
from __future__ import annotations

import random
from dataclasses import dataclass, field

import numpy as np

from . import params as p
from .naming import (NAME_PACKS, country_name, generate_parties, mp_name,
                     mp_names)
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
                 name: str | None = None, age: int | None = None,
                 pack: str = "insular") -> Hopeful:
    """One aspiring politician: stats rolled, leaning toward the nearest platform."""
    plat = np.asarray(rng.choice(list(parties.values())).platform)
    hpos = tuple(np.clip(plat + np_rng.normal(0, p.MP_POS_JITTER, 2), -1, 1))
    stat = lambda k: min(1, max(0, rng.gauss(p.MP_STAT_MEANS[k], p.MP_STAT_SD)))
    return Hopeful(
        name=name or mp_name(rng, pack), pos=hpos,
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


_CLAUSES = {
    (0, -1): "the Property Clause",      # fences redistribution statutes
    (0, +1): "the Common Provision",     # fences market-fundamentalist statutes
    (1, -1): "the Order Clause",         # fences libertarian statutes
    (1, +1): "the Liberty Clause",       # fences authoritarian statutes
}


def make_constitution(rng: random.Random, centroid) -> list:
    """The country's written rules. Fiscal and Mandate clauses always; per
    axis, the pole opposite the country's lean is guarded, and its own pole
    on a coin flip — centrist countries write symmetric books."""
    from .state import Article
    arts = [Article(0, "the Fiscal Clause", "cost", limit=p.ARTICLE_COST_CAP),
            Article(1, "the Mandate Clause", "margin", limit=p.ARTICLE_MARGIN_FLOOR)]
    for ax in (0, 1):
        far_pole = -1 if centroid[ax] >= 0 else 1
        for i, pole in enumerate((far_pole, -far_pole)):
            if i == 0 or rng.random() < p.ARTICLE_MIRROR_P:
                limit = float(np.clip(
                    p.ARTICLE_LIMIT + rng.gauss(0, p.ARTICLE_LIMIT_SD), 0.35, 0.8))
                arts.append(Article(len(arts), _CLAUSES[(ax, pole)], "pos",
                                    axis=ax, pole=pole, limit=limit))
    return arts


def make_bench(rng: random.Random, np_rng: np.random.Generator,
               centroid, activism: float, pack: str = "insular") -> list:
    """The inaugural court: doctrine spread around the seed's character,
    temperament around the country's center, ages spread wide enough that
    vacancies open during play."""
    from .state import Justice
    return [Justice(id=i, name=mp_name(rng, pack),
                    pos=tuple(np.clip(np.asarray(centroid)
                                      + np_rng.normal(0, 0.2, 2), -1, 1)),
                    activism=float(np.clip(rng.gauss(activism, 0.12), 0, 1)),
                    age=rng.randint(p.JUDGE_APPOINT_AGE[0], p.RETIRE_AGE - 100))
            for i in range(p.BENCH_SIZE)]


@dataclass
class Scenario:
    """A dealt world: same generator, named overrides. params entries are
    worldgen-scoped — applied to sim.params while new_game runs, restored
    after, so a scenario can't leak tunables into the next run."""
    name: str
    player_seat: str = "median"       # "safe" | "marginal" | "median"
    player_party: str | None = None   # "largest" | "smallest" | "outsider"
    party_pool: list | None = None    # pins generate_parties' archetype draw
    constructive_confidence: bool = False
    district_magnitude: int = 1
    params: dict = field(default_factory=dict)


SCENARIOS = {
    "standard": Scenario("standard"),
    "safe_seat": Scenario("safe_seat", player_seat="safe"),
    "marginal": Scenario("marginal", player_seat="marginal"),
    "outsider": Scenario("outsider", player_party="outsider",
                         player_seat="marginal"),
    "duopoly": Scenario("duopoly",
                        party_pool=["social_democrat", "conservative"]),
    "fragmented": Scenario("fragmented",
                           party_pool=["social_democrat", "liberal", "conservative",
                                       "green", "nationalist", "agrarian"]),
    "constructive": Scenario("constructive", constructive_confidence=True),
}


def _player_district(voters, parties, mps, n_districts: int,
                     sc: Scenario) -> int:
    """Which incumbent the player replaces. 'safe' takes the largest district
    margin among eligible parties, 'marginal' the thinnest, 'median' the
    middling-centroid seat (the classic start)."""
    cands = list(range(n_districts))
    if sc.player_party in ("largest", "smallest"):
        sizes = sorted((pt.id for pt in parties.values() if pt.members),
                       key=lambda i: len(parties[i].members))
        want = sizes[-1] if sc.player_party == "largest" else sizes[0]
        cands = [d for d in cands if mps[d].party == want] or cands
    if sc.player_seat == "median":
        centroids = np.array([voters.pos[voters.district == d].mean(axis=0)
                              for d in range(n_districts)])
        norms = np.linalg.norm(centroids, axis=1)
        return sorted(cands, key=lambda d: norms[d])[len(cands) // 2]
    # margins: winner share minus runner-up share over nearest-platform tally
    plats = np.array([parties[i].platform for i in sorted(parties)])
    d2 = np.linalg.norm(voters.pos[:, None] - plats[None, :], axis=2)
    near = d2.argmin(1)
    margins = np.zeros(n_districts)
    for d in cands:
        tally = np.bincount(near[voters.district == d], minlength=len(plats))
        t = np.sort(tally)
        margins[d] = (t[-1] - t[-2]) / max(int(tally.sum()), 1)
    best = max if sc.player_seat == "safe" else min
    return best(cands, key=lambda d: margins[d])


def new_game(seed: int, scenario: "Scenario | str | None" = None) -> GameState:
    sc = (SCENARIOS[scenario] if isinstance(scenario, str)
          else scenario or SCENARIOS["standard"])
    saved = {k: getattr(p, k) for k in sc.params if hasattr(p, k)}
    for k, v in sc.params.items():
        if hasattr(p, k):
            setattr(p, k, v)
    try:
        return _worldgen(seed, sc)
    finally:
        for k, v in saved.items():
            setattr(p, k, v)


def _worldgen(seed: int, sc: Scenario) -> GameState:
    rng = random.Random(seed)
    # cosmetic stream: seeded separately so wording/naming draws can never
    # move the politics — prose changes must never perturb the mechanical rng
    prose_rng = random.Random(seed ^ p.PROSE_SEED_KEY)
    pack = prose_rng.choice(list(NAME_PACKS))
    np_rng = np.random.default_rng(seed)
    # the party system comes first — the electorate clusters around its anchors
    specs = generate_parties(rng, np_rng, party_pool=sc.party_pool)
    voters = make_voters(rng, np_rng, np.array([pl for _, pl in specs]))
    n_districts = int(voters.district.max()) + 1

    parties = {
        i: Party(id=i, name=name, platform=platform)
        for i, (name, platform) in enumerate(specs)
    }

    # one incumbent per district, anchored near the district centroid
    mps: dict[int, MP] = {}
    names = mp_names(rng, n_districts + p.N_HOPEFULS, pack)
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

    # player: the scenario names the seat — median centroid is the classic deal
    med = _player_district(voters, parties, mps, n_districts, sc)
    if sc.player_party == "outsider":
        old = mps[med].party
        if old in parties:
            parties[old].members.discard(med)
        mps[med].party = None
    conds = {f: float(np.clip(v + np_rng.normal(0, p.COND_JITTER_SD), -1, 1))
             for f, v in p.COND_BASE.items()}
    activism = rng.random()   # the seed's judicial character — inaugural bench doctrine
    centroid = voters.pos.mean(axis=0)
    constitution = make_constitution(rng, centroid)
    bench = make_bench(rng, np_rng, centroid, activism, pack)
    return GameState(
        rng=rng, week=0, phase="campaign", voters=voters, mps=mps, parties=parties,
        seed=seed, prose_rng=prose_rng, country=country_name(prose_rng),
        name_pack=pack, scenario=sc.name,
        constructive_confidence=sc.constructive_confidence,
        district_magnitude=sc.district_magnitude,
        hopefuls=hopefuls, outlets=make_outlets(rng, np_rng, parties),
        conditions=Conditions(**conds),
        player_id=int(med), weeks_to_election=p.CAMPAIGN_WEEKS,
        court_activism=activism,
        constitution=constitution, article_seq=len(constitution),
        bench=bench, justice_seq=len(bench),
    )
