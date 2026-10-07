"""Spectator policy — a rule pipeline that plays the player.

`auto_actions` returns the week's picks an engaged politician would
make: survive the threats, answer the house's business, push the
declared ambition, and spend what's left on the career. The bot
declares an ambition like a player (`bot_pick_ambition`) and works the
full action menu — each rule gated by the same numbers `explain_action`
surfaces, so a spectated run exercises the game a player actually
faces. Risk rides a dossier-heat budget: dirty ops pause while your
own file is hot, unless the odds are exceptional. Draws ride
`state.rng` — the bot IS a player, its choices belong in the
deterministic stream, never on `prose_rng`.
No mutation: the rules read state and emit Actions.
"""
from __future__ import annotations

import numpy as np

from . import params as p
from .actions import Action, available_actions
from .conditions import mood
from .parliament import whip_direction
from .parties import _stay_utility
from .state import GameState, dist


def bot_pick_ambition(state: GameState) -> str:
    """Declare a career arc — weighted by feasibility, drawn on state.rng."""
    player = state.mps.get(state.player_id)
    w = {"pm": 1.0, "majority": 0.5, "founder": 0.4,
         "survivor": 0.8, "reformer": 1.0}
    if player is not None and player.party is not None:
        pt = state.parties[player.party]
        if _stay_utility(state, player) < p.BOT_STAY_UTILITY:
            w["founder"] = 2.5                      # a bad home breeds founders
        if pt.leader == player.id or len(pt.members) * 2 > len(state.mps):
            w["majority"] = 2.0                     # the chair or the size to dream
        if player.seat_safety <= p.BOT_MARGINAL_SAFETY:
            w["survivor"], w["pm"] = 2.5, 0.3       # a marginal seat narrows dreams
        else:
            w["pm"] = 2.0
    elif player is not None:
        # no party: the vehicle is yours to build
        w.update({"pm": 0.4, "majority": 0.1, "founder": 1.5,
                  "survivor": 1.5, "reformer": 0.6})
    return state.rng.choices(list(w), weights=list(w.values()))[0]


class _Ctx:
    """Shared plumbing for the rules — the menu, the spend, the trace."""

    def __init__(self, state: GameState, trace: list | None):
        self.state = state
        self.player = state.mps[state.player_id]
        self.menu = available_actions(state)
        self.picks: list[Action] = []
        self.spent = 0
        self.trace = trace
        self.rule = ""

    def take(self, kind: str, gate: str = "", **kw) -> None:
        cost = p.ACTION_COST.get(kind, 1)
        if kind in self.menu and self.spent + cost <= p.ACTION_POINTS:
            self.picks.append(Action(kind, **kw))
            self.spent += cost
            if self.trace is not None:
                self.trace.append({"week": self.state.week, "rule": self.rule,
                                   "kind": kind, "gate": gate})


def _hot(c: _Ctx) -> bool:
    """Dossier heat — your own file is thick enough that more dirt is a gamble."""
    pl = c.player
    return pl.dossier >= p.BOT_DIRTY_CEILING or pl.scandal_weeks > 0


def _blocking_clause(state: GameState, plat) -> int | None:
    """A positional clause fencing the party's own pole — the repeal target."""
    for a in state.constitution:
        if a.kind != "pos" or a.id in state.government.amend_attempted:
            continue
        if abs(plat[a.axis]) > a.limit * 0.7 \
                and np.sign(plat[a.axis]) == a.pole:
            return a.id
    return None


# --- rules: each fires at most one action, in priority order ---

def _r_seat_defense(c: _Ctx) -> None:
    """A marginal seat gets casework before ambition — campaign weeks
    get worked regardless; you don't sleepwalk into a loss."""
    if c.player.seat_safety < p.BOT_MARGINAL_SAFETY or c.state.phase == "campaign":
        c.take("campaign" if c.state.phase == "campaign" else "constituency",
               gate=f"safety {c.player.seat_safety:.2f}")


def _r_offers(c: _Ctx) -> None:
    """A hung parliament waits on your answer: take the slate that
    seats you; else back the nearest ground, decline if all are far."""
    s, pl = c.state, c.player
    if not s.offers:
        return
    seated = [i for i, o in enumerate(s.offers) if pl.party in o["coalition"]]
    if seated:
        c.take("pick_offer",
               offer=max(seated, key=lambda i: len(s.offers[i]["coalition"])),
               gate="seated")
        return

    def offer_dist(i: int) -> float:
        plats = [s.parties[pid].platform for pid in s.offers[i]["coalition"]
                 if pid in s.parties]
        return float(np.mean([dist(q, pl.pos) for q in plats])) if plats else 9.0

    best = min(range(len(s.offers)), key=offer_dist)
    if offer_dist(best) <= p.BOT_OFFER_MAX_DIST:
        c.take("pick_offer", offer=best, gate=f"kingmaker {offer_dist(best):.2f}")
    else:
        c.take("decline_offers", gate=f"nearest {offer_dist(best):.2f}")


