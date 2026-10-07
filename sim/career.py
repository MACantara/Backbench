"""Career machinery: appointments, leadership challenges, scoring, expulsion."""
from __future__ import annotations

import numpy as np

from . import params as p
from .state import GameState, MP, dist
from .worldgen import make_hopeful

PORTFOLIOS = list(p.PORTFOLIO_INDICATOR)   # the cabinet table — append rows to grow


def _seat_queue(state: GameState) -> list[int]:
    """Portfolio slots dealt to coalition parties by seat share (Gamson-lite)."""
    seats = {pid: len(state.parties[pid].members)
             for pid in state.government.parties if pid in state.parties}
    total = max(sum(seats.values()), 1)
    return [pid for pid, n in seats.items()
            for _ in range(round(len(PORTFOLIOS) * n / total))]


def appointment_terms(state: GameState, mp: MP, appointer: int | None) -> dict[str, float]:
    """Named candidacy terms — the same score decides cabinet and bench picks.
    record is the fixed merit ceiling; standing/backing/rung are movable."""
    # backing reads the appointer's view of the candidate — the leader picks
    backer = state.mps.get(appointer) if appointer is not None else None
    backing = backer.relationships.get(mp.id, 0.0) if backer is not None else 0.0
    return {
        "record": mp.competence + max(0.0, mp.perf),
        "standing": p.STANDING_W * mp.standing,
        "backing": p.BACKING_W * max(-1.0, min(1.0, backing)),  # lobbying helps, can't buy it
        "seniority": p.SENIORITY_W * min(mp.seniority / p.SENIORITY_CAP_WEEKS, 1),
        "rung": p.RUNG_W * min(mp.junior_weeks / p.RUNG_CAP_WEEKS, 1),
    }


def _ranked(state: GameState, cands: list[int], appointer: int | None):
    """Candidates scored by appointment terms, best first."""
    scored = [(m, appointment_terms(state, state.mps[m], appointer)) for m in cands]
    scored.sort(key=lambda kv: -sum(kv[1].values()))
    return scored


def _passed_over(state: GameState, ranked, post: str) -> None:
    """The player was a candidate and lost — say who beat them and on what."""
    ids = [m for m, _ in ranked]
    if state.player_id not in ids:
        return
    rank = ids.index(state.player_id) + 1
    if rank == 1:
        return
    winner, wterms = ranked[0]
    pterms = ranked[rank - 1][1]
    w = state.mps[winner]
    diffs = sorted(wterms, key=lambda k: wterms[k] - pterms[k], reverse=True)
    top = ", ".join(f"{k} {wterms[k]:+.2f} vs your {pterms[k]:+.2f}"
                    for k in diffs[:2] if wterms[k] > pterms[k] + 0.01)
    state.emit("CareerEvent",
               f"Passed over for {post} — {w.name} picked "
               f"(you rank {rank} of {len(ranked)}): {top or 'razor-thin'}.",
               post=post, winner=winner, rank=rank,
               winner_terms=wterms, player_terms=pterms)


def cabinet_cands(state: GameState, pid: int) -> list[int]:
    """Members eligible for a ministry — the inspect rank mirrors this pool."""
    return [m for m in sorted(state.parties[pid].members)
            if m in state.mps and state.mps[m].portfolio is None
            and m != state.government.pm and m not in state.government.sacked]


def _appoint(state: GameState, pid: int, ministry: str, reason: str = "cabinet") -> bool:
    """Best-scoring available MP of a party takes a ministry; the leader picks."""
    cands = cabinet_cands(state, pid)
    if not cands:
        return False
    ranked = _ranked(state, cands, state.parties[pid].leader)
    best, terms = ranked[0]
    mp = state.mps[best]
    mp.portfolio, mp.perf, mp.portfolio_weeks = ministry, 0.0, 0
    mp.junior, mp.junior_weeks = None, 0    # promotion vacates the rung — someone climbs
    state.emit("Promoted", f"{mp.name} appointed {ministry}.",
               mp=best, ministry=ministry, reason=reason, terms=terms)
    _passed_over(state, ranked, ministry)
    return True


