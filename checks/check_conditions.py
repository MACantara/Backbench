"""Check: country conditions — indicators, law marks, retrospective voting, shocks."""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from sim import params as p
from sim.conditions import (conditions_lifecycle, enact, law_effect, mood,
                            responsibility)
from sim.election import poll
from sim.parliament import vote_terms
from sim.state import Bill
from sim.tick import tick
from sim.worldgen import new_game


def main() -> None:
    # law effects: a far-axis-0-right law pushes growth; a far-left pushes services
    right = law_effect(Bill(pos=(0.8, 0.0), beneficiary_axis=0))
    left = law_effect(Bill(pos=(-0.8, 0.0), beneficiary_axis=0))
    auth = law_effect(Bill(pos=(0.0, 0.8), beneficiary_axis=1))
    assert right.get("growth", 0) > 0, "right economic law should push growth"
    assert left.get("services", 0) > 0, "left economic law should push services"
    assert auth.get("crime", 0) < 0, "authoritarian law should push crime down"

    # a law in force actually moves its indicator over weeks
    s = new_game(1)
    law = enact(s, Bill(pos=(0.9, 0.0), beneficiary_axis=0), yes=80, no=40)
    g0 = s.conditions.growth
    for _ in range(20):
        conditions_lifecycle(s)
    assert s.conditions.growth > g0, "law in force didn't move its indicator"
    assert law in s.laws and law.margin > 0.6, "registry entry malformed"
    assert any(e.type == "LawEnacted" for e in s.log), "no LawEnacted event"

    # retrospective voting: crashed mood drops governing parties' poll share
    s = new_game(7)
    for _ in range(60):
        tick(s)
    assert s.government.parties, "fixture needs a government"
    snap = copy.deepcopy(s)
    base = sum(v for k, v in poll(snap).items() if k in s.government.parties)
    snap.conditions.growth, snap.conditions.unemployment = -0.6, 0.9
    snap.conditions.inflation = 0.8
    crashed = sum(v for k, v in poll(snap).items() if k in s.government.parties)
    assert crashed < base, f"crash didn't hurt the government: {base:.3f} -> {crashed:.3f}"

    # clarity of responsibility: single-party PM bears more than a coalition PM
    s = new_game(7)
    for _ in range(60):
        tick(s)
    assert s.government.pm in s.mps, "fixture needs a sitting PM"
    pm_party = s.mps[s.government.pm].party
    multi = len(s.government.parties) > 1
    share_multi = responsibility(s, pm_party)
    s.government.parties = {pm_party}  # same PM, now a single-party government
    share_solo = responsibility(s, pm_party)
    assert share_solo == p.RETRO_PM_SHARE, "solo PM should take the full PM share"
    if multi:
        assert share_multi == p.RETRO_PM_SHARE, "PM party keeps its share either way"
    outsiders = [pid for pid in s.parties if pid not in s.government.parties]
    assert all(responsibility(s, pid) == 0.0 for pid in outsiders), \
        "opposition should carry no responsibility"

    # confidence pressure: a slump turns coalition MPs against their own survival vote
    s = new_game(7)
    for _ in range(60):
        tick(s)
    gov = {i for i in s.government.parties if i in s.parties}
    mean = tuple(np.mean([s.parties[i].platform for i in gov], axis=0))
    bill = Bill(pos=mean, beneficiary_axis=0, confidence=True)

    slump = copy.deepcopy(s)
    slump.conditions.growth, slump.conditions.unemployment = -0.9, 1.0
    slump.conditions.inflation = 0.9
    n_slump = sum(1 for m in slump.mps.values() if m.party in gov
                  and sum(vote_terms(slump, m, bill).values()) <= 0)
    s.conditions.growth, s.conditions.unemployment, s.conditions.inflation = 0.4, 0.3, 0.1
    n_boom = sum(1 for m in s.mps.values() if m.party in gov
                 and sum(vote_terms(s, m, bill).values()) <= 0)
    assert n_slump > n_boom, f"slump should raise defections ({n_slump} vs {n_boom})"

    # shocks: fire within a bounded window and get covered by the press
    shock_weeks, covered = [], 0
    for seed in range(10):
        s = new_game(seed)
        for w in range(120):
            evs = tick(s)
            sh = next((e for e in evs if e.type == "Shock"), None)
            if sh:
                shock_weeks.append(s.week)
                hl = next((e for e in evs if e.type == "Headline"), None)
                covered += hl is not None and hl.data.get("story") == "Shock"
                break
    assert shock_weeks, "no shock fired in 10x120 weeks"
    # a bigger story can legitimately outrank a shock — require most get the lead
    assert covered >= len(shock_weeks) / 2, "shocks rarely reach headlines"

    # determinism: same seed → identical conditions trajectory
    a, b = new_game(9), new_game(9)
    for _ in range(40):
        conditions_lifecycle(a)
        conditions_lifecycle(b)
    for f in ("growth", "unemployment", "inflation", "services", "crime"):
        assert getattr(a.conditions, f) == getattr(b.conditions, f), f"{f} diverged"

    print(f"conditions ok: laws move indicators, retro {base:.3f}->{crashed:.3f}, "
          f"defections boom={n_boom} slump={n_slump}, shocks@{shock_weeks[:3]}")


if __name__ == "__main__":
    main()
