"""Terminal driver: print the week, take 2 actions, repeat. The dumb shell around the sim."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # cp1252 consoles

from sim.actions import Action, available_actions
from sim.career import final_score
from sim.inspect import explain_bill, explain_mp, explain_vote
from sim.tick import tick
from sim.worldgen import new_game

INTERRUPTS = {"ConfidenceLost", "CoalitionFormed", "PartyFormed", "Defection",
              "PartyDissolved", "Scandal", "ElectionCalled", "ElectionResult", "SeatLost",
              "ScandalBreaks", "Expelled", "Resigned", "MinisterSacked",
              "PressCycle", "OfferMade", "OfferDeclined"}


def prompt_actions(state) -> list[Action]:
    menu = available_actions(state)
    picks = []
    while len(picks) < 2:
        print("\nActions (pick 2):", ", ".join(f"{i}:{a}" for i, a in enumerate(menu)),
              "| inspect <mp_id> | why")
        try:
            raw = input(f"action {len(picks) + 1}/2 > ").strip()
        except EOFError:
            return picks + [Action("nothing")] * (2 - len(picks))
        if raw == "why":
            print(explain_vote(state))
            continue
        if raw.startswith("inspect"):
            parts = raw.split()
            if len(parts) == 2 and parts[1].isdigit() and int(parts[1]) in state.mps:
                print(explain_mp(state, int(parts[1])))
            continue
        if raw.isdigit() and int(raw) < len(menu):
            kind = menu[int(raw)]
            target = axis = vote = offer = None
            if kind in ("lobby", "dig_dirt", "deal"):
                t = input("target mp id > ").strip()
                target = int(t) if t.isdigit() else None
            if kind in ("speech", "promise"):
                a = input("axis 0=economic 1=social > ").strip()
                axis = int(a) if a in "01" else None
            if kind in ("vote", "deal"):
                print(explain_bill(state))
                v = input("vote 1=aye -1=no 0=abstain > ").strip()
                vote = int(v) if v in ("1", "0", "-1") else None
            if kind == "pick_offer":
                for e in [e for e in state.log if e.type == "OfferMade"][-len(state.offers):]:
                    print(" ", e.text)
                o = input("offer # > ").strip()
                offer = int(o) - 1 if o.isdigit() else None
            picks.append(Action(kind, target=target, axis=axis, vote=vote, offer=offer))
        else:
            print("?")
    return picks


def show_poll(state) -> None:
    last = next((e for e in reversed(state.log) if e.type == "PollShift"), None)
    if last:
        shares = {state.parties[pid].name: f"{v:.0%}" for pid, v in last.data["shares"].items() if pid in state.parties}
        print("  polls:", "  ".join(f"{k} {v}" for k, v in shares.items()))


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
