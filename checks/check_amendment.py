"""Check: constitutional amendment — the two-thirds gate and the strike loop."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sim.params as p
from sim.conditions import enact
from sim.courts import file_case
from sim.parliament import resolve_vote
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


def _house(s, share: float) -> Bill:
    """A clause-repeal bill and a house engineered to aye it at `share`.
    Everyone's position sits at the bill's, then `share` of the house
    moves far enough away to vote no — rough but deterministic in effect."""
    s.constitution = [Article(0, "the Property Clause", "pos",
                              axis=0, pole=-1, limit=0.3)]
    bill = Bill(pos=(0.0, 0.0), beneficiary_axis=0,
                amends=s.constitution[0], name="Repeal of the Property Clause")
    n_no = int(round(len(s.mps) * (1 - share)))
    for pt in s.parties.values():
        pt.platform = (0.0, 0.0)   # every whip lines up behind the bill
    for i, mp in enumerate(sorted(s.mps.values(), key=lambda m: m.id)):
        mp.pos = (0.9, 0.9) if i < n_no else (0.0, 0.0)
        mp.faction = None
    return bill


def main() -> None:
    # 55% ayes loses; 70% carries — the supermajority gate is real
    for share, expect in ((0.55, False), (0.70, True)):
        s = _governing(0)
        bill = _house(s, share)
        passed = resolve_vote(s, bill)
        assert passed == expect, \
            f"amendment at {share:.0%} aye-share should {'pass' if expect else 'fail'}"
        vr = next(e for e in reversed(s.log) if e.type == "VoteResult")
        assert "Amendment" in vr.text
        if expect:
            assert vr.data["passed"], "a 70% aye-share amendment must pass"
            assert not s.constitution, "repealed clause still on the book"
            assert any(e.type == "ArticleRepealed" for e in s.log)
        else:
            assert not vr.data["passed"], "a 55% aye-share amendment must fail"
            assert "two-thirds" in vr.text, \
                "a majority that misses the bar should say so"
            assert s.constitution, "a failed repeal still struck the clause"

    # an all-abstain division can't move the book — nobody casting means
    # nobody carried it, and 0-0 must never satisfy the supermajority
    s = _governing(0)
    s.constitution = [Article(0, "the Property Clause", "pos",
                              axis=0, pole=-1, limit=0.3)]
    s.government.parties = set()              # a dead coalition whips nobody
    s.voters.pos[:] = 0.0                     # districts indifferent too
    for m in s.mps.values():
        m.pos = (0.0, 0.0)
        m.party = None                        # independents take no whip
        m.faction = None
        m.scandal_weeks = 0
    bill = Bill(pos=(0.0, 0.0), beneficiary_axis=0,
                amends=s.constitution[0], name="Mute Repeal")
    old_noise = p.VOTE_NOISE
    p.VOTE_NOISE = 0.0                        # silence the ballot noise: every
    try:                                      # utility lands exactly on zero
        assert not resolve_vote(s, bill), \
            "an amendment carried on nobody's ayes"
    finally:
        p.VOTE_NOISE = old_noise
    assert s.constitution, "a silent house still struck the clause"

    # the closed loop: court strikes the coalition's law under a clause →
    # the wounded government tables that clause's repeal (once per term)
    s = _governing(0)
    gov = set(s.government.parties)
    s.constitution = [Article(0, "the Property Clause", "pos",
                              axis=0, pole=-1, limit=0.3)]
    s.bench = [Justice(i, f"J{i}", (0.9, 0.9), 1.0, 2600)
               for i in range(p.BENCH_SIZE)]
    law = enact(s, Bill(pos=(-0.8, 0.0), beneficiary_axis=0, cost=0.2,
                        name="Flagship Act"), 80, 20)
    law.enacted_by = gov
    filer = next((pid for pid in s.parties
                  if pid not in s.government.parties), None)  # independent if none
    old_table_p, old_weeks = p.AMEND_TABLE_P, p.REVIEW_WEEKS
    p.AMEND_TABLE_P, p.REVIEW_WEEKS = 1.0, 1
    try:
        file_case(s, law, filer)
        saw_amend = None
        for _ in range(30):
            for e in tick(s):
                if e.type == "BillTabled" and e.data.get("amends") is not None:
                    saw_amend = e
            if saw_amend:
                break
        assert saw_amend is not None, \
            "a struck coalition never moved against the citing clause"
        assert "Property Clause" in saw_amend.text
    finally:
        p.AMEND_TABLE_P, p.REVIEW_WEEKS = old_table_p, old_weeks

    # one swing per clause per term: after the move, the agenda doesn't refill
    tick(s)
    for _ in range(8):
        for e in tick(s):
            assert not (e.type == "BillTabled"
                        and e.data.get("amends") == 0), \
                "the government re-tabled a spent amendment"

    print("amendment ok: two-thirds gate, strike loop, one swing per clause")


if __name__ == "__main__":
    main()
