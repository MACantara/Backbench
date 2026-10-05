"""The treasury: one stock (debt), derived flows, insolvency crises."""
from __future__ import annotations

import numpy as np

from . import params as p
from .state import GameState


def revenue(state: GameState) -> float:
    """Weekly intake — the country pays what it earns, times the tax posture."""
    c = state.conditions
    return (p.REV_BASE + p.REV_GROWTH_W * c.growth - p.REV_UE_W * c.unemployment) \
        * state.treasury.posture[0]


def upkeep(state: GameState) -> float:
    """Weekly cost of every law still in force, times the spend posture."""
    return sum(law.cost for law in state.laws) * state.treasury.posture[1]


def budget_posture(state: GameState) -> tuple[float, float]:
    """The (tax, spend) a government would propose: agenda-ward on the econ
    axis, tightened by debt pressure whatever the ideology."""
    from .state import gov_platform
    x = gov_platform(state)[0]  # + market / - redistribution
    spend = 1.0 - p.BUDGET_AXIS_W * x - p.BUDGET_DEBT_TIGHT * debt_pressure(state)
    tax = 1.0 - 0.5 * p.BUDGET_AXIS_W * x
    return float(np.clip(tax, 0.7, 1.3)), float(np.clip(spend, 0.7, 1.3))


def interest(state: GameState) -> float:
    return state.treasury.debt * p.DEBT_INTEREST


def flow(state: GameState) -> float:
    """Weekly surplus (positive) or deficit (negative)."""
    return revenue(state) - upkeep(state) - interest(state)


def debt_pressure(state: GameState) -> float:
    """0 while the books are fine → 1 at DEBT_WARN — feeds the fiscal vote term."""
    return min(1.0, state.treasury.debt / p.DEBT_WARN)


def treasury_lifecycle(state: GameState) -> None:
    """Weekly: accumulate the deficit, drag inflation, fire insolvency crises."""
    t = state.treasury
    for law in state.laws:  # programs normalize into baseline spending
        law.cost *= p.LAW_COST_DECAY
    t.debt = max(0.0, t.debt - flow(state))
    c = state.conditions
    if t.debt > p.DEBT_WARN:
        c.inflation = float(np.clip(
            c.inflation + p.DEBT_INFLATION_W * (t.debt - p.DEBT_WARN), 0, 1))
    # insolvency is a state, not an event: while past CRISIS the crisis re-fires
    # on a cooldown — each repeat demands confidence again. Solvency is the exit:
    # a real recovery re-arms the meter so relapse fires promptly, not late.
    if t.debt < p.DEBT_WARN:
        t.last_crisis_week = -10**9
    if (t.debt > p.DEBT_CRISIS and state.phase == "governing"
            and state.week - t.last_crisis_week >= p.DEBT_CRISIS_EVERY):
        t.last_crisis_week, t.crises = state.week, t.crises + 1
        pm_party = state.mps[state.government.pm].party \
            if state.government.pm in state.mps else None
        for i in state.government.parties:
            if i in state.parties:
                state.parties[i].brand -= p.DEBT_BRAND_HIT
        # stamp the party now — the confidence vote below may clear government state
        ordinal = {1: "Insolvency", 2: "Second insolvency",
                   3: "Third insolvency"}.get(t.crises, f"Insolvency no. {t.crises}")
        state.emit("DebtCrisis", f"{ordinal} — the treasury is {t.debt:.1f} in debt "
                                 f"and confidence is demanded.",
                   debt=t.debt, party=pm_party, crises=t.crises)
        # deferred import: government→parliament→treasury is a cycle at module level
        from .government import confidence_vote
        confidence_vote(state)
