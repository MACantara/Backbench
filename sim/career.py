"""Career machinery: appointments, leadership challenges, scoring, expulsion."""
from __future__ import annotations

import numpy as np

from . import params as p
from .state import GameState, dist
from .worldgen import make_hopeful

PORTFOLIOS = list(p.PORTFOLIO_INDICATOR)   # the cabinet table — append rows to grow


def _seat_queue(state: GameState) -> list[int]:
    """Portfolio slots dealt to coalition parties by seat share (Gamson-lite)."""
    seats = {pid: len(state.parties[pid].members)
             for pid in state.government.parties if pid in state.parties}
    total = max(sum(seats.values()), 1)
    return [pid for pid, n in seats.items()
            for _ in range(round(len(PORTFOLIOS) * n / total))]


def _appoint(state: GameState, pid: int, ministry: str, reason: str = "cabinet") -> bool:
    """Best available MP of a party takes a ministry."""
    cands = [m for m in state.parties[pid].members
             if m in state.mps and state.mps[m].portfolio is None
             and m != state.government.pm and m not in state.government.sacked]
    if not cands:
        return False
    best = max(cands, key=lambda m: (state.mps[m].competence + state.mps[m].loyalty
                                     + min(state.mps[m].seniority / p.SENIORITY_CAP_WEEKS, 1)
                                     * p.SENIORITY_W))
    mp = state.mps[best]
    mp.portfolio, mp.perf, mp.portfolio_weeks = ministry, 0.0, 0
    state.emit("Promoted", f"{mp.name} appointed {ministry}.",
               mp=best, ministry=ministry, reason=reason)
    return True


def assign_portfolios(state: GameState) -> None:
    """PM hands ministries to coalition MPs by competence + loyalty, split by seats."""
    for mp in state.mps.values():
        mp.portfolio, mp.portfolio_weeks = None, 0
    for pid, ministry in zip(_seat_queue(state), PORTFOLIOS):
        _appoint(state, pid, ministry)


def ministerial_lifecycle(state: GameState) -> None:
    """Weekly: strip defectors, judge records, refill every dark chair.
    A reshuffle swaps the person — seat-weighted shares decide the party."""
    gov = state.government.parties
    if not gov:
        return
    # a portfolio belongs to a government, not the person — defectors lose it
    for mp in state.mps.values():
        if mp.portfolio is not None and mp.party not in gov:
            mp.portfolio, mp.portfolio_weeks = None, 0
    for mp in state.mps.values():
        if (mp.portfolio is None or mp.party not in gov
                or mp.id == state.government.pm):
            continue
        if mp.portfolio_weeks >= p.MINISTER_TENURE and mp.perf < p.MINISTER_SACK_RECORD:
            ministry, pid = mp.portfolio, mp.party
            mp.portfolio, mp.portfolio_weeks = None, 0
            state.government.sacked.add(mp.id)   # no same-term re-hire
            pm = state.mps.get(state.government.pm)
            if pm is not None and pm.party in state.parties:
                state.parties[pm.party].brand -= p.MINISTER_SACK_BRAND
            what = p.PORTFOLIO_INDICATOR.get(ministry) or "ministerial"
            state.emit("MinisterSacked",
                       f"{mp.name} is sacked as {ministry} — the {what} numbers got worse.",
                       mp=mp.id, party=pid, portfolio=ministry, reason="performance")
    # every dark chair gets a body — sacks, scandals, defections, retirements
    held = {mp.portfolio for mp in state.mps.values()
            if mp.portfolio is not None and mp.party in gov}
    for pid, ministry in zip(_seat_queue(state), PORTFOLIOS):
        if ministry not in held and _appoint(state, pid, ministry, reason="reshuffle"):
            held.add(ministry)


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


