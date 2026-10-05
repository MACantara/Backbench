"""Parliamentary mechanics: whips, per-MP vote utility, bill resolution."""
from __future__ import annotations

import numpy as np

from . import params as p
from .conditions import enact, mood
from .naming import austerity_name, bill_name, describe_pos
from .state import Bill, GameState, MP, dist, gov_platform
from .treasury import budget_posture, debt_pressure


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
    line = fwhip if fwhip is not None else whip
    if line and mp.scandal_weeks > 0:
        # a burning member votes to look independent — distance from the line
        terms["selfpres"] = -p.W_SELFPRES * line
    return terms


def vote_utility(state: GameState, mp: MP, bill: Bill) -> float:
    """u > 0 votes yes."""
    return sum(vote_terms(state, mp, bill).values())


def _struck_article(state: GameState):
    """The clause that struck down a law of the sitting coalition, if any —
    the wound that motivates a repeal amendment. Gone clauses don't qualify."""
    gov = set(state.government.parties)
    for e in reversed(state.log):
        if e.type == "LawStruck" and gov & set(e.data.get("parties", ())):
            art = next((a for a in state.constitution
                        if a.id == e.data.get("article")), None)
            # a government gets one swing at a clause per term — a failed
            # repeal is spent, the wound doesn't refill the agenda forever
            if art is not None and art.id not in state.government.amend_attempted:
                return art
    return None


def table_bill(state: GameState) -> Bill:
    """The government tables a bill near the coalition's mean platform —
    or, while insolvent, is forced to table cuts: receivership is agenda capture.
    At REPEAL_P the government instead strikes the inherited standing law most
    hostile to its agenda — the repeal bill rides the agreement itself (a
    repeal IS the government's program); the law's authors defend it through
    their own policy/district terms."""
    bill = None
    pm_move = False
    if state.week % p.BUDGET_EVERY_WEEKS == 0:
        # supply day: the government lays its fiscal posture before the house —
        # a confidence matter, pending like any bill so the week reads it
        stance = state.government.budget_stance
        state.government.budget_stance = None
        tax, spend = (p.BUDGET_STANCES[stance] if stance is not None
                      else budget_posture(state))
        label = "austerity" if spend < 0.97 else "stimulus" if spend > 1.03 else "balanced"
        bill = Bill(pos=tuple(gov_platform(state)), beneficiary_axis=0,
                    cost=p.BUDGET_COST_SCALE * (spend - 1.0),
                    confidence=True, budget=True, tax=tax, spend=spend,
                    name=f"Budget {state.week // p.BUDGET_EVERY_WEEKS} ({label})")
    elif state.treasury.debt > p.DEBT_CRISIS:
        bill = Bill(pos=(p.AUSTERITY_POS, 0.0), beneficiary_axis=0,
                    cost=-p.AUSTERITY_SAVING,
                    name=austerity_name(state.rng), austerity=True)
    elif state.government.amend_move is not None:
        # the player-PM's queued amendment takes the floor as government
        # business — tabled this week, divided next like everything else
        queued = state.government.amend_move
        state.government.amend_move = None
        stale = (queued.amends is not None
                 and queued.amends not in state.constitution) \
            or (queued.entrenches is not None and any(
                a.kind == "pos" and a.axis == queued.entrenches.axis
                and a.pole == queued.entrenches.pole for a in state.constitution))
        if stale:
            # the book moved under the queued amendment — the moment passed
            state.emit("CareerEvent",
                       "Your amendment is overtaken — the clause it moved on "
                       "is gone.", action="amendment")
        else:
            bill = queued
            pm_move = True
    elif (wounded := _struck_article(state)) is not None \
            and state.rng.random() < p.AMEND_TABLE_P:
        # the court struck our flagship citing a clause — try to repeal the
        # clause itself; the constitution bends at two-thirds, not before
        bill = Bill(pos=tuple(gov_platform(state)), beneficiary_axis=0,
                    amends=wounded, name=f"Repeal of {wounded.name}")
        state.government.amend_attempted.add(wounded.id)
    elif state.laws and state.rng.random() < p.REPEAL_P:
        agenda = gov_platform(state)
        term_start = state.week - state.government.weeks_in_office
        foreign = [l for l in state.laws if l.passed_week < term_start]
        if foreign:  # no inherited statutes → falls through to an ordinary week
            law = max(foreign, key=lambda l: dist(l.pos, agenda))
            bill = Bill(pos=tuple(agenda),
                        beneficiary_axis=law.beneficiary_axis,
                        cost=-law.cost,   # repealing a costly law saves — fiscal term reads it
                        repeals=law, name=f"Repeal of the {law.name}")
    if bill is None:
        anchor = tuple(gov_platform(state))
        # the agenda remembers its defeats — a cooled-off failure may return
        ripe = [f for f in state.failed
                if state.week - f["week"] >= p.RETABLE_CD
                and dist(f["pos"], anchor) < p.COALITION_FREE_DIST]
        if ripe and state.rng.random() < p.RETABLE_P:
            f = ripe[0]
            state.failed.remove(f)
            bill = Bill(pos=f["pos"], beneficiary_axis=f["axis"], cost=f["cost"],
                        name=f"{f['name']} (Revisited)")
        else:
            pos = tuple(np.clip(np.asarray(anchor)
                        + np.array([state.rng.gauss(0, 0.05), state.rng.gauss(0, 0.05)]), -1, 1))
            ax = state.rng.randrange(2)
            bill = Bill(pos=pos, beneficiary_axis=ax,
                        cost=float(max(0.0, p.COST_BASE + p.COST_EXTREMITY_W * abs(pos[ax])
                                       + state.rng.gauss(0, p.COST_JITTER))),
                        name=bill_name(pos, ax, state.rng))
    state.current_bill = bill
    if bill.amends is not None or bill.entrenches is not None:
        mover = "You move" if pm_move or bill.author == state.player_id \
            else "Government tables"
        text = (f"{mover} the {bill.name} — a constitutional amendment — "
                "division next week, and it needs two-thirds.")
    elif bill.repeals is not None:
        text = (f"Government moves to repeal the {bill.repeals.name} "
                "— division next week.")
    else:
        verb = "is forced to table" if bill.austerity else "tables"
        text = (f"Government {verb} the {bill.name} — "
                f"{describe_pos(bill.pos)} (cost {bill.cost:+.3f}/wk) "
                "— division next week.")
    state.emit("BillTabled", text,
               pos=bill.pos, beneficiary_axis=bill.beneficiary_axis, cost=bill.cost,
               bill=bill.name, austerity=bill.austerity,
               amends=bill.amends.id if bill.amends else None,
               entrenches=bill.entrenches.name if bill.entrenches else None,
               repeals=bill.repeals.name if bill.repeals else None)
    return bill


