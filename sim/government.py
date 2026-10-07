"""Government formation, coalition bargaining, confidence, and dissolution."""
from __future__ import annotations

import numpy as np

from . import params as p
from .dynamism import niche_entry
from .prose import render
from .state import Bill, GameState, dist, gov_platform
from .parliament import describe_pos, resolve_vote

def _majority(state: GameState) -> int:
    return len(state.mps) // 2 + 1

_ELECTION_TEXT = {
    "scheduled": "Term ends — election called.",
    "confidence": "Government fallen — snap election called.",
    "deadlock": "No stable government can be formed — parliament dissolved.",
    "strategic": "The PM calls an early election to capitalize on the polls.",
}


def _seats(state: GameState) -> dict[int, int]:
    seats = {pid: len(pt.members) for pid, pt in state.parties.items()}
    return {pid: n for pid, n in seats.items() if n > 0}


def _join_price(state: GameState, partner_id: int, proposer_id: int) -> float | None:
    """What a partner extracts to join: platform distance the proposer must
    close toward them. Near partners come free; too far won't join at all."""
    a = state.parties[partner_id].platform
    b = state.parties[proposer_id].platform
    d = dist(a, b)
    if d >= p.COALITION_MAX_DIST:
        return None
    return p.CONCESSION_STEP * max(0.0, d - p.COALITION_FREE_DIST)


def _viable_offers(state: GameState, exclude_parties: set[int] | None = None) -> list[dict]:
    """Every proposer's buildable majority — nearest (cheapest) partners first.
    Each offer: proposer, coalition, bloc, price{partner: concession}."""
    seats = _seats(state)
    for pid in (exclude_parties or ()):
        seats.pop(pid, None)
    majority = _majority(state)
    offers = []
    for proposer in sorted(seats, key=seats.get, reverse=True):
        coalition, bloc, price = {proposer}, seats[proposer], {}
        for partner in sorted(seats, key=lambda pid: dist(state.parties[pid].platform,
                                                          state.parties[proposer].platform)):
            if bloc >= majority:
                break
            if partner == proposer:
                continue
            pr = _join_price(state, partner, proposer)
            if pr is not None:
                coalition.add(partner)
                bloc += seats[partner]
                price[partner] = pr
        if bloc >= majority:
            offers.append({"proposer": proposer, "coalition": coalition,
                           "bloc": bloc, "price": price})
    return offers


def _best_coalition(state: GameState, exclude_parties: set[int] | None = None
                    ) -> tuple[int, set[int], int] | None:
    offers = _viable_offers(state, exclude_parties)
    if not offers:
        return None
    o = offers[0]
    return o["proposer"], o["coalition"], o["bloc"]


def _player_party(state: GameState) -> int | None:
    mp = state.mps.get(state.player_id)
    return mp.party if mp is not None else None


def _form(state: GameState, offer: dict) -> None:
    """Seat the coalition and settle the bill: each priced partner drags the
    *agreement* — not the manifesto — toward its platform, and the proposer's
    members pay standing for the compromise. AI governments pay exactly what
    the player would."""
    proposer, coalition, bloc = offer["proposer"], offer["coalition"], offer["bloc"]
    pt = state.parties[proposer]
    agenda = np.mean([state.parties[i].platform for i in coalition], axis=0)
    for pid, pr in offer["price"].items():
        if pr <= 0:
            continue
        partner = state.parties[pid]
        d = max(dist(tuple(agenda), partner.platform), 1e-9)
        agenda = agenda + (pr / d) * (np.asarray(partner.platform) - agenda)
        for m in pt.members:
            if m in state.mps:
                mp = state.mps[m]
                mp.standing = float(np.clip(mp.standing - p.STANDING_CONCESSION * pr, -1, 1))
        state.emit("CoalitionDeal",
                   f"{partner.name} extracts {pr:.2f} of platform — the agreement "
                   f"tilts {describe_pos(partner.platform)}; {pt.name}'s members "
                   "pay for the compromise.", party=proposer, partner=pid, concession=pr)
    state.government.parties = coalition
    state.government.pm = pt.leader
    state.government.platform = tuple(np.clip(agenda, -1, 1))
    state.government.minority = False
    state.government.weeks_in_office = 0
    state.government.budget_stance = None  # the new cabinet writes its own budget
    state.government.amend_attempted = set()  # its own grievances with the book
    state.government.amend_move = None        # and owns its pending moves
    state.bench_shortlist = []               # and picks its own nominees
    names = [state.parties[i].name for i in coalition]
    state.emit("CoalitionFormed",
               render(state, "CoalitionFormed", names=" + ".join(names),
                      bloc=bloc),
               parties=sorted(coalition), seats=bloc)


