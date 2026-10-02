"""Tuning gate: 50 seeded runs — governments should survive a meaningful, varied span."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from sim.tick import tick
from sim.worldgen import new_game


def survival_spans(seed: int) -> list[int]:
    """Weeks each government survived (formation → collapse or election)."""
    s = new_game(seed)
    spans, formed_week = [], None
    for _ in range(200):
        for e in tick(s):
            if e.type == "CoalitionFormed":
                formed_week = s.week
            elif e.type in ("ConfidenceLost", "ElectionCalled") and formed_week is not None:
                spans.append(s.week - formed_week)
                formed_week = None
        if s.phase == "over":
            break
    return spans


def main() -> None:
    spans = [x for seed in range(50) for x in survival_spans(seed)]
    med = float(np.median(spans))
    print(f"50 runs, {len(spans)} governments: median {med:.0f} weeks, "
          f"mean {np.mean(spans):.0f}, p10={np.percentile(spans,10):.0f}, p90={np.percentile(spans,90):.0f}")
    assert 10 <= med <= 40, f"median survival {med:.0f} out of band"
    assert np.std(spans) > 2, "no variance — governments are all identical"
    print("sweep ok")


if __name__ == "__main__":
    main()
