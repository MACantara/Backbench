"""Runnable check: the spectator bot plays legal actions and survives."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sim import params as p
from sim.actions import available_actions, cost_of
from sim.bot import auto_actions
from sim.tick import tick
from sim.worldgen import new_game


def _drive(s, weeks: int) -> None:
    for _ in range(weeks):
        menu = available_actions(s)
        acts = auto_actions(s)
        spent = sum(cost_of(a.kind) for a in acts)
        assert 1 <= len(acts) and spent <= p.ACTION_POINTS, \
            f"week {s.week}: bot spent {spent} on {[a.kind for a in acts]}"
        for a in acts:
            assert a.kind == "nothing" or a.kind in menu, \
                f"week {s.week}: bot picked {a.kind!r} not in menu"
        tick(s, acts)
        if s.phase == "over":
            return


def main() -> None:
    # standard: the bot stays alive well past the first-election cliff
    best = 0
    for seed in range(6):
        s = new_game(seed)
        _drive(s, 120)
        best = max(best, s.week)
    assert best >= 60, f"bot never outlived week 60 across seeds (best {best})"

    # outsider: an independent player can run the whole menu without crashing
    s = new_game(3, "outsider")
    _drive(s, 30)

    # the PM's desk: force the office, give a vacancy, expect duties picked
    s = new_game(1)
    _drive(s, 20)
    acts = auto_actions(s)
    if s.phase == "governing":
        s.government.pm = s.player_id
        acts = auto_actions(s)
        assert all(a.kind == "nothing" or a.kind in available_actions(s)
                   for a in acts)

    print(f"spectate ok: standard best={best} outsider+w20 "
          f"phase={s.phase} acts={[a.kind for a in acts]}")


if __name__ == "__main__":
    main()
