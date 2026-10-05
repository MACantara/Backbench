"""Runnable check: dissolution on lost confidence, deadlock, and strategic calls."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sim.params as p
from sim.actions import Action, available_actions
from sim.election import poll, publish_poll
from sim.government import confidence_vote, resolve_formation, strategic_call
from sim.tick import tick
from sim.worldgen import new_game


def _three_party(seed: int, c_platform: tuple[float, float]):
    """Gov A(40)+B(25) at (0,0)/(0.4,0); C(55) positioned by the caller.
    B's MPs are parked hostile at (-1,-1) so the confidence bill always fails."""
    s = new_game(seed)
    pids = sorted(s.parties)
    for pt in s.parties.values():
        pt.members = set()
    s.parties[pids[0]].platform = (0.0, 0.0)
    s.parties[pids[1]].platform = (0.4, 0.0)
    s.parties[pids[2]].platform = c_platform
    mids = sorted(s.mps)
    assign = [(mids[:40], pids[0], (0.0, 0.0)),
              (mids[40:65], pids[1], (-1.0, -1.0)),
              (mids[65:], pids[2], c_platform)]
    for group, pid, pos in assign:
        for m in group:
            s.mps[m].party = pid
            s.mps[m].pos = pos
            s.parties[pid].members.add(m)
    s.government.parties = {pids[0], pids[1]}
    s.government.pm = mids[0]
    s.government.minority = False
    s.government.collapses = 0
    return s


def _policy(s) -> list:
    return [Action(k) for k in ("campaign", "constituency") if k in available_actions(s)][:2]


def main() -> None:
    # confidence snap: C is too far for any bloc without the fallen largest party
    s = _three_party(3, (-0.9, -0.9))
    survived = confidence_vote(s)
    calls = [e for e in s.log if e.type == "ElectionCalled"]
    assert not survived and s.weeks_to_election == p.CAMPAIGN_WEEKS
    assert calls and calls[-1].data.get("snap") and calls[-1].data["reason"] == "confidence"

    # constructive re-formation: C+B reach a majority without A → no dissolution,
    # and the fallen largest is barred from the successor government
    s2 = _three_party(4, (-0.3, -0.3))
    fallen = sorted(s2.parties)[0]   # A — the fallen government's largest party
    survived2 = confidence_vote(s2)
    calls2 = [e for e in s2.log if e.type == "ElectionCalled"]
    assert not survived2 and s2.phase == "formation" and not calls2, \
        "a viable alternative should re-form in place, not dissolve"
    for _ in range(3):   # a pivotal-player pause resolves on the next pass
        if resolve_formation(s2, []):
            break
    assert s2.government.parties, "formation stalled even with a viable majority"
    assert fallen not in s2.government.parties, \
        "the fallen largest walked straight back into government"

    # deadlock: viable alternative exists but collapses hit the cap → dissolve
    s3 = _three_party(5, (-0.3, -0.3))
    s3.government.collapses = p.SNAP_COLLAPSE_MAX - 1
    confidence_vote(s3)
    calls3 = [e for e in s3.log if e.type == "ElectionCalled"]
    assert calls3 and calls3[-1].data["reason"] == "deadlock" and s3.phase == "campaign"

    # strategic: a government polling above its seat share gambles inside the
    # window — on the *published* (sponsored) number, not the oracle
    s4 = None
    for seed in range(30):
        cand = new_game(seed)
        sponsor = cand.outlets[cand.week % len(cand.outlets)] if cand.outlets else None
        shares = poll(cand, outlet=sponsor)
        pid = max(shares, key=shares.get)
        seat_share = len(cand.parties[pid].members) / max(len(cand.mps), 1)
        if shares[pid] >= seat_share + p.SNAP_POLL_EDGE:
            s4, s4_pid = cand, pid
            break
    assert s4 is not None, "no seed gave a government a poll-over-seats surplus"
    s4.government.parties = {s4_pid}
    s4.government.pm = next(iter(s4.parties[s4_pid].members))
    s4.government.weeks_in_office = sum(p.SNAP_WINDOW) // 2
    s4.phase = "governing"  # strategic calls only exist inside a term
    n_calls = sum(1 for e in s4.log if e.type == "ElectionCalled")  # starts in campaign
    for _ in range(200):
        publish_poll(s4)          # the tick publishes before the PM reads it
        strategic_call(s4)
        if sum(1 for e in s4.log if e.type == "ElectionCalled") > n_calls:
            break
    calls4 = [e for e in s4.log if e.type == "ElectionCalled"]
    assert calls4, "strategic call never fired despite an open gate"
    assert calls4[-1].data["snap"] and calls4[-1].data["reason"] == "strategic"

    # long run: snaps occur on some seeds, scheduled calls keep working
    snaps, scheduled = 0, 0
    for seed in range(4):
        s = new_game(seed)
        for _ in range(250):
            if s.phase == "over":
                break
            tick(s, _policy(s))
        for e in s.log:
            if e.type == "ElectionCalled":
                snaps += bool(e.data.get("snap"))
                scheduled += not e.data.get("snap")
    assert snaps > 0, "no snap election fired in four seeds"
    assert scheduled > 0, "scheduled elections vanished"
    print(f"snap-elections ok: constructive, deadlock, strategic all fire "
          f"(snaps={snaps} scheduled={scheduled})")


if __name__ == "__main__":
    main()
