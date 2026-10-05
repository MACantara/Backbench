"""Parliamentary mechanics: whips, per-MP vote utility, bill resolution."""
from __future__ import annotations

import numpy as np

from . import params as p
from .conditions import enact, mood
from .naming import austerity_name, bill_name, describe_pos
from .state import Bill, GameState, MP, dist, gov_platform
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
    if not state.government.parties:
        return -dist(centroid, bill.pos) * 0.3  # no baseline → weak absolute opinion
    return dist(centroid, gov_platform(state)) - dist(centroid, bill.pos)


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


def vote_terms(state: GameState, mp: MP, bill: Bill,
               noisy: bool = True) -> dict[str, float]:
    """Named utility components — the inspector reads these to explain votes.
    noisy=False strips the draw so projections stay off the rng stream."""
    in_gov = mp.party in state.government.parties
    whip = whip_direction(state, mp.party, bill) if mp.party is not None else 0
    fwhip = faction_whip(state, mp, bill)
    terms = {
        "policy": -p.W_POLICY * dist(mp.pos, bill.pos),
        "whip": p.W_WHIP * whip * mp.loyalty,
        "gov": p.W_GOV * in_gov,
        "rel": p.W_REL * (mp.relationships.get(state.government.pm, 0.0)
                        if in_gov and state.government.pm is not None else 0.0),
        "district": p.W_SAFETY * (1 - mp.seat_safety) * district_opinion(state, mp.district, bill),
        "fiscal": -p.W_FISCAL * (bill.cost / (p.COST_BASE + p.COST_EXTREMITY_W))
                  * debt_pressure(state),  # stingy house when the books are red
    }
    if noisy:
        terms["noise"] = state.rng.gauss(0, p.VOTE_NOISE)
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
        anchor = np.asarray(gov_platform(state))  # bills ride the agreement
        pos = tuple(np.clip(anchor + np.array([state.rng.gauss(0, 0.05), state.rng.gauss(0, 0.05)]), -1, 1))
        ax = state.rng.randrange(2)
        bill = Bill(pos=pos, beneficiary_axis=ax,
                    cost=float(max(0.0, p.COST_BASE + p.COST_EXTREMITY_W * abs(pos[ax])
                                   + state.rng.gauss(0, p.COST_JITTER))),
                    name=bill_name(pos, ax, state.rng))
    state.current_bill = bill
    verb = "is forced to table" if bill.austerity else "tables"
    state.emit("BillTabled", f"Government {verb} the {bill.name} — "
                             f"{describe_pos(bill.pos)} (cost {bill.cost:+.3f}/wk) "
                             "— division next week.",
               pos=bill.pos, beneficiary_axis=bill.beneficiary_axis, cost=bill.cost,
               bill=bill.name, austerity=bill.austerity)
    return bill


