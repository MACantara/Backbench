"""Tuning gate: 50 seeded runs — the long-run health table from the roadmap.

Each row watches one feedback channel; the bands assert medians across seeds,
not per-seed values — a hegemonic seed is honest variance, a dead channel is not.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from sim import params as p
from sim.conditions import _BOUNDS
from sim.tick import tick
from sim.worldgen import new_game

_WEEKS = 200
_PIN_EPS = 0.02   # an indicator within this of a bound counts as pinned


def run_seed(seed: int) -> dict:
    """One passive-player run; collect every invariant's tallies."""
    s = new_game(seed)
    spans, formed_week = [], None
    enps, top_shares, prev_top, turnover = [], [], None, 0
    counts = {t: 0 for t in ("ConfidenceLost", "PartyFormed", "PartyDissolved",
                             "Secession", "Promoted", "Retired", "MinisterSacked",
                             "LawStruck", "DebtCrisis")}
    pin_slots = debt_max = 0
    debts, weeks_run = [], 0
    for _ in range(_WEEKS):
        for e in tick(s):
            if e.type == "CoalitionFormed":
                formed_week = s.week
            elif e.type in ("ConfidenceLost", "ElectionCalled") and formed_week is not None:
                spans.append(s.week - formed_week)
                formed_week = None
            if e.type in counts:
                counts[e.type] += 1
            elif e.type == "ElectionResult":
                seats = e.data["seats"]
                total = sum(seats.values())
                enps.append(1 / sum((n / total) ** 2 for n in seats.values()))
                top = max(seats, key=seats.get)
                top_shares.append(seats[top] / total)
                turnover += prev_top is not None and top != prev_top
                prev_top = top
        weeks_run += 1
        c = s.conditions
        for f in ("growth", "unemployment", "inflation", "services", "crime"):
            lo, hi = _BOUNDS[f]
            pin_slots += getattr(c, f) <= lo + _PIN_EPS or getattr(c, f) >= hi - _PIN_EPS
        debt_max = max(debt_max, s.treasury.debt)
        debts.append(s.treasury.debt)
        if s.phase == "over":
            break
    if formed_week is not None:      # a government seated at the horizon still counts
        spans.append(weeks_run - formed_week)
    return {"spans": spans, "enps": enps, "top_shares": top_shares,
            "turnover": turnover, "counts": counts,
            "pin_rate": pin_slots / max(weeks_run * 5, 1), "debt_max": debt_max,
            "debt_med": float(np.median(debts)), "laws_end": len(s.laws),
            "juniors": sum(1 for m in s.mps.values() if m.junior),
            "parties_end": len(s.parties), "week": s.week}


def _med(xs) -> float:
    return float(np.median(xs)) if len(xs) else 0.0


def main() -> None:
    runs = [run_seed(seed) for seed in range(50)]
    spans = [x for r in runs for x in r["spans"]]
    med = _med(spans)

    # --- the invariant table ---
    enp = _med([x for r in runs for x in r["enps"]])
    top = _med([x for r in runs for x in r["top_shares"]])
    turnovers = _med([r["turnover"] for r in runs])
    conf = sum(r["counts"]["ConfidenceLost"] for r in runs)
    formed = sum(r["counts"]["PartyFormed"] for r in runs)
    dissolved = sum(r["counts"]["PartyDissolved"] for r in runs)
    secessions = sum(r["counts"]["Secession"] for r in runs)
    pin = _med([r["pin_rate"] for r in runs])
    debt_med = _med([r["debt_med"] for r in runs])
    debt_max = max(r["debt_max"] for r in runs)
    laws = _med([r["laws_end"] for r in runs])
    parties = _med([r["parties_end"] for r in runs])
    promoted = sum(r["counts"]["Promoted"] for r in runs)
    sacked = sum(r["counts"]["MinisterSacked"] for r in runs)
    retired = sum(r["counts"]["Retired"] for r in runs)
    crises = sum(r["counts"]["DebtCrisis"] for r in runs)
    player = _med([r["week"] for r in runs])

    print(f"{'area':<13} {'metric':<38} value")
    print(f"{'party system':<13} median ENP / parties at end / formed-dissolved"
          f"{'':<4} {enp:.2f} / {parties:.0f} / {formed}-{dissolved} (+{secessions} sec)")
    print(f"{'elections':<13} median largest share / median turnovers"
          f"{'':<13} {top:.2f} / {turnovers:.0f}")
    print(f"{'government':<13} survival med-mean-p10 / confidence defeats"
          f"{'':<5} {med:.0f}-{np.mean(spans):.0f}-{np.percentile(spans,10):.0f} / {conf}")
    print(f"{'economy':<13} median pin-rate / debt med / debt max"
          f"{'':<14} {pin:.2f} / {debt_med:.2f} / {debt_max:.1f}")
    print(f"{'legislation':<13} median laws in force / struck"
          f"{'':<19} {laws:.0f} / {sum(r['counts']['LawStruck'] for r in runs)}")
    juniors = _med([r["juniors"] for r in runs])
    print(f"{'careers':<13} promoted / sacked / retired / bench posts"
          f"{'':<11} {promoted} / {sacked} / {retired} / {juniors:.0f}")
    print(f"{'player':<13} median week reached (passive)"
          f"{'':<19} {player:.0f}")
    print(f"{'':<13} debt crises total{'':<41} {crises}")

    # --- bands: medians across seeds, loose enough for honest variance ---
    assert 10 <= med <= 40, f"median survival {med:.0f} out of band"
    assert np.std(spans) > 2, "no variance — governments are all identical"
    assert enp >= 1.8, f"seat-ENP median {enp:.2f} — duopoly lock-in"
    assert top < 0.9, f"median largest share {top:.2f} — permanent landslide"
    assert formed > 0, "party births died — dynamism channels silent"
    assert pin < 0.5, f"indicators pinned {pin:.0%} of the time — saturation"
    assert debt_max < 50, f"debt ran to {debt_max:.0f} — the spiral has no exit"
    assert laws < 500, f"median {laws:.0f} laws in force — the registry ratchets"
    assert promoted > 0 and retired > 0, "career churn died"
    assert juniors > 0, "the bench went unstaffed — junior rungs died"
    assert crises > 0 or debt_max < p.DEBT_CRISIS + 0.5, \
        "insolvency went silent again"
    print("sweep ok")


if __name__ == "__main__":
    main()