def junior_lifecycle(state: GameState) -> None:
    """Weekly while governing: every seated party staffs its bench — in power or
    out. A cabinet pick or defection vacates a rung; a climber refills it."""
    if state.phase != "governing":
        return
    for pid, pt in state.parties.items():
        if not pt.seated or pt.leader is None or pt.leader not in pt.members:
            continue
        leader = state.mps[pt.leader]
        if leader.junior is not None:  # leadership vacates the bench — any path up
            leader.junior, leader.junior_weeks = None, 0
        held = {state.mps[m].junior for m in pt.members
                if m in state.mps and state.mps[m].junior is not None}
        # the second rung fills first — a bench holder climbs, vacating
        # the lower post for the refill pass below
        for post in p.SENIOR_POSTS:
            if post in held:
                continue
            cands = [m for m in sorted(pt.members)
                     if m in state.mps and state.mps[m].junior in p.JUNIOR_POSTS
                     and (post != "Chief Whip" or state.mps[m].junior == "Whip")]
            if not cands:
                continue
            ranked = _ranked(state, cands, pt.leader)
            best, terms = ranked[0]
            mp = state.mps[best]
            held.discard(mp.junior)
            mp.junior, mp.junior_weeks = post, 0
            held.add(post)
            state.emit("Promoted", f"{mp.name} becomes {pt.name} {post}.",
                       mp=best, ministry=post, party=pid, reason="senior",
                       terms=terms)
            _passed_over(state, ranked, f"{pt.name} {post}")
        for post in p.JUNIOR_POSTS:
            if post in held:
                continue
            cands = [m for m in sorted(pt.members)
                     if m in state.mps and state.mps[m].junior is None
                     and state.mps[m].portfolio is None and m != pt.leader
                     and m not in state.government.sacked]
            if not cands:
                continue
            ranked = _ranked(state, cands, pt.leader)
            best, terms = ranked[0]
            mp = state.mps[best]
            mp.junior, mp.junior_weeks = post, 0
            held.add(post)
            state.emit("Promoted", f"{mp.name} becomes {pt.name} {post}.",
                       mp=best, ministry=post, party=pid, reason="junior",
                       terms=terms)
            _passed_over(state, ranked, f"{pt.name} {post}")


def assign_portfolios(state: GameState) -> None:
    """PM hands ministries to coalition MPs by competence + loyalty, split by seats."""
    for mp in state.mps.values():
        mp.portfolio, mp.portfolio_weeks = None, 0
    for pid, ministry in zip(_seat_queue(state), PORTFOLIOS):
        _appoint(state, pid, ministry)


def ministerial_lifecycle(state: GameState) -> None:
    """Weekly: strip defectors, judge records, refill every dark chair.
    A reshuffle swaps the person — seat-weighted shares decide the party."""
    gov = state.government.parties
    if not gov:
        return
    # a portfolio belongs to a government, not the person — defectors lose it
    for mp in state.mps.values():
        if mp.portfolio is not None and mp.party not in gov:
            mp.portfolio, mp.portfolio_weeks = None, 0
    for mp in state.mps.values():
        if (mp.portfolio is None or mp.party not in gov
                or mp.id == state.government.pm):
            continue
        if mp.portfolio_weeks >= p.MINISTER_TENURE and mp.perf < p.MINISTER_SACK_RECORD:
            ministry, pid = mp.portfolio, mp.party
            mp.portfolio, mp.portfolio_weeks = None, 0
            mp.standing -= p.STANDING_SACK_HIT   # a sack burns standing
            state.government.sacked.add(mp.id)   # no same-term re-hire
            pm = state.mps.get(state.government.pm)
            if pm is not None and pm.party in state.parties:
                state.parties[pm.party].brand -= p.MINISTER_SACK_BRAND
            what = p.PORTFOLIO_INDICATOR.get(ministry) or "ministerial"
            state.emit("MinisterSacked",
                       f"{mp.name} is sacked as {ministry} — the {what} numbers got worse.",
                       mp=mp.id, party=pid, portfolio=ministry, reason="performance")
    # every dark chair gets a body — sacks, scandals, defections, retirements
    held = {mp.portfolio for mp in state.mps.values()
            if mp.portfolio is not None and mp.party in gov}
    for pid, ministry in zip(_seat_queue(state), PORTFOLIOS):
        if ministry not in held and _appoint(state, pid, ministry, reason="reshuffle"):
            held.add(ministry)


def leadership_challenge(state: GameState) -> None:
    """Weak leaders face ambitious challengers — members vote on utility."""
    for pid, pt in state.parties.items():
        if pt.leader is None or len(pt.members) < 4:
            continue
        if pt.cohesion >= p.LEADERSHIP_COHESION_MIN:
            continue
        # the player is the careerist by definition — a declared arc
        # qualifies them whenever the chair is weak; their candidacy
        # lives or dies on the relationships they built
        challengers = [m for m in sorted(pt.members)
                       if m != pt.leader and (m == state.player_id
                       or state.mps[m].ambition > p.CHALLENGE_AMBITION_MIN)]
        if not challengers:
            continue
        candidates = [pt.leader] + challengers
        fleaders = {f.leader for f in pt.factions}
        votes = {c: 0 for c in candidates}
        for m in pt.members:
            mp = state.mps[m]
            best = max(candidates, key=lambda c: (
                -dist(mp.pos, state.mps[c].pos)
                + mp.relationships.get(c, 0.0)
                + 0.3 * state.mps[c].competence
                + p.LEADERSHIP_STANDING_W * state.mps[c].standing
                + (p.FACTION_LEADER_BONUS if c in fleaders else 0.0)
                + (p.DEPUTY_HEIR_BONUS if state.mps[c].junior == "Deputy Leader"
                   else 0.0)))
            votes[best] += 1
        winner = max(votes, key=votes.get)
        if winner != pt.leader:
            old = state.mps[pt.leader].name
            pt.leader = winner
            w = state.mps[winner]
            w.junior, w.junior_weeks = None, 0   # the chair vacates the bench
            state.emit("CareerEvent", f"{state.mps[winner].name} ousts {old} as {pt.name} leader.",
                       party=pid, new_leader=winner)


