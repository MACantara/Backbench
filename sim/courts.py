"""Judicial review: the registry under challenge — docket, delay, verdict."""
from __future__ import annotations

from . import params as p
from .state import CourtCase, GameState, Law, dist


def legal_risk(law: Law) -> float:
    """How contestable a statute is: radicalism, expense, thin mandate."""
    extremity = (law.pos[0] ** 2 + law.pos[1] ** 2) ** 0.5
    return (p.RISK_EXTREMITY_W * extremity
            + p.RISK_COST_W * law.cost / (p.COST_BASE + p.COST_EXTREMITY_W)
            + p.RISK_MARGIN_W * (1 - law.margin))


def _verdict(state: GameState, case: CourtCase) -> None:
    """A rule, not a roll: the bench's per-seed character decides the line."""
    if not any(l is case.law for l in state.laws):
        return  # moot — the law left the registry another way
    risk = legal_risk(case.law)
    case.law.reviewed = True
    line = p.COURT_STRIKE_BASE - p.COURT_ACTIVISM_W * (state.court_activism - 0.5)
    if risk >= line:
        state.laws = [l for l in state.laws if l is not case.law]
        authors = [state.parties[i].name for i in sorted(case.law.enacted_by) if i in state.parties]
        for pid in case.law.enacted_by:
            if pid in state.parties:
                state.parties[pid].brand -= p.COURT_BRAND_HIT
        by = f" — a blow to {'/'.join(authors)}" if authors else ""
        state.emit("LawStruck", f"The court strikes down the {case.law.name}{by}.",
                   law=case.law.name, risk=risk, parties=sorted(case.law.enacted_by))
    else:
        state.emit("LawUpheld", f"The court upholds the {case.law.name}.",
                   law=case.law.name, risk=risk, parties=sorted(case.law.enacted_by))


def courts_lifecycle(state: GameState) -> None:
    """Weekly: due verdicts land, then the most hostile loser files the next case."""
    for case in list(state.docket):
        if case.due_week <= state.week:
            state.docket.remove(case)
            _verdict(state, case)
    # the venue for losers: hostile opposition drags the riskiest statute in
    if len(state.docket) >= p.COURT_DOCKET_MAX:
        return
    pending = {id(c.law) for c in state.docket}
    filers = [pid for pid, pt in state.parties.items()
              if pid not in state.government.parties and pt.members]
    best = None  # (risk, law, challenger)
    for law in state.laws:
        if law.reviewed or id(law) in pending:
            continue
        r = legal_risk(law)
        if r < p.CHALLENGE_RISK_MIN:
            continue
        challenger = max(filers, key=lambda pid: dist(state.parties[pid].platform, law.pos),
                         default=None)
        if challenger is None or dist(state.parties[challenger].platform, law.pos) < p.CHALLENGE_DIST:
            continue
        if best is None or r > best[0]:
            best = (r, law, challenger)
    if best:
        r, law, pid = best
        case = CourtCase(law=law, due_week=state.week + p.REVIEW_WEEKS, challenger=pid)
        state.docket.append(case)
        state.emit("ReviewOpened",
                   f"{state.parties[pid].name} challenges the {law.name} in court (risk {r:.2f}).",
                   law=law.name, challenger=pid, risk=r, due=case.due_week)
