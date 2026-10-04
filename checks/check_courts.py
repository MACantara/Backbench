"""Runnable check: legal risk gates, docket delay, activism verdicts, strikes."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sim.params as p
from sim.actions import Action, available_actions
from sim.conditions import enact
from sim.courts import courts_lifecycle, legal_risk
from sim.state import Bill
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

    # the verdict is a rule: same statute, different bench
    outcomes = {}
    for activism, expect in ((1.0, "LawStruck"), (0.0, "LawUpheld")):
        s2 = _gov(4, activism)
        s2.government.parties = {0}  # set before enact — it's the recorded author
        law = enact(s2, Bill(pos=(0.5, 0.0), beneficiary_axis=0, cost=0.004), yes=70, no=50)
        for _ in range(p.REVIEW_WEEKS + 1):
            courts_lifecycle(s2)
            s2.week += 1
        verdicts = [e.type for e in s2.log if e.type in ("LawStruck", "LawUpheld")]
        assert verdicts == [expect], f"activism={activism} gave {verdicts}, want {expect}"
        outcomes[expect] = (s2, law)
    struck_s, struck_law = outcomes["LawStruck"]
    author_brand = struck_s.parties[0].brand
    assert author_brand < 0, "the authoring party took no brand hit"
    upheld_s, upheld_law = outcomes["LawUpheld"]
    assert upheld_law.reviewed and upheld_law in upheld_s.laws, \
        "upheld law should stay in force, immune"

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
