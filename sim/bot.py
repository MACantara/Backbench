"""Spectator policy — a legible rule list that plays the player.

`auto_actions` returns the two weekly picks an engaged backbencher would
make: answer the coalition question, vote the whip line, defend a
marginal seat, build the relationships a career is made of, and run the
PM's desk when the office is yours. The rules are draw-free today; if a
draw ever joins, it rides `state.rng` — the bot IS a player, its choices
belong in the deterministic stream, never on `prose_rng`.
No mutation: the rules read state and emit Actions.
"""
from __future__ import annotations

import numpy as np

from . import params as p
from .actions import Action, available_actions
from .conditions import mood
from .parliament import whip_direction
from .state import GameState, dist


def _blocking_clause(state: GameState, plat) -> int | None:
    """A positional clause fencing the party's own pole — the repeal target."""
    for a in state.constitution:
        if a.kind != "pos" or a.id in state.government.amend_attempted:
            continue
        if abs(plat[a.axis]) > a.limit * 0.7 \
                and np.sign(plat[a.axis]) == a.pole:
            return a.id
    return None


def auto_actions(state: GameState) -> list[Action]:
    menu = available_actions(state)
    player = state.mps.get(state.player_id)
    picks: list[Action] = []
    spent = 0

    def take(kind: str, **kw) -> None:
        nonlocal spent
        cost = p.ACTION_COST.get(kind, 1)
        if kind in menu and spent + cost <= p.ACTION_POINTS:
            picks.append(Action(kind, **kw))
            spent += cost

    if player is None:
        return picks

    # formation: a hung parliament waits on your answer — take the slate
    # that seats you, else the biggest table
    if "pick_offer" in menu and state.offers:
        best = max(range(len(state.offers)),
                   key=lambda i: (player.party in state.offers[i]["coalition"],
                                  len(state.offers[i]["coalition"])))
        take("pick_offer", offer=best)

    # pending division: vote the whip; on a free vote, vote proximity
    bill = state.current_bill
    if "vote" in menu and bill is not None:
        whip = whip_direction(state, player.party, bill) if player.party is not None else 0
        v = whip if whip else (1 if dist(player.pos, bill.pos) < p.BOT_FREE_VOTE_DIST else -1)
        take("vote", vote=v)

    # the PM's desk: fill the bench, set the budget, move the constitution
    if state.government.pm == player.id:
        if "appoint" in menu and state.bench_shortlist:
            take("appoint", judge=min(
                range(len(state.bench_shortlist)),
                key=lambda i: dist(state.bench_shortlist[i].pos, player.pos)))
        if "budget" in menu:
            stance = 0 if state.treasury.debt > p.BOT_AUSTERITY_FLOOR else (
                2 if mood(state.conditions) < p.BOT_STIMULUS_MOOD else 1)
            take("budget", axis=stance)
        if "amendment" in menu and state.government.amend_move is None \
                and player.party is not None:
            art = _blocking_clause(state, state.parties[player.party].platform)
            if art is not None:
                take("amendment", article=art)

    # a marginal seat gets casework before ambition — and every campaign
    # week gets worked regardless; you don't sleepwalk into a loss
    if player.seat_safety < p.BOT_MARGINAL_SAFETY or state.phase == "campaign":
        take("campaign" if state.phase == "campaign" else "constituency")

    # a live bill far from your ground gets dragged; a colleague gets your word
    if bill is not None:
        if "amend" in menu and not bill.amended \
                and dist(bill.pos, player.pos) > p.BOT_AMEND_DIST:
            take("amend")
        elif "deal" in menu:
            cold = min((m for m in state.mps.values()
                        if m.id != player.id and m.party is not None),
                       key=lambda m: m.relationships.get(player.id, 0.0),
                       default=None)
            if cold is not None:
                whip = whip_direction(state, player.party, bill) \
                    if player.party is not None else 0
                take("deal", target=cold.id,
                     vote=whip if whip else
                     (1 if dist(player.pos, bill.pos) < p.BOT_FREE_VOTE_DIST else -1))

    # build the career: lobby the leader while unpromoted, court the
    # hostile desk, work the room — filler keeps the week honest
    if player.party is not None and player.portfolio is None:
        pt = state.parties.get(player.party)
        if pt is not None and pt.leader is not None and pt.leader != player.id:
            take("lobby", target=pt.leader)
    if "court" in menu and player.party is not None and state.outlets:
        hostile = min(state.outlets,
                      key=lambda o: o.warmth.get(player.party, 0.0))
        if hostile.warmth.get(player.party, 0.0) < p.BOT_COURT_WARMTH:
            take("court", target=hostile.id)
    # filler stays clean: scheme and media grow the dossier that kills
    # careers — a surviving bot spends quiet weeks on voters, not dirt
    while spent < p.ACTION_POINTS:
        n = len(picks)
        for kind in ("speech", "constituency"):
            take(kind)
        if len(picks) == n:
            break                       # nothing affordable fits the remainder
    return picks
