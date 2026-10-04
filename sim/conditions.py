"""Country conditions: indicators, shocks, the law registry's weekly effects."""
from __future__ import annotations

import numpy as np

from . import params as p
from .state import Bill, Conditions, GameState, Law

_FIELDS = ("growth", "unemployment", "inflation", "services", "crime")
_BOUNDS = {"growth": (-1.0, 1.0), "unemployment": (0.0, 1.0), "inflation": (0.0, 1.0),
           "services": (0.0, 1.0), "crime": (0.0, 1.0)}
_GOOD_DIR = {"growth": 1, "services": 1, "unemployment": -1, "inflation": -1, "crime": -1}
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
    if len(gov) == 1:
        return p.RETRO_PM_SHARE  # a lone party bears it even after the PM falls
    n = len(gov) - 1
    return (1 - p.RETRO_PM_SHARE) / n if n > 0 else 0.0


def law_effect(bill: Bill) -> dict[str, float]:
    """A law's weekly indicator push — legible quadrant map, magnitude ∝ extremity."""
    s, ax = p.LAW_EFFECT_SCALE, bill.beneficiary_axis
    if bill.pos[ax] == 0:
        return {}
    if ax == 0:
        return {"growth" if bill.pos[0] > 0 else "services": s * abs(bill.pos[0])}
    return {"crime": -s * bill.pos[1]}


def enact(state: GameState, bill: Bill, yes: int, no: int) -> Law:
    """Register a passed bill as a law in force."""
    law = Law(name=bill.name or f"Week-{state.week} Act", pos=bill.pos,
              beneficiary_axis=bill.beneficiary_axis, cost=bill.cost,
              passed_week=state.week, margin=yes / max(yes + no, 1),
              effect=law_effect(bill))
    state.laws.append(law)
    eff = f" — {next(iter(law.effect))} {next(iter(law.effect.values())):+.3f}/wk" \
        if law.effect else ""
    state.emit("LawEnacted", f"{law.name} becomes law{eff} (cost {law.cost:.3f}/wk).",
               law=law.name, cost=law.cost)
    return law


def _ministers(state: GameState):
    """Government MPs holding a portfolio — the push gate is office, not the label."""
    gov = state.government.parties
    return [mp for mp in state.mps.values()
            if mp.portfolio is not None and mp.party in gov]


def conditions_lifecycle(state: GameState) -> None:
    """Weekly: mean-revert, couple, apply laws in force, ministerial push, shocks."""
    c, rng = state.conditions, state.rng
    before = {f: getattr(c, f) for f in _FIELDS}
    for f in _FIELDS:
        lo, hi = _BOUNDS[f]
        v = getattr(c, f) + p.COND_REVERT * (p.COND_BASE[f] - getattr(c, f)) \
            + rng.gauss(0, p.COND_NOISE_SD)
        setattr(c, f, float(np.clip(v, lo, hi)))
    # couplings: the economy is a small causal web, not five independent dials
    c.unemployment = float(np.clip(c.unemployment - p.COUPLE_GROWTH_UE * c.growth, 0, 1))
    c.crime = float(np.clip(c.crime + p.COUPLE_UE_CRIME * (c.unemployment - p.COND_BASE["unemployment"])
                            - p.COUPLE_SVC_CRIME * (c.services - p.COND_BASE["services"]), 0, 1))
    # laws in force keep pushing while they stand — diminishing returns near the
    # bound, so a long legislative record saturates an indicator, not pins it
    for law in state.laws:
        for ind, dv in law.effect.items():
            lo, hi = _BOUNDS[ind]
            v = getattr(c, ind)
            v += dv * (hi - v) if dv > 0 else dv * (v - lo)
            setattr(c, ind, float(np.clip(v, lo, hi)))
    # ministers push their own dial — continuous pressure, bound-scaled like laws
    ministers = _ministers(state)
    for mp in ministers:
        ind = p.PORTFOLIO_INDICATOR.get(mp.portfolio)
        if ind is None:
            continue
        lo, hi = _BOUNDS[ind]
        v = getattr(c, ind)
        dv = (mp.competence - 0.5) * p.PORTFOLIO_EFFECT * _GOOD_DIR[ind]
        v += dv * (hi - v) if dv > 0 else dv * (v - lo)
        setattr(c, ind, float(np.clip(v, lo, hi)))
    # shocks: rare, seeded, legible
    if rng.random() < p.SHOCK_P:
        ind, direction, variant = _SHOCKS[rng.randrange(len(_SHOCKS))]
        mag = rng.uniform(*p.SHOCK_MAG)
        lo, hi = _BOUNDS[ind]
        setattr(c, ind, float(np.clip(getattr(c, ind) + direction * mag, lo, hi)))
        state.emit("Shock", f"{variant.replace('_', ' ')} — {ind} {direction * mag:+.2f}.",
                   variant=variant, indicator=ind, delta=direction * mag,
                   good=variant == "Boom", big=mag >= p.SHOCK_INTERRUPT)
    # the record: what their indicator did on their watch, decayed — recency rules
    for mp in ministers:
        ind = p.PORTFOLIO_INDICATOR.get(mp.portfolio)
        if ind is not None:
            mp.perf = mp.perf * p.PERF_DECAY + _GOOD_DIR[ind] * (getattr(c, ind) - before[ind])
        mp.portfolio_weeks += 1
