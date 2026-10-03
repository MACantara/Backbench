"""Legibility tools: explain why MPs voted how they did, why events happened."""
from __future__ import annotations

from .state import GameState


def explain_vote(state: GameState, event_index: int = -1) -> str:
    """Break down a VoteResult/ConfidenceLost event into per-MP term contributions."""
    votes = [e for e in state.log if e.type in ("VoteResult",)]
    if not votes:
        return "no votes yet"
    e = votes[event_index]
    lines = [e.text]
    detail = e.data.get("detail", {})
    for mp_id, d in sorted(detail.items(), key=lambda kv: kv[1]["u"]):
        mp = state.mps.get(mp_id)
        name = mp.name if mp else f"MP#{mp_id}"
        terms = ", ".join(f"{k}={v:+.2f}" for k, v in d["terms"].items() if abs(v) > 0.01)
        lines.append(f"  {name:<20} u={d['u']:+.2f} {'YES' if d['u'] > 0 else 'no '} ({terms})")
    return "\n".join(lines)


def explain_mp(state: GameState, mp_id: int) -> str:
    m = state.mps[mp_id]
    pt = state.parties.get(m.party)
    faction = next((f for f in pt.factions if f.id == m.faction), None) if pt else None
    wing = f", {faction.name}" if faction else ""
    rels = sorted(m.relationships.items(), key=lambda kv: -abs(kv[1]))[:5]
    rel_txt = ", ".join(f"{state.mps[k].name if k in state.mps else k}:{v:+.2f}" for k, v in rels)
    return (f"{m.name} ({pt.name if pt else 'independent'}{wing}) — district {m.district}\n"
            f"  pos=({m.pos[0]:+.2f},{m.pos[1]:+.2f}) ambition={m.ambition:.2f} "
            f"loyalty={m.loyalty:.2f} competence={m.competence:.2f} integrity={m.integrity:.2f}\n"
            f"  seat_safety={m.seat_safety:.2f} portfolio={m.portfolio or '—'} "
            f"{'[YOU]' if mp_id == state.player_id else ''}\n"
            f"  top relationships: {rel_txt or 'none'}")


def explain_district(state: GameState, district: int) -> str:
    v = state.voters
    mask = v.district == district
    centroid = v.pos[mask].mean(axis=0)
    mp = next((m for m in state.mps.values() if m.district == district), None)
    holder = "vacant" if mp is None else (
        f"{mp.name} ({state.parties[mp.party].name if mp.party in state.parties else 'ind'}, "
        f"margin {mp.seat_safety:.0%})")
    return (f"District {district}: {int(mask.sum())} voters, centroid "
            f"({centroid[0]:+.2f},{centroid[1]:+.2f}), {holder}")


def player_status(state: GameState) -> str:
    return explain_mp(state, state.player_id)
