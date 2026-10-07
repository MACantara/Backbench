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
        if mp.id == state.speaker:
            continue                # the chair only casts on a tie
        terms = vote_terms(state, mp, bill, noisy=False)
        rows.append((sum(terms.values()), mp, terms))
    yes = sum(1 for u, _, _ in rows if u > p.ABSTAIN_MARGIN)
    no = sum(1 for u, _, _ in rows if u < -p.ABSTAIN_MARGIN)
    abstain = len(state.mps) - yes - no
    is_amendment = bill.amends is not None or bill.entrenches is not None
    passes = (yes > 0 and yes >= p.AMEND_MAJORITY * (yes + no)) if is_amendment \
        else yes > no
    lines = [f"{bill.name} — projected {yes}-{no} +{abstain} abstain "
             f"({'pass' if passes else 'fail'})"]
    from .parliament import whip_direction
    me = state.mps.get(state.player_id)
    post = (me.junior or me.portfolio) if me is not None else None
    if me is not None and me.party is not None and post is not None \
            and me.junior not in p.WHIP_POSTS \
            and whip_direction(state, me.party, bill):
        lines.append(f"  the payroll binds: rebelling the whip costs your {post}")
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
    label = (pt.name if pt else
             "Speaker" if mp_id == state.speaker else "independent")
    return (f"{m.name} ({label}{wing}{seen}) — district {m.district}\n"
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


def explain_party(state: GameState, pid: int) -> str:
    """The party's internal order: who holds the bench, how fractious it is,
    where the player ranks — and the votes a challenge would cast today."""
    from .career import appointment_terms, cabinet_cands, challenge_votes
    pt = state.parties[pid]
    hold = lambda post: next((state.mps[m] for m in sorted(pt.members)
                              if m in state.mps and state.mps[m].junior == post), None)
    fuse = (" — fractious: a challenge could land" if pt.cohesion < p.LEADERSHIP_COHESION_MIN
            else " — the chair is safe" if pt.cohesion >= p.LEADERSHIP_COHESION_MIN
            + p.FUSE_SAFE_MARGIN else "")
    leader = state.mps.get(pt.leader)
    lines = [f"{pt.name} — {len(pt.members)} members, cohesion {pt.cohesion:.2f}{fuse}",
             f"  leader: {leader.name if leader else '—'}"]
    for post in (*p.SENIOR_POSTS, *p.JUNIOR_POSTS):
        h = hold(post)
        you = " [YOU]" if h is not None and h.id == state.player_id else ""
        lines.append(f"  {post.lower()}: {h.name if h else '—'}{you}")
    gov = state.government
    pm_pid = state.mps[gov.pm].party if gov.pm in state.mps else None
    if pid in gov.parties and pid != pm_pid and gov.platform is not None:
        strain = dist(pt.platform, gov.platform)
        share = state.last_poll["shares"].get(pid, 0.0) if state.last_poll else None
        seat = len(pt.members) / max(len(state.mps), 1)
        bits = f"  in government: strain {strain:.2f}"
        if share is not None:
            bits += f", poll {share:.0%} vs seats {seat:.0%}"
        if strain > p.COAL_EXIT_DIST and share is not None and share < seat:
            bits += " — LEAVING RISK"
        lines.append(bits)
    for f in pt.factions:
        heir = state.mps.get(f.leader)
        lines.append(f"  {f.name}: {len(f.members)} members"
                     f" — heir {heir.name if heir else '—'}")
    me = state.mps.get(state.player_id)
    if state.player_id in pt.members and me is not None and leader is not None:
        ranked = sorted(cabinet_cands(state, pid), key=lambda c: -sum(
            appointment_terms(state, state.mps[c], pt.leader).values()))
        if state.player_id in ranked:
            terms = appointment_terms(state, me, pt.leader)
            lines.append(f"  your candidacy: rank {ranked.index(state.player_id) + 1}"
                         f"/{len(ranked)} — " + " ".join(
                             f"{k} {v:+.2f}" for k, v in terms.items()))
        if pt.leader != state.player_id:
            lines.append(f"  the leader's view of you: "
                         f"{leader.relationships.get(state.player_id, 0.0):+.2f}")
        if len(pt.members) >= p.CHALLENGE_MIN_MEMBERS:
            votes = challenge_votes(state, pt)
            backers = [state.mps[m].name for m in votes.get(state.player_id, [])
                       if m != state.player_id and m in state.mps]
            lines.append(f"  if the party fractured today: you'd take "
                         f"{len(votes.get(state.player_id, []))} of {len(pt.members)} votes"
                         + (f" — {', '.join(backers[:4])} would back you"
                            if backers else ""))
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


# --- action legibility ------------------------------------------------
# Every weekly pick gets a blurb (what it is) and a live preview (what it
# would do now, with real numbers where the code can compute them).

ACTION_INFO: dict[str, str] = {
    "campaign": "knock doors in your seat — voters drift toward your platform",
    "constituency": "casework — loyalty up, grudges fade, standing up",
    "speech": "push an axis in your seat — salience rises, voters drift to you",
    "promise": "a public pledge — the electorate checks it at the election",
    "media": "a broadcast slot — brand up if it lands, a gaffe if it doesn't",
    "dig_dirt": "hire researchers — a dossier grows, unless you're noticed",
    "leak": "detonate a dossier through a venue — friendly press shields you",
    "court": "wine and dine an editorial board — warmth buys coverage",
    "lobby": "press a colleague — their regard for you rises",
    "scheme": "quiet dinners with colleagues — a little regard, a little dirt",
    "vote": "your column on the pending division — a duty, not a pick",
    "deal": "promise your column to a colleague — they bank the credit",
    "amend": "drag the pending bill toward your ground — once per bill",
    "attack": "go for the government — lands only when it's weak",
    "table": "write and divide your own bill — your name on the book",
    "platform": "pull the party platform toward you — a leader's prerogative",
    "evolve": "reposition — the voters price the slide, the whip reads the direction",
    "budget": "signal the next budget's posture — the treasury reads it",
    "defect": "cross the floor — your district remembers betrayal",
    "found": "walk out and name a vehicle — whoever loves you walks too",
    "challenge": "sue a statute — the venue for losers takes your filing",
    "appoint": "seat a justice — the bench outlasts governments",
    "amendment": "move the constitution — repeal a clause or fence a pole",
    "pick_offer": "choose a coalition — a hung parliament waits on you",
    "decline_offers": "refuse the slates — bargain another week",
    "nothing": "a quiet week — the world ticks without you",
}


def explain_action(state: GameState, kind: str,
                   target: int | None = None,
                   outlet: int | None = None) -> str:
    """What this pick does right now — live numbers where the code can
    compute them, the blurb when it can't. Never lies: odds are the same
    expressions apply_action rolls against."""
    blurb = ACTION_INFO.get(kind, kind)
    me = state.mps.get(state.player_id)
    if me is None:
        return blurb
    v = state.voters
    mask = v.district == me.district
    t = state.mps.get(target) if target is not None else None

    if kind == "campaign":
        pt = state.parties.get(me.party)
        plat = pt.platform if pt else me.pos
        gap = dist(v.pos[mask].mean(axis=0), plat) if mask.any() else 0.0
        return (f"the district sits {gap:.2f} from the platform — "
                f"each knock closes ~0.03 and lifts turnout ~{p.GOTV_LIFT:.0%}")
    if kind == "constituency":
        return (f"standing {me.standing:.2f} -> "
                f"{min(1.0, me.standing + p.STANDING_SERVICE):.2f}, "
                "loyalty +0.02, grudges fade 15%")
    if kind == "speech":
        return ("salience +0.05 on the axis you pick; the district "
                "drifts ~0.03 toward you on it")
    if kind == "promise":
        return f"{len(state.promises)} pledges on record — this adds one"
    if kind == "media":
        pt = state.parties.get(me.party)
        ref = pt.platform if pt else me.pos
        friend = 1 - min(1.0, sum(dist(o.slant, ref) for o in state.outlets)
                         / max(len(state.outlets), 1) / 2)
        return (f"~80%: brand +{p.MEDIA_APPEAR_BRAND * (0.5 + friend):.2f} "
                f"(press friendliness {friend:.0%}); ~20%: a gaffe "
                f"(+0.15 dossier, -0.05 brand)")
    if kind == "dig_dirt":
        if t is None:
            return blurb + " — pick a colleague"
        return (f"{t.name}'s dossier {t.dossier:.2f} -> "
                f"{t.dossier + 0.25:.2f}; ~30% they notice (-0.20 regard)")
    if kind == "leak":
        if t is None:
            return blurb + " — pick a colleague"
        thin = (f"their dossier is thin ({t.dossier:.2f} < "
                f"{p.LEAK_MIN_DOSSIER}) — nothing will move the press"
                if t.dossier <= p.LEAK_MIN_DOSSIER else
                f"their dossier will burn ({t.dossier:.2f})")
        if outlet is None:
            return (f"{thin}; open-market trace ~{p.LEAK_TRACE_P:.0%}, "
                    f"friendly venue ~{p.LEAK_TRACE_P * p.FRIENDLY_TRACE_MULT:.0%}, "
                    f"hostile ~{p.LEAK_TRACE_P * p.HOSTILE_TRACE_MULT:.0%}")
        o = next((x for x in state.outlets if x.id == outlet), None)
        warm = o.warmth.get(me.party, 0.0) if o else -1.0
        mult = 1.0 if o is None else (
            p.FRIENDLY_TRACE_MULT if warm >= p.COURT_FRIENDLY_MIN
            else p.HOSTILE_TRACE_MULT)
        venue = (f"{o.name} (warmth {warm:.2f})" if o else "the open market")
        return f"{thin}; through {venue} the trace risk is ~{p.LEAK_TRACE_P * mult:.0%}"
    if kind == "court":
        o = next((x for x in state.outlets if x.id == target), None)
        if o is None or me.party is None:
            return blurb + " — pick an editorial board"
        w = o.warmth.get(me.party, 0.0)
        return (f"{o.name} warmth {w:.2f} -> "
                f"{min(1.0, w + p.COURT_WARMTH):.2f} — friendlier "
                "coverage, safer leaks")
    if kind == "lobby":
        if t is None:
            return blurb + " — pick a colleague"
        r = t.relationships.get(me.id, 0.0)
        return f"{t.name}'s regard {r:.2f} -> {r + 0.2:.2f} — careers run on this ledger"
    if kind == "evolve":
        # same expressions apply_action prices: clip, moved, betrayal, standing
        def _ev(a):
            new = tuple(min(1.0, max(-1.0, me.pos[i] + p.EVOLVE_STEP * (a[i] - me.pos[i])))
                        for i in (0, 1))
            mv = dist(me.pos, new)
            return new, (f"{dist(me.pos, a):.2f} away, moves {mv:.2f} "
                         f"(+{p.EVOLVE_BETRAYAL_W * mv:.2f} mistrust)")
        parts = []
        if mask.any():
            parts.append("district: " + _ev(tuple(v.pos[mask].mean(axis=0)))[1])
        pt = state.parties.get(me.party)
        if pt is not None:
            new, txt = _ev(tuple(pt.platform))
            sd = p.EVOLVE_STANDING_W * (dist(me.pos, pt.platform) - dist(new, pt.platform))
            parts.append(f"party: {txt}, standing {sd:+.2f}")
        return " | ".join(parts) or "no anchor to read"
    if kind == "scheme":
        pt = state.parties.get(me.party)
        n = max(0, min(8, len(pt.members) - 1)) if pt else 0
        return (f"+0.05 regard with up to {n} colleagues; your dossier "
                f"+0.03 (now {me.dossier:.2f})")
    if kind == "attack":
        ministers = [m for m in state.mps.values() if m.portfolio is not None]
        weak = -mood(state.conditions) - min((m.perf for m in ministers),
                                           default=0.0)
        odds = float(max(0.02, min(0.9, p.ATTACK_P + p.ATTACK_WEAK_W * weak)))
        return (f"lands ~{odds:.0%}: -{p.ATTACK_BRAND:.2f} brand across the "
                f"coalition, your standing +{p.ATTACK_STANDING:.2f}; "
                f"whiff -{p.ATTACK_WHIFF:.2f}")
    if kind == "amend" and state.current_bill is not None:
        import numpy as np
        d = float(np.linalg.norm(p.AMEND_STEP
                                 * (np.asarray(me.pos)
                                    - np.asarray(state.current_bill.pos))))
        return f"the {state.current_bill.name} would move ~{d:.2f} toward you"
    if kind == "table":
        return (f"a bill on your ground ({me.pos[0]:+.1f},{me.pos[1]:+.1f}), "
                "your name in the record — the whole week")
    if kind == "platform":
        pt = state.parties.get(me.party)
        if pt is None:
            return blurb
        return (f"the platform pulls ~5% toward you "
                f"(now {pt.platform[0]:+.2f},{pt.platform[1]:+.2f})")
    if kind == "budget":
        cur = ["austerity", "balanced", "stimulus"][state.government.budget_stance]
        return f"the books currently read '{cur}' — signal a different posture"
    if kind == "deal":
        return (f"promise your column — they bank +{p.DEAL_REL:.2f} regard "
                "and the whip sees the pledge")
    if kind == "vote":
        return "the pending division — 'why?' decomposes it"
    if kind == "defect":
        return (f"betrayal +{p.DEFECT_BETRAYAL:.2f} in your seat, standing "
                "resets — pick where you land")
    if kind == "found":
        from .parties import _stay_utility
        old = me.party
        followers = [m.id for m in state.mps.values()
                     if m.party == old and m.id != me.id
                     and m.id != state.government.pm
                     and m.relationships.get(me.id, 0.0) >= p.FOUND_REL_MIN
                     and _stay_utility(state, m) < p.PARTY_FORM_STAY_UTILITY]
        return f"{len(followers)} colleagues would walk out with you"
    if kind == "challenge":
        from .courts import challengeable
        n = len(challengeable(state))
        return f"{n} statute(s) are contestable — risk shows on the pick"
    if kind == "appoint":
        return f"{len(state.bench_shortlist)} nominee(s) wait — lean and activism show on the pick"
    return blurb
