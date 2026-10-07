"""Player-bot: the spectated career is a real playtest.

The M8 contract — the bot declares an ambition, spends the same point
budget a player gets, exercises the toolkit, and leaves a trace that
turns a dead run into tuning data. Prints a box score per seed:
weeks, peak office, ambition verdict, cause of death, score, and
which rules fired.
"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from sim import params as p
from sim.actions import available_actions
from sim.bot import auto_actions, bot_pick_ambition
from sim.career import final_score
from sim.parties import _stay_utility
from sim.state import Ambition
from sim.tick import tick
from sim.worldgen import new_game

CAP = 400          # a long-run ceiling — "alive" is a legal outcome
SEEDS = (0, 3, 7, 11, 19, 23, 29, 37)
_RANK = ("backbencher", "junior post", "party leader", "minister", "PM")
CORE = {"vote", "lobby", "speech", "constituency", "campaign"}
OPS = ("attack", "media", "dig_dirt", "leak", "promise", "table",
       "platform", "challenge", "defect", "found", "decline_offers")


def _rank(state, pl) -> int:
    if state.government.pm == pl.id:
        return 4
    if pl.portfolio is not None:
        return 3
    pt = state.parties.get(pl.party)
    if pt is not None and pt.leader == pl.id:
        return 2
    return 1 if pl.junior is not None else 0


def _run(seed: int, trace: list | None = None):
    """One spectated career; asserts the invariants on the way through."""
    state = new_game(seed)
    state.ambition = Ambition(bot_pick_ambition(state))
    assert state.ambition.kind is not None
    peak, fired = 0, Counter()
    while state.phase != "over" and state.week < CAP:
        acts = auto_actions(state, trace)
        spent = sum(p.ACTION_COST.get(a.kind, 1) for a in acts)
        assert spent <= p.ACTION_POINTS, (seed, spent,
                                          [a.kind for a in acts])
        assert all(a.kind in available_actions(state)
                   for a in acts), (seed, [a.kind for a in acts])
        tick(state, acts)
        pl = state.mps.get(state.player_id)
        if pl is not None:
            peak = max(peak, _rank(state, pl))
    if trace is not None:
        for t in trace:
            fired[t["kind"]] += 1
    cause = "alive"
    for e in reversed(state.log):
        if e.type in ("SeatLost", "Expelled"):
            cause = e.text
            break
    amb = state.ambition
    verdict = "met" if amb.met else ("failed" if amb.failed else "open")
    return state, peak, verdict, cause, fired


def _force_state() -> object:
    """A governing week on demand — the base for the conditional probes."""
    state = new_game(7)
    state.ambition = Ambition("survivor")
    while state.phase != "governing":
        tick(state, auto_actions(state))
    return state


def main() -> None:
    # conditional rules fire when their gate is forced open:
    # — a poisoned home and a sinking seat means crossing the floor
    state = _force_state()
    pl = state.mps[state.player_id]
    pt = state.parties[pl.party]
    pt.platform = tuple(np.clip(np.asarray(pl.pos) * -1, -1, 1))
    pt.cohesion = 0.05
    pl.seat_safety = 0.05
    tr: list = []
    auto_actions(state, tr)
    defect = [t for t in tr if t["kind"] == "defect"]
    assert defect, [t for t in tr]
    assert _stay_utility(state, pl) < p.BOT_STAY_UTILITY

    # — a crashing government earns the scrutiny swing
    state = _force_state()
    pl = state.mps[state.player_id]
    if pl.party in state.government.parties:
        # sit the player in opposition instead of rewriting the world
        state.government.parties = [i for i in state.parties
                                    if i != pl.party][:1]
    state.conditions.growth = -1.0
    state.conditions.unemployment = 1.0
    for m in state.mps.values():
        m.perf = -1.0
    tr = []
    auto_actions(state, tr)
    assert any(t["kind"] == "attack" for t in tr), [t for t in tr]

    # determinism: same seed, same trace
    t1, t2 = [], []
    _run(11, t1)
    _run(11, t2)
    assert t1 == t2, "identical seed must replay the bot's week"

    # the box score — every dead run is a row of tuning data
    print(f"{'seed':>4} {'ambition':<9} {'weeks':>5} {'peak':<12} "
          f"{'verdict':<7} {'score':>5}  death")
    all_fired = Counter()
    for seed in SEEDS:
        tr = []
        state, peak, verdict, cause, fired = _run(seed, tr)
        all_fired.update(fired)
        print(f"{seed:>4} {state.ambition.kind:<9} {state.week:>5} "
              f"{_RANK[peak]:<12} {verdict:<7} {final_score(state):>5}  "
              f"{cause[:60]}")
    assert CORE <= set(all_fired), sorted(CORE - set(all_fired))
    print("\ntoolkit coverage:",
          ", ".join(f"{k} {all_fired.get(k, 0)}" for k in OPS))
    cold = [k for k in OPS if all_fired.get(k, 0) == 0]
    if cold:
        print("never fired:", ", ".join(cold), "— a dead rule or a "
              "dead feature; check the gates")
    print("check_bot ok")


if __name__ == "__main__":
    main()
