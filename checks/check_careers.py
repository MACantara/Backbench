"""Runnable check: MP lifecycle — retirements, vacancies, the hopeful pipeline."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sim.params as p
from sim.tick import tick
from sim.worldgen import new_game


def main() -> None:
    retired = promoted = newcomer = eligible = 0
    for seed in range(10):
        s = new_game(seed)
        for _ in range(300):
            tick(s, [])
            if s.phase == "over":
                break

        retired += sum(e.type == "Retired" for e in s.log)
        promoted += sum(e.type == "Promoted" for e in s.log)
        newcomer += sum(e.type == "Newcomer" for e in s.log)
        eligible += sum(h.age >= p.MIN_MP_AGE for h in s.hopefuls)

        # structural invariants
        assert 90 <= len(s.mps) <= 120, f"seed {seed}: parliament size {len(s.mps)}"
        assert len({m.district for m in s.mps.values()}) == len(s.mps), \
            f"seed {seed}: two MPs share a district"
        for m in s.mps.values():
            assert m.party is None or m.id in s.parties[m.party].members, \
                f"seed {seed}: orphan MP {m.id}"
        for pt in s.parties.values():
            assert pt.members <= set(s.mps), f"seed {seed}: ghost member in {pt.name}"
            if pt.leader is not None:
                assert pt.leader in s.mps, f"seed {seed}: dead leader in {pt.name}"
        if s.phase != "over":
            assert s.player_id in s.mps, f"seed {seed}: player vanished"

    assert retired >= 10, f"only {retired} retirements across 10 seeds"
    assert promoted >= 10, f"only {promoted} promotions across 10 seeds"
    assert newcomer >= 3, f"only {newcomer} newcomers across 10 seeds"
    assert eligible >= 20, f"only {eligible} hopefuls crossed eligibility"
    print(f"careers ok: retired={retired} promoted={promoted} newcomer={newcomer} "
          f"eligible={eligible}")


if __name__ == "__main__":
    main()