def _r_division(c: _Ctx) -> None:
    """A pending division: vote the whip; on a free vote, vote proximity."""
    s, pl = c.state, c.player
    bill = s.current_bill
    if "vote" not in c.menu or bill is None:
        return
    whip = whip_direction(s, pl.party, bill) if pl.party is not None else 0
    c.take("vote",
           vote=whip if whip else
           (1 if dist(pl.pos, bill.pos) < p.BOT_FREE_VOTE_DIST else -1),
           gate="whip" if whip else "free")


def _r_pm_desk(c: _Ctx) -> None:
    """The PM's desk: fill the bench, set the budget, move the constitution."""
    s, pl = c.state, c.player
    if s.government.pm != pl.id:
        return
    if "appoint" in c.menu and s.bench_shortlist:
        c.take("appoint", judge=min(
            range(len(s.bench_shortlist)),
            key=lambda i: dist(s.bench_shortlist[i].pos, pl.pos)),
            gate="nearest justice")
    if "budget" in c.menu:
        stance = 0 if s.treasury.debt > p.BOT_AUSTERITY_FLOOR else (
            2 if mood(s.conditions) < p.BOT_STIMULUS_MOOD else 1)
        c.take("budget", axis=stance, gate=f"debt {s.treasury.debt:.2f}")
    if "amendment" in c.menu and s.government.amend_move is None \
            and pl.party is not None:
        art = _blocking_clause(s, s.parties[pl.party].platform)
        if art is not None:
            c.take("amendment", article=art, gate=f"clause {art}")


def _r_ambition(c: _Ctx) -> None:
    """The declared arc's signature move — a reformer writes bills, a
    climber works the room, a survivor doubles down on the district."""
    s = c.state
    kind = s.ambition.kind if s.ambition is not None else None
    if kind == "reformer" and s.legacy_bills < p.AMBITION_REFORMER_LAWS:
        c.take("table", axis=int(np.argmax(np.abs(c.player.pos))),
               gate="reformer")
    elif kind in ("pm", "majority", "founder") and not _hot(c):
        c.take("scheme", gate="climb")
    elif kind == "survivor":
        c.take("constituency", gate="survivor")


def _r_division_ops(c: _Ctx) -> None:
    """A live bill far from your ground gets dragged; a colleague gets
    your word."""
    s, pl = c.state, c.player
    bill = s.current_bill
    if bill is None:
        return
    if "amend" in c.menu and not bill.amended \
            and dist(bill.pos, pl.pos) > p.BOT_AMEND_DIST:
        c.take("amend", gate=f"dist {dist(bill.pos, pl.pos):.2f}")
        return
    if "deal" in c.menu:
        cold = min((m for m in s.mps.values()
                    if m.id != pl.id and m.party is not None),
                   key=lambda m: m.relationships.get(pl.id, 0.0),
                   default=None)
        if cold is not None:
            whip = whip_direction(s, pl.party, bill) \
                if pl.party is not None else 0
            c.take("deal", target=cold.id,
                   vote=whip if whip else
                   (1 if dist(pl.pos, bill.pos) < p.BOT_FREE_VOTE_DIST else -1),
                   gate=f"warms {cold.relationships.get(pl.id, 0.0):.2f}")


def _r_relations(c: _Ctx) -> None:
    """Build the career: lobby the leader while unpromoted, court the
    hostile desk."""
    s, pl = c.state, c.player
    if pl.party is not None and pl.portfolio is None:
        pt = s.parties.get(pl.party)
        if pt is not None and pt.leader is not None and pt.leader != pl.id:
            c.take("lobby", target=pt.leader, gate="unpromoted")
    if "court" in c.menu and pl.party is not None and s.outlets:
        hostile = min(s.outlets,
                      key=lambda o: o.warmth.get(pl.party, 0.0))
        warm = hostile.warmth.get(pl.party, 0.0)
        if warm < p.BOT_COURT_WARMTH:
            c.take("court", target=hostile.id, gate=f"warmth {warm:.2f}")


_RULES = (_r_seat_defense, _r_offers, _r_division, _r_pm_desk,
          _r_ambition, _r_division_ops, _r_relations)


def auto_actions(state: GameState, trace: list | None = None) -> list[Action]:
    """Walk the pipeline until the week's points are spent."""
    if state.mps.get(state.player_id) is None:
        return []
    c = _Ctx(state, trace)
    for rule in _RULES:
        c.rule = rule.__name__
        rule(c)
    c.rule = "filler"
    while c.spent < p.ACTION_POINTS:
        n = len(c.picks)
        for kind in (("campaign",) if state.phase == "campaign" else ()) \
                + ("speech", "constituency"):
            c.take(kind)
        if len(c.picks) == n:
            break                       # nothing affordable fits the remainder
    return c.picks