def remove_mp(state: GameState, mp) -> None:
    """Take an MP out of parliament: membership, leadership, premiership handoffs."""
    del state.mps[mp.id]
    pt = state.parties.get(mp.party)
    if pt is not None:
        pt.members.discard(mp.id)
        if pt.leader == mp.id:
            cands = [m for m in sorted(pt.members) if m in state.mps]
            # the named successor takes the chair; else the hungriest member
            deputy = next((m for m in cands
                           if state.mps[m].junior == "Deputy Leader"), None)
            pt.leader = deputy if deputy is not None else (
                max(cands, key=lambda m: state.mps[m].ambition) if cands else None)
            if pt.leader is not None:
                new = state.mps[pt.leader]
                new.junior, new.junior_weeks = None, 0   # the chair vacates the bench
                state.emit("CareerEvent",
                           f"{state.mps[pt.leader].name} succeeds {mp.name} as {pt.name} leader.",
                           party=pt.id, new_leader=pt.leader)
    if state.government.pm == mp.id:
        succ = pt.leader if pt is not None and pt.members else None
        state.government.pm = succ
        if succ is not None:
            state.emit("CareerEvent", f"{state.mps[succ].name} succeeds {mp.name} as PM.", mp=succ)


def mp_lifecycle(state: GameState) -> None:
    """Weekly aging + retirement. Vacated seats stay empty until the election."""
    for mp in state.mps.values():
        mp.age += 1
        mp.seniority += 1
        # standing: office pays a trickle, a burning scandal bleeds, the rest decays
        mp.standing += (p.STANDING_OFFICE if mp.portfolio is not None or mp.junior is not None
                        else 0.0) - (p.STANDING_SCANDAL_WK if mp.scandal_weeks > 0 else 0.0)
        mp.standing = float(np.clip(mp.standing * p.STANDING_DECAY, -1, 1))
        if mp.junior is not None:
            mp.junior_weeks += 1
    gone = []
    for mp in state.mps.values():
        if mp.id == state.player_id:
            continue
        prob = 0.0
        if mp.age >= p.RETIRE_FLOOR:
            prob = min(p.RETIRE_MAX_P,
                       p.RETIRE_BASE_P + max(0, mp.age - p.RETIRE_AGE) * p.RETIRE_SLOPE)
        if state.rng.random() < prob:
            gone.append(mp)
    for mp in gone:
        remove_mp(state, mp)
        state.emit("Retired", f"{mp.name} retires at {mp.age // 52}; the seat sits vacant.",
                   mp=mp.id, district=mp.district, age=mp.age)

    for h in state.hopefuls:
        h.age += 1
    if state.rng.random() < p.HOPEFULS_PER_WEEK_P:
        np_rng = np.random.default_rng(int(state.rng.random() * 2**63))
        n_districts = int(state.voters.district.max()) + 1
        state.hopefuls.append(make_hopeful(state.rng, np_rng, state.parties, n_districts,
                                           age=p.HOPEFUL_AGE[0], pack=state.name_pack))


def update_score(state: GameState) -> None:
    """Called after each election the player survives."""
    player = state.mps[state.player_id]
    state.score_terms["mp"] += 1
    if player.junior:
        state.score_terms["junior"] += 1
    if player.portfolio:
        state.score_terms["minister"] += 1
    if state.government.pm == state.player_id:
        state.score_terms["pm"] += 1


