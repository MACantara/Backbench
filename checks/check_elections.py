"""Election integrity: the ballot data M9 emits must add up — named rosters,
votes that sum to turnout, shares that sum to 1, and projections that can't
mutate the world they describe."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sim.bot import auto_actions
from sim.election import INDEPENDENT, battleground, district_forecast
from sim.tick import tick
from sim.worldgen import new_game


def run_to_election(state):
    """Tick until the election resolves; return that week's DistrictResults."""
    while state.phase != "over":
        events = tick(state, auto_actions(state))
        drs = [e for e in events if e.type == "DistrictResult"]
        if drs:
            return drs, next(e for e in events if e.type == "ElectionResult")
    return None, None


def ballot_arith(seed: int) -> None:
    s = new_game(seed)
    drs, res = run_to_election(s)
    assert drs, f"seed {seed}: no districts resolved"
    ndist = int(s.voters.district.max()) + 1
    nat = {}
    for e in drs:
        cands = e.data["candidates"]
        assert cands, f"seed {seed} d{e.data['district']}: empty ballot"
        assert all(c["name"] for c in cands), "every candidate needs a name"
        assert all(isinstance(c["incumbent"], bool) for c in cands)
        tot = sum(c["votes"] for c in cands)
        assert tot == e.data["turnout"], \
            f"d{e.data['district']}: votes {tot} != turnout {e.data['turnout']}"
        assert 0 <= e.data["turnout"] <= int((s.voters.district == e.data["district"]).sum())
        if tot:
            assert abs(sum(c["share"] for c in cands) - 1.0) < 1e-6
            top = max(cands, key=lambda c: c["votes"])
            if s.district_magnitude == 1:
                assert top["won"], "FPTP: highest vote-getter must win"
                assert top is cands[0], "candidates sorted by votes"
        for c in cands:
            nat[c["party"]] = nat.get(c["party"], 0) + c["votes"]
    assert len(drs) == ndist
    # national votes on ElectionResult equal the sum of district ballots
    for q, n in res.data["votes"].items():
        key = INDEPENDENT if q == "ind" else q
        assert nat.get(key, 0) == n, f"party {q}: nat {nat.get(key)} != event {n}"
    # every district named a winner
    assert sum(res.data["seats"].values()) >= ndist


def forecast_safety(seed: int) -> None:
    s = new_game(seed)
    st = s.rng.getstate()
    f1 = district_forecast(s, 3)
    battleground(s)
    assert s.rng.getstate() == st, "a forecast must never consume the stream"
    f2 = district_forecast(s, 3)
    assert f1 == f2, "same world, same projection"
    me = s.mps[s.player_id]
    f = district_forecast(s, me.district)
    assert f["candidates"], "player district needs a ballot"
    names = {c["name"] for c in f["candidates"]}
    assert me.name in names, "the incumbent stands in their own forecast"


def determinism(seed: int) -> None:
    def first_district(s):
        while s.phase != "over":
            drs, _res = run_to_election(s)
            if drs:
                return drs[0]
        return None
    a, b = new_game(seed), new_game(seed)
    da, db = first_district(a), first_district(b)
    assert da is not None and db is not None
    assert da.data["candidates"] == db.data["candidates"], \
        "same seed must print the same ballot"
    assert da.text == db.text


if __name__ == "__main__":
    for seed in (7, 23, 41):
        ballot_arith(seed)
    for seed in (7, 23):
        forecast_safety(seed)
        determinism(seed)
    print("check_elections ok")
