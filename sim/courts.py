"""Judicial review: statutes answer to the constitution — docket, delay, verdict."""
from __future__ import annotations

import numpy as np

from . import params as p
from .naming import mp_name
from .state import Article, CourtCase, GameState, Law, dist, gov_platform

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


def file_case(state: GameState, law: Law, challenger: int | None,
              by_player: bool = False) -> CourtCase:
    """Open a review — AI filers are opposition parties; the player may file
    too (party id, or None for an independent)."""
    risk = legal_risk(state, law)
    case = CourtCase(law=law, due_week=state.week + p.REVIEW_WEEKS,
                     challenger=challenger, risk=risk, by_player=by_player)
    state.docket.append(case)
    clause = worst_breach(state, law)
    plead = f" under {clause.name}" if clause else ""
    who = ("You" if by_player
           else state.parties[challenger].name if challenger in state.parties
           else "An independent")
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
    """A rule, not a roll: each justice votes from doctrine plus ideology,
    and the bench's majority decides — the court is people, not a scalar."""
    if not any(l is case.law for l in state.laws):
        return  # moot — the law left the registry another way
    if not state.bench:
        return  # nobody sits — the case waits rather than a phantom verdict
                # marking the statute reviewed forever
    risk = case.risk              # the statute as challenged, not as decayed since
    case.law.reviewed = True
    clause = worst_breach(state, case.law)
    plead = clause.name if clause else "general review"
    votes = []
    for j in state.bench:
        line = p.COURT_STRIKE_BASE - p.COURT_ACTIVISM_W * (j.activism - 0.5)
        u = risk - line + p.BENCH_DIST_W * dist(j.pos, case.law.pos)
        votes.append({"justice": j.id, "name": j.name, "strike": u > 0,
                      "u": round(u, 3)})
    strikes = sum(v["strike"] for v in votes)
    struck = bool(votes) and strikes * 2 > len(votes)
    if struck:
        state.laws = [l for l in state.laws if l is not case.law]
        authors = [state.parties[i].name for i in sorted(case.law.enacted_by) if i in state.parties]
        for pid in case.law.enacted_by:
            if pid in state.parties:
                state.parties[pid].brand -= p.COURT_BRAND_HIT
        by = f" — a blow to {'/'.join(authors)}" if authors else ""
        state.emit("LawStruck",
                   f"The court strikes down the {case.law.name} {strikes}-"
                   f"{len(votes)-strikes} — it offends {plead}{by}.",
                   law=case.law.name, risk=risk,
                   article=clause.id if clause else None,
                   bench=votes,
                   parties=sorted(case.law.enacted_by),
                   by_player=case.by_player)
    else:
        state.emit("LawUpheld",
                   f"The court upholds the {case.law.name} {strikes}-"
                   f"{len(votes)-strikes} against a {plead} challenge.",
                   law=case.law.name, risk=risk,
                   article=clause.id if clause else None,
                   bench=votes,
                   parties=sorted(case.law.enacted_by))


def _retirements(state: GameState) -> None:
    """Justices age on the MP hazard curve and vacate the bench."""
    for j in list(state.bench):
        j.age += 1
        prob = 0.0
        if j.age >= p.RETIRE_FLOOR:
            prob = min(p.RETIRE_MAX_P,
                       p.RETIRE_BASE_P + max(0, j.age - p.RETIRE_AGE) * p.RETIRE_SLOPE)
        if state.rng.random() < prob:
            state.bench.remove(j)
            state.emit("JusticeRetired",
                       f"Justice {j.name} leaves the bench at {j.age // 52}.",
                       justice=j.id, appointed_by=j.appointed_by)


def _appoint(state: GameState) -> None:
    """Vacancies fill on the PM's say-so. AI PMs pick a same-week loyalist;
    a player PM gets a shortlist that waits in `bench_shortlist` until
    they appoint — a caretaker fills nothing."""
    if len(state.bench) >= p.BENCH_SIZE or state.phase != "governing":
        return
    pm = state.government.pm
    if pm is None or pm not in state.mps:
        return
    if pm == state.player_id:
        if not state.bench_shortlist:
            np_rng = np.random.default_rng(int(state.rng.random() * 2**63))
            agenda = np.asarray(gov_platform(state))
            # a loyalist, a half-loyal, a moderate — the classic appointment
            # tradeoff: how much doctrine do you buy with how much drift?
            weights = (1.0, 0.5, 0.2)[:p.APPOINT_POOL]  # pools >3 share the tail
            state.bench_shortlist = [
                _candidate(state, np_rng,
                           near=tuple(np.clip(agenda * w, -1, 1)))
                for w in weights]
            state.emit("JusticeNominees",
                       "A seat on the bench is vacant — your nominees await.",
                       count=len(state.bench_shortlist))
        return  # the seat waits on the player's pick
    state.bench.append(_candidate(state, None, near=gov_platform(state),
                                  appointed_by=pm))
    j = state.bench[-1]
    state.emit("JusticeAppointed",
               f"Justice {j.name} takes the bench — appointed by the PM.",
               justice=j.id, appointed_by=pm)


def _candidate(state: GameState, np_rng, near=None, appointed_by=None):
    """A bench nominee: ideology near the appointer's agenda, doctrine drawn."""
    from .state import Justice
    rng = state.rng
    if np_rng is None:
        np_rng = np.random.default_rng(int(rng.random() * 2**63))
    base = np.asarray(near if near is not None else gov_platform(state))
    jid = state.justice_seq     # monotonic — verdict and appointment records
    state.justice_seq += 1      # cite justice ids long after they've gone
    return Justice(
        id=jid, name=mp_name(rng, state.name_pack),
        pos=tuple(np.clip(base + np_rng.normal(0, 0.25, 2), -1, 1)),
        activism=float(np.clip(rng.gauss(0.5, 0.15), 0, 1)),
        age=rng.randint(*p.JUDGE_APPOINT_AGE),
        appointed_by=appointed_by)


def appoint(state: GameState, pick: int) -> bool:
    """Seat a shortlisted nominee — the player-PM's pick. Returns success."""
    if not (0 <= pick < len(state.bench_shortlist)) \
            or len(state.bench) >= p.BENCH_SIZE:
        return False
    j = state.bench_shortlist.pop(pick)
    j.appointed_by = state.player_id
    state.bench.append(j)
    state.bench_shortlist = []
    state.emit("JusticeAppointed",
               f"You appoint Justice {j.name} to the bench.",
               justice=j.id, appointed_by=state.player_id)
    return True


def courts_lifecycle(state: GameState) -> None:
    """Weekly: due verdicts land, the bench ages and fills, then the most
    hostile loser files the next case."""
    for case in list(state.docket):
        if case.due_week <= state.week:
            state.docket = [c for c in state.docket if c is not case]
            _verdict(state, case)
    _retirements(state)
    _appoint(state)
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
