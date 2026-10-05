"""Check: the career ladder — deliberate play reaches office, passivity doesn't."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sim import params as p
from sim.actions import Action
from sim.career import junior_lifecycle, mp_lifecycle
from sim.tick import tick
from sim.worldgen import new_game

WEEKS = 150
SEEDS = range(8)


def run(seed: int, climber: bool):
    """How far the player climbs in WEEKS weeks: (junior, cabinet, week reached)."""
    s = new_game(seed)
    junior = cabinet = False
    for _ in range(WEEKS):
        if s.phase == "over":
            break
        me = s.mps.get(s.player_id)
        if me is None:
            break
        acts = []
        if climber:  # court the leader, serve the district — the honest grind
            pt = s.parties.get(me.party)
            if pt is not None and pt.leader is not None:
                acts.append(Action("lobby", target=pt.leader))
            acts.append(Action("campaign") if s.phase == "campaign"
                        else Action("constituency"))
        tick(s, acts)
        me = s.mps.get(s.player_id)
        if me is not None:
            junior |= me.junior is not None
            cabinet |= me.portfolio is not None
    return junior, cabinet, s.week


def main() -> None:
    # the done-when: deliberate climbing reaches office, passivity doesn't
    climb = [run(i, True) for i in SEEDS]
    passive = [run(i, False) for i in SEEDS]
    c_cab = sum(r[1] for r in climb)
    p_off = sum(r[0] or r[1] for r in passive)
    assert c_cab >= 4, f"climber reached cabinet only {c_cab}/{len(SEEDS)} seeds"
    assert c_cab >= p_off + 2, "climbing didn't beat doing nothing"
    print(f"ladder: climber cabinet {c_cab}/{len(SEEDS)} "
          f"vs passive office {p_off}/{len(SEEDS)}")

    # standing: whip fidelity earns it, rebellion burns it, decay returns it
    s = new_game(0)
    while s.phase != "governing":
        tick(s)
    tick(s)
    loyal = [m for m in s.mps.values() if m.standing > 0.01]
    rebels = [m for m in s.mps.values() if m.standing < -0.01]
    assert loyal, "a week of whipped votes earned nobody standing"
    me = s.mps[s.player_id]
    me.standing = 0.5
    mp_lifecycle(s)
    assert 0.4 < me.standing < 0.5, f"standing didn't decay: {me.standing:.3f}"
    s2 = new_game(1)
    while s2.phase != "governing":
        tick(s2)
    m2 = s2.mps[s2.player_id]
    m2.standing = 0.3
    m2.scandal_weeks = 4
    mp_lifecycle(s2)
    assert m2.standing < 0.3, "a burning scandal didn't bleed standing"
    print(f"standing: loyal={len(loyal)} rebels={len(rebels)}, "
          f"decay+scandal verified")

    # junior posts fill for every seated party, and vacated rungs refill
    s3 = new_game(2)
    while s3.phase != "governing":
        tick(s3)
    holders = [(m.id, m.party) for m in s3.mps.values() if m.junior]
    assert holders, "no junior posts filled"
    filled_parties = {pid for _, pid in holders}
    assert len(filled_parties) >= 2, "only the coalition has a bench"
    jid, pid = holders[0]
    s3.mps[jid].junior, s3.mps[jid].junior_weeks = None, 0
    s3.government.sacked.add(jid)   # bar the same MP — a refill means another climber
    junior_lifecycle(s3)
    new = next((m for m in s3.mps.values()
                if m.junior and m.party == pid and m.id != jid), None)
    assert new is not None, "a vacated rung wasn't refilled"
    print(f"bench: {len(holders)} posts across {len(filled_parties)} parties, "
          f"refill -> {new.name}")

    # passed-over legibility fires when the player is a losing candidate
    s4 = new_game(3)
    while s4.phase != "governing":
        tick(s4)
    if not any(e.type == "CareerEvent" and "Passed over" in e.text
               for e in s4.log):
        for _ in range(30):
            tick(s4)
            if s4.phase == "over":
                break
    assert any(e.type == "CareerEvent" and "Passed over" in e.text
               for e in s4.log), "the player was never told why they lost a post"
    print("legibility: passed-over events fire")

    print("ladder ok")


if __name__ == "__main__":
    main()
