"""Runnable check: ambitions resolve deterministically — met at the boundary,
failed at game over, silent in the sandbox."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sim.state import Ambition, Party
from sim.tick import tick
from sim.worldgen import new_game


def _met(s, kind):
    s.ambition = Ambition(kind)
    tick(s)
    return next((e for e in s.log if e.type == "AmbitionMet"), None)


def main() -> None:
    # pm: hold the office
    s = new_game(0)
    s.government.pm = s.player_id
    assert _met(s, "pm"), "pm arc never fired"
    assert s.score_terms.get("ambition", 0) > 0

    # majority: your party alone over half the seats
    s = new_game(0)
    me = s.mps[s.player_id]
    s.parties[me.party].members = set(s.mps)   # engineered sweep
    assert _met(s, "majority"), "majority arc never fired"

    # founder: the vehicle fights a later election without you
    s = new_game(0)
    veh = Party(id=99, name="The Vehicle", platform=(0.0, 0.0),
                members={next(i for i in s.mps if i != s.player_id)},
                founded_week=0, founded_by=s.player_id)
    s.parties[99] = veh
    s.ambition = Ambition("founder")
    tick(s)                                   # records the vehicle
    s.emit("ElectionResult", "test")          # week >= 1 > founded_week
    tick(s)                                   # evaluates
    assert s.ambition.met, "founder arc never fired"

    # founder fails when the vehicle dies first
    s = new_game(0)
    s.ambition = Ambition("founder")
    tick(s)                                   # records nothing — no vehicle yet
    veh = Party(id=99, name="The Vehicle", platform=(0.0, 0.0),
                members={s.player_id}, founded_week=s.week,
                founded_by=s.player_id)
    s.parties[99] = veh
    tick(s)                                   # records the vehicle
    assert s.ambition.party == 99
    del s.parties[99]                         # it folds before contesting
    tick(s)
    assert s.ambition.failed, "dissolved vehicle didn't fail the arc"

    # survivor / reformer: thresholds on existing counters
    s = new_game(0)
    s.score_terms["mp"] = 4
    assert _met(s, "survivor"), "survivor arc never fired"
    s = new_game(0)
    s.legacy_bills = 3
    assert _met(s, "reformer"), "reformer arc never fired"

    # game over with an unmet arc fails it
    s = new_game(0)
    s.ambition = Ambition("pm")
    s.phase = "over"
    # check_ambition fires inside tick — phase=over returns early, so drive
    # the boundary the way election does: seat lost -> over -> same tick
    from sim.career import check_ambition
    check_ambition(s)
    assert s.ambition.failed

    # sandbox: no events ever
    s = new_game(0)
    for _ in range(30):
        tick(s)
    assert not any(e.type in ("AmbitionMet", "AmbitionFailed")
                   for e in s.log)

    # a real run can fire one honestly — pm arc on a long played run
    s = new_game(0)
    s.ambition = Ambition("survivor")
    for _ in range(400):
        tick(s)
        if s.phase == "over":
            break
    assert any(e.type in ("AmbitionMet", "AmbitionFailed") for e in s.log), \
        "400 weeks and the arc never resolved"

    print("goals check OK")


if __name__ == "__main__":
    main()
