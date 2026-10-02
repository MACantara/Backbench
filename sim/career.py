"""Career machinery: appointments, leadership challenges, scoring, expulsion."""
from __future__ import annotations

import numpy as np

from . import params as p
from .state import GameState, dist

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
            best = max(cands, key=lambda m: state.mps[m].competence + state.mps[m].loyalty)
            state.mps[best].portfolio = ministry
            state.emit("CareerEvent", f"{state.mps[best].name} appointed {ministry}.",
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
        votes = {c: 0 for c in candidates}
        for m in pt.members:
            mp = state.mps[m]
            best = max(candidates, key=lambda c: (
                -dist(mp.pos, state.mps[c].pos)
                + mp.relationships.get(c, 0.0)
                + 0.3 * state.mps[c].competence))
            votes[best] += 1
        winner = max(votes, key=votes.get)
        if winner != pt.leader:
            old = state.mps[pt.leader].name
            pt.leader = winner
            state.emit("CareerEvent", f"{state.mps[winner].name} ousts {old} as {pt.name} leader.",
                       party=pid, new_leader=winner)


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


def check_expulsion(state: GameState) -> None:
    player = state.mps.get(state.player_id)
    if player and player.dossier >= p.DOSSIER_EXPEL_THRESHOLD and state.phase != "over":
        state.phase = "over"
        state.emit("Scandal", "Your dossier reaches the press. You are expelled.",
                   mp=state.player_id)
