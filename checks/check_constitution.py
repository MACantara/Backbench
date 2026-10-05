"""Check: the constitution — article violations, citations, player challenges."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sim.params as p
from sim.actions import Action
from sim.conditions import enact
from sim.courts import challengeable, legal_risk, violation
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


def _striking_bench(s) -> None:
    """A bench that will strike anything contestable: activist doctrine,
    temperament parked far from the statute's pole."""
    s.bench = [Justice(i, f"J{i}", (0.9, 0.9), 1.0, 2600)
               for i in range(p.BENCH_SIZE)]


def main() -> None:
    # the oracle scores clause breaches, not vibes
    s = _governing(4)
    s.constitution = [Article(0, "the Property Clause", "pos",
                              axis=0, pole=-1, limit=0.3)]
    radical = Bill(pos=(-0.8, 0.0), beneficiary_axis=0, cost=0.1)
    centrist = Bill(pos=(0.1, 0.0), beneficiary_axis=0, cost=0.1)
    assert violation(s.constitution[0], type("L", (),
                    {"pos": radical.pos, "cost": 0.1, "margin": 0.6})()) > 0
    law_r = enact(s, radical, 80, 20)
    law_c = enact(s, centrist, 80, 20)
    assert legal_risk(s, law_r) > legal_risk(s, law_c), \
        "a pole-breaching statute should out-risk a centrist one"

    # filings cite the clause and verdicts carry the citation forward —
    # a short docket: politics (collapse, repeal) must not moot the fixture
    _striking_bench(s)
    n = len(s.log)
    filer = next(pid for pid in s.parties if pid not in s.government.parties)
    s.docket.clear()
    old_weeks = p.REVIEW_WEEKS
    p.REVIEW_WEEKS = 1
    try:
        from sim.courts import file_case
        file_case(s, law_r, filer)
        opened = s.log[-1]
        assert opened.type == "ReviewOpened" \
            and opened.data["article"] == 0, \
            "ReviewOpened didn't cite the breached clause"
        for _ in range(4):
            tick(s)
    finally:
        p.REVIEW_WEEKS = old_weeks
    struck = next((e for e in s.log[n:]
                   if e.type == "LawStruck"
                   and e.data.get("law") == law_r.name), None)
    assert struck is not None and struck.data["article"] == 0, \
        "LawStruck didn't cite the Property Clause"
    assert "Property Clause" in struck.text
    assert law_r not in s.laws
    assert law_c in s.laws, "the centrist statute was collateral damage"

    # player challenge: a qualifying law takes the player's filing
    s2 = _governing(8)
    s2.constitution = [Article(0, "the Fiscal Clause", "cost", limit=0.01)]
    law = enact(s2, Bill(pos=tuple(s2.government.platform),
                         beneficiary_axis=0, cost=0.9, name="Spendthrift Act"),
                90, 10)
    ch = challengeable(s2)
    assert law in ch, "a fiscal-clause breach should be challengeable"
    idx = s2.laws.index(law)
    n = len(s2.log)
    tick(s2, [Action("challenge", law=idx)])
    case = next((c for c in s2.docket if c.law is law), None)
    assert case is not None, "player filing didn't open a case"
    me = s2.mps[s2.player_id]
    assert case.challenger == me.party
    ev = next(e for e in s2.log[n:] if e.type == "ReviewOpened")
    assert "You challenge" in ev.text

    print("constitution ok: violations, citations, player challenge")


if __name__ == "__main__":
    main()
