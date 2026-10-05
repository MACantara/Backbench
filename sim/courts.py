"""Judicial review: statutes answer to the constitution — docket, delay, verdict."""
from __future__ import annotations

from . import params as p
from .state import Article, CourtCase, GameState, Law, dist

_KIND_W = {"pos": p.RISK_EXTREMITY_W, "cost": p.RISK_COST_W,
           "margin": p.RISK_MARGIN_W}


def violation(article: Article, law: Law) -> float:
    """How far a statute crosses a clause, normalized — 0 means it stands clear."""
    if article.kind == "pos":
        return max(0.0, article.pole * law.pos[article.axis]
                   - article.limit) / max(1 - article.limit, 1e-9)
    if article.kind == "cost":
        ceiling = p.COST_BASE + p.COST_EXTREMITY_W
        return min(1.0, max(0.0, law.cost - article.limit)
                   / max(ceiling - article.limit, 1e-9))
    return max(0.0, article.limit - law.margin) / max(article.limit - 0.5, 1e-9)


def legal_risk(state: GameState, law: Law) -> float:
    """How contestable a statute is: the sum of its clause violations, plus a
    residual extremity term — radicalism invites review even on open ground."""
    extremity = (law.pos[0] ** 2 + law.pos[1] ** 2) ** 0.5
    return (p.RISK_EXTREMITY_W * p.RISK_RESIDUAL * extremity
            + sum(_KIND_W[a.kind] * violation(a, law)
                  for a in state.constitution))


def worst_breach(state: GameState, law: Law) -> Article | None:
    """The clause a law most offends — the citation strikes carry."""
    best = max(((a, violation(a, law)) for a in state.constitution),
               key=lambda t: t[1], default=None)
    return best[0] if best and best[1] > 0 else None


def file_case(state: GameState, law: Law, challenger: int | None) -> CourtCase:
    """Open a review — AI filers are opposition parties; the player may file
    too (party id, or None for an independent)."""
    risk = legal_risk(state, law)
    case = CourtCase(law=law, due_week=state.week + p.REVIEW_WEEKS,
                     challenger=challenger, risk=risk)
    state.docket.append(case)
    clause = worst_breach(state, law)
    plead = f" under {clause.name}" if clause else ""
    who = (state.parties[challenger].name if challenger in state.parties
           else "You")
    state.emit("ReviewOpened",
               f"{who} challenge{'s' if who != 'You' else ''} the {law.name} "
               f"in court{plead} (risk {risk:.2f}).",
               law=law.name, challenger=challenger, risk=risk,
               article=clause.id if clause else None, due=case.due_week)
    return case


def challengeable(state: GameState) -> list[Law]:
    """Statutes a challenge can lawfully reach right now."""
    if len(state.docket) >= p.COURT_DOCKET_MAX:
        return []
    pending = {id(c.law) for c in state.docket}
    return [law for law in state.laws
            if not law.reviewed and id(law) not in pending
            and legal_risk(state, law) >= p.CHALLENGE_RISK_MIN]


def _verdict(state: GameState, case: CourtCase) -> None:
    """A rule, not a roll: the bench's per-seed character decides the line."""
    if not any(l is case.law for l in state.laws):
        return  # moot — the law left the registry another way
    risk = case.risk              # the statute as challenged, not as decayed since
    case.law.reviewed = True
    clause = worst_breach(state, case.law)
    plead = clause.name if clause else "general review"
    line = p.COURT_STRIKE_BASE - p.COURT_ACTIVISM_W * (state.court_activism - 0.5)
    if risk >= line:
        state.laws = [l for l in state.laws if l is not case.law]
        authors = [state.parties[i].name for i in sorted(case.law.enacted_by) if i in state.parties]
        for pid in case.law.enacted_by:
            if pid in state.parties:
                state.parties[pid].brand -= p.COURT_BRAND_HIT
        by = f" — a blow to {'/'.join(authors)}" if authors else ""
        state.emit("LawStruck",
                   f"The court strikes down the {case.law.name} — it offends "
                   f"{plead}{by}.",
                   law=case.law.name, risk=risk,
                   article=clause.id if clause else None,
                   parties=sorted(case.law.enacted_by))
    else:
        state.emit("LawUpheld",
                   f"The court upholds the {case.law.name} against a "
                   f"{plead} challenge.",
                   law=case.law.name, risk=risk,
                   article=clause.id if clause else None,
                   parties=sorted(case.law.enacted_by))


def courts_lifecycle(state: GameState) -> None:
    """Weekly: due verdicts land, then the most hostile loser files the next case."""
    for case in list(state.docket):
        if case.due_week <= state.week:
            state.docket = [c for c in state.docket if c is not case]
            _verdict(state, case)
    # the venue for losers: hostile opposition drags the riskiest statute in
    if len(state.docket) >= p.COURT_DOCKET_MAX:
        return
    filers = [pid for pid, pt in state.parties.items()
              if pid not in state.government.parties and pt.members]
    best = None  # (risk, law)
    for law in challengeable(state):
        challenger = max(filers, key=lambda pid: dist(state.parties[pid].platform, law.pos),
                         default=None)
        if challenger is None:
            continue
        hostility = dist(state.parties[challenger].platform, law.pos)
        if hostility < p.CHALLENGE_DIST:
            continue
        r = legal_risk(state, law)
        if best is None or r > best[0]:
            best = (r, law, challenger)
    if best:
        file_case(state, best[1], best[2])
