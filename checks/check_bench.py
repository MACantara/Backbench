"""Check: the bench — doctrine decides, vacancies fill, PMs leave a legacy."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sim.params as p
from sim.actions import Action
from sim.conditions import enact
from sim.courts import file_case
from sim.state import Article, Bill, Justice
from sim.tick import tick
from sim.worldgen import new_game


def _governing(seed: int):
    s = new_game(seed)
    for _ in range(60):
        tick(s)
        if s.phase == "governing" and s.government.pm is not None:
            return s
    raise AssertionError(f"seed {seed} never formed a government")


def _bench(pos, activism):
    return [Justice(i, f"J{i}", pos, activism, 2600)
            for i in range(p.BENCH_SIZE)]


def _case_against(s, law):
    """File and fast-forward a docket entry on a fixture statute — a short
    docket so politics (a collapse, a repeal) can't moot the case first."""
    filer = next((pid for pid in s.parties
                  if pid not in s.government.parties), None)
    s.docket.clear()
    old_weeks = p.REVIEW_WEEKS
    p.REVIEW_WEEKS = 1
    try:
        file_case(s, law, filer)
        for _ in range(4):
            tick(s)
            if not any(c.law is law for c in s.docket):
                break
    finally:
        p.REVIEW_WEEKS = old_weeks
    e = next((e for e in reversed(s.log)
              if e.type in ("LawStruck", "LawUpheld")
              and e.data.get("law") == law.name), None)
    assert e is not None, "the case resolved without a verdict"
    return e


def main() -> None:
    # doctrine decides: aligned benches held constant, activism swings verdicts
    outcomes = {}
    for activism, expect in ((0.0, "LawUpheld"), (1.0, "LawStruck")):
        s = _governing(0)
        s.constitution = [Article(0, "the Property Clause", "pos",
                                  axis=0, pole=-1, limit=0.3)]
        s.bench = _bench((-0.8, 0.0), activism)   # temperament on the law's pole
        law = enact(s, Bill(pos=(-0.8, 0.0), beneficiary_axis=0,
                            cost=0.2, name="Lands Act"), 80, 20)
        e = _case_against(s, law)
        outcomes[expect] = e.type == expect
        assert all("u" in v and "strike" in v for v in e.data["bench"]), \
            "the verdict should carry per-justice vote detail"
    assert all(outcomes.values()), f"doctrine didn't decide: {outcomes}"

    # ideology swings the middle: same doctrine, an aligned bench holds
    outcomes2 = {}
    for pos, expect in (((-0.8, 0.0), "LawUpheld"), ((0.9, 0.9), "LawStruck")):
        s = _governing(0)
        s.constitution = [Article(0, "the Property Clause", "pos",
                                  axis=0, pole=-1, limit=0.3)]
        s.bench = _bench(pos, 0.0)     # deferential doctrine; only sympathy varies
        law = enact(s, Bill(pos=(-0.8, 0.0), beneficiary_axis=0,
                            cost=0.2, name="Lands Act"), 80, 20)
        e = _case_against(s, law)
        outcomes2[expect] = e.type == expect
    assert all(outcomes2.values()), f"ideology didn't decide: {outcomes2}"

    # vacancies: a retirement opens a seat; the AI PM fills it and signs it
    s = _governing(0)
    pm = s.government.pm
    s.bench = s.bench[:p.BENCH_SIZE - 1]
    for j in s.bench:
        j.age = 2600   # below the hazard floor — no mid-tick retirement
    n = len(s.log)
    tick(s)
    assert len(s.bench) == p.BENCH_SIZE, "the vacancy wasn't filled"
    assert s.bench[-1].appointed_by == pm, "the appointee isn't signed by the PM"
    assert any(e.type == "JusticeAppointed" for e in s.log[n:])

    # the player-PM gets a shortlist and their pick takes the seat
    s = _governing(0)
    gov_pid = next(iter(s.government.parties))
    s.player_id = next(iter(s.parties[gov_pid].members))
    s.government.pm = s.player_id
    s.parties[gov_pid].leader = s.player_id
    s.bench = s.bench[:p.BENCH_SIZE - 1]
    for j in s.bench:
        j.age = 2600
    tick(s)
    assert len(s.bench_shortlist) == p.APPOINT_POOL, \
        "the player-PM got no nominee shortlist"
    pick = s.bench_shortlist[1]
    tick(s, [Action("appoint", judge=1)])
    assert pick in s.bench and pick.appointed_by == s.player_id
    assert not s.bench_shortlist, "the shortlist didn't clear after the pick"

    # caretaker void: no government, no appointments — the seat stays empty
    s = _governing(0)
    s.bench = s.bench[:p.BENCH_SIZE - 1]
    for j in s.bench:
        j.age = 2600
    s.government.parties = set()
    s.government.pm = None
    tick(s)
    assert len(s.bench) == p.BENCH_SIZE - 1, \
        "a caretaker void seated a justice"

    print("bench ok: doctrine, ideology, vacancies, appointments")


if __name__ == "__main__":
    main()
