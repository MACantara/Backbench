"""Runnable check: M12 entropy — fatigue, coalition exit, frontier
rookies, differentiation. The late game must not be absorbing."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

import sim.params as p
from sim.government import coalition_exits
from sim.parties import party_lifecycle
from sim.state import dist
from sim.tick import tick
from sim.worldgen import make_hopeful, new_game


def governing(seed: int):
    s = new_game(seed)
    while s.phase != "governing" and s.phase != "over":
        tick(s, [])
    return s


def main() -> None:
    # fatigue: voters drift away from the agenda, compounding with tenure
    s = governing(4)
    gov = s.government
    assert gov.platform is not None and gov.parties, "fixture needs a government"
    agenda = np.asarray(gov.platform)
    d0 = np.linalg.norm(s.voters.pos - agenda, axis=1).mean()
    for _ in range(30):
        tick(s, [])
    d1 = np.linalg.norm(s.voters.pos - agenda, axis=1).mean()
    assert d1 > d0, f"fatigue should open distance ({d0:.3f} -> {d1:.3f})"

    # exit: fires only when strain AND bleed AND grace all hold
    s = governing(4)
    gov = s.government
    pm_pid = s.mps[gov.pm].party if gov.pm in s.mps else None
    junior = next(pid for pid in gov.parties if pid != pm_pid)
    pt = s.parties[junior]
    s.last_poll = {"week": s.week, "shares": {pid: 0.5 for pid in s.parties}}
    gov.weeks_in_office = p.COAL_EXIT_GRACE
    before = set(gov.parties)
    coalition_exits(s)
    assert set(gov.parties) == before, "exited during grace"
    gov.weeks_in_office = p.COAL_EXIT_GRACE + 5
    pt.platform = tuple(-np.asarray(gov.platform) * 4)
    coalition_exits(s)
    assert set(gov.parties) == before, "exited on strain alone — no bleed"
    s.last_poll["shares"][junior] = 0.0
    coalition_exits(s)
    assert junior not in gov.parties, "strain + bleed should end the tie"
    assert any(e.type == "CoalitionExit" for e in s.log), "no CoalitionExit event"

    # frontier rookies: some hopefuls arrive far from every platform
    s = governing(4)
    np_rng = np.random.default_rng(1)
    n_d = int(s.voters.district.max()) + 1
    frontier = sum(
        min(dist(make_hopeful(s.rng, np_rng, s.parties, n_d,
                              voters=s.voters).pos, pt.platform)
            for pt in s.parties.values()) >= p.DYNAMIC_GAP_DIST - 0.2
        for _ in range(40))
    assert frontier > 3, f"frontier channel dead — only {frontier}/40 far rookies"

    # differentiation: an opposition platform tracks its own base over time
    s = governing(4)
    opp = [pid for pid in s.parties if pid not in s.government.parties]
    moved = False
    for pid in opp:
        pt = s.parties[pid]
        p0 = pt.platform
        for _ in range(20):
            party_lifecycle(s)
        if pid in s.parties and dist(p0, s.parties[pid].platform) > 1e-6:
            moved = True
    assert moved or not opp, "opposition platform never tracked its base"

    print("check_entropy ok")


if __name__ == "__main__":
    main()
