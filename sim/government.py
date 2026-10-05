"""Government formation, coalition bargaining, confidence, and dissolution."""
from __future__ import annotations

import numpy as np

from . import params as p
from .dynamism import niche_entry
from .election import poll
from .state import Bill, GameState, dist
from .parliament import resolve_vote

MAJORITY = 61  # of 120 seats

_ELECTION_TEXT = {
    "scheduled": "Term ends — election called.",
    "confidence": "Government fallen — snap election called.",
    "deadlock": "No stable government can be formed — parliament dissolved.",
    "strategic": "The PM calls an early election to capitalize on the polls.",
}


def _seats(state: GameState) -> dict[int, int]:
    seats = {pid: len(pt.members) for pid, pt in state.parties.items()}
    return {pid: n for pid, n in seats.items() if n > 0}


def _will_join(state: GameState, partner_id: int, proposer_id: int) -> bool:
    """A party joins a coalition if its platform isn't too far from the proposer's."""
    a = state.parties[partner_id].platform
    b = state.parties[proposer_id].platform
    # ponytail: distance threshold only — portfolio/concession haggling is v2
    return dist(a, b) < p.COALITION_MAX_DIST


def _best_coalition(state: GameState, exclude_parties: set[int] | None = None
                    ) -> tuple[int, set[int], int] | None:
    """Dry-run coalition builder: each party by size tries partners by proximity.
    Returns (proposer, coalition, bloc) for the first majority, else None."""
    seats = _seats(state)
    for pid in (exclude_parties or ()):
        seats.pop(pid, None)
    for proposer in sorted(seats, key=seats.get, reverse=True):
        coalition, bloc = {proposer}, seats[proposer]
        for partner in sorted(seats, key=lambda pid: dist(state.parties[pid].platform,
                                                          state.parties[proposer].platform)):
            if bloc >= MAJORITY:
                break
            if partner != proposer and _will_join(state, partner, proposer):
                coalition.add(partner)
                bloc += seats[partner]
        if bloc >= MAJORITY:
            return proposer, coalition, bloc
    return None


def form_government(state: GameState) -> bool:
    """Largest party tries to build a majority; falls back to minority government.
    Parties blocked by a lost confidence vote can't re-form this house."""
    blocked = state.government.blocked
    state.government.blocked = set()
    found = _best_coalition(state, exclude_parties=blocked)
    if found is not None:
        proposer, coalition, bloc = found
        state.government.parties = coalition
        state.government.pm = state.parties[proposer].leader
        state.government.minority = False
        state.government.weeks_in_office = 0
        names = [state.parties[i].name for i in coalition]
        state.emit("CoalitionFormed", f"{' + '.join(names)} form a government ({bloc} seats).",
                   parties=sorted(coalition), seats=bloc)
        return True
    # nobody could build a majority — largest unblocked party tries minority rule
    seats = _seats(state)
    for pid in blocked:
        seats.pop(pid, None)
    biggest = max(seats, key=seats.get)
    state.government.parties = {biggest}
    state.government.pm = state.parties[biggest].leader
    state.government.minority = True
    state.government.weeks_in_office = 0
    state.emit("CoalitionFormed", f"{state.parties[biggest].name} forms a minority government ({seats[biggest]} seats).",
               parties=[biggest], seats=seats[biggest], minority=True)
    return True


def call_election(state: GameState, snap: bool, reason: str,
                  party: int | None = None) -> None:
    """Dissolve to campaign — scheduled or snap. Entrants declare at the call."""
    if party is None and state.government.pm in state.mps:
        party = state.mps[state.government.pm].party
    state.emit("ElectionCalled", _ELECTION_TEXT[reason],
               snap=snap, reason=reason, party=party)
    state.current_bill = None   # the pending division dies with the parliament
    state.phase = "campaign"
    state.weeks_to_election = p.CAMPAIGN_WEEKS
    niche_entry(state)


def strategic_call(state: GameState) -> None:
    """A riding-high PM gambles on an early election — scheduling power."""
    gov = state.government
    if not gov.parties or not (p.SNAP_WINDOW[0] <= gov.weeks_in_office <= p.SNAP_WINDOW[1]):
        return
    # early calls convert a poll surplus into seats — no surplus, no gamble
    seat_share = sum(len(state.parties[i].members) for i in gov.parties) / max(len(state.mps), 1)
    poll_share = sum(poll(state).get(pid, 0.0) for pid in gov.parties)
    if poll_share < seat_share + p.SNAP_POLL_EDGE:
        return
    if state.rng.random() < p.SNAP_CALL_P:
        call_election(state, snap=True, reason="strategic")


def confidence_vote(state: GameState) -> bool:
    """A confidence vote is a bill at the government's mean platform.
    On failure the house replaces the government if it can — else it dissolves."""
    gov = [state.parties[i].platform for i in state.government.parties if i in state.parties]
    if not gov:
        return True  # a caretaker void can't lose a vote it never holds
    mean = tuple(np.mean(gov, axis=0))
    survived = resolve_vote(state, Bill(pos=mean, beneficiary_axis=0, confidence=True))
    if not survived:
        pm_party = state.mps[state.government.pm].party \
            if state.government.pm in state.mps else None
        state.emit("ConfidenceLost", "Government loses confidence of the house.",
                   party=pm_party, parties=sorted(state.government.parties))
        state.government.collapses += 1
        fallen_largest = max(state.government.parties,
                             key=lambda pid: len(state.parties[pid].members), default=None)
        alt = _best_coalition(state, exclude_parties={fallen_largest})
        state.government.parties = set()
        state.government.pm = None
        if state.government.collapses >= p.SNAP_COLLAPSE_MAX:
            call_election(state, snap=True, reason="deadlock", party=pm_party)
        elif alt is None:
            call_election(state, snap=True, reason="confidence", party=pm_party)
        else:
            if fallen_largest is not None:
                state.government.blocked = {fallen_largest}
            state.phase = "formation"   # a different majority exists — it forms in place
    return survived
