"""Hall of fame — scores.json read/record. Driver-side file I/O; the sim
stays pure. One entry per run, ranked, capped."""
from __future__ import annotations

import json
from pathlib import Path

FAME = Path(__file__).resolve().parent.parent / "saves" / "scores.json"
FAME_MAX = 10


def load_fame() -> list[dict]:
    try:
        return json.loads(FAME.read_text(encoding="utf-8"))
    except Exception:
        return []


def _entry(state) -> dict:
    from sim.career import final_score, score_title
    me = state.mps.get(state.player_id)
    score = final_score(state)
    return {"name": me.name if me else "the former member",
            "score": score, "title": score_title(score),
            "seed": state.seed, "scenario": state.scenario,
            "week": state.week}


def same_run(a: dict, b: dict) -> bool:
    return (a["seed"], a["week"], a["name"]) == (b["seed"], b["week"], b["name"])


def record_fame(state) -> list[dict]:
    """Bank this run once (idempotent — replaying a game-over dedups);
    returns the ranked table including this entry."""
    entry = _entry(state)
    table = [e for e in load_fame() if not same_run(e, entry)]
    table.append(entry)
    table.sort(key=lambda e: (-e["score"], -e["week"]))
    table = table[:FAME_MAX]
    FAME.parent.mkdir(exist_ok=True)
    FAME.write_text(json.dumps(table, indent=1), encoding="utf-8")
    return table
