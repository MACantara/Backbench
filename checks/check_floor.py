"""Check: crossing the floor — defect, found, leak."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from sim import params as p
from sim.actions import Action, apply_action
from sim.tick import tick
from sim.worldgen import new_game


def _governing(seed: int):
    s = new_game(seed)
    for _ in range(60):
        tick(s)
        if s.phase == "governing":
            return s
    raise AssertionError(f"seed {seed} never reached governing")


def main() -> None:
    # defect to independent: betrayal, bridge-burn, standing reset, posts gone
    s = _governing(1)
    me = s.mps[s.player_id]
    old_pid = me.party
    me.portfolio, me.standing = "Finance", 0.6
    bet0 = s.voters.betrayal[s.voters.district == me.district].mean()
    apply_action(s, Action("defect"))
    assert me.party is None, "defect didn't seat the player independent"
    assert me.portfolio is None and me.standing == 0.0
    assert me.id not in s.parties[old_pid].members
    assert s.voters.betrayal[s.voters.district == me.district].mean() > bet0
    assert any(e.type == "Defection" for e in s.log)

    # defect to a party: membership moves
    s = _governing(2)
    me = s.mps[s.player_id]
    dest = next(i for i in s.parties if i != me.party)
    apply_action(s, Action("defect", target=dest))
    assert me.party == dest and me.id in s.parties[dest].members

    # a defecting PM forfeits the office — succession or collapse
    s = _governing(3)
    me = s.mps[s.player_id]
    s.parties[me.party].leader = me.id
    s.government.pm = me.id
    if me.party not in s.government.parties:
        s.government.parties.add(me.party)
    apply_action(s, Action("defect"))
    assert s.government.pm != me.id, "defecting PM kept the office"

    # found: only real loyalty walks out
    s = _governing(4)
    me = s.mps[s.player_id]
    loyal = next(m for m in s.mps.values()
                 if m.party == me.party and m.id != me.id
                 and m.id != s.government.pm)
    loyal.relationships[me.id] = p.FOUND_REL_MIN + 0.1
    # and miserable — loyalty alone doesn't walk a happy member
    loyal.pos = tuple(-1.0 * np.asarray(s.parties[me.party].platform))
    cold = next(m for m in s.mps.values()
                if m.party == me.party and m.id not in (me.id, loyal.id)
                and m.id != s.government.pm)
    cold.relationships[me.id] = 0.0
    apply_action(s, Action("found"))
    new_pid = me.party
    assert new_pid is not None and new_pid in s.parties, "founding created no party"
    assert s.parties[new_pid].leader == me.id
    assert loyal.id in s.parties[new_pid].members, "loyal follower didn't walk"
    assert cold.id not in s.parties[new_pid].members, "cold colleague followed anyway"

    # found from no party — an independent launches a vehicle alone
    s = _governing(10)
    me = s.mps[s.player_id]
    apply_action(s, Action("defect"))          # sit independent first
    apply_action(s, Action("found"))
    assert me.party is not None and s.parties[me.party].members == {me.id}, \
        "independent founder didn't get a solo vehicle"

    # leak: a dirty dossier detonates on schedule; a clean one whiffs; no self-leak
    s = _governing(5)
    dirty = next(m for m in s.mps.values() if m.id != s.player_id)
    dirty.dossier, dirty.scandal_weeks = p.LEAK_MIN_DOSSIER + 0.2, 0
    apply_action(s, Action("leak", target=dirty.id))
    assert dirty.scandal_weeks > 0 or dirty.id not in s.mps, "leak didn't detonate"
    clean = next((m for m in s.mps.values()
                  if m.id != s.player_id and m.dossier <= p.LEAK_MIN_DOSSIER
                  and m.scandal_weeks <= 0), None)
    if clean is not None:
        n = len(s.log)
        apply_action(s, Action("leak", target=clean.id))
        assert not any(e.type == "ScandalBreaks" and e.data.get("mp") == clean.id
                       for e in s.log[n:]), "leak surfaced a clean target"
    me = s.mps[s.player_id]
    me.dossier, me.scandal_weeks = 1.0, 0
    n = len(s.log)
    apply_action(s, Action("leak", target=me.id))
    assert not any(e.type == "ScandalBreaks" and e.data.get("mp") == me.id
                   for e in s.log[n:]), "self-leak detonated"

    # the trace cost: a caught leak burns the bridge and marks your own dossier
    s = _governing(6)
    me = s.mps[s.player_id]
    t = next(m for m in s.mps.values() if m.id != s.player_id)
    t.dossier, t.scandal_weeks = p.LEAK_MIN_DOSSIER + 0.2, 0
    rel0 = t.relationships.get(me.id, 0.0)
    doss0 = me.dossier
    saved = p.LEAK_TRACE_P
    p.LEAK_TRACE_P = 1.0
    try:
        apply_action(s, Action("leak", target=t.id))
    finally:
        p.LEAK_TRACE_P = saved
    assert t.relationships.get(me.id, 0.0) < rel0, "traced leak didn't burn the bridge"
    assert me.dossier > doss0, "traced leak left the player's dossier clean"

    print("floor ok: defect costs + PM forfeiture + found gate + leak all fire")


if __name__ == "__main__":
    main()
