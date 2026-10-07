"""Runnable check: a saved run resumes identical to an uninterrupted one,
and object refs held by identity survive the round trip."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sim.actions import Action, available_actions
from sim.persist import _enc, from_json, to_json
from sim.state import Article, Bill, CourtCase, Deal, Law
from sim.tick import tick
from sim.worldgen import new_game

CTX = {"bills": {}, "laws": {}, "arts": {}}   # event data never carries refs


def canon(events) -> str:
    return json.dumps([{"type": e.type, "text": e.text,
                        "data": _enc(e.data, CTX)} for e in events],
                      sort_keys=True)


def scripted(state):
    menu = available_actions(state)
    out = []
    for want in ("constituency", "campaign", "speech", "lobby"):
        if want in menu and len(out) < 2:
            if want == "lobby":
                other = next(i for i in state.mps if i != state.player_id)
                out.append(Action("lobby", target=other))
            elif want == "speech":
                out.append(Action("speech", axis=0))
            else:
                out.append(Action(want))
    return out


def run(s, weeks):
    seen = []
    for _ in range(weeks):
        seen.append(tick(s, scripted(s)))
        if s.phase == "over":
            break
    return seen


def main() -> None:
    # the done-when: save mid-run, resume, and the future replays identically
    s1 = new_game(0)
    run(s1, 60)
    blob = to_json(s1)
    s2 = from_json(blob)
    assert to_json(s2) == blob          # re-serialization is byte-stable
    a, b = run(s1, 40), run(s2, 40)
    assert [canon(w) for w in a] == [canon(w) for w in b]
    assert to_json(s1) == to_json(s2)   # whole-state fingerprint, byte for byte

    # mid-formation save: slates on the table resume and resolve
    s3 = new_game(0)
    found = False
    for _ in range(150):
        tick(s3, scripted(s3))
        if s3.phase == "formation" and s3.offers:
            found = True
            s4 = from_json(to_json(s3))
            a, b = run(s3, 3), run(s4, 3)
            assert [canon(w) for w in a] == [canon(w) for w in b]
            break
    assert found, "no formation week reached in 150 ticks on seed 0"

    # the identity web: refs into the tables land on the same objects
    s = new_game(0)
    run(s, 5)
    law = Law(name="Test Act", pos=(0.2, 0.0), beneficiary_axis=0, cost=0.1,
              passed_week=s.week, margin=0.1, effect={})
    s.laws.append(law)
    bill = Bill(pos=(0.0, 0.0), beneficiary_axis=0, repeals=law,
                amends=s.constitution[0], name="Repeal of the Test Act")
    s.current_bill = bill
    s.deals.append(Deal(mp=0, vote=1, bill=bill))
    s.government.amend_move = Bill(
        pos=(0.0, 0.0), beneficiary_axis=0,
        entrenches=Article(id=-1, name="the Entrenched Clause",
                           kind="cost", limit=0.5))
    s.docket.append(CourtCase(law=law, due_week=s.week + 10,
                              challenger=None, risk=0.9))
    t = from_json(to_json(s))
    assert t.deals[0].bill is t.current_bill
    assert t.current_bill.repeals is t.laws[-1]
    assert t.current_bill.repeals is t.docket[0].law
    assert t.current_bill.amends is t.constitution[0]
    assert t.government.amend_move is not t.current_bill
    assert t.government.amend_move.entrenches.id == -1  # owned, not a table ref

    # a foreign format refuses loudly
    try:
        from_json(json.dumps({"format": 999}))
    except ValueError:
        pass
    else:
        raise AssertionError("foreign format accepted")

    print("persist check OK")


if __name__ == "__main__":
    main()
