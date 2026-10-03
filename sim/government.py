"""Government formation, coalition bargaining, and confidence."""
from __future__ import annotations

import numpy as np

from . import params as p
from .state import Bill, GameState, dist
from .parliament import resolve_vote

MAJORITY = 61  # of 120 seats


def _seats(state: GameState) -> dict[int, int]:
    seats = {pid: len(pt.members) for pid, pt in state.parties.items()}
    return {pid: n for pid, n in seats.items() if n > 0}


def _will_join(state: GameState, partner_id: int, proposer_id: int) -> bool:
    """A party joins a coalition if its platform isn't too far from the proposer's."""
    a = state.parties[partner_id].platform
    b = state.parties[proposer_id].platform
    # ponytail: distance threshold only — portfolio/concession haggling is v2
    return dist(a, b) < p.COALITION_MAX_DIST


def form_government(state: GameState) -> bool:
    """Largest party tries to build a majority; falls back to minority government."""
    seats = _seats(state)
    for proposer in sorted(seats, key=seats.get, reverse=True):
        coalition = {proposer}
        bloc = seats[proposer]
        for partner in sorted(seats, key=lambda pid: dist(state.parties[pid].platform, state.parties[proposer].platform)):
            if bloc >= MAJORITY:
                break
            if partner != proposer and _will_join(state, partner, proposer):
                coalition.add(partner)
                bloc += seats[partner]
        if bloc >= MAJORITY:
            state.government.parties = coalition
            state.government.pm = state.parties[proposer].leader
            state.government.minority = False
            state.government.weeks_in_office = 0
            names = [state.parties[i].name for i in coalition]
            state.emit("CoalitionFormed", f"{' + '.join(names)} form a government ({bloc} seats).",
                       parties=sorted(coalition), seats=bloc)
            return True
    # nobody could build a majority — largest party tries minority rule
    biggest = max(seats, key=seats.get)
    state.government.parties = {biggest}
    state.government.pm = state.parties[biggest].leader
    state.government.minority = True
    state.government.weeks_in_office = 0
    state.emit("CoalitionFormed", f"{state.parties[biggest].name} forms a minority government ({seats[biggest]} seats).",
               parties=[biggest], seats=seats[biggest], minority=True)
    return True


def confidence_vote(state: GameState) -> bool:
    """A confidence vote is a bill at the government's mean platform."""
    gov = [state.parties[i].platform for i in state.government.parties if i in state.parties]
    mean = tuple(np.mean(gov, axis=0))
    survived = resolve_vote(state, Bill(pos=mean, beneficiary_axis=0, confidence=True))
    if not survived:
        pm_party = state.mps[state.government.pm].party \
            if state.government.pm in state.mps else None
        state.emit("ConfidenceLost", "Government loses confidence of the house.",
                   party=pm_party, parties=sorted(state.government.parties))
        state.government.parties = set()
        state.government.pm = None
        state.phase = "formation"
    return survived
