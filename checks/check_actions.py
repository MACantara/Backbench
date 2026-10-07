"""Action legibility: the economy holds, previews explain, feedback counts.

The M7 contract — no pick is a mystery: the cost table is total over the
menu, explain_action answers every kind (with and without context),
numeric actions emit digits, and the bot never outspends the week.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sim import params as p
from sim.actions import (Action, available_actions, apply_action,
                         cost_of)
from sim.bot import auto_actions
from sim.inspect import ACTION_INFO, explain_action
from sim.tick import tick
from sim.worldgen import new_game


def main() -> None:
    # the cost table covers the vocabulary — every kind has a price
    for kind in ACTION_INFO:
        assert cost_of(kind) >= 0, kind
    assert cost_of("nothing") == 0
    assert cost_of("vote") == 0          # duties are free
    assert cost_of("unlisted-kind") == 1  # the default is a morning's work

    # previews exist for every kind the menu can produce — all phases,
    # with and without a target
    for seed in (0, 7, 21):
        state = new_game(seed)
        for _ in range(60):
            if state.player_id not in state.mps or state.phase == "over":
                break
            tick(state, auto_actions(state))
        if state.player_id not in state.mps:
            continue
        me = state.mps[state.player_id]
        other = next((m.id for m in state.mps.values() if m.id != me.id),
                     None)
        outlet = state.outlets[0].id if state.outlets else None
        for kind in available_actions(state):
            for tgt in (None, other):
                line = explain_action(state, kind, target=tgt,
                                      outlet=outlet)
                assert isinstance(line, str) and line.strip(), \
                    (kind, tgt, seed)
        # every kind has a blurb — the fallback can't be a bare name
        for kind in available_actions(state):
            assert ACTION_INFO.get(kind), kind

    # numeric feedback: actions that move numbers say the numbers
    state = new_game(3)
    base = len(state.log)
    for kind, act in (("constituency", Action("constituency")),
                      ("scheme", Action("scheme"))):
        apply_action(state, act)
    texts = [e.text for e in state.log[base:]
             if e.data.get("action") in ("constituency", "scheme")]
    assert any(any(ch.isdigit() for ch in t) for t in texts), texts
    assert all(len(t) > 30 for t in texts), texts  # a delta, not a bare verb

    # the bot lives inside the budget — a long run, every week
    for seed in (0, 5, 11):
        state = new_game(seed)
        for _ in range(80):
            if state.phase == "over":
                break
            acts = auto_actions(state)
            spent = sum(cost_of(a.kind) for a in acts)
            assert spent <= p.ACTION_POINTS, (seed, spent,
                                              [a.kind for a in acts])
            tick(state, acts)

    print("check_actions ok")


if __name__ == "__main__":
    main()