def _minority(state: GameState, exclude_parties: set[int] | None = None) -> None:
    """Nobody built a majority — largest unblocked party tries minority rule."""
    seats = _seats(state)
    for pid in state.government.blocked | (exclude_parties or set()):
        seats.pop(pid, None)
    if not seats:
        return  # a parliament of independents: nobody to seat — caretaker void
    biggest = max(seats, key=seats.get)
    state.government.parties = {biggest}
    state.government.pm = state.parties[biggest].leader
    state.government.platform = state.parties[biggest].platform  # rules alone on its manifesto
    state.government.minority = True
    state.government.weeks_in_office = 0
    state.government.budget_stance = None
    state.government.amend_attempted = set()
    state.government.amend_move = None
    state.bench_shortlist = []
    state.emit("CoalitionFormed",
               render(state, "MinorityFormed", name=state.parties[biggest].name,
                      seats=seats[biggest]),
               parties=[biggest], seats=seats[biggest], minority=True)


def resolve_formation(state: GameState, actions: list) -> bool:
    """One formation week; True when a government now exists.
    When the player's party sits in a viable slate, the table pauses a week —
    OfferMade events enumerate the deals. The player picks one, declines all
    (their party sits out), or stays silent — which accepts the default."""
    gov = state.government
    if state.offers:
        offers, state.offers = state.offers, []
        decline = any(a.kind == "decline_offers" for a in actions)
        pick = next((a.offer for a in actions
                     if a.kind == "pick_offer" and a.offer is not None), None)
        if decline:
            state.emit("OfferDeclined", "You turn down every offer — "
                                        "your party sits this one out.")
            out = gov.blocked | {_player_party(state)}
            found = _viable_offers(state, out)
            _form(state, found[0]) if found else _minority(state, out)
        else:
            wanted = offers[pick] if pick is not None and 0 <= pick < len(offers) else offers[0]
            # a bargaining week moves the house — re-validate the slate
            fresh = _viable_offers(state, gov.blocked)
            o = next((f for f in fresh if f["proposer"] == wanted["proposer"]
                      and f["coalition"] == wanted["coalition"]), None)
            if o is None:
                state.emit("OfferLapsed", "The slate you backed no longer "
                                          "commands a majority — the table re-deals.")
                o = fresh[0] if fresh else None
            if o is None:
                _minority(state)
            else:
                if o["coalition"] != offers[0]["coalition"]:
                    state.emit("OfferTaken",
                               f"You back {state.parties[o['proposer']].name}'s slate "
                               f"({o['bloc']} seats).", parties=sorted(o["coalition"]))
                _form(state, o)
        gov.blocked = set()
        return True

    offers = _viable_offers(state, gov.blocked)
    pid = _player_party(state)
    if pid is not None and any(pid in o["coalition"] for o in offers):
        state.offers = offers          # a hung parliament pauses — one week to deal
        # (prices shown are indicative — the settled deal re-emits as CoalitionDeal)
        for i, o in enumerate(offers):
            con = "; ".join(f"{state.parties[p_].name} takes {pr:.2f}"
                            for p_, pr in o["price"].items() if pr > 0) or "clean hands"
            state.emit("OfferMade",
                       f"Offer {i+1}: {state.parties[o['proposer']].name} heads "
                       f"{' + '.join(sorted(state.parties[c].name for c in o['coalition']))} "
                       f"({o['bloc']} seats) — {con}.",
                       offer=i, proposer=o["proposer"], parties=sorted(o["coalition"]),
                       bloc=o["bloc"], price={k: v for k, v in o["price"].items() if v > 0})
        return False
    _form(state, offers[0]) if offers else _minority(state)
    gov.blocked = set()
    return True


def call_election(state: GameState, snap: bool, reason: str,
                  party: int | None = None) -> None:
    """Dissolve to campaign — scheduled or snap. Entrants declare at the call."""
    if party is None and state.government.pm in state.mps:
        party = state.mps[state.government.pm].party
    state.emit("ElectionCalled", _ELECTION_TEXT[reason],
               snap=snap, reason=reason, party=party)
    state.current_bill = None   # the pending division dies with the parliament
    state.offers = []           # dead slates die with it too
    state.deals = []            # and promises made to a dissolved house lapse
    state.government.budget_stance = None  # a caretaker's signals lapse too
    state.government.amend_move = None       # and its pending amendment
    state.bench_shortlist = []               # no caretaker appointments
    state.phase = "campaign"
    state.weeks_to_election = p.CAMPAIGN_WEEKS
    niche_entry(state)


def strategic_call(state: GameState) -> None:
    """A riding-high PM gambles on an early election — scheduling power."""
    gov = state.government
    if not gov.parties or not (p.SNAP_WINDOW[0] <= gov.weeks_in_office <= p.SNAP_WINDOW[1]):
        return
    # early calls convert a *published* poll surplus into seats — the number
    # the country read, sponsor's bias and all; a flattered government can
    # ride its own friendly press into a doomed snap. No fresh poll, no gamble.
    lp = state.last_poll
    if lp is None or state.week - lp["week"] > p.SNAP_POLL_STALE:
        return
    seat_share = sum(len(state.parties[i].members) for i in gov.parties) / max(len(state.mps), 1)
    poll_share = sum(lp["shares"].get(pid, 0.0) for pid in gov.parties)
    if poll_share < seat_share + p.SNAP_POLL_EDGE:
        return
    if state.rng.random() < p.SNAP_CALL_P:
        call_election(state, snap=True, reason="strategic")


