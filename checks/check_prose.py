"""Runnable check: prose varies, echo tiers mark correctly, and the cosmetic
stream never touches the mechanical one."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from sim.actions import Action, available_actions
from sim.prose import POOLS
from sim.tick import tick
from sim.worldgen import new_game


def scripted(state):
    menu = available_actions(state)
    out = []
    for want in ("constituency", "campaign", "speech", "lobby"):
        if want in menu and len(out) < 2:
            out.append(Action(want, axis=0) if want == "speech" else Action(want))
    return out


def data_stream(s, weeks):
    """tick and keep (type, data) — everything but the cosmetic text."""
    out = []
    for _ in range(weeks):
        out.extend((e.type, repr(sorted(e.data.items())))
                   for e in tick(s, scripted(s)))
        if s.phase == "over":
            break
    return out


def main() -> None:
    s = new_game(0)
    assert s.country and s.name_pack          # dateline + flavor drawn at worldgen
    texts, echoes = {}, []
    run = data_stream(s, 120)
    for e in s.log:
        if e.type in POOLS:
            texts.setdefault(e.type, set()).add(e.text)
        if e.text.startswith("You"):
            assert e.data.get("echo"), f"unmarked echo: {e.text}"
        elif e.data.get("echo"):
            echoes.append(e)
    assert not echoes, f"echo flag on a world event: {echoes[0].text}"
    pooled = [k for k, v in texts.items() if len(POOLS[k]) > 1]
    assert any(len(texts[k]) > 1 for k in pooled), \
        "no template variety landed in 120 weeks"

    # the stream proof: corrupt prose_rng, and the politics don't notice
    a, b = new_game(1), new_game(1)
    b.prose_rng = random.Random(999)          # different wording draws
    da, db = data_stream(a, 60), data_stream(b, 60)
    assert da == db, "prose stream leaked into mechanical outcomes"
    assert a.rng.getstate() == b.rng.getstate()
    assert np.array_equal(a.voters.pos, b.voters.pos)
    ta = [e.text for e in a.log if e.type in POOLS]
    tb = [e.text for e in b.log if e.type in POOLS]
    assert ta != tb, "prose_rng made no difference — pools not wired"

    print("prose check OK")


if __name__ == "__main__":
    main()
