"""Runnable check: the player's vote matters — thin divisions, abstention,
quorum stalls, pending-bill cadence, deals, and noise-free inspection."""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sim.params as p
from sim.actions import Action, available_actions
from sim.inspect import explain_bill
from sim.parliament import resolve_vote, vote_terms
from sim.tick import tick
from sim.worldgen import new_game


def _governing(seed: int):
    """First governing state for a seed, or None if the player died reaching it."""
    s = new_game(seed)
    for _ in range(120):
        if s.phase in ("governing", "over"):
            return s if s.phase == "governing" else None
        tick(s)
    return None


def _projected_gap(s, bill) -> int:
    """Noise-free yes-minus-no on a bill, the player's own u excluded."""
    yes = no = 0
    for m in s.mps.values():
        if m.id == s.player_id:
            continue
        u = sum(vote_terms(s, m, bill, noisy=False).values())
        yes += u > p.ABSTAIN_MARGIN
        no += u < -p.ABSTAIN_MARGIN
    return yes - no


def main() -> None:
    # --- pending cadence: tabled this week, divided next ---
    s = _governing(0)
    assert s is not None
    tick(s)
    assert s.current_bill is not None, "no bill tabled in a governing week"
    assert not any(e.type == "VoteResult" for e in s.log[-5:]
                   if e.data.get("week") == s.week), \
        "a bill resolved the week it was tabled — no time to read it"
    name = s.current_bill.name
    tick(s)
    assert s.current_bill is None or s.current_bill.name != name, \
        "the pending bill never got its division"
    assert any(e.type == "VoteResult" for e in s.log[-30:]), "division never resolved"

    # --- the player's vote flips a thin division ---
    # a division where the player decides is a realized exact tie — build one:
    # party A whipped aye (platform pinned to the bill), party B whipped no,
    # 60-60 minus the player. The player's ballot is the deciding vote.
    c = _governing(0)
    tick(c)
    bill = c.current_bill
    pa, pb = sorted(c.parties)[:2]
    c.parties[pa].platform = bill.pos                       # whips aye (d < 0.4)
    c.parties[pb].platform = (1.0, 1.0)                     # whips no (far)
    c.government.parties = set()
    mids = [m for m in sorted(c.mps) if m != c.player_id]
    for i, mid in enumerate(mids):
        m = c.mps[mid]
        m.party = pa if i % 2 == 0 else pb
        m.pos = bill.pos if m.party == pa else (1.0, 1.0)   # policy agrees with the whip
        m.loyalty = 0.9
        m.seat_safety = 1.0                                 # no district exposure
        m.faction = None                                    # no wing overriding the whip
    c.mps[c.player_id].party = pa
    for pt in c.parties.values():
        pt.members = {m.id for m in c.mps.values() if m.party == pt.id}
        pt.factions = []
    # the fixture wants the realized tie — no noise, nobody home sick
    saved = {k: getattr(p, k) for k in
             ("VOTE_NOISE", "ATTEND_BASE", "ATTEND_LATE", "ATTEND_SCANDAL", "ATTEND_AGE")}
    for k in saved:
        setattr(p, k, 0.0)
    try:
        a, b = copy.deepcopy(c), copy.deepcopy(c)
        r_a = resolve_vote(a, bill, player_vote=1)
        r_b = resolve_vote(b, bill, player_vote=-1)
    finally:
        for k, v in saved.items():
            setattr(p, k, v)
    assert r_a is True and r_b is False, \
        f"the player's vote didn't decide a 60-60 house: aye {r_a} / no {r_b}"

    # --- abstention really is a third column ---
    abstained = False
    for seed in range(8):
        s2 = _governing(seed)
        if s2 is None:
            continue
        for _ in range(40):
            tick(s2)
            for e in s2.log[-10:]:
                if e.type == "VoteResult" and e.data.get("abstain", 0) > 0:
                    abstained = True
        if abstained:
            break
    assert abstained, "no abstentions in eight runs — the margin band is dead code"

    # --- quorum: an empty house stalls the division, the bill carries ---
    s3 = _governing(1)
    assert s3 is not None
    tick(s3)
    bill = s3.current_bill
    old = p.ATTEND_BASE
    p.ATTEND_BASE = 0.9
    try:
        res = resolve_vote(s3, bill)
    finally:
        p.ATTEND_BASE = old
    assert res is None, "a two-thirds-empty house still divided"
    assert s3.current_bill is bill, "a stalled division lost the pending bill"
    assert any(e.type == "DivisionStalled" for e in s3.log), "no stall event"
    tick(s3)
    assert s3.current_bill is not bill, "the carried bill never came back for division"

    # --- inspection stays off the rng stream ---
    s4 = _governing(0)
    assert s4 is not None
    tick(s4)
    twin = copy.deepcopy(s4)
    text1, text2 = explain_bill(s4), explain_bill(s4)
    assert text1 == text2 and "projected" in text1
    assert s4.rng.random() == twin.rng.random(), \
        "explain_bill consumed rng — projections leak determinism"

    # --- deals: kept word banks, broken word bites ---
    s5 = _governing(0)
    assert s5 is not None
    tick(s5)
    assert "deal" in available_actions(s5), "deal action absent with a bill pending"
    t = next(m for m in s5.mps.values() if m.id != s5.player_id)
    rel0 = t.relationships.get(s5.player_id, 0.0)
    tick(s5, [Action("deal", target=t.id, vote=1), Action("vote", vote=1)])
    assert any(e.type == "DealKept" for e in s5.log), "kept promise not honored"
    assert t.relationships.get(s5.player_id, 0.0) > rel0, "a kept deal paid nothing"
    tick(s5)  # next bill
    rel1 = t.relationships.get(s5.player_id, 0.0)
    tick(s5, [Action("deal", target=t.id, vote=1), Action("vote", vote=-1)])
    assert any(e.type == "DealBroken" for e in s5.log[-20:]), "reneged silently"
    assert t.relationships.get(s5.player_id, 0.0) < rel1, "a broken deal cost nothing"
    assert not s5.deals, "judged deals linger on the books"

    print("conscience ok: pending cadence, player flip, abstention, quorum, "
          "pure inspection, deals")


if __name__ == "__main__":
    main()
