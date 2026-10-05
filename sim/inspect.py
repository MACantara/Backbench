"""Legibility tools: explain why MPs voted how they did, why events happened."""
from __future__ import annotations

from . import params as p
from .conditions import mood
from .state import GameState, dist
from .treasury import flow, interest, revenue, upkeep


def decisive_term(terms: dict, u: float) -> str | None:
    """The term whose removal flips the sign of u — the one that *decided* it.
    None when no single term alone would flip the call."""
    for k in sorted(terms, key=lambda k: -abs(terms[k])):
        if terms[k] and (u - terms[k]) * u <= 0:
            return k
    return None


def explain_vote(state: GameState, event_index: int = -1) -> str:
    """Break down a VoteResult into per-MP terms, marking each vote's decider."""
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
        dec = decisive_term(d["terms"], d["u"])
        cast = d.get("cast", 1 if d["u"] > 0 else -1)
        col = "YES" if cast == 1 else "no " if cast == -1 else "abs"
        lines.append(f"  {name:<20} u={d['u']:+.2f} {col}"
                     f"  <- {dec or '—'} ({terms})")
    return "\n".join(lines)


def explain_bill(state: GameState) -> str:
    """Pre-vote stakes on the pending bill: projected tally, the marginals, and
    what decides each of them. Noise-free — inspect never touches the rng."""
    bill = state.current_bill
    if bill is None:
        return "no bill pending"
    from .parliament import vote_terms
    rows = []
    for mp in state.mps.values():
        terms = vote_terms(state, mp, bill, noisy=False)
        rows.append((sum(terms.values()), mp, terms))
    yes = sum(1 for u, _, _ in rows if u > p.ABSTAIN_MARGIN)
    no = sum(1 for u, _, _ in rows if u < -p.ABSTAIN_MARGIN)
    abstain = len(rows) - yes - no
    is_amendment = bill.amends is not None or bill.entrenches is not None
    passes = (yes > 0 and yes >= p.AMEND_MAJORITY * (yes + no)) if is_amendment \
        else yes > no
    lines = [f"{bill.name} — projected {yes}-{no} +{abstain} abstain "
             f"({'pass' if passes else 'fail'})"]
    if is_amendment:
        what = (f"repeal {bill.amends.name}" if bill.amends
                else f"entrench {bill.entrenches.name}")
        lines.append(f"  constitutional — {what}; needs two-thirds of "
                     "votes cast")
    if bill.budget:
        lines.append(f"  supply — tax ×{bill.tax:.2f}, spend ×{bill.spend:.2f} "
                     "if enacted")
    if bill.repeals is not None:
        lines.append(f"  strikes the {bill.repeals.name} from the book")
    for u, mp, terms in sorted((r for r in rows if abs(r[0]) < p.MARGINAL_BAND),
                               key=lambda r: abs(r[0]))[:8]:
        you = " [YOU]" if mp.id == state.player_id else ""
        lines.append(f"  {mp.name:<20}{you} u={u:+.2f} — decided by "
                     f"{decisive_term(terms, u) or '—'}")
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
    ladder = ""
    if mp_id == state.player_id and pt is not None and pt.leader is not None:
        from .career import appointment_terms, cabinet_cands
        ranked = sorted(cabinet_cands(state, pt.id), key=lambda c: -sum(
            appointment_terms(state, state.mps[c], pt.leader).values()))
        if mp_id in ranked:   # no line for the ineligible — PM or sacked
            terms = appointment_terms(state, m, pt.leader)
            ladder = ("\n  cabinet candidacy: rank "
                      f"{ranked.index(mp_id) + 1}/{len(ranked)} — "
                      + " ".join(f"{k} {v:+.2f}" for k, v in terms.items()))
    return (f"{m.name} ({pt.name if pt else 'independent'}{wing}{seen}) — district {m.district}\n"
            f"  pos=({m.pos[0]:+.2f},{m.pos[1]:+.2f}) ambition={m.ambition:.2f} "
            f"loyalty={m.loyalty:.2f} competence={m.competence:.2f} integrity={m.integrity:.2f}\n"
            f"  seat_safety={m.seat_safety:.2f} portfolio={m.portfolio or '—'} "
            f"junior={m.junior or '—'} standing={m.standing:+.2f} "
            f"dossier={m.dossier:.2f}{' BURNING' if m.scandal_weeks else ''} "
            f"{'[YOU]' if mp_id == state.player_id else ''}\n"
            f"  top relationships: {rel_txt or 'none'}{ladder}")


def explain_bench(state: GameState) -> str:
    """The sitting court: who holds each seat, their doctrine and lean, and
    which PM put them there — packing the bench stays legible."""
    from .naming import describe_pos
    lines = [f"the bench: {len(state.bench)}/{p.BENCH_SIZE} seats, "
             f"{len(state.docket)} case(s) pending"]
    for j in sorted(state.bench, key=lambda j: -j.age):
        who = (state.mps[j.appointed_by].name if j.appointed_by in state.mps
               else "the founders" if j.appointed_by is None
               else "a departed PM")
        lines.append(f"  J. {j.name:<22} {describe_pos(j.pos):<18} "
                     f"activism {j.activism:.2f}  {j.age // 52}y  <- {who}")
    for c in state.bench_shortlist:
        lines.append(f"  nominee {c.name:<17} {describe_pos(c.pos):<18} "
                     f"activism {c.activism:.2f}  {c.age // 52}y")
    return "\n".join(lines)


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
