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

    # the price reads distance actually moved — betrayal delta == W * |Δpos|
    mask = s.voters.district == me.district
    betray0 = float(s.voters.betrayal[mask].mean())
    pos0 = np.asarray(me.pos)
    apply_action(s, Action("evolve", pos=target))
    betray1 = float(s.voters.betrayal[mask].mean())
    assert abs((betray1 - betray0) - p.EVOLVE_BETRAYAL_W *
               dist(pos0, me.pos)) < 1e-6, "mistrust should price the real slide"

    # bounded — a target past the wall clips inside [-1, 1]
    apply_action(s, Action("evolve", pos=(9.0, 9.0)))
    assert all(-1.0 <= c <= 1.0 for c in me.pos), "pos escaped bounds"

    # standing follows the party's read — toward the platform pays, away costs
    s2 = None
    for i in range(40):
        cand = new_game(i)
        m = cand.mps[cand.player_id]
        pt = cand.parties.get(m.party)
        if pt is not None and dist(m.pos, pt.platform) > 0.1:
            s2, me2, pt2 = cand, m, pt
            break
    assert s2 is not None, "no seed gives a party member off the platform"
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

    # zero-distance is a silent no-op — no move, no mistrust, no event
    s3 = new_game(4)
    me3 = s3.mps[s3.player_id]
    pos3 = me3.pos
    betray3 = float(s3.voters.betrayal[
        s3.voters.district == me3.district].mean())
    n_events = len(s3.log)
    apply_action(s3, Action("evolve", pos=me3.pos))
    assert dist(pos3, me3.pos) < 1e-12, "standing still should move nothing"
    assert abs(float(s3.voters.betrayal[
        s3.voters.district == me3.district].mean()) - betray3) < 1e-12
    assert len(s3.log) == n_events, "a null slide shouldn't be news"

    # the bot repositions when the forecast is lost on the ground — force it:
    # push the player to the corner opposite their district until losing holds
    bot_checked = False
    for i in range(40):
        s4 = new_game(i)
        me4 = s4.mps[s4.player_id]
        cent4 = s4.voters.pos[s4.voters.district == me4.district].mean(axis=0)
        me4.pos = tuple(float(-np.sign(c) or 1.0) for c in cent4)
        gap4 = dist(me4.pos, tuple(cent4))
        if gap4 <= p.BOT_EVOLVE_GAP:
            continue
        f = district_forecast(s4, me4.district)
        lead = f["candidates"][0] if f["candidates"] else None
        if lead and lead["name"] == me4.name:
            continue
        acts = auto_actions(s4)
        assert any(a.kind == "evolve" for a in acts), \
            f"seed {i}: losing on the ground (gap {gap4:.2f}) should " \
            f"reposition, got {[a.kind for a in acts]}"
        bot_checked = True
        break
    assert bot_checked, "no seed produced a losing, far-off fixture"

    print("check_evolve ok")


if __name__ == "__main__":
    main()
