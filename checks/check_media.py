"""Check: the media layer — outlets, coverage, caricature, agenda, headlines."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from sim import params as p
from sim.media import media_lifecycle
from sim.tick import tick
from sim.worldgen import new_game


def main() -> None:
    # worldgen: outlets exist, spread, one centrist, both axes covered
    s = new_game(1)
    assert 3 <= len(s.outlets) <= 4
    assert {o.focus_axis for o in s.outlets} == {0, 1}
    assert any(abs(o.slant[0]) < 0.5 and abs(o.slant[1]) < 0.5 for o in s.outlets), \
        "no centrist outlet"
    assert all(pt.pub_pos == pt.platform for pt in s.parties.values())

    # coverage: a scandal moves the subject's brand down and its pub_pos out
    s = new_game(2)
    pt = min(s.parties.values(), key=lambda t: len(t.members))
    mp = next(m for m in s.mps.values() if m.party == pt.id)
    base = len(s.log)
    s.emit("ScandalBreaks", "test scandal", mp=mp.id)
    brand0, pub0 = pt.brand, np.asarray(pt.pub_pos)
    media_lifecycle(s, base)
    assert pt.brand < brand0, "scandal coverage didn't bleed the brand"
    moved = np.asarray(pt.pub_pos) - pub0
    assert np.linalg.norm(moved) > 0, "coverage didn't move pub_pos"
    hl = [e for e in s.log[base:] if e.type == "Headline"]
    assert len(hl) == 1 and hl[0].data["party"] == pt.id, "no headline attribution"

    # attribution survives the MP being gone (Resigned emits post-removal)
    from sim.career import remove_mp
    s = new_game(9)
    pt = min(s.parties.values(), key=lambda t: len(t.members))
    mp = next(m for m in s.mps.values() if m.party == pt.id)
    base = len(s.log)   # week's slice starts before the emit
    s.emit("Resigned", "test resignation", mp=mp.id, party=mp.party,
           district=mp.district)
    remove_mp(s, mp)
    brand0 = pt.brand
    media_lifecycle(s, base)
    assert pt.brand < brand0, "post-removal story didn't reach its subject"

    # framing asymmetry: hostile outlets hurt more than friendly ones
    s = new_game(3)
    pt = min((t for t in s.parties.values() if t.members),
             key=lambda t: len(t.members))
    far = max(s.outlets, key=lambda o: dist_slant(o, pt))
    near = min(s.outlets, key=lambda o: dist_slant(o, pt))
    deltas = {}
    for o in (far, near):
        s2 = new_game(3)
        pt2 = s2.parties[pt.id]
        mp2 = next(m for m in s2.mps.values() if m.party == pt.id)
        s2.outlets = [o2 for o2 in s2.outlets if o2.id == o.id]
        base = len(s2.log)
        s2.emit("ScandalBreaks", "test scandal", mp=mp2.id)
        media_lifecycle(s2, base)
        deltas[o.id] = pt2.brand
    assert deltas[far.id] < deltas[near.id], \
        f"hostile coverage should hurt more ({deltas})"

    # agenda-setting: in-audience voters gain salience on the focus axis
    s = new_game(4)
    o = s.outlets[0]
    base = len(s.log)
    sal0 = s.voters.salience[:, o.focus_axis].copy()
    media_lifecycle(s, base)
    d = s.voters.salience[:, o.focus_axis] - sal0
    aff = np.exp(-((s.voters.pos - np.asarray(o.slant))**2).sum(axis=1)
                 / (2 * p.AUDIENCE_AFFINITY_SD**2))
    near_v = aff > np.median(aff)
    assert d[near_v].mean() > d[~near_v].mean(), \
        "salience gain didn't concentrate in the audience"

    # sustained coverage builds a measurable caricature gap — coherent pulls
    # consolidate on a polar party (scattered slants cancel on a centrist one)
    s = new_game(5)
    pt = max(s.parties.values(), key=lambda t: np.linalg.norm(t.platform))
    mp = next(m for m in s.mps.values() if m.party == pt.id)
    for _ in range(10):
        base = len(s.log)
        s.emit("ScandalBreaks", "weekly scandal", mp=mp.id)
        media_lifecycle(s, base)
    gap = np.linalg.norm(np.asarray(pt.pub_pos) - np.asarray(pt.platform))
    assert gap > 0.1, f"sustained coverage left no caricature (gap {gap:.3f})"
    cycles = [e for e in s.log if e.type == "PressCycle"]
    assert cycles, "a 10-week scandal streak never became a press frenzy"
    heads = [e for e in s.log if e.type == "Headline"]
    assert all(e.data.get("party") == pt.id for e in heads)

    # headline discipline: never more than one per week, silent on slow weeks
    s = new_game(6)
    for _ in range(60):
        base = len(s.log)
        tick(s)
        assert sum(e.type == "Headline" for e in s.log[base:]) <= 1

    # brand now moves the poll: same electorate, dirty vs clean brand
    from sim.election import poll
    s = new_game(7)
    pt = min(s.parties.values(), key=lambda t: t.brand)
    shares_clean = poll(s)[pt.id]
    pt.brand = -1.0
    shares_dirty = poll(s)[pt.id]
    assert shares_dirty < shares_clean, "brand term is dead in the poll"

    # determinism: same seed → identical headlines
    def headlines(seed):
        s = new_game(seed)
        for _ in range(60):
            tick(s)
        return [e.text for e in s.log if e.type == "Headline"]
    assert headlines(8) == headlines(8), "media pass broke determinism"

    print("media ok: coverage, caricature, agenda, headlines, brand-in-poll all fire")


def dist_slant(o, pt) -> float:
    return float(np.hypot(o.slant[0] - pt.platform[0],
                          o.slant[1] - pt.platform[1]))


if __name__ == "__main__":
    main()
