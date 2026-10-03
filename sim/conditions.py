"""Country conditions: indicators, shocks, the law registry's weekly effects."""
from __future__ import annotations

import numpy as np

from . import params as p
from .state import Bill, Conditions, GameState, Law

_FIELDS = ("growth", "unemployment", "inflation", "services", "crime")
_BOUNDS = {"growth": (-1.0, 1.0), "unemployment": (0.0, 1.0), "inflation": (0.0, 1.0),
           "services": (0.0, 1.0), "crime": (0.0, 1.0)}
_SHOCKS = [  # (indicator, direction, event variant name)
    ("growth", -1, "Recession"),
    ("growth", 1, "Boom"),
    ("inflation", 1, "InflationSpike"),
    ("crime", 1, "CrimeWave"),
]


def mood(c: Conditions) -> float:
    """The number voters feel: deviations from normal, weighted, in -1..1."""
    w, b = p.MOOD_W, p.COND_BASE
    m = (w["growth"] * (c.growth - b["growth"])
         + w["services"] * (c.services - b["services"])
         - w["unemployment"] * (c.unemployment - b["unemployment"])
         - w["inflation"] * (c.inflation - b["inflation"])
         - w["crime"] * (c.crime - b["crime"]))
    return float(np.clip(m, -1, 1))


def responsibility(state: GameState, pid: int) -> float:
    """A party's share of credit/blame for conditions — clarity of responsibility."""
    gov = state.government.parties
    if not gov or pid not in gov:
        return 0.0
    pm = state.government.pm
    if pm in state.mps and state.mps[pm].party == pid:
        return p.RETRO_PM_SHARE
    n = len(gov) - 1
    return (1 - p.RETRO_PM_SHARE) / n if n > 0 else 0.0


def law_effect(bill: Bill) -> dict[str, float]:
    """A law's weekly indicator push — legible quadrant map, magnitude ∝ extremity."""
    s = p.LAW_EFFECT_SCALE
    if bill.beneficiary_axis == 0:
        return {"growth" if bill.pos[0] > 0 else "services": s * abs(bill.pos[0])}
    return {"crime": -s * abs(bill.pos[1]) if bill.pos[1] > 0 else s * abs(bill.pos[1])}


def enact(state: GameState, bill: Bill, yes: int, no: int) -> Law:
    """Register a passed bill as a law in force."""
    law = Law(name=f"Week-{state.week} Act", pos=bill.pos,
              beneficiary_axis=bill.beneficiary_axis, cost=bill.cost,
              passed_week=state.week, margin=yes / max(yes + no, 1),
              effect=law_effect(bill))
    state.laws.append(law)
    eff = next(iter(law.effect.items()))
    state.emit("LawEnacted", f"{law.name} becomes law — {eff[0]} {'+' if eff[1] > 0 else '-'}"
                             f"{abs(eff[1]):.3f}/wk.", law=law.name, indicator=eff[0],
               weekly=eff[1])
    return law


def conditions_lifecycle(state: GameState) -> None:
    """Weekly: mean-revert, couple, apply laws in force, roll for shocks."""
    c, rng = state.conditions, state.rng
    for f in _FIELDS:
        lo, hi = _BOUNDS[f]
        v = getattr(c, f) + p.COND_REVERT * (p.COND_BASE[f] - getattr(c, f)) \
            + rng.gauss(0, p.COND_NOISE_SD)
        setattr(c, f, float(np.clip(v, lo, hi)))
    # couplings: the economy is a small causal web, not five independent dials
    c.unemployment = float(np.clip(c.unemployment - p.COUPLE_GROWTH_UE * c.growth, 0, 1))
    c.crime = float(np.clip(c.crime + p.COUPLE_UE_CRIME * (c.unemployment - p.COND_BASE["unemployment"])
                            - p.COUPLE_SVC_CRIME * (c.services - p.COND_BASE["services"]), 0, 1))
    # laws in force keep pushing while they stand
    for law in state.laws:
        for ind, dv in law.effect.items():
            lo, hi = _BOUNDS[ind]
            setattr(c, ind, float(np.clip(getattr(c, ind) + dv, lo, hi)))
    # shocks: rare, seeded, legible
    if rng.random() < p.SHOCK_P:
        ind, direction, variant = _SHOCKS[rng.randrange(len(_SHOCKS))]
        mag = rng.uniform(*p.SHOCK_MAG)
        lo, hi = _BOUNDS[ind]
        setattr(c, ind, float(np.clip(getattr(c, ind) + direction * mag, lo, hi)))
        state.emit("Shock", f"{variant.replace('_', ' ')} — {ind} {direction * mag:+.2f}.",
                   variant=variant, indicator=ind, delta=direction * mag,
                   big=mag >= p.SHOCK_INTERRUPT)
