"""Runnable check: wings emerge, whip separately, secede as a bloc."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sim.params as p
from sim.factions import update_factions
from sim.parliament import resolve_vote
from sim.parties import party_lifecycle
from sim.state import Bill
from sim.worldgen import new_game


def bimodal(seed: int, left: tuple, right: tuple, platform: tuple):
    """A party split cleanly into two wings."""
    s = new_game(seed)
    pt = s.parties[0]
    members = list(pt.members)
    half = len(members) // 2
    for m in members[:half]:
        s.mps[m].pos = left
    for m in members[half:]:
        s.mps[m].pos = right
    pt.platform = platform
    return s, pt, members


def main() -> None:
    # wings emerge with names and leaders
    s, pt, members = bimodal(1, (-0.9, 0.0), (0.9, 0.0), (-0.75, -0.15))
    update_factions(s)
    assert len(pt.factions) == 2, "bimodal party should produce two wings"
    assert all(f.name and f.leader in f.members for f in pt.factions)
    assert any(e.type == "FactionEmerged" for e in s.log)
    wing_members = {m for f in pt.factions for m in f.members}
    assert wing_members == set(members), "every member should land in a wing"

    # a wing whips against the party line on a distant bill
    s.government.parties = {0}
    resolve_vote(s, Bill(pos=(-0.75, -0.15), beneficiary_axis=0))  # on-platform bill
    rebels = [e for e in s.log if e.type == "FactionRebels"]
    assert len(rebels) == 1, "exactly the off-platform wing should rebel"
    detail = [e for e in s.log if e.type == "VoteResult"][-1].data["detail"]
    fwing = rebels[0].data["faction"]
    for mid, d in detail.items():
        if s.mps.get(mid) and s.mps[mid].faction == fwing:
            assert "fwhip" in d["terms"], f"rebel wing MP {mid} missing fwhip term"
        elif s.mps.get(mid) and s.mps[mid].party == 0:
            assert "fwhip" not in d["terms"], f"loyal wing MP {mid} got fwhip term"

    # sustained estrangement → the wing secedes as a bloc
    s2, pt2, members2 = bimodal(2, (-1.0, -1.0), (1.0, 1.0), (0.0, 0.0))
    for m in members2:
        s2.mps[m].loyalty = 0.1
        s2.mps[m].ambition = 0.4   # suppress lone-founder path
    pt2.schism_cooldown = 0
    n_parties = len(s2.parties)
    for _ in range(p.SECESSION_WEEKS + 1):
        party_lifecycle(s2)
        s2.week += 1
    seceded = [e for e in s2.log if e.type == "Secession"]
    assert seceded, "sustained estrangement should produce a secession"
    assert len(s2.parties) == n_parties + 1
    assert 0 in s2.parties, "parent party should survive with its other wing"
    assert len(s2.parties[0].members) >= p.FACTION_MIN_SIZE

    # the player is never dragged out of their party by a secession
    s3, pt3, members3 = bimodal(3, (-1.0, -1.0), (1.0, 1.0), (0.0, 0.0))
    pid = s3.player_id
    s3.mps[pid].party = 0
    pt3.members.add(pid)
    s3.mps[pid].pos = (-1.0, -1.0)
    for m in members3:
        s3.mps[m].loyalty = 0.1
        s3.mps[m].ambition = 0.4
    pt3.schism_cooldown = 0
    for _ in range(p.SECESSION_WEEKS + 2):
        party_lifecycle(s3)
        s3.week += 1
    assert s3.mps[pid].party == 0, "player must stay when their wing walks"
    assert s3.mps[pid].faction is None or any(
        s3.mps[pid].faction == f.id for pt in s3.parties.values() for f in pt.factions)

    print("factions ok: wings emerge, rebel whip fires, secession takes the bloc")


if __name__ == "__main__":
    main()