def coalition_exits(state: GameState) -> None:
    """A strained, bleeding junior partner walks out — weekly, in office.
    Grand coalitions are a phase, not an ending: the check fires only when
    the agenda sits far from the platform AND the polls show staying costs
    votes, so it can't dissolve a healthy coalition on a whim."""
    gov = state.government
    lp = state.last_poll
    if (gov.platform is None or lp is None
            or gov.weeks_in_office < p.COAL_EXIT_GRACE):
        return
    pm_pid = state.mps[gov.pm].party if gov.pm in state.mps else None
    n = max(len(state.mps), 1)
    for pid in sorted(gov.parties):
        if pid == pm_pid or pid not in state.parties:
            continue
        pt = state.parties[pid]
        strain = dist(pt.platform, gov.platform)
        bleed = lp["shares"].get(pid, 0.0) < len(pt.members) / n
        if strain <= p.COAL_EXIT_DIST or not bleed:
            continue
        gov.parties.discard(pid)
        for mid in pt.members:
            if mid in state.mps:
                state.mps[mid].portfolio = None  # the spoils die with the tie
        state.emit("CoalitionExit",
                   f"{pt.name} walks out of the government — the agenda sits "
                   f"{strain:.2f} from their platform and the polls have them "
                   f"bleeding.", party=pid, strain=strain)
        bloc = sum(len(state.parties[q].members) for q in gov.parties
                   if q in state.parties)
        if bloc * 2 < n:
            collapse(state, "walkout")
        else:
            state.emit("GovernmentContinues",
                       f"The rump government governs on — {bloc} of {n} seats.",
                       parties=sorted(gov.parties))
        return  # one walk-out per week


def collapse(state: GameState, cause: str = "confidence") -> None:
    """The government falls — the house replaces it in place if a different
    majority exists, else it dissolves. cause: 'confidence' | 'supply'."""
    pm_party = state.mps[state.government.pm].party \
        if state.government.pm in state.mps else None
    fallen_largest = max(sorted(state.government.parties),
                         key=lambda pid: len(state.parties[pid].members), default=None)
    alt = _best_coalition(state, exclude_parties={fallen_largest})
    if state.constructive_confidence and cause == "confidence" \
            and alt is None \
            and state.government.collapses + 1 < p.SNAP_COLLAPSE_MAX:
        # constructive no-confidence: a lost division falls the government
        # only when a successor slate exists — no slate, no dissolution; the
        # wounded PM limps on, brand bleeding, pending business dead
        state.government.collapses += 1
        for pid in state.government.parties:
            if pid in state.parties:
                state.parties[pid].brand -= p.CONFIDENCE_WOUND_BRAND
        state.current_bill = None
        state.deals = []
        state.emit("ConfidenceHeld",
                   "The government loses the division — but no successor "
                   "slate exists, so it limps on wounded.",
                   parties=sorted(state.government.parties))
        return
    text = {"supply": "Government loses supply — the budget is dead.",
            "defection": "The Prime Minister's defection brings the government down.",
            "walkout": "The coalition's collapse brings the government down.",
            }.get(cause, "Government loses confidence of the house.")
    state.emit("ConfidenceLost", text,
               party=pm_party, parties=sorted(state.government.parties))
    state.government.collapses += 1
    state.government.parties = set()
    state.government.pm = None
    state.government.platform = None   # the agreement dies with the government
    state.current_bill = None          # and its pending business dies too
    state.deals = []                   # promises made on that business lapse
    state.government.budget_stance = None  # a fallen PM's signals lapse
    state.government.amend_move = None       # and their queued amendment
    state.bench_shortlist = []               # and a fallen PM's nominees lapse
    if state.government.collapses >= p.SNAP_COLLAPSE_MAX:
        call_election(state, snap=True, reason="deadlock", party=pm_party)
    elif alt is None:
        call_election(state, snap=True, reason="confidence", party=pm_party)
    else:
        if fallen_largest is not None:
            state.government.blocked = {fallen_largest}
        state.phase = "formation"   # a different majority exists — it forms in place


def confidence_vote(state: GameState) -> bool:
    """A forced confidence motion — resolves immediately; crises can't wait.
    On failure the house replaces the government if it can — else it dissolves."""
    if not state.government.parties:
        return True  # a caretaker void can't lose a vote it never holds
    res = resolve_vote(state, Bill(pos=gov_platform(state), beneficiary_axis=0,
                                   confidence=True))
    survived = res is not False   # a stalled division isn't a lost one
    if not survived:
        collapse(state)
    return survived
