"""Career machinery: appointments, leadership challenges, scoring, expulsion."""
from __future__ import annotations

import numpy as np

from . import params as p
from .state import GameState, dist
from .worldgen import make_hopeful

PORTFOLIOS = ["Finance", "Interior", "Foreign", "Health", "Justice"]


def assign_portfolios(state: GameState) -> None:
    """PM hands ministries to coalition MPs by competence + loyalty, split by seats."""
    for mp in state.mps.values():
        mp.portfolio = None
    seats = {pid: len(state.parties[pid].members) for pid in state.government.parties if pid in state.parties}
    total = max(sum(seats.values()), 1)
    queue = []
    for pid, n in seats.items():
        queue += [pid] * round(len(PORTFOLIOS) * n / total)
    for pid, ministry in zip(queue, PORTFOLIOS):
        cands = [m for m in state.parties[pid].members
                 if m in state.mps and state.mps[m].portfolio is None and m != state.government.pm]
        if cands:
            best = max(cands, key=lambda m: (state.mps[m].competence + state.mps[m].loyalty
                                             + min(state.mps[m].seniority / 1040, 1) * p.SENIORITY_W))
            state.mps[best].portfolio = ministry
            state.emit("Promoted", f"{state.mps[best].name} appointed {ministry}.",
                       mp=best, ministry=ministry)


def leadership_challenge(state: GameState) -> None:
    """Weak leaders face ambitious challengers — members vote on utility."""
    for pid, pt in state.parties.items():
        if pt.leader is None or len(pt.members) < 4:
            continue
        if pt.cohesion >= p.LEADERSHIP_COHESION_MIN:
            continue
        challengers = [m for m in pt.members
                       if m != pt.leader and state.mps[m].ambition > p.CHALLENGE_AMBITION_MIN]
        if not challengers:
            continue
        candidates = [pt.leader] + challengers
        fleaders = {f.leader for f in pt.factions}
        votes = {c: 0 for c in candidates}
        for m in pt.members:
            mp = state.mps[m]
            best = max(candidates, key=lambda c: (
                -dist(mp.pos, state.mps[c].pos)
                + mp.relationships.get(c, 0.0)
                + 0.3 * state.mps[c].competence
                + (p.FACTION_LEADER_BONUS if c in fleaders else 0.0)))
            votes[best] += 1
        winner = max(votes, key=votes.get)
        if winner != pt.leader:
            old = state.mps[pt.leader].name
            pt.leader = winner
            state.emit("CareerEvent", f"{state.mps[winner].name} ousts {old} as {pt.name} leader.",
                       party=pid, new_leader=winner)


def remove_mp(state: GameState, mp) -> None:
    """Take an MP out of parliament: membership, leadership, premiership handoffs."""
    del state.mps[mp.id]
    pt = state.parties.get(mp.party)
    if pt is not None:
        pt.members.discard(mp.id)
        if pt.leader == mp.id:
            cands = [m for m in pt.members if m in state.mps]
            pt.leader = max(cands, key=lambda m: state.mps[m].ambition) if cands else None
            if pt.leader is not None:
                state.emit("CareerEvent",
                           f"{state.mps[pt.leader].name} succeeds {mp.name} as {pt.name} leader.",
                           party=pt.id, new_leader=pt.leader)
    if state.government.pm == mp.id:
        succ = pt.leader if pt is not None and pt.members else None
        state.government.pm = succ
        if succ is not None:
            state.emit("CareerEvent", f"{state.mps[succ].name} succeeds {mp.name} as PM.", mp=succ)


def mp_lifecycle(state: GameState) -> None:
    """Weekly aging + retirement. Vacated seats stay empty until the election."""
    for mp in state.mps.values():
        mp.age += 1
        mp.seniority += 1
    gone = []
    for mp in state.mps.values():
        if mp.id == state.player_id:
            continue
        prob = 0.0
        if mp.age >= p.RETIRE_FLOOR:
            prob = min(p.RETIRE_MAX_P,
                       p.RETIRE_BASE_P + max(0, mp.age - p.RETIRE_AGE) * p.RETIRE_SLOPE)
        if state.rng.random() < prob:
            gone.append(mp)
    for mp in gone:
        remove_mp(state, mp)
        state.emit("Retired", f"{mp.name} retires at {mp.age // 52}; the seat sits vacant.",
                   mp=mp.id, district=mp.district, age=mp.age)

    for h in state.hopefuls:
        h.age += 1
    if state.rng.random() < p.HOPEFULS_PER_WEEK_P:
        np_rng = np.random.default_rng(int(state.rng.random() * 2**63))
        n_districts = int(state.voters.district.max()) + 1
        state.hopefuls.append(make_hopeful(state.rng, np_rng, state.parties, n_districts,
                                           age=p.HOPEFUL_AGE[0]))


def update_score(state: GameState) -> None:
    """Called after each election the player survives."""
    player = state.mps[state.player_id]
    state.score_terms["mp"] += 1
    if player.portfolio:
        state.score_terms["minister"] += 1
    if state.government.pm == state.player_id:
        state.score_terms["pm"] += 1


def final_score(state: GameState) -> int:
    t = state.score_terms
    return t["mp"] + 3 * t["minister"] + 5 * t["pm"] + state.legacy_bills