def score_breakdown(state: GameState) -> list[tuple[str, int, int, int]]:
    """The career's accounting — (label, count, weight, points) per row.
    Counts the run's feats from the log: this is the only place the score
    exists, and final_score just sums it."""
    t = state.score_terms
    w = p.SCORE_W
    pid = state.player_id
    founded = sum(1 for pt in state.parties.values() if pt.founded_by == pid)
    struck = sum(1 for e in state.log
                 if e.type == "LawStruck" and e.data.get("by_player"))
    kept = sum(1 for e in state.log
               if e.type == "CareerEvent" and e.data.get("kept") is True)
    leader = any(pt.leader == pid for pt in state.parties.values())
    rows = [
        ("terms in parliament", t.get("mp", 0), w["mp"]),
        ("terms in junior office", t.get("junior", 0), w["junior"]),
        ("terms in cabinet", t.get("minister", 0), w["minister"]),
        ("terms as prime minister", t.get("pm", 0), w["pm"]),
        ("laws bearing your name", state.legacy_bills, w["laws"]),
        ("parties founded, still standing", founded, w["founded"]),
        ("statutes struck on your filing", struck, w["struck"]),
        ("promises the voters judged kept", kept, w["promises"]),
        ("ended leading a party", int(leader), w["leader"]),
        ("ambition realized", t.get("ambition", 0) // w["ambition"],
         w["ambition"]),
    ]
    return [(lab, n, wt, n * wt) for lab, n, wt in rows if n]


def final_score(state: GameState) -> int:
    return sum(pts for _, _, _, pts in score_breakdown(state))


def score_title(score: int) -> str:
    """The career's verdict word — first band the score clears."""
    return next(t for floor, t in p.SCORE_TITLES if score >= floor)


_AMBITION_LABEL = {
    "pm": "hold the premiership",
    "majority": "lead a single-party majority",
    "founder": "found a party that outlives you",
    "survivor": f"hold your seat {p.AMBITION_SURVIVOR_TERMS} terms",
    "reformer": f"author {p.AMBITION_REFORMER_LAWS} laws",
}


def check_ambition(state: GameState) -> None:
    """Resolve the player's arc. Runs every week including the fatal one —
    an unmet ambition on a lost seat fails at the boundary."""
    amb = state.ambition
    if amb is None or amb.met or amb.failed or amb.kind not in _AMBITION_LABEL:
        return
    player = state.mps.get(state.player_id)
    met = False
    if amb.kind == "pm":
        met = state.government.pm == state.player_id
    elif amb.kind == "majority":
        pt = state.parties.get(player.party) if player else None
        met = bool(pt) and len(pt.members) > len(state.mps) / 2
    elif amb.kind == "founder":
        if amb.party is None:
            amb.party = next((pt.id for pt in state.parties.values()
                              if pt.founded_by == state.player_id), None)
        if amb.party is not None and amb.party not in state.parties:
            amb.failed = True          # the vehicle died before it outlived you
            state.emit("AmbitionFailed",
                       f"Ambition unmet — {_AMBITION_LABEL[amb.kind]}.",
                       kind=amb.kind)
            return
        if amb.party is not None:
            pt = state.parties[amb.party]
            elections = [e.data["week"] for e in state.log
                         if e.type == "ElectionResult"]
            met = (pt.members and state.player_id not in pt.members
                   and elections and max(elections) > pt.founded_week)
    elif amb.kind == "survivor":
        met = state.score_terms.get("mp", 0) >= p.AMBITION_SURVIVOR_TERMS
    elif amb.kind == "reformer":
        met = state.legacy_bills >= p.AMBITION_REFORMER_LAWS
    if met:
        amb.met = True
        state.score_terms["ambition"] = state.score_terms.get("ambition", 0) \
            + p.AMBITION_SCORE
        state.emit("AmbitionMet",
                   f"Ambition realized — {_AMBITION_LABEL[amb.kind]}.",
                   kind=amb.kind)
    elif state.phase == "over":
        amb.failed = True
        state.emit("AmbitionFailed",
                   f"Ambition unmet — {_AMBITION_LABEL[amb.kind]}.",
                   kind=amb.kind)


def epilogue(state: GameState) -> list[str]:
    """The career retelling at game over — offices, statutes, the bench,
    the ambition verdict. Reads like an obituary, costs nothing."""
    me = state.mps.get(state.player_id)
    name = me.name if me else "The former member"
    t = state.score_terms
    lines = [f"{name} served {t.get('mp', 0)} term(s) in parliament."]
    posts = ([f"{t['junior']} term(s) on the party bench"] if t.get("junior") else []) \
        + ([f"{t['minister']} in cabinet"] if t.get("minister") else []) \
        + ([f"{t['pm']} as Prime Minister"] if t.get("pm") else [])
    if posts:
        lines.append("High office: " + ", ".join(posts) + ".")
    if state.legacy_bills:
        lines.append(f"{state.legacy_bills} law(s) bear your name.")
    seated = [j for j in state.bench if j.appointed_by == state.player_id]
    if seated:
        lines.append(f"{len(seated)} of your justices still sit the bench.")
    amb = state.ambition
    if amb is not None and amb.kind in _AMBITION_LABEL:
        verdict = "realized" if amb.met else "went unmet"
        lines.append(f"Ambition to {_AMBITION_LABEL[amb.kind]} — {verdict}.")
    return lines


