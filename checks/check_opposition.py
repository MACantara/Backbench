"""Check: the opposition toolkit — attack, amend, private bills, selfpres."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from sim import params as p
from sim.actions import Action, apply_action
from sim.parliament import vote_terms, whip_direction
from sim.state import gov_platform
from sim.tick import tick
from sim.worldgen import new_game


def _governing(seed: int):
    s = new_game(seed)
    for _ in range(60):
        tick(s)
        if s.phase == "governing":
            return s
    raise AssertionError(f"seed {seed} never reached governing")


def _set_mood(s, strong: bool) -> None:
    c = s.conditions
    c.growth, c.services = (1.0, 1.0) if strong else (-1.0, 0.0)
    c.unemployment, c.inflation, c.crime = (0.0, 0.0, 0.0) if strong else (1.0, 1.0, 1.0)
    for m in s.mps.values():
        if m.portfolio is not None:
            m.perf = 1.0 if strong else -1.0


def _to_opposition(s) -> None:
    me = s.mps[s.player_id]
    if me.party in s.parties:
        s.parties[me.party].members.discard(me.id)
    me.party, me.faction = None, None


def main() -> None:
    # attack lands on a weak government and whiffs on a strong one
    lands_weak = lands_strong = 0
    for seed, strong in ((7, False), (2, True)):
        s = _governing(seed)
        _to_opposition(s)
        _set_mood(s, strong)
        for _ in range(30):
            n = len(s.log)
            apply_action(s, Action("attack"))
            if any(e.type == "AttackLands" for e in s.log[n:]):
                lands_weak += not strong
                lands_strong += strong
    assert lands_weak >= 20, f"attack didn't land on a weak gov ({lands_weak}/30)"
    assert lands_strong <= 8, f"attack landed too often on a strong gov ({lands_strong}/30)"

    # amend: drags the pending bill toward the mover — once only
    s = _governing(3)
    for _ in range(40):
        if s.current_bill is not None:
            break
        tick(s)
    assert s.current_bill is not None, "no bill tabled in 40 weeks"
    me = s.mps[s.player_id]
    me.pos = (-0.8, 0.8)
    bill = s.current_bill
    d0 = np.linalg.norm(np.asarray(bill.pos) - np.asarray(me.pos))
    apply_action(s, Action("amend"))
    d1 = np.linalg.norm(np.asarray(bill.pos) - np.asarray(me.pos))
    assert d1 < d0, "amendment didn't drag the bill toward the mover"
    pos_after = bill.pos
    apply_action(s, Action("amend"))
    assert bill.pos == pos_after, "a second amendment moved the bill"

    # private member's bill: positioned on the government's ground it can pass,
    # and the sponsor — not the PM — gets the authorship
    s = _governing(12)   # this house passes an agenda-aligned private bill
    _to_opposition(s)
    me = s.mps[s.player_id]
    me.pos = tuple(gov_platform(s))
    n = len(s.log)
    apply_action(s, Action("table", axis=0))
    vr = next(e for e in s.log[n:] if e.type == "VoteResult")
    assert vr.data["passed"], "a private bill on the government's ground failed"
    mine = [l for l in s.laws if l.author == s.player_id]
    assert mine, "passed private bill didn't credit its sponsor"
    assert s.legacy_bills >= 1

    # selfpres: a burning whipped MP's terms pull against the line
    s = _governing(9)
    for _ in range(40):
        if s.current_bill is not None:
            break
        tick(s)
    assert s.current_bill is not None, "no bill tabled in 40 weeks"
    bill = s.current_bill
    whipped = next((m for m in s.mps.values()
                    if m.party is not None and whip_direction(s, m.party, bill)),
                   None)
    assert whipped is not None, "no whipped MP found"
    whipped.faction = None      # party line owns this member for the check
    whipped.scandal_weeks = 3
    terms = vote_terms(s, whipped, bill)
    line = whip_direction(s, whipped.party, bill)
    assert "selfpres" in terms and np.sign(terms["selfpres"]) == -line, \
        "burning MP shows no self-preservation pull"

    print("opposition ok: attack whiffs/lands, amend once, PMB authorship, selfpres")


if __name__ == "__main__":
    main()
