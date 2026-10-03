"""Check: the treasury — revenue, upkeep, debt drag, insolvency crisis, fiscal votes."""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sim import params as p
from sim.parliament import vote_terms
from sim.state import Bill
from sim.tick import tick
from sim.treasury import (debt_pressure, flow, interest, revenue,
                          treasury_lifecycle, upkeep)
from sim.worldgen import new_game


def main() -> None:
    # revenue responds to conditions: boom pays more than bust on the same state
    s = new_game(1)
    rev_base = revenue(s)
    s.conditions.growth, s.conditions.unemployment = 0.8, 0.1
    rev_boom = revenue(s)
    s.conditions.growth, s.conditions.unemployment = -0.8, 0.9
    rev_bust = revenue(s)
    assert rev_boom > rev_base > rev_bust, "revenue doesn't track conditions"

    # upkeep counts laws in force; a costly enacted law raises it by its cost
    s = new_game(1)
    from sim.conditions import enact
    u0 = upkeep(s)
    law = enact(s, Bill(pos=(0.8, 0.0), beneficiary_axis=0, cost=0.05), yes=80, no=40)
    assert abs(upkeep(s) - u0 - 0.05) < 1e-9, "enacted law cost didn't hit upkeep"
    assert law.cost == 0.05

    # deficits accumulate debt; a surplus can't push it below zero
    s = new_game(1)
    s.treasury.debt = 0.0
    for law_ in list(s.laws):
        s.laws.remove(law_)
    for _ in range(10):
        treasury_lifecycle(s)
    assert s.treasury.debt == 0.0, "surplus should floor debt at 0, not create savings"
    s.treasury.debt = 0.5
    for _ in range(5):  # a heavy legislative program → real deficit
        enact(s, Bill(pos=(0.8, 0.0), beneficiary_axis=0, cost=0.05), yes=80, no=40)
    d0 = s.treasury.debt
    for _ in range(10):
        treasury_lifecycle(s)
    assert s.treasury.debt > d0, "deficit program didn't grow the debt"
    print(f"  flow under load: {flow(s):+.3f}/wk -> debt {d0:.2f}->{s.treasury.debt:.2f}")

    def _to_governing(seed):
        s_ = new_game(seed)
        for _ in range(400):
            if s_.phase == "governing" and s_.government.parties:
                return s_
            tick(s_)
        raise AssertionError("fixture never reached governing")

    # debt past WARN drags inflation; debt past CRISIS fires the crisis once
    s = _to_governing(7)
    snap = copy.deepcopy(s)
    snap.treasury.debt = p.DEBT_WARN + 0.5
    i0 = snap.conditions.inflation
    for _ in range(10):
        treasury_lifecycle(snap)
    assert snap.conditions.inflation > i0, "debt didn't drag inflation"

    s.treasury.debt = p.DEBT_CRISIS + 0.1
    brand0 = sum(state_.brand for state_ in
                 (s.parties[i] for i in s.government.parties if i in s.parties))
    treasury_lifecycle(s)
    crises = [e for e in s.log if e.type == "DebtCrisis"]
    assert crises, "insolvency didn't fire DebtCrisis"
    brand1 = sum(state_.brand for state_ in
                 (s.parties[i] for i in s.government.parties if i in s.parties))
    assert brand1 < brand0, "crisis didn't hit government brand"
    assert any(e.type == "ConfidenceLost" or e.type == "VoteResult"
               for e in s.log[-10:]), "crisis didn't force a confidence vote"
    n1 = len(crises)
    s.treasury.debt = p.DEBT_CRISIS + 0.5  # still insolvent — must NOT re-fire
    treasury_lifecycle(s)
    assert len([e for e in s.log if e.type == "DebtCrisis"]) == n1, \
        "crisis re-fired while still armed-down (hysteresis broken)"

    # fiscal term: a dear bill loses the house when the books are red
    s = _to_governing(7)
    dear = Bill(pos=(0.0, 0.0), beneficiary_axis=0, cost=0.010)
    cheap = Bill(pos=(0.0, 0.0), beneficiary_axis=0, cost=0.001)
    solvent, broke = copy.deepcopy(s), copy.deepcopy(s)
    solvent.treasury.debt = 0.0
    broke.treasury.debt = p.DEBT_WARN * 1.5
    assert debt_pressure(solvent) == 0.0 and debt_pressure(broke) == 1.0
    yes_solvent = sum(1 for m in solvent.mps.values()
                      if sum(vote_terms(solvent, m, dear).values()) > 0)
    yes_broke = sum(1 for m in broke.mps.values()
                    if sum(vote_terms(broke, m, dear).values()) > 0)
    yes_cheap = sum(1 for m in broke.mps.values()
                    if sum(vote_terms(broke, m, cheap).values()) > 0)
    assert yes_broke < yes_solvent, "debt didn't sting the expensive bill"
    assert yes_cheap > yes_broke, "stinginess should scale with bill cost"

    # the crisis is news
    s = _to_governing(7)
    base = len(s.log)
    s.treasury.debt = p.DEBT_CRISIS + 0.1
    from sim.media import media_lifecycle
    treasury_lifecycle(s)
    media_lifecycle(s, base)
    assert any(e.type == "Headline" and e.data.get("story") == "DebtCrisis"
               for e in s.log[base:]), "DebtCrisis didn't reach a headline"

    # determinism
    a, b = new_game(9), new_game(9)
    for _ in range(40):
        treasury_lifecycle(a)
        treasury_lifecycle(b)
    assert a.treasury.debt == b.treasury.debt, "debt trajectory diverged"

    print(f"treasury ok: rev {rev_bust:.3f}<{rev_base:.3f}<{rev_boom:.3f}, "
          f"fiscal {yes_solvent}->{yes_broke} yes votes under debt, crisis fires")


if __name__ == "__main__":
    main()
