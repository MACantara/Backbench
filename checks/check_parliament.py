"""Runnable check: whips move votes, loved bills pass, hated bills fail."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sim.params as p
from sim.parliament import resolve_vote, table_bill, vote_utility
from sim.state import Bill
from sim.worldgen import new_game


def yes_rate(state, bill, party_id=None):
    votes = [vote_utility(state, m, bill) > 0
             for m in state.mps.values() if party_id is None or m.party == party_id]
    return sum(votes) / max(len(votes), 1)


def main() -> None:
    s = new_game(3)
    s.government.parties = {2}          # Centre Democrats govern alone
    s.government.pm = s.parties[2].leader

    centre_bill = Bill(pos=s.parties[2].platform, beneficiary_axis=0)
    far_bill = Bill(pos=(1.0, 1.0), beneficiary_axis=1)

    # whip alignment: centre MPs back a centre bill far more than others
    in_rate = yes_rate(s, centre_bill, 2)
    out_rate = yes_rate(s, centre_bill)
    assert in_rate > 0.6, in_rate
    assert in_rate > out_rate

    # a bill at the corner nobody likes fails (is False — a None stall is not a loss)
    assert resolve_vote(s, far_bill) is False

    # utility is monotonic in distance for the same MP
    mp = next(iter(s.mps.values()))
    near = Bill(pos=mp.pos, beneficiary_axis=0)
    assert vote_utility(s, mp, near) > vote_utility(s, mp, far_bill)

    # a majority coalition's bill passes (minority govt failing is correct, not a bug)
    s2 = new_game(4)
    s2.government.parties = {0, 1, 2}  # Labour + Green + Centre = 85/120
    s2.government.pm = s2.parties[2].leader
    b = table_bill(s2)
    assert resolve_vote(s2, b)

    print(f"parliament ok: gov_yes={in_rate:.0%} avg_yes={out_rate:.0%}")


if __name__ == "__main__":
    main()
