"""Runnable check: niche entry, graves/revival, and a party system that stays plural."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

import sim.params as p
from sim.actions import Action, available_actions
from sim.dynamism import _unserved_clusters, niche_entry
from sim.state import dist
from sim.tick import tick
from sim.worldgen import new_game

BIRTH_KINDS = {"entry", "revival", "founder", "secession"}


def _policy(s) -> list:
    """Seat-defending scripted play so the world gets to run its course."""
    return [Action(k) for k in ("campaign", "constituency") if k in available_actions(s)][:2]


def _enp(s) -> float:
    shares = np.array([len(pt.members) for pt in s.parties.values()], dtype=float)
    shares /= shares.sum()
    return float(1.0 / (shares**2).sum())


def main() -> None:
    # revival: orphan a flank, bury it, and its heir rises in the same space
    s = victim = None
    for seed in range(40):
        cand = new_game(seed)
        for pid, pt in list(cand.parties.items()):
            keep = dict(cand.parties)
            del cand.parties[pid]
            for cluster in _unserved_clusters(cand):
                if len(cluster) < p.DYNAMIC_GAP_MIN_SEATS:
                    continue
                mask = np.isin(cand.voters.district, cluster)
                cent = tuple(cand.voters.pos[mask].mean(axis=0))
                if dist(cent, pt.platform) < p.DYNAMIC_GAP_DIST * 0.5:
                    s, victim = cand, pt
                    break
            if s is not None:
                break
            cand.parties = keep
        if s is not None:
            break
    assert s is not None, "no seed produced an unserved cluster after a flank party died"
    s.graves.append({"name": victim.name, "platform": victim.platform, "died": s.week})
    niche_entry(s)
    births = [e for e in s.log if e.type == "PartyFormed"]
    assert births
    heirs = [e for e in births if e.data.get("kind") == "revival"]
    assert heirs and heirs[0].text.startswith(f"Second {victim.name}"), \
        [b.text for b in births]

    # long run: births carry kind, deaths leave graves, the system stays plural.
    # A hegemonic seed may still collapse to a dominant-party system — that's a
    # legitimate world; plurality is the attractor, not a universal outcome.
    enps, kinds_seen, factions_seen, end_counts = [], set(), 0, []
    for seed in range(6):
        s = new_game(seed)
        counts = []
        for _ in range(300):
            if s.phase == "over":
                break
            tick(s, _policy(s))
            counts.append(len(s.parties))
        dissolved = sum(1 for e in s.log if e.type == "PartyDissolved")
        formed = [e for e in s.log if e.type == "PartyFormed"]
        factions_seen += sum(1 for e in s.log if e.type == "FactionEmerged")
        kinds_seen |= {e.data.get("kind") for e in formed}
        assert all(e.data.get("kind") in BIRTH_KINDS for e in formed)
        assert len(s.graves) == dissolved, "every dissolution should leave a grave"
        enps.append(_enp(s))
        end_counts.append(counts[-1] if counts else len(s.parties))
    assert sum(c >= 3 for c in end_counts) >= 4, \
        f"too many seeds collapsed below 3 parties: {end_counts}"
    assert kinds_seen & {"entry", "founder", "secession"}, f"no births fired: {kinds_seen}"
    assert factions_seen > 0, "wings should form under the retuned gate"
    med_enp = float(np.median(enps))
    assert med_enp >= 2.0, f"median seat ENP {med_enp:.2f} < 2.0"
    print(f"party-dynamism ok: kinds={sorted(kinds_seen)} factions={factions_seen} "
          f"median ENP={med_enp:.2f} end parties={end_counts}")


if __name__ == "__main__":
    main()
