"""Runnable check: competence moves dials, records are judged, reshuffles refill."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sim.params as p
from sim.actions import Action, available_actions
from sim.career import ministerial_lifecycle
from sim.conditions import conditions_lifecycle
from sim.tick import tick
from sim.worldgen import new_game


def _policy(s) -> list:
    return [Action(k) for k in ("campaign", "constituency") if k in available_actions(s)][:2]


def _finance_gov(seed: int, competence: float):
    """Solo government whose Finance minister has a fixed competence."""
    s = new_game(seed)
    pid = next(iter(s.parties))
    s.government.parties = {pid}
    mp = next(m for m in s.mps.values() if m.party == pid and m != s.government.pm)
    mp.portfolio = "Finance"
    mp.competence = competence
    return s, mp


def main() -> None:
    # competence divergence: same seed, same noise — only the minister differs
    s_hi, hi = _finance_gov(3, 0.95)
    s_lo, lo = _finance_gov(3, 0.05)
    for _ in range(60):
        conditions_lifecycle(s_hi)
        conditions_lifecycle(s_lo)
    assert s_hi.conditions.growth > s_lo.conditions.growth, \
        "a strong Finance minister failed to out-grow a weak one"
    assert hi.perf > lo.perf and hi.portfolio_weeks == 60, \
        "performance record didn't accumulate tenure"

    # performance sacking: a bad record past tenure is fired and refilled same-week
    s2 = new_game(7)
    pid2 = next(iter(s2.parties))
    s2.government.parties = {pid2}
    bad = next(m for m in s2.mps.values() if m.party == pid2 and m != s2.government.pm)
    bad.portfolio, bad.perf, bad.portfolio_weeks = "Interior", p.MINISTER_SACK_RECORD - 0.01, p.MINISTER_TENURE
    ministerial_lifecycle(s2)
    sack = [e for e in s2.log if e.type == "MinisterSacked"]
    refill = [e for e in s2.log if e.type == "Promoted" and e.data.get("reason") == "reshuffle"]
    holder = [m for m in s2.mps.values() if m.portfolio == "Interior"]
    assert sack and sack[-1].data["reason"] == "performance" and sack[-1].data["mp"] == bad.id
    assert bad.portfolio is None, "a sacked minister kept the portfolio"
    assert holder and holder[0] is not bad, "vacated ministry not refilled by someone else"
    assert holder[0].perf == 0.0 and holder[0].portfolio_weeks == 0, \
        "the replacement inherited the predecessor's record"
    assert refill, "reshuffle appointment didn't carry reason='reshuffle'"

    # a minister below the record keeps the job; tenure gate protects new appointees
    ok_mp = next(m for m in s2.mps.values() if m.party == pid2 and m != s2.government.pm
                 and m.portfolio is None)
    ok_mp.portfolio, ok_mp.perf, ok_mp.portfolio_weeks = "Health", 0.0, p.MINISTER_TENURE + 50
    ministerial_lifecycle(s2)
    assert ok_mp.portfolio == "Health", "a clean record was sacked"

    # defector sweep: a portfolio belongs to a government, not the person
    bad2 = next(m for m in s2.mps.values() if m.party == pid2 and m != s2.government.pm
                and m.portfolio is None)
    bad2.portfolio = "Labour"
    bad2.party = max(s2.parties)  # an opposition party takes the defector
    ministerial_lifecycle(s2)
    assert bad2.portfolio is None, "a defector kept a government portfolio"

    # long run: performance sackings actually occur, scandal sacks stay distinct
    perf_sacks = scandal_sacks = reshuffles = 0
    for seed in range(4):
        s = new_game(seed)
        for _ in range(300):
            if s.phase == "over":
                break
            tick(s, _policy(s))
        for e in s.log:
            if e.type == "MinisterSacked":
                assert e.data.get("reason") in ("performance", "scandal"), \
                    f"MinisterSacked missing reason: {e.data}"
                perf_sacks += e.data["reason"] == "performance"
                scandal_sacks += e.data["reason"] == "scandal"
            elif e.type == "Promoted":
                reshuffles += e.data.get("reason") == "reshuffle"
    assert perf_sacks > 0, "no performance sacking fired in four seeds"
    assert reshuffles >= perf_sacks, "a sack didn't produce a same-week refill"
    print(f"ministerial ok: competence diverges, sacks={perf_sacks} refills={reshuffles} "
          f"scandal_sacks={scandal_sacks}")


if __name__ == "__main__":
    main()
