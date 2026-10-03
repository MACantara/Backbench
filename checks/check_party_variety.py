"""Runnable check: per-seed party systems, archetype names, named bills."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import random

import sim.params as p
from sim.naming import _BILL_NAMES, _BILL_NEUTRAL, bill_name, describe_pos
from sim.parliament import resolve_vote, table_bill
from sim.parties import party_lifecycle
from sim.state import Bill, dist
from sim.worldgen import new_game


def main() -> None:
    # different seeds → different countries
    a, b, c = new_game(7), new_game(7), new_game(42)
    assert [pt.name for pt in a.parties.values()] == [pt.name for pt in b.parties.values()]
    assert [pt.platform for pt in a.parties.values()] == [pt.platform for pt in b.parties.values()], \
        "same seed must reproduce the same party system"
    assert [pt.name for pt in a.parties.values()] != [pt.name for pt in c.parties.values()], \
        "different seeds should produce different party systems"

    # pool shape across many seeds: count in range, names unique, platforms spread
    for seed in range(20):
        s = new_game(seed)
        names = [pt.name for pt in s.parties.values()]
        plats = [pt.platform for pt in s.parties.values()]
        assert p.PARTY_COUNT_RANGE[0] <= len(names) <= p.PARTY_COUNT_RANGE[1], \
            f"seed {seed}: {len(names)} parties outside range"
        assert len(set(names)) == len(names), f"seed {seed}: duplicate party names {names}"
        assert all(dist(x, y) >= p.PARTY_MIN_SEPARATION
                   for i, x in enumerate(plats) for y in plats[i + 1:]), \
            f"seed {seed}: overlapping platforms"
        # both flanks of the class axis are represented
        assert min(x[0] for x in plats) < 0.2 and max(x[0] for x in plats) > -0.2

    # describe_pos is the one position vocabulary
    assert describe_pos((-0.6, 0.0)) == "left"
    assert describe_pos((0.0, 0.6)) == "traditional"
    assert describe_pos((-0.6, -0.6)) == "left-libertarian"
    assert describe_pos((0.0, 0.0)) == "centrist"

    # bill names follow the domain map
    rng = random.Random(0)
    for _ in range(30):
        assert bill_name((-0.6, 0.0), 0, rng) in _BILL_NAMES[(0, -1)]
        assert bill_name((0.6, 0.0), 0, rng) in _BILL_NAMES[(0, 1)]
        assert bill_name((0.0, 0.6), 1, rng) in _BILL_NAMES[(1, 1)]
        assert bill_name((0.0, -0.6), 1, rng) in _BILL_NAMES[(1, -1)]
        assert bill_name((0.05, 0.0), 0, rng) in _BILL_NEUTRAL

    # tabled bills are named; enacted laws carry the name through
    s = new_game(11)
    for m in s.mps.values():  # one-party majority — the bill must pass
        m.party = 0
    s.parties[0].members = set(s.mps)
    s.government.parties = {0}
    s.government.pm = next(iter(s.parties[0].members))
    bill = table_bill(s)
    assert bill.name and bill.name in s.log[-1].text
    assert "+0." not in s.log[-1].text and "-0." not in s.log[-1].text, \
        "BillTabled should speak a name, not coordinates"
    resolve_vote(s, bill, player_vote=1)
    laws = [e for e in s.log if e.type == "LawEnacted"]
    assert laws and laws[-1].data["law"] == bill.name
    assert s.laws[-1].name == bill.name

    # a bloc secession gets an archetype name; a lone founder gets "X List"
    s = new_game(2)
    pt = s.parties[0]
    members = sorted(pt.members - {s.player_id})
    half = len(members) // 2
    for i, m in enumerate(members):
        s.mps[m].pos = (-1.0, -1.0) if i < half else (1.0, 1.0)
        s.mps[m].loyalty = 0.1
        s.mps[m].ambition = 0.4  # suppress the lone-founder path
    pt.platform = (0.0, 0.0)
    pt.schism_cooldown = 0
    for _ in range(p.SECESSION_WEEKS + 1):
        party_lifecycle(s)
        s.week += 1
    formed = [e for e in s.log if e.type == "PartyFormed"]
    assert formed, "the estranged wing should have walked"
    seceded = s.parties[formed[-1].data["party"]]
    assert not seceded.name.endswith(" List"), \
        f"bloc secession should take an archetype name, got {seceded.name!r}"

    s = new_game(3)
    pt = s.parties[0]
    sad = min(pt.members - {s.player_id}, key=lambda m: s.mps[m].id)
    for m in pt.members:
        s.mps[m].pos = (0.9, 0.9)   # everyone far from platform → cohesion ~0
        s.mps[m].loyalty = 0.0
    s.mps[sad].pos = (-0.9, -0.9)   # ... and this one far from everyone
    s.mps[sad].ambition = 0.9
    party_lifecycle(s)
    formed = [e for e in s.log if e.type == "PartyFormed"]
    assert formed, "the miserable MP should found a party"
    assert formed[-1].text.endswith("MPs).") and " List " in formed[-1].text, \
        f"lone founder should take a surname List, got {formed[-1].text!r}"

    print("party-variety ok: seeded systems, archetype secessions, named bills")


if __name__ == "__main__":
    main()
