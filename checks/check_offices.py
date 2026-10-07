"""Check: offices with functions — the payroll binds, the bench ladders,
the deputy inherits, and the chair stands unopposed."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sim import params as p
from sim.actions import Action
import random

from sim.career import remove_mp
from sim.election import _ballot
from sim.inspect import explain_party
from sim.parliament import vote_terms, whip_direction, whip_strength
from sim.state import Bill
from sim.tick import tick
from sim.worldgen import new_game


def bench_posts(s, pid):
    return {s.mps[m].junior: m for m in s.parties[pid].members
            if m in s.mps and s.mps[m].junior}


def main() -> None:
    # 1. the ladder orders itself: Chief Whip only rises from the Whip rung
    held_before: dict[int, set] = {}
    ok_order = True
    s = new_game(1)
    for _ in range(60):
        tick(s, [])
        for e in s.log:
            if e.type != "Promoted" or e.data.get("reason") != "senior":
                continue
            if e.data["ministry"] == "Chief Whip" \
                    and "Whip" not in held_before.get(e.data["mp"], set()):
                ok_order = False
        for e in s.log:
            if e.type == "Promoted":
                held_before.setdefault(e.data["mp"], set()).add(e.data["ministry"])
    staffed = sum(1 for pt in s.parties.values()
                  if "Chief Whip" in bench_posts(s, pt.id)
                  and "Deputy Leader" in bench_posts(s, pt.id))
    assert ok_order, "a Chief Whip was staffed without holding the Whip rung"
    assert staffed >= 4, f"only {staffed} parties filled both senior posts"

    # 2. the deputy inherits the chair on a vacancy
    s2 = new_game(2)
    for _ in range(60):
        tick(s2, [])
    pt = next(pt for pt in s2.parties.values()
              if pt.leader in s2.mps and "Deputy Leader" in bench_posts(s2, pt.id))
    dep = bench_posts(s2, pt.id)["Deputy Leader"]
    remove_mp(s2, s2.mps[pt.leader])
    assert pt.leader == dep, \
        f"deputy {dep} didn't inherit — got {s2.mps.get(pt.leader)}"

    # 3. a staffed whips office binds the line harder
    s3 = new_game(3)
    pid = None
    for _ in range(80):
        tick(s3, [])
        pid = next((pid for pid, pt in s3.parties.items()
                    if any(s3.mps[m].junior in p.WHIP_POSTS for m in pt.members
                           if m in s3.mps)), None)
        if pid is not None:
            break
    assert pid is not None, "no whips office staffed in 80 weeks"
    base = whip_strength(s3, pid)
    assert base > 1.0, f"whip_strength {base} with a Whip staffed"
    bill = Bill(pos=(0.0, 0.0), beneficiary_axis=0, cost=0.0)
    member = next(m for m in s3.parties[pid].members
                  if s3.mps[m].junior is None and m != s3.parties[pid].leader)
    w = vote_terms(s3, s3.mps[member], bill, noisy=False)["whip"]
    for m in list(s3.parties[pid].members):
        if s3.mps[m].junior in p.WHIP_POSTS:
            s3.mps[m].junior = None
    stripped = vote_terms(s3, s3.mps[member], bill, noisy=False)["whip"]
    assert abs(w) > abs(stripped), f"whip term didn't bite: {w} vs {stripped}"

    # 4. the payroll binds: rebellion while holding office vacates the post
    s4 = new_game(4)
    me = s4.mps[s4.player_id]
    me.junior = "Spokesperson"
    fell = False
    for _ in range(80):
        b = s4.current_bill
        acts = []
        if b is not None and s4.mps.get(s4.player_id) is not None \
                and s4.mps[s4.player_id].party is not None:
            w4 = whip_direction(s4, s4.mps[s4.player_id].party, b)
            if w4 and s4.mps[s4.player_id].junior:
                acts = [Action("vote", vote=-w4)]
        tick(s4, acts)
        if any(e.type == "PayrollFall" and e.data.get("mp") == s4.player_id
               for e in s4.log):
            fell = True
            break
    assert fell and s4.mps[s4.player_id].junior is None, \
        "payroll rebellion didn't cost the post"

    # 5. the chair: elected, renounced, unopposed, and never a divider
    s5 = new_game(5)
    tick(s5, [])
    spk = s5.mps[s5.speaker]
    assert spk.party is None and spk.junior is None, "speaker didn't renounce"
    cand, ballot = _ballot(s5, spk.district, [spk], random.Random(0))
    assert len(ballot) == 1, f"speaker's ballot had {len(ballot)} candidates"

    # the chair's cast is always 0 (or -1 casting on a tie) — drive a real
    # division rather than hoping a seed survives to governing
    s5b = new_game(11)
    for _ in range(120):
        if s5b.phase == "governing":
            break
        tick(s5b, [])
    assert s5b.phase == "governing" and s5b.speaker in s5b.mps
    from sim.parliament import resolve_vote
    import copy
    ev = copy.deepcopy(s5b)
    bill = Bill(pos=(0.0, 0.0), beneficiary_axis=0)
    res = resolve_vote(ev, bill)
    spk_cast = ev.log[-1].data["detail"][ev.speaker]["cast"]
    assert spk_cast in (0, -1), f"the chair cast {spk_cast}"

    # and across a real run the uncontested seat holds
    s5c = new_game(17)
    held = 0
    for _ in range(260):
        if s5c.phase == "over":
            break
        tick(s5c, [])
        held += 1
    elections = sum(1 for e in s5c.log if e.type == "ElectionResult")
    spk = s5c.mps.get(s5c.speaker)
    assert spk is not None and (elections == 0 or spk.seat_safety >= 0.99), \
        "the chair's uncontested seat didn't hold"
    assert spk.party is None

    # 6. the party card reads rank, fuse, and the contest preview
    s6 = new_game(6)
    for _ in range(30):
        tick(s6, [])
    me6 = s6.mps.get(s6.player_id)
    if me6 is not None and me6.party in s6.parties:
        txt = explain_party(s6, me6.party)
        for needle in ("cohesion", "leader:", "your candidacy: rank",
                       "leader's view of you", "fractured today"):
            assert needle in txt, f"party card missing '{needle}'"
    else:
        txt = explain_party(s6, next(iter(s6.parties)))
        assert "cohesion" in txt and "leader:" in txt

    # 7. the bot's payroll discipline: spectating, it never falls off the whip
    from sim.bot import auto_actions, bot_pick_ambition
    s7 = new_game(7)
    bot_pick_ambition(s7)
    for _ in range(120):
        if s7.phase == "over":
            break
        tick(s7, auto_actions(s7))
    assert not any(e.type == "PayrollFall" and e.data.get("mp") == s7.player_id
                   for e in s7.log), "the bot fell off the payroll"
    print("offices: ladder order, deputy succession, whip bite, payroll, "
          "speaker, party card, bot discipline — all green")


if __name__ == "__main__":
    main()
