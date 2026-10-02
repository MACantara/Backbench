"""Runnable check: a full scripted game runs end to end with real actions."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sim.actions import Action, available_actions
from sim.career import final_score
from sim.inspect import explain_vote
from sim.tick import tick
from sim.worldgen import new_game


def scripted_actions(state) -> list[Action]:
    menu = available_actions(state)
    out = []
    for want in ("constituency", "campaign", "speech", "lobby"):
        if want in menu and len(out) < 2:
            if want == "lobby":
                others = [m.id for m in state.mps.values() if m.id != state.player_id]
                out.append(Action("lobby", target=others[0]))
            elif want == "speech":
                out.append(Action("speech", axis=0))
            else:
                out.append(Action(want))
    return out


def main() -> None:
    s = new_game(0)
    for _ in range(200):
        tick(s, scripted_actions(s))
        if s.phase == "over":
            break
    types = {e.type for e in s.log}
    assert {"PollShift", "ElectionResult", "CoalitionFormed", "VoteResult"} <= types
    # inspector produces a real explanation of the last vote
    text = explain_vote(s)
    assert "u=" in text and "policy" in text
    # score exists and player's history is traceable
    assert isinstance(final_score(s), int)
    assert s.log, "event log is the audit trail"
    print(f"e2e ok: week={s.week} phase={s.phase} score={final_score(s)} "
          f"events={len(s.log)} parties={len(s.parties)}")


if __name__ == "__main__":
    main()