def resolve_vote(state: GameState, bill: Bill, player_vote: int | None = None) -> bool | None:
    """Every present MP votes — or abstains. player_vote (+1/-1/0) is the
    player's override; 0 is a real abstain. None return = quorum failed and
    the division carries to next week."""
    # attendance: the house isn't always full — absence spikes near term end,
    # in burning scandal weeks, and late in careers (the player always shows)
    loom = (state.government.weeks_in_office
            >= p.GOVERNING_WEEKS_PER_TERM - p.ATTEND_ELECTION_WEEKS)
    present = []
    for mp in state.mps.values():
        ap = p.ATTEND_BASE
        ap += (p.ATTEND_LATE if loom else 0.0) + (p.ATTEND_SCANDAL if mp.scandal_weeks > 0 else 0.0) \
            + (p.ATTEND_AGE if mp.age >= p.RETIRE_AGE else 0.0)
        if mp.id == state.player_id or state.rng.random() >= ap:
            present.append(mp)
    if len(present) < p.QUORUM * max(len(state.mps), 1):
        state.emit("DivisionStalled",
                   f"Quorum fails on the {bill.name} — {len(present)} of "
                   f"{len(state.mps)} present; the division carries over.",
                   bill=bill.name, present=len(present), house=len(state.mps))
        return None
    yes, no, abstain, detail = 0, 0, 0, {}
    rebels: dict[int, int] = {}
    for mp in present:
        terms = vote_terms(state, mp, bill)
        if "fwhip" in terms:
            rebels[mp.faction] = mp.party
        u = float(player_vote) if (mp.id == state.player_id
                                   and player_vote is not None) else sum(terms.values())
        detail[mp.id] = {"u": u, "terms": terms}
        whip = whip_direction(state, mp.party, bill) if mp.party is not None else 0
        # confidence divisions are three-line whips — a whipped MP can't abstain
        can_abstain = not (bill.confidence and whip)
        if u > p.ABSTAIN_MARGIN or (u > 0 and not can_abstain):
            yes += 1
        elif u < -p.ABSTAIN_MARGIN or (u < 0 and not can_abstain):
            no += 1
        else:
            abstain += 1
        # the whip remembers: standing accrues on the actual vote, override
        # included; an abstain is half a rebellion — the line wasn't delivered.
        # A faction whip is organized rebellion — the party line still marks you.
        if whip:
            if u > p.ABSTAIN_MARGIN:
                delta = p.STANDING_WHIP_YES if whip > 0 else -p.STANDING_WHIP_NO
            elif u < -p.ABSTAIN_MARGIN:
                delta = p.STANDING_WHIP_YES if whip < 0 else -p.STANDING_WHIP_NO
            else:
                delta = -p.STANDING_WHIP_ABSTAIN
            mp.standing = float(np.clip(mp.standing + delta, -1, 1))
    passed = yes > no
    if bill is state.current_bill:
        state.current_bill = None   # a confidence motion isn't the pending bill
    # the player keeps or breaks their word — judged on the cast column
    player = state.mps.get(state.player_id)
    for deal in [d for d in state.deals if d.bill is bill]:
        col = detail.get(state.player_id, {}).get("u", 0.0)
        cast = 1 if col > p.ABSTAIN_MARGIN else (-1 if col < -p.ABSTAIN_MARGIN else 0)
        kept = cast == deal.vote
        t = state.mps.get(deal.mp)
        if t is not None:
            t.relationships[state.player_id] = t.relationships.get(state.player_id, 0.0) \
                + (p.DEAL_KEPT_REL if kept else -p.DEAL_BROKEN_REL)
        if player is not None:
            player.standing = float(np.clip(
                player.standing + (p.DEAL_STANDING if kept else -p.DEAL_STANDING), -1, 1))
        who = state.mps[deal.mp].name if deal.mp in state.mps else "a departed member"
        state.emit("DealKept" if kept else "DealBroken",
                   f"Your promise to {who} on the {bill.name} — "
                   + ("kept; your word is banked." if kept else "broken."),
                   mp=deal.mp, bill=bill.name, kept=kept)
        state.deals.remove(deal)
    for fid, pid in rebels.items():
        f = next((f for f in state.parties[pid].factions if f.id == fid), None)
        if f is not None:
            state.emit("FactionRebels", f"{f.name} whips against the party line on this bill.",
                       party=pid, faction=fid)

    # consequences: brand + voter drift toward/away from government
    gov_parties = [i for i in state.government.parties if i in state.parties]
    if passed and gov_parties:
        agenda = gov_platform(state)
        ax = bill.beneficiary_axis
        state.voters.pos[:, ax] += p.BILL_PERSUASION * np.sign(agenda[ax] - state.voters.pos[:, ax])
        for i in gov_parties:
            state.parties[i].brand += p.BILL_PASS_BRAND
        state.legacy_bills += state.player_id == state.government.pm
        state.emit("VoteResult", f"Bill passes {yes}-{no} ({abstain} abstain).",
                   passed=True, yes=yes, no=no, abstain=abstain,
                   detail=detail, player=player_vote)
        if not bill.confidence:  # survival votes aren't legislation
            enact(state, bill, yes, no)
    else:
        for i in gov_parties:
            state.parties[i].brand -= p.BILL_FAIL_BRAND
        state.emit("VoteResult", f"Bill fails {yes}-{no} ({abstain} abstain).",
                   passed=False, yes=yes, no=no, abstain=abstain,
                   detail=detail, player=player_vote)
    return passed
