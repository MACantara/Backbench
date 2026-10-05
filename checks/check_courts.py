"""Runnable check: legal risk gates, docket delay, activism verdicts, strikes."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sim.params as p
from sim.actions import Action, available_actions
from sim.conditions import enact
from sim.courts import courts_lifecycle, legal_risk
from sim.media import _subjects
from sim.state import Article, Bill, Justice
from sim.tick import tick
from sim.treasury import upkeep
from sim.worldgen import new_game


def _policy(s) -> list:
    return [Action(k) for k in ("campaign", "constituency") if k in available_actions(s)][:2]


def _gov(seed: int, activism: float | None = None):
    s = new_game(seed)
    s.government.parties = {next(iter(s.parties))}
    s.government.pm = None
    if activism is not None:
        s.court_activism = activism
    return s


def main() -> None:
    # gates: a radical thin-margin law is challenged; a centrist one never is
    s = _gov(3, 1.0)
    hot = enact(s, Bill(pos=(0.95, 0.9), beneficiary_axis=0, cost=0.012), yes=52, no=48)
    calm = enact(s, Bill(pos=(0.05, -0.05), beneficiary_axis=0, cost=0.003), yes=110, no=10)
    courts_lifecycle(s)
    opened = [e for e in s.log if e.type == "ReviewOpened"]
    assert opened and opened[-1].data["law"] == hot.name, \
        "the radical law wasn't the one challenged"
    assert opened[-1].data["challenger"] not in s.government.parties, \
        "the government sued itself"
    assert len(s.docket) == 1 and calm not in [c.law for c in s.docket], \
        "the centrist law entered the docket"

    # delay: the verdict lands REVIEW_WEEKS later, in force meanwhile
    for _ in range(p.REVIEW_WEEKS - 1):
        courts_lifecycle(s)
        s.week += 1
    assert not hot.reviewed and any(l is hot for l in s.laws) and s.docket, \
        "pending case resolved early or vanished"
    s.week += 1
    courts_lifecycle(s)  # due now
    struck = any(e.type == "LawStruck" for e in s.log)
    upkeep_after = upkeep(s)
    assert struck and hot.reviewed and not any(l is hot for l in s.laws), \
        "due case didn't strike the law"
    assert upkeep_after < hot.cost, "struck law kept costing upkeep"
    courts_lifecycle(s)
    assert len(s.docket) == 0, "a struck/reviewed law got re-challenged"

    # the verdict is a rule: same statute, different bench — and a strike blames
    # the authors even after they leave office; the filer joining gov mid-case
    # doesn't stop the case
    outcomes = {}
    for activism, expect in ((1.0, "LawStruck"), (0.0, "LawUpheld")):
        s2 = _gov(4)
        # a controlled constitution: the fixture statute breaches the clause
        s2.constitution = [Article(0, "the Property Clause", "pos",
                                   axis=0, pole=-1, limit=0.4)]
        # a controlled bench: aligned with the statute, doctrine varies
        s2.bench = [Justice(i, f"J{i}", (-0.8, 0.0), activism, 2600)
                    for i in range(p.BENCH_SIZE)]
        author = next(iter(s2.parties))
        law = enact(s2, Bill(pos=(-0.8, 0.0), beneficiary_axis=0, cost=0.004),
                    yes=70, no=50)
        courts_lifecycle(s2)  # file it first
        assert s2.docket, "fixture law never got challenged"
        challenger = s2.docket[0].challenger
        # the author loses office and the filer joins the new government —
        # the case must proceed regardless
        s2.government.parties = {challenger}
        for _ in range(p.REVIEW_WEEKS + 1):
            courts_lifecycle(s2)
            s2.week += 1
        verdicts = [e.type for e in s2.log if e.type in ("LawStruck", "LawUpheld")]
        assert verdicts == [expect], f"activism={activism} gave {verdicts}, want {expect}"
        outcomes[expect] = (s2, law, author)
    struck_s, struck_law, struck_author = outcomes["LawStruck"]
    assert struck_s.parties[struck_author].brand < 0, \
        "a struck law didn't bleed its (now opposition) author"
    struck_ev = next(e for e in struck_s.log if e.type == "LawStruck")
    assert _subjects(struck_s, struck_ev) == [struck_author], \
        "the press should blame the authors, not the incumbents"
    assert struck_ev.data["article"] == 0 and "Property Clause" in struck_ev.text, \
        "a strike must cite the clause it enforces"
    upheld_s, upheld_law, _ = outcomes["LawUpheld"]
    assert upheld_law.reviewed and any(l is upheld_law for l in upheld_s.laws), \
        "upheld law should stay in force, immune"

    # capacity + hostility gates: full docket blocks new filings; a friendly
    # opposition can't file no matter the risk
    s5 = _gov(6, 1.0)
    for _ in range(3):
        enact(s5, Bill(pos=(0.95, 0.9), beneficiary_axis=0, cost=0.012), yes=55, no=45)
        courts_lifecycle(s5)
    assert len(s5.docket) <= p.COURT_DOCKET_MAX, "docket exceeded bench capacity"
    s6 = _gov(7, 1.0)
    law6 = enact(s6, Bill(pos=(0.95, 0.9), beneficiary_axis=0, cost=0.012), yes=55, no=45)
    for pt in s6.parties.values():
        pt.platform = law6.pos  # every party loves it — nobody is hostile enough to sue
    courts_lifecycle(s6)
    assert not s6.docket, "a case opened without a hostile opposition"

    # no opposition, no court: a one-party world never opens a case
    s3 = _gov(5, 1.0)
    s3.government.parties = set(s3.parties)
    enact(s3, Bill(pos=(0.95, 0.9), beneficiary_axis=0, cost=0.012), yes=100, no=10)
    courts_lifecycle(s3)
    assert not s3.docket, "a case opened with no opposition to file it"

    # long run: review happens naturally, and rarely — a few cases per term
    opened = struck = upheld = 0
    for seed in range(4):
        s4 = new_game(seed)
        for _ in range(250):
            if s4.phase == "over":
                break
            tick(s4, _policy(s4))
        for e in s4.log:
            opened += e.type == "ReviewOpened"
            struck += e.type == "LawStruck"
            upheld += e.type == "LawUpheld"
    assert opened > 0, "no natural challenge in four seeds"
    assert struck + upheld == opened or opened - (struck + upheld) <= 4 * p.COURT_DOCKET_MAX, \
        "cases vanished without verdicts"
    print(f"courts ok: gates+delay+verdicts fire "
          f"(opened={opened} struck={struck} upheld={upheld})")

    # determinism: identical seeds produce identical weeks
    a, b = new_game(11), new_game(11)
    for _ in range(80):
        tick(a, _policy(a))
        tick(b, _policy(b))
    sig = lambda s: [(e.type, e.text) for e in s.log]
    assert sig(a) == sig(b), "same seed diverged"


if __name__ == "__main__":
    main()