def resolve_vote(state: GameState, bill: Bill, player_vote: int | None = None) -> bool | None:
    """Every present MP votes — or abstains. player_vote (+1/-1/0) is the
    player's override; 0 is a real abstain. None return = quorum failed and
    the division carries to next week."""
    # attendance: the house isn't always full — absence spikes near term end,
    # in burning scandal weeks, and late in careers (the player always shows)
    loom = (state.government.weeks_in_office
            >= p.GOVERNING_WEEKS_PER_TERM - p.ATTEND_ELECTION_WEEKS)
    shock = p.ATTEND_SHOCK if state.rng.random() < p.ATTEND_SHOCK_P else 0.0
    present = []
    for mp in state.mps.values():
        ap = p.ATTEND_BASE + shock
        ap += (p.ATTEND_LATE if loom else 0.0) + (p.ATTEND_SCANDAL if mp.scandal_weeks > 0 else 0.0) \
            + (p.ATTEND_AGE if mp.age >= p.RETIRE_AGE else 0.0)
        if mp.id == state.player_id or state.rng.random() >= ap:
            present.append(mp)
    if len(present) < p.QUORUM * max(len(state.mps), 1):
        # a pending division (incl. a budget) carries to next week; a
        # free-standing motion — a forced confidence vote, a private
        # member's bill — simply lapses
        tail = ("the division carries over." if bill is state.current_bill
                else "the motion lapses — the government survives the empty benches."
                if bill.confidence else "the motion lapses.")
        state.emit("DivisionStalled",
                   f"Quorum fails on the {bill.name} — {len(present)} of "
                   f"{len(state.mps)} present; {tail}",
                   bill=bill.name, present=len(present), house=len(state.mps))
        return None
    yes, no, abstain, detail = 0, 0, 0, {}
    rebels: dict[int, int] = {}
    for mp in present:
        terms = vote_terms(state, mp, bill)
        if "fwhip" in terms:
            rebels[mp.faction] = mp.party
        is_player = mp.id == state.player_id and player_vote is not None
        u = float(player_vote) if is_player else sum(terms.values())
        whip = whip_direction(state, mp.party, bill) if mp.party is not None else 0
        # confidence divisions are three-line whips — a whipped MP in the
        # deadzone falls in with the line (the player still can abstain:
        # their franchise, rebellion price and all)
        can_abstain = is_player or not (bill.confidence and whip)
        if u > p.ABSTAIN_MARGIN:
            cast = 1
        elif u < -p.ABSTAIN_MARGIN:
            cast = -1
        elif can_abstain:
            cast = 0
        else:
            cast = 1 if whip > 0 else -1   # lukewarm whipped MPs fall in line
        detail[mp.id] = {"u": u, "cast": cast, "terms": terms}
        yes, no, abstain = yes + (cast == 1), no + (cast == -1), abstain + (cast == 0)
        # the whip remembers: standing accrues on the cast column, override
        # included; an abstain is half a rebellion — the line wasn't delivered.
        # A faction whip is organized rebellion — the party line still marks you.
        if whip:
            if cast == 1:
                delta = p.STANDING_WHIP_YES if whip > 0 else -p.STANDING_WHIP_NO
            elif cast == -1:
                delta = p.STANDING_WHIP_YES if whip < 0 else -p.STANDING_WHIP_NO
            else:
                delta = -p.STANDING_WHIP_ABSTAIN
            mp.standing = float(np.clip(mp.standing + delta, -1, 1))
    is_amendment = bill.amends is not None or bill.entrenches is not None
    # amendments need two-thirds of votes cast — the constitution is hard
    # to move on purpose; abstentions waste the mover
    passed = (yes > 0 and yes >= p.AMEND_MAJORITY * (yes + no) if is_amendment
              else yes > no)
    if bill is state.current_bill:
        state.current_bill = None   # a confidence motion isn't the pending bill
    # the player keeps or breaks their word — judged on the cast column
    player = state.mps.get(state.player_id)
    for deal in [d for d in state.deals if d.bill is bill]:
        cast = detail.get(state.player_id, {}).get("cast", 0)
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

    # consequences: voter drift on passage, brand for the government when it
    # owns the bill — a private member's win or loss isn't theirs
    gov_parties = [i for i in state.government.parties if i in state.parties]
    label = "Budget" if bill.budget else "Amendment" if is_amendment else "Bill"
    if passed:
        ax = bill.beneficiary_axis
        state.voters.pos[:, ax] += p.BILL_PERSUASION * np.sign(bill.pos[ax] - state.voters.pos[:, ax])
        if gov_parties and bill.author is None:
            for i in gov_parties:
                state.parties[i].brand += p.BILL_PASS_BRAND
        state.emit("VoteResult", f"{label} passes {yes}-{no} ({abstain} abstain).",
                   passed=True, yes=yes, no=no, abstain=abstain,
                   detail=detail, player=player_vote)
        if bill.budget:
            state.treasury.posture = (bill.tax, bill.spend)
            state.emit("BudgetSet",
                       f"The {bill.name} sets the fiscal stance — "
                       f"tax ×{bill.tax:.2f}, spend ×{bill.spend:.2f}.",
                       bill=bill.name, tax=bill.tax, spend=bill.spend)
        if bill.amends is not None:
            state.constitution = [a for a in state.constitution
                                  if a is not bill.amends]
            state.emit("ArticleRepealed",
                       f"{bill.amends.name} is struck from the constitution — "
                       "the statute book stands past it.",
                       article=bill.amends.id)
        if bill.entrenches is not None:
            art = bill.entrenches
            art.id = state.article_seq
            state.article_seq += 1
            state.constitution.append(art)
            state.emit("ArticleEntrenched",
                       f"{art.name} is written into the constitution — "
                       "the courts gain a new guard.",
                       article=art.id)
        state.legacy_bills += is_amendment and (
            bill.author == state.player_id
            or (bill.author is None and state.government.pm == state.player_id))
        if not bill.confidence and not is_amendment:
            # survival votes aren't legislation; amendments rewrite the book
            # itself — the bench doesn't review its own charter
            law = enact(state, bill, yes, no)
            state.legacy_bills += law is not None and law.author == state.player_id
    else:
        if gov_parties and bill.author is None:
            for i in gov_parties:
                state.parties[i].brand -= p.BILL_FAIL_BRAND
        if not bill.confidence and bill.repeals is None and not bill.austerity \
                and not is_amendment and bill.author is None:
            # defeated *government* bills are remembered — the agenda may retry;
            # a private member's defeat isn't the government's to revive
            state.failed.append({"pos": bill.pos, "name": bill.name or "a bill",
                                 "week": state.week, "axis": bill.beneficiary_axis,
                                 "cost": bill.cost})
            del state.failed[:-p.FAILED_MAX]
        short = " — the majority wasn't two-thirds" if is_amendment and yes > no else ""
        state.emit("VoteResult", f"{label} fails {yes}-{no} ({abstain} abstain).{short}",
                   passed=False, yes=yes, no=no, abstain=abstain,
                   detail=detail, player=player_vote)
    return passed
