"""Check: the law lifecycle — authorship, repeal, sunset, retable."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from sim import params as p
from sim.conditions import conditions_lifecycle
from sim.state import Law, gov_platform
from sim.tick import tick
from sim.worldgen import new_game


def _governing(seed: int):
    """A fresh state with a seated government."""
    s = new_game(seed)
    for _ in range(60):
        tick(s)
        if s.phase == "governing":
            return s
    raise AssertionError(f"seed {seed} never reached governing")


def _law(s, name, week=None, pos=(0.5, 0.0)) -> Law:
    """A fixture statute already on the books."""
    return Law(name=name, pos=pos, beneficiary_axis=0, cost=0.01,
               passed_week=s.week if week is None else week, margin=0.6,
               effect={}, enacted_by=set(s.government.parties),
               author=s.government.pm)


def main() -> None:
    # authorship: an enacted law names the PM and the coalition that passed it
    s = _governing(2)
    for _ in range(200):
        tick(s)
        if s.laws:
            break
    assert s.laws, "no law enacted in 200 governing weeks"
    law = s.laws[0]
    assert law.author is not None, "enacted law has no author"
    assert law.enacted_by, "enacted law has no authoring parties"

    # repeal: an inherited law is a target; a same-term law is not.
    # And the flagship path — the law being struck is the player's own.
    s = _governing(3)
    foreign = _law(s, "Ancient Act", week=0)   # long before this term started
    foreign.author = s.player_id             # the milestone's done-when
    own = _law(s, "Fresh Act")               # passed this week — same term
    s.laws += [foreign, own]
    saved = p.REPEAL_P
    p.REPEAL_P = 1.0                         # fixture: every agenda slot is a repeal
    try:
        for _ in range(150):
            if s.current_bill is not None and s.current_bill.repeals is not None:
                # term-relative: a formation resets the clock mid-loop
                term_start = s.week - s.government.weeks_in_office
                if own.passed_week >= term_start:
                    assert s.current_bill.repeals is not own, \
                        "government tries to repeal its own term's law"
            tick(s)
            if any(e.type == "LawRepealed" for e in s.log):
                break
    finally:
        p.REPEAL_P = saved
    rep = next((e for e in s.log if e.type == "LawRepealed"), None)
    assert rep is not None, "no repeal landed in 150 weeks"
    assert rep.data.get("law") == foreign.name, \
        "repeal struck a same-term law instead of the inherited one"
    assert rep.data.get("player"), "the player's flagship repeal isn't flagged"
    assert "flagship" in rep.text, "flagship repeal text doesn't name the stakes"
    assert foreign not in s.laws, "repealed law still in force"

    # sunset: an ancient statute lapses
    s = _governing(3)
    old = _law(s, "Aged Act", week=-10**6)
    s.laws.append(old)
    saved = p.SUNSET_P
    p.SUNSET_P = 1.0                      # fixture: aged statutes always lapse
    try:
        conditions_lifecycle(s)
    finally:
        p.SUNSET_P = saved
    assert old not in s.laws, "aged statute survived a certain lapse roll"
    assert any(e.type == "LawLapsed" for e in s.log), "no LawLapsed event"

    # retable: a cooled-off failure returns on the agenda's own motion
    s = _governing(8)
    s.failed.append({"pos": tuple(gov_platform(s)), "name": "Dead Bill",
                     "week": s.week - p.RETABLE_CD - 1, "axis": 0, "cost": 0.01})
    saved = p.RETABLE_P
    p.RETABLE_P = 1.0
    try:
        for _ in range(30):
            tick(s)
            if any("Revisited" in e.text for e in s.log):
                break
    finally:
        p.RETABLE_P = saved
    assert any("Revisited" in e.text for e in s.log), "failed bill never retabled"
    assert not any(f["name"] == "Dead Bill" for f in s.failed), \
        "retabled bill still sits in the failed registry"

    # budget supply: a passed budget sets the standing posture; a lost one
    # falls the government and the event names supply
    s = _governing(11)
    bb = None
    for _ in range(60):
        if s.current_bill is not None and s.current_bill.budget:
            bb = s.current_bill
            break
        tick(s)
    assert bb is not None, "no budget tabled in 60 weeks"
    for m in s.mps.values():            # the whole house sits on the bill
        m.pos = tuple(bb.pos)
    tick(s)                             # division week — the budget passes
    assert s.treasury.posture == (bb.tax, bb.spend), \
        "passed budget didn't set the standing posture"
    assert any(e.type == "BudgetSet" for e in s.log), "no BudgetSet event"

    bb = None
    for _ in range(150):
        if s.phase == "governing" and s.current_bill is not None \
                and s.current_bill.budget:
            bb = s.current_bill
            break
        tick(s)
    assert bb is not None, "no second budget tabled in 150 weeks"
    bb.pos = (1.0, 1.0)                 # a corner-case budget; the house sits
    for m in s.mps.values():            # at the opposite corner — even the
        m.pos = (-1.0, -1.0)            # whip can't reach across the map
    gov0 = set(s.government.parties)
    tick(s)
    assert s.government.parties != gov0 or s.phase != "governing", \
        "lost supply left the same government standing"
    assert any("supply" in e.text for e in s.log), "supply loss not named"

    print("legacy ok: authorship, repeal gate, sunset, retable, supply")


if __name__ == "__main__":
    main()
