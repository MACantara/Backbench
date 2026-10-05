"""Parliamentary mechanics: whips, per-MP vote utility, bill resolution."""
from __future__ import annotations

import numpy as np

from . import params as p
from .conditions import enact, mood
from .naming import austerity_name, bill_name, describe_pos
from .state import Bill, GameState, MP, dist
from .treasury import debt_pressure


def whip_direction(state: GameState, party_id: int, bill: Bill) -> int:
    """Party leader's line on a bill: +1 whip yes, -1 whip no, 0 free vote."""
    if bill.confidence and party_id in state.government.parties:
        return 1  # survival votes: the coalition always whips yes
    pt = state.parties[party_id]
    d = dist(pt.platform, bill.pos)
    if party_id in state.government.parties:
        # the coalition agreement binds: partners whip FOR the government program
        # unless the bill is so far out it breaks the agreement itself
        return -1 if d > p.COALITION_WHIP_TOL else 1
    return 1 if -d > -0.4 else -1


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


def _faction_of(state: GameState, mp: MP):
    """The MP's wing, if their party has one and it survives a staleness check."""
    if mp.party is None or mp.faction is None or mp.party not in state.parties:
        return None
    return next((f for f in state.parties[mp.party].factions if f.id == mp.faction), None)


def faction_whip(state: GameState, mp: MP, bill: Bill) -> int | None:
    """A wing whips against bills far from its centroid; None = follow the party line."""
    f = _faction_of(state, mp)
    if f is None or bill.confidence:
        return None
    return -1 if dist(f.centroid, bill.pos) > p.FACTION_REBEL_DIST else None


def vote_terms(state: GameState, mp: MP, bill: Bill) -> dict[str, float]:
    """Named utility components — the inspector reads these to explain votes."""
    in_gov = mp.party in state.government.parties
    whip = whip_direction(state, mp.party, bill) if mp.party is not None else 0
    fwhip = faction_whip(state, mp, bill)
    terms = {
        "policy": -p.W_POLICY * dist(mp.pos, bill.pos),
        "whip": p.W_WHIP * whip * mp.loyalty,
        "gov": p.W_GOV * in_gov,
        "rel": p.W_REL * (mp.relationships.get(state.government.pm or -1, 0.0) if in_gov else 0.0),
        "district": p.W_SAFETY * (1 - mp.seat_safety) * district_opinion(state, mp.district, bill),
        "fiscal": -p.W_FISCAL * (bill.cost / (p.COST_BASE + p.COST_EXTREMITY_W))
                  * debt_pressure(state),  # stingy house when the books are red
        "noise": state.rng.gauss(0, p.VOTE_NOISE),
    }
    if bill.confidence and in_gov:
        terms["retro"] = p.W_RETRO_CONF * mood(state.conditions)  # the slump votes too
    if fwhip is not None and fwhip != whip:
        terms["fwhip"] = p.W_WHIP * fwhip * mp.loyalty
        terms["whip"] = 0.0  # the wing overrules the party line
    return terms


def vote_utility(state: GameState, mp: MP, bill: Bill) -> float:
    """u > 0 votes yes."""
    return sum(vote_terms(state, mp, bill).values())


def table_bill(state: GameState) -> Bill:
    """The government tables a bill near the coalition's mean platform —
    or, while insolvent, is forced to table cuts: receivership is agenda capture."""
    if state.treasury.debt > p.DEBT_CRISIS:
        bill = Bill(pos=(p.AUSTERITY_POS, 0.0), beneficiary_axis=0,
                    cost=-p.AUSTERITY_SAVING,
                    name=austerity_name(state.rng), austerity=True)
    else:
        gov = [state.parties[i].platform for i in state.government.parties if i in state.parties]
        anchor = np.mean(gov, axis=0) if gov else np.array([0.0, 0.0])
        pos = tuple(np.clip(anchor + np.array([state.rng.gauss(0, 0.05), state.rng.gauss(0, 0.05)]), -1, 1))
        ax = state.rng.randrange(2)
        bill = Bill(pos=pos, beneficiary_axis=ax,
                    cost=float(max(0.0, p.COST_BASE + p.COST_EXTREMITY_W * abs(pos[ax])
                                   + state.rng.gauss(0, p.COST_JITTER))),
                    name=bill_name(pos, ax, state.rng))
    state.current_bill = bill
    verb = "is forced to table" if bill.austerity else "tables"
    state.emit("BillTabled", f"Government {verb} the {bill.name} — "
                             f"{describe_pos(bill.pos)} (cost {bill.cost:+.3f}/wk).",
               pos=bill.pos, beneficiary_axis=bill.beneficiary_axis, cost=bill.cost,
               bill=bill.name, austerity=bill.austerity)
    return bill


def resolve_vote(state: GameState, bill: Bill, player_vote: int | None = None) -> bool:
    """Every MP votes; player_vote (+1/-1/0) overrides the player's utility."""
    yes, no, detail = 0, 0, {}
    rebels: dict[int, int] = {}
    for mp in state.mps.values():
        terms = vote_terms(state, mp, bill)
        if "fwhip" in terms:
            rebels[mp.faction] = mp.party
        u = player_vote if (mp.id == state.player_id and player_vote is not None) else sum(terms.values())
        detail[mp.id] = {"u": u, "terms": terms}
        yes += u > 0
        no += u <= 0
    passed = yes > no
    state.current_bill = None
    for fid, pid in rebels.items():
        f = next((f for f in state.parties[pid].factions if f.id == fid), None)
        if f is not None:
            state.emit("FactionRebels", f"{f.name} whips against the party line on this bill.",
                       party=pid, faction=fid)

    # consequences: brand + voter drift toward/away from government
    gov_parties = [i for i in state.government.parties if i in state.parties]
    if passed and gov_parties:
        gov_platform = np.mean([state.parties[i].platform for i in gov_parties], axis=0)
        ax = bill.beneficiary_axis
        state.voters.pos[:, ax] += p.BILL_PERSUASION * np.sign(gov_platform[ax] - state.voters.pos[:, ax])
        for i in gov_parties:
            state.parties[i].brand += p.BILL_PASS_BRAND
        state.legacy_bills += state.player_id == state.government.pm
        state.emit("VoteResult", f"Bill passes {yes}-{no}.", passed=True, yes=yes, no=no, detail=detail)
        if not bill.confidence:  # survival votes aren't legislation
            enact(state, bill, yes, no)
    else:
        for i in gov_parties:
            state.parties[i].brand -= p.BILL_FAIL_BRAND
        state.emit("VoteResult", f"Bill fails {yes}-{no}.", passed=False, yes=yes, no=no, detail=detail)
    return passed
