"""Runnable check: the evolve action — lerp, price, direction, bot gate."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

import sim.params as p
from sim.actions import Action, apply_action, available_actions
from sim.bot import auto_actions
from sim.election import district_forecast
from sim.state import dist
from sim.worldgen import new_game


def main() -> None:
    s = new_game(4)
    me = s.mps[s.player_id]
    assert "evolve" in available_actions(s), "evolve missing from the menu"

    # partial move toward the target — a lerp, not a teleport
    cent = s.voters.pos[s.voters.district == me.district].mean(axis=0)
    target = (float(cent[0]), float(cent[1]))
    before = np.asarray(me.pos)
    apply_action(s, Action("evolve", pos=target))
    step = dist(before, me.pos)
    gap = dist(before, target)
    assert 0 < step < gap, f"moved {step:.3f} of {gap:.3f} — should be partial"
    assert abs(step - p.EVOLVE_STEP * gap) < 1e-9, "step should be the lerp share"

    # betrayal prices distance actually moved — a second slide accrues again
    mask = s.voters.district == me.district
    betray0 = float(s.voters.betrayal[mask].mean())
    apply_action(s, Action("evolve", pos=target))
    betray1 = float(s.voters.betrayal[mask].mean())
    assert betray1 > betray0, "each slide should cost the district's trust"

    # bounded — a target past the wall clips inside [-1, 1]
    apply_action(s, Action("evolve", pos=(9.0, 9.0)))
    assert all(-1.0 <= c <= 1.0 for c in me.pos), "pos escaped bounds"

    # standing follows the party's read — toward the platform pays, away costs
    s2 = new_game(4)
    me2 = s2.mps[s2.player_id]
    pt2 = s2.parties.get(me2.party)
    if pt2 is not None and dist(me2.pos, pt2.platform) > 0.1:
        st0 = me2.standing
        apply_action(s2, Action("evolve", pos=tuple(pt2.platform)))
        toward = me2.standing - st0
        st1 = me2.standing
        away = tuple(np.clip(np.asarray(me2.pos) -
                             0.5 * (np.asarray(pt2.platform) -
                                    np.asarray(me2.pos)), -1, 1))
        apply_action(s2, Action("evolve", pos=away))
        assert me2.standing - st1 < toward, \
            "trimming to the platform should beat drifting from it"

    # zero-distance is a no-op — no free betrayal, no standing reroll
    s3 = new_game(4)
    me3 = s3.mps[s3.player_id]
    pos3 = me3.pos
    betray3 = float(s3.voters.betrayal[
        s3.voters.district == me3.district].mean())
    apply_action(s3, Action("evolve", pos=me3.pos))
    assert dist(pos3, me3.pos) < 1e-12, "standing still should move nothing"
    assert abs(float(s3.voters.betrayal[
        s3.voters.district == me3.district].mean()) - betray3) < 1e-12

    # the bot repositions when the forecast is lost on the ground
    s4 = new_game(4)
    me4 = s4.mps[s4.player_id]
    cent4 = s4.voters.pos[s4.voters.district == me4.district].mean(axis=0)
    me4.pos = tuple(np.clip(np.asarray(cent4) + np.array([0.9, 0.9]), -1, 1))
    f = district_forecast(s4, me4.district)
    lead = f["candidates"][0] if f["candidates"] else None
    losing = not (lead and lead["name"] == me4.name)
    gap4 = dist(me4.pos, tuple(cent4))
    if losing and gap4 > p.BOT_EVOLVE_GAP:
        acts = auto_actions(s4)
        assert any(a.kind == "evolve" for a in acts), \
            f"losing on the ground should reposition, got {[a.kind for a in acts]}"
    else:
        print(f"  (fixture not losing — gap {gap4:.2f} losing={losing})")

    print("check_evolve ok")


if __name__ == "__main__":
    main()
