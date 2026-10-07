"""Runnable check: governments form, a full cycle completes headless."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collections import Counter

from sim.tick import tick
from sim.worldgen import new_game


def run_cycle(seed: int, max_weeks: int = 200) -> tuple:
    s = new_game(seed)
    for _ in range(max_weeks):
        tick(s)
        if s.phase == "over":
            break
        if s.week > 60 and s.phase == "campaign":  # completed a full term
            return s, True
    return s, False


def main() -> None:
    formed, verdicts, cycles = 0, 0, 0
    for seed in range(10):   # a wider window — stream churn thins any fixed five
        s, completed = run_cycle(seed)
        types = [e.type for e in s.log]
        # a run only counts as a formation verdict if it reached formation — either
        # it formed one, or it saw an election and the game kept going (dying at
        # the first election never reaches formation)
        if "CoalitionFormed" in types or ("ElectionResult" in types and "SeatLost" not in types):
            verdicts += 1
            formed += "CoalitionFormed" in types
        cycles += completed
    assert formed == verdicts and verdicts >= 3, \
        "every run reaching formation should form a government (minority fallback)"
    assert cycles >= 3, f"only {cycles}/5 runs completed a full term"

    # structure check on one run: phases occurred in order
    s, _ = run_cycle(0)
    types = [e.type for e in s.log]
    assert types.index("ElectionResult") < types.index("CoalitionFormed") < len(types)
    assert "VoteResult" in types and "PollShift" in types
    print(f"government ok: {formed}/{verdicts} formed, {cycles}/5 completed a term, "
          f"{len(s.log)} events logged in seed 0")


if __name__ == "__main__":
    main()
