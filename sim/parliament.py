"""Parliamentary mechanics: whips, per-MP vote utility, bill resolution."""
from __future__ import annotations

import numpy as np

from . import params as p
from .state import Bill, GameState, MP, dist


def whip_direction(state: GameState, party_id: int, bill: Bill) -> int:
    """Party leader's line on a bill: +1 whip yes, -1 whip no, 0 free vote."""
    pt = state.parties[party_id]
    d = dist(pt.platform, bill.pos)
    # coalition partners lean yes — the government made this bill
    bonus = 0.3 if party_id in state.government.parties else 0.0
    return 1 if (-d + bonus) > -0.4 else -1


def district_opinion(state: GameState, district: int, bill: Bill) -> float:
    """District's view of the bill relative to the government platform:
    positive when the bill is *closer* to the district than the gov baseline."""
    v = state.voters
    centroid = tuple(v.pos[v.district == district].mean(axis=0))
    gov = [state.parties[i].platform for i in state.government.parties if i in state.parties]
    if not gov:
        return -dist(centroid, bill.pos) * 0.3  # no baseline → weak absolute opinion
    gov_mean = tuple(np.mean(gov, axis=0))
    return dist(centroid, gov_mean) - dist(centroid, bill.pos)


def vote_utility(state: GameState, mp: MP, bill: Bill) -> float:
    """u > 0 votes yes. Policy distance, whip, government ties, district exposure."""
    in_gov = mp.party in state.government.parties
    whip = whip_direction(state, mp.party, bill) if mp.party is not None else 0
    rel = mp.relationships.get(state.government.pm or -1, 0.0) if in_gov else 0.0
    district = district_opinion(state, mp.district, bill)
    return (-p.W_POLICY * dist(mp.pos, bill.pos)
            + p.W_WHIP * whip * mp.loyalty
            + p.W_GOV * in_gov
            + p.W_REL * rel
            + p.W_SAFETY * (1 - mp.seat_safety) * district
            + state.rng.gauss(0, p.VOTE_NOISE))


def table_bill(state: GameState) -> Bill:
    """The government tables a bill near the coalition's mean platform."""
    gov = [state.parties[i].platform for i in state.government.parties if i in state.parties]
    anchor = np.mean(gov, axis=0) if gov else np.array([0.0, 0.0])
    pos = tuple(np.clip(anchor + np.array([state.rng.gauss(0, 0.05), state.rng.gauss(0, 0.05)]), -1, 1))
    bill = Bill(pos=pos, beneficiary_axis=state.rng.randrange(2))
    state.current_bill = bill
    state.emit("BillTabled", f"Government tables a bill at ({pos[0]:+.2f}, {pos[1]:+.2f}).",
               pos=pos, beneficiary_axis=bill.beneficiary_axis)
    return bill


def resolve_vote(state: GameState, bill: Bill, player_vote: int | None = None) -> bool:
    """Every MP votes; player_vote (+1/-1/0) overrides the player's utility."""
    yes, no, detail = 0, 0, {}
    for mp in state.mps.values():
        u = player_vote if (mp.id == state.player_id and player_vote is not None) else vote_utility(state, mp, bill)
        detail[mp.id] = u
        yes += u > 0
        no += u <= 0
    passed = yes > no
    state.current_bill = None

    # consequences: brand + voter drift toward/away from government
    gov_parties = [i for i in state.government.parties if i in state.parties]
    if passed and gov_parties:
        gov_platform = np.mean([state.parties[i].platform for i in gov_parties], axis=0)
        ax = bill.beneficiary_axis
        state.voters.pos[:, ax] += 0.02 * np.sign(gov_platform[ax] - state.voters.pos[:, ax])
        for i in gov_parties:
            state.parties[i].brand += 0.02
        state.legacy_bills += state.player_id == state.government.pm
        state.emit("VoteResult", f"Bill passes {yes}-{no}.", passed=True, yes=yes, no=no, detail=detail)
    else:
        for i in gov_parties:
            state.parties[i].brand -= 0.03
        state.emit("VoteResult", f"Bill fails {yes}-{no}.", passed=False, yes=yes, no=no, detail=detail)
    return passed
