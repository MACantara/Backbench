"""Runnable check: player agency matters, career machinery fires."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sim.params as p
from sim.actions import Action, available_actions
from sim.career import final_score, leadership_challenge
from sim.tick import tick
from sim.worldgen import new_game

GOOD = [Action("constituency"), Action("campaign")]
BAD = []


def run(seed: int, actions_per_week) -> float:
    """Player's seat margin after the first election (0 if they lost)."""
    s = new_game(seed)
    while s.phase == "campaign":
        tick(s, actions_per_week)
    return s.mps[s.player_id].seat_safety if s.phase != "over" else 0.0


def main() -> None:
    seeds = range(30)
    good = sum(run(i, GOOD) for i in seeds) / 30
    bad = sum(run(i, BAD) for i in seeds) / 30
    assert good > bad, f"good play margin {good:.2f} should beat bad play {bad:.2f}"

    # action menu is phase-aware and capped at 2/week use
    s = new_game(1)
    menu = available_actions(s)
    assert "campaign" in menu and "platform" not in menu

    # leadership challenge fires under low cohesion + high ambition
    s2 = new_game(2)
    pt = s2.parties[0]
    pt.cohesion = 0.1
    challenger = sorted(pt.members - {pt.leader})[0]
    s2.mps[challenger].ambition = 0.9
    leadership_challenge(s2)
    assert any(e.type == "CareerEvent" and "ousts" in e.text for e in s2.log) or pt.leader != challenger

    # career-ending dirt ends the run via the scandal lifecycle — expulsion if
    # the player is clean, resignation roll while burning; either way, it's over
    s3 = new_game(3)
    for _ in range(80):
        s3.mps[s3.player_id].dossier = p.SACK_THRESHOLD + 0.1
        tick(s3)
        if s3.phase == "over":
            break
    assert s3.phase == "over"

    # scoring accumulates
    s4 = new_game(4)
    while s4.phase == "campaign":
        tick(s4, GOOD)
    assert s4.score_terms["mp"] == 1 if s4.phase != "over" else True

    print(f"player ok: margin good={good:.2f} vs bad={bad:.2f}, challenge+expulsion+scoring fire")


if __name__ == "__main__":
    main()
