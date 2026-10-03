"""Legibility tools: explain why MPs voted how they did, why events happened."""
from __future__ import annotations

from .conditions import mood
from .state import GameState, dist
from .treasury import flow, interest, revenue, upkeep


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
    seen = (f" [seen {pt.pub_pos[0]:+.2f},{pt.pub_pos[1]:+.2f} "
            f"vs platform {pt.platform[0]:+.2f},{pt.platform[1]:+.2f}]"
            if pt and dist(pt.pub_pos, pt.platform) > 0.05 else "")
    rels = sorted(m.relationships.items(), key=lambda kv: -abs(kv[1]))[:5]
    rel_txt = ", ".join(f"{state.mps[k].name if k in state.mps else k}:{v:+.2f}" for k, v in rels)
    return (f"{m.name} ({pt.name if pt else 'independent'}{wing}{seen}) — district {m.district}\n"
            f"  pos=({m.pos[0]:+.2f},{m.pos[1]:+.2f}) ambition={m.ambition:.2f} "
            f"loyalty={m.loyalty:.2f} competence={m.competence:.2f} integrity={m.integrity:.2f}\n"
            f"  seat_safety={m.seat_safety:.2f} portfolio={m.portfolio or '—'} "
            f"dossier={m.dossier:.2f}{' BURNING' if m.scandal_weeks else ''} "
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
    c = state.conditions
    country = (f"country: growth {c.growth:+.2f} unemp {c.unemployment:.2f} "
               f"infl {c.inflation:.2f} services {c.services:.2f} crime {c.crime:.2f} "
               f"| mood {mood(c):+.2f} | {len(state.laws)} laws in force")
    t = state.treasury
    books = (f"treasury: debt {t.debt:.2f} | rev {revenue(state):.3f} "
             f"upkeep {upkeep(state):.3f} interest {interest(state):.3f} "
             f"flow {flow(state):+.3f}/wk")
    return explain_mp(state, state.player_id) + "\n" + country + "\n" + books
