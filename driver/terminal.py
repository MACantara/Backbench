"""Terminal driver: print the week, take 2 actions, repeat. The dumb shell around the sim."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # cp1252 consoles

from sim.actions import Action, available_actions
from sim.career import final_score
from sim.inspect import explain_bench, explain_bill, explain_mp, explain_vote
from sim.tick import tick
from sim.worldgen import new_game

INTERRUPTS = {"ConfidenceLost", "CoalitionFormed", "PartyFormed", "Defection",
              "PartyDissolved", "Scandal", "ElectionCalled", "ElectionResult", "SeatLost",
              "ScandalBreaks", "Expelled", "Resigned", "MinisterSacked",
              "PressCycle", "OfferMade", "OfferDeclined", "OfferLapsed",
              "LawRepealed", "LawLapsed", "PmChange", "BudgetSet",
              "AttackLands", "DebtCrisis"}


def _ask(prompt: str, ok) -> str | None:
    """Re-prompt until ok(input); None on EOF — the pick is abandoned."""
    try:
        while True:
            s = input(prompt).strip()
            if ok(s):
                return s
            print("?")
    except EOFError:
        return None


def prompt_actions(state) -> list[Action]:
    menu = available_actions(state)
    picks = []
    while len(picks) < 2:
        print("\nActions (pick 2):", ", ".join(f"{i}:{a}" for i, a in enumerate(menu)),
              "| inspect <mp_id|bench> | why")
        try:
            raw = input(f"action {len(picks) + 1}/2 > ").strip()
        except EOFError:
            return picks + [Action("nothing")] * (2 - len(picks))
        if raw == "why":
            print(explain_vote(state))
            continue
        if raw.startswith("inspect"):
            parts = raw.split()
            if len(parts) == 2 and parts[1] == "bench":
                print(explain_bench(state))
            elif len(parts) == 2 and parts[1].isdigit() and int(parts[1]) in state.mps:
                print(explain_mp(state, int(parts[1])))
            continue
        if raw.isdigit() and int(raw) < len(menu):
            kind = menu[int(raw)]
            target = axis = vote = offer = law = judge = None
            article = entrench = outlet = None
            if kind in ("lobby", "dig_dirt", "deal", "leak"):
                s = _ask("target mp id > ",
                         lambda s: s.isdigit() and int(s) in state.mps
                         and (kind != "leak" or int(s) != state.player_id))
                if s is None:
                    continue
                target = int(s)
            if kind == "leak":
                me = state.mps[state.player_id]
                for o in state.outlets:
                    print(f"  {o.id}: {o.name} — warmth "
                          f"{o.warmth.get(me.party, 0.0):.2f} to your party")
                s = _ask("route through outlet id (blank = open market) > ",
                         lambda s: s == "" or (s.isdigit()
                                 and any(o.id == int(s) for o in state.outlets)))
                if s is None:
                    continue
                outlet = int(s) if s else None
            if kind == "court":
                from sim.naming import describe_pos
                me = state.mps[state.player_id]
                for o in state.outlets:
                    print(f"  {o.id}: {o.name} — {describe_pos(o.slant)}, "
                          f"warmth {o.warmth.get(me.party, 0.0):.2f}")
                s = _ask("outlet id > ",
                         lambda s: s.isdigit()
                         and any(o.id == int(s) for o in state.outlets))
                if s is None:
                    continue
                target = int(s)
            if kind == "defect":
                others = [f"{i}:{pt.name}" for i, pt in sorted(state.parties.items())
                          if i != state.mps[state.player_id].party]
                s = _ask(f"to ({' '.join(others)} | i=independent) > ",
                         lambda s: s == "i" or (s.isdigit() and int(s) in state.parties
                                                and int(s) != state.mps[state.player_id].party))
                if s is None:
                    continue
                target = None if s == "i" else int(s)
            if kind == "budget":
                s = _ask("posture 0=austerity 1=balanced 2=stimulus > ",
                         lambda s: s in ("0", "1", "2"))
                if s is None:
                    continue
                axis = int(s)
            if kind in ("speech", "promise", "table"):
                s = _ask("axis 0=economic 1=social > ", lambda s: s in ("0", "1"))
                if s is None:
                    continue
                axis = int(s)
            if kind in ("vote", "deal"):
                print(explain_bill(state))
                s = _ask("vote 1=aye -1=no 0=abstain > ", lambda s: s in ("1", "0", "-1"))
                if s is None:
                    continue
                vote = int(s)
            if kind == "appoint":
                from sim.naming import describe_pos
                for i, j in enumerate(state.bench_shortlist):
                    print(f"  {i}: {j.name} — {describe_pos(j.pos)}, "
                          f"activism {j.activism:.2f}, {j.age // 52}y")
                s = _ask("nominee # > ",
                         lambda s: s.isdigit() and int(s) < len(state.bench_shortlist))
                if s is None:
                    continue
                judge = int(s)
            if kind == "challenge":
                from sim.courts import challengeable, legal_risk
                laws = challengeable(state)
                for i, lw in enumerate(laws):
                    print(f"  {i}: {lw.name} (risk {legal_risk(state, lw):.2f})")
                s = _ask("law # > ",
                         lambda s: s.isdigit() and int(s) < len(laws))
                if s is None:
                    continue
                pick = laws[int(s)]
                law = next(i for i, lw in enumerate(state.laws) if lw is pick)
            if kind == "amendment":
                from sim.worldgen import _CLAUSES
                fenced = {(a.axis, a.pole) for a in state.constitution
                          if a.kind == "pos"}
                for a in state.constitution:
                    print(f"  r{a.id}: repeal {a.name}")
                for ax in (0, 1):
                    for pole in (-1, 1):
                        if (ax, pole) not in fenced:
                            side = "economic" if ax == 0 else "social"
                            print(f"  e{ax}{'+-'[pole > 0]}: entrench "
                                  f"{_CLAUSES[(ax, pole)]} ({side} pole)")
                s = _ask("clause > ",
                         lambda s: (s.startswith("r") and s[1:].isdigit()
                                    and any(a.id == int(s[1:]) for a in state.constitution))
                                   or (s.startswith("e") and len(s) == 3
                                       and s[1] in "01" and s[2] in "-+"
                                       and (int(s[1]), 1 if s[2] == "+" else -1)
                                           not in fenced))
                if s is None:
                    continue
                if s[0] == "r":
                    article = int(s[1:])
                else:
                    entrench = (int(s[1]), 1 if s[2] == "+" else -1)
            if kind == "pick_offer":
                for e in [e for e in state.log if e.type == "OfferMade"][-len(state.offers):]:
                    print(" ", e.text)
                s = _ask("offer # > ", lambda s: s.isdigit() and 1 <= int(s) <= len(state.offers))
                if s is None:
                    continue
                offer = int(s) - 1
            picks.append(Action(kind, target=target, axis=axis, vote=vote,
                                offer=offer, law=law, judge=judge,
                                article=article, entrench=entrench,
                                outlet=outlet))
        else:
            print("?")
    return picks


def show_poll(state) -> None:
    last = next((e for e in reversed(state.log) if e.type == "PollShift"), None)
    if last:
        oid = last.data.get("outlet")
        sponsor = next((o.name for o in state.outlets if o.id == oid), None)
        label = f"{sponsor} poll" if sponsor else "polls"
        shares = {state.parties[pid].name: f"{v:.0%}" for pid, v in last.data["shares"].items() if pid in state.parties}
        print(f"  {label}:", "  ".join(f"{k} {v}" for k, v in shares.items()))


def run(seed: int = 0) -> None:
    state = new_game(seed)
    print(f"=== BACKBENCH - seed {seed} ===")
    print(f"You are {state.mps[state.player_id].name}, MP for district {state.mps[state.player_id].district}.")
    while state.phase != "over":
        print(f"\n-- Week {state.week} [{state.phase}] {'-' * 40}")
        show_poll(state)
        actions = prompt_actions(state)
        for e in tick(state, actions):
            mark = "***" if e.type in INTERRUPTS else "   "
            print(f" {mark} {e.text}")
    print(f"\n=== Game over - score {final_score(state)} ===")
    print(explain_mp(state, state.player_id) if state.player_id in state.mps else "You are out of parliament.")


if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 0)
