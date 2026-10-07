"""FPTP district elections: vectorized voter scoring, winner takes the seat."""
from __future__ import annotations

import math
import random

import numpy as np

from . import params as p
from .career import remove_mp, successor
from .conditions import mood, responsibility
from .state import GameState, Hopeful, MP, dist, district_centroid
from .naming import mp_name
from .prose import render

INDEPENDENT = -1  # sentinel pid in the district tally — keeps last_party int-typed


def _candidate(state: GameState, district: int, party_id: int,
               incumbent: MP | None, rnd: random.Random | None = None
               ) -> tuple[tuple[float, float], Hopeful | None]:
    """Candidate for a party in a district: incumbent, eligible hopeful, or platform placeholder."""
    rnd = rnd if rnd is not None else state.rng
    if incumbent and incumbent.party == party_id:
        return incumbent.pos, None
    for h in state.hopefuls:
        if h.party == party_id and h.district == district and h.age >= p.MIN_MP_AGE:
            return h.pos, h
    plat = np.asarray(state.parties[party_id].platform)  # the person is real; the label is perceived
    return (float(np.clip(plat[0] + rnd.gauss(0, p.MP_POS_JITTER), -1, 1)),
            float(np.clip(plat[1] + rnd.gauss(0, p.MP_POS_JITTER), -1, 1))), None


def _ballot(state: GameState, d: int, incs: list, rnd: random.Random
            ) -> tuple[dict, dict]:
    """Who stands in a district: cand positions + the named roster voters see."""
    cand: dict[int, tuple] = {}
    ballot: dict[int, dict] = {}
    spk = next((i for i in incs if i.id == state.speaker), None)
    if spk is not None and state.district_magnitude == 1:
        # the chair stands unopposed by convention — a seat for life
        cand[INDEPENDENT] = spk.pos
        ballot[INDEPENDENT] = {"name": spk.name, "incumbent": True}
        return cand, ballot
    for pid in state.parties:
        inc_p = next((i for i in incs if i.party == pid), None)
        pos, hopeful = _candidate(state, d, pid, inc_p, rnd)
        cand[pid] = pos
        ballot[pid] = {
            "name": (inc_p.name if inc_p is not None
                     else hopeful.name if hopeful is not None
                     else mp_name(rnd, state.name_pack)),
            "incumbent": inc_p is not None}
    inc_indep = next((i for i in incs if i.party is None), None)
    if inc_indep is not None or rnd.random() < p.INDEPENDENT_P:
        centroid = district_centroid(state.voters, d)
        cand[INDEPENDENT] = (inc_indep.pos if inc_indep is not None else tuple(float(np.clip(
            c + rnd.gauss(0, p.INDEPENDENT_POS_SD), -1, 1)) for c in centroid))
        ballot[INDEPENDENT] = {
            "name": inc_indep.name if inc_indep is not None
                    else mp_name(rnd, state.name_pack),
            "incumbent": inc_indep is not None}
    return cand, ballot


def _seat_alloc(tally: np.ndarray, parties: list, mag: int
                ) -> tuple[dict[int, int], float, dict[int, float]]:
    """Seats per candidate from a vote tally: FPTP winner-take-all at mag 1,
    largest remainder above it — proportionality keeps small parties alive
    where FPTP starves them. Returns (won, margin, share-for-safety)."""
    total = max(int(tally.sum()), 1)
    if mag == 1:
        winner = parties[int(tally.argmax())]
        runner_up = np.sort(tally)[-2] if len(parties) > 1 else 0
        return {winner: 1}, float((tally.max() - runner_up) / total), {}
    exact = tally * mag / total
    base = {parties[i]: int(exact[i]) for i in range(len(parties))}
    if INDEPENDENT in base:
        base[INDEPENDENT] = min(base[INDEPENDENT], 1)  # one person, one seat
    won = {k: n for k, n in base.items() if n}
    rem = mag - sum(won.values())
    order = np.argsort(-(exact - np.floor(exact)), kind="stable")
    for i in order:
        if rem <= 0:
            break
        pid = parties[int(i)]
        if pid == INDEPENDENT and won.get(pid, 0) >= 1:
            continue
        won[pid] = won.get(pid, 0) + 1
        rem -= 1
    margin = (float(exact.max() - np.sort(exact)[-2]) / mag
              if len(parties) > 1 else 0.0)
    share = {pid: float(exact[i]) / mag for i, pid in enumerate(parties)}
    return won, margin, share


def _district_scores(state: GameState, mask: np.ndarray, cand_pos: dict,
                     incumbents: list, rnd: random.Random | None = None,
                     noise: bool = True) -> tuple[np.ndarray, list]:
    """score[voter, party] = -salience-weighted dist to perceived pos + brand + loyalty - betrayal + noise."""
    v = state.voters
    dpos, dsal = v.pos[mask], v.salience[mask]
    parties = sorted(cand_pos)
    inc_parties = {i.party for i in incumbents}
    # the published poll is the viability signal: voters desert candidates
    # the country has already counted out — Duverger's desertion term
    poll_sh = (state.last_poll or {}).get("shares") or {}
    viable = lambda pid: p.VIABILITY_WEIGHT * math.log(
        poll_sh.get(pid, 0.0) + p.VIABILITY_EPS)
    score = np.empty((dpos.shape[0], len(parties)))
    for j, pid in enumerate(parties):
        if pid == INDEPENDENT:
            # no label, no brand, no loyalty — voters score the person directly
            d = dpos - np.asarray(cand_pos[pid])
            score[:, j] = -np.sqrt((d * d * dsal).sum(axis=1))
            if None in inc_parties:
                score[:, j] += p.INCUMBENT_BONUS
                score[:, j] -= v.betrayal[mask]  # betrayal sticks to the person too
            # polls never name independents — they pay the full desertion floor
            score[:, j] += viable(pid)
            continue
        pt = state.parties[pid]
        # the candidate is a person; the label is a media-constructed caricature
        eff = ((1 - p.PUB_POS_MIX) * np.asarray(cand_pos[pid])
               + p.PUB_POS_MIX * np.asarray(pt.pub_pos))
        d = dpos - eff
        score[:, j] = -np.sqrt((d * d * dsal).sum(axis=1))
        score[:, j] += p.BRAND_WEIGHT * pt.brand
        score[:, j] += p.LOYALTY_WEIGHT * v.loyalty[mask] * (v.last_party[mask] == pid)
        score[:, j] += p.RETRO_WEIGHT * mood(state.conditions) * responsibility(state, pid)
        score[:, j] += viable(pid)
        if pid in inc_parties:
            score[:, j] += p.INCUMBENT_BONUS  # the personal vote — a known name
            score[:, j] -= v.betrayal[mask]   # broken promises bite the incumbent's party
    if noise:
        rnd = rnd if rnd is not None else state.rng
        score += np.random.default_rng(
            int(rnd.random() * 2**63)).normal(0, p.VOTE_NOISE_SD, score.shape)
    return score, parties


def resolve_election(state: GameState) -> None:
    v = state.voters
    n_districts = int(v.district.max()) + 1
    seat_counts: dict[int, int] = {}
    nat_votes: dict[int, int] = {}
    rng = np.random.default_rng(int(state.rng.random() * 2**63))
    turnout_hit = rng.random(len(v.pos)) < np.clip(
        v.turnout + rng.normal(0, p.TURNOUT_MODEL_NOISE, len(v.pos)), 0, 1)
    new_mps: dict[int, MP] = {}
    player_district = state.mps[state.player_id].district
    prev_seats: dict = {}
    incumbents: dict[int, list[MP]] = {}
    for m in state.mps.values():
        prev_seats["ind" if m.party is None else m.party] = \
            prev_seats.get("ind" if m.party is None else m.party, 0) + 1
        incumbents.setdefault(m.district, []).append(m)
    next_id = max(state.mps) + 1
    mag = state.district_magnitude

    for d in range(n_districts):
        incs = incumbents.get(d, [])
        cand, ballot = _ballot(state, d, incs, state.rng)
        mask = (v.district == d) & turnout_hit
        share: dict[int, float] = {}
        votes: dict[int, int] = {}
        if not mask.any():  # nobody voted — incumbents survive, else nearest party takes all
            if incs:
                won: dict[int, int] = {}
                for i in incs:
                    won[i.party if i.party is not None else INDEPENDENT] = \
                        won.get(i.party if i.party is not None else INDEPENDENT, 0) + 1
                while sum(won.values()) < mag:
                    centroid = district_centroid(v, d)
                    near = min(state.parties.values(),
                               key=lambda pt: float(np.hypot(*(centroid - pt.platform)))).id
                    won[near] = won.get(near, 0) + 1
            else:
                centroid = district_centroid(v, d)
                winner = min(state.parties.values(),
                             key=lambda pt: float(np.hypot(*(centroid - pt.platform)))).id
                won = {winner: mag}
            margin = 0.0
        else:
            score, parties = _district_scores(state, mask, cand, incs)
            picks = score.argmax(axis=1)
            tally = np.bincount(picks, minlength=len(parties))
            votes = {parties[i]: int(tally[i]) for i in range(len(parties))}
            won, margin, share = _seat_alloc(tally, parties, mag)
            # loyalty attaches to the party each voter actually backed
            v.last_party[mask] = np.asarray(parties)[picks]

        unseated = list(incs)
        unseated.sort(key=lambda i: i.id != state.player_id)  # your seat defends first
        for pid, nv in votes.items():
            nat_votes[pid] = nat_votes.get(pid, 0) + nv
        for winner, k in won.items():
            seat_counts[winner] = seat_counts.get(winner, 0) + k
            safety = share.get(winner, margin)
            for _ in range(k):
                kept = next((i for i in unseated
                             if (i.party if i.party is not None else INDEPENDENT) == winner),
                            None)
                if kept is not None:
                    kept.seat_safety = safety
                    new_mps[kept.id] = kept
                    unseated.remove(kept)
                    continue
                hopeful = next((h for h in state.hopefuls
                                if h.party == winner and h.district == d
                                and h.age >= p.MIN_MP_AGE), None)
                if hopeful is not None:
                    mp = MP(id=next_id, name=hopeful.name, pos=hopeful.pos,
                            ambition=hopeful.ambition, loyalty=hopeful.loyalty,
                            competence=hopeful.competence, integrity=hopeful.integrity,
                            district=d, party=winner, seat_safety=safety, age=hopeful.age)
                    state.hopefuls.remove(hopeful)
                    state.emit("Newcomer", f"{mp.name}, {mp.age // 52}, wins their first seat "
                                           f"in district {d} for {state.parties[winner].name}.",
                               mp=next_id, district=d, party=winner, age=mp.age)
                else:
                    stat = lambda: min(1, max(0, state.rng.gauss(0.5, p.MP_STAT_SD)))
                    mp = MP(id=next_id, name=mp_name(state.rng, state.name_pack),
                            pos=cand[winner], ambition=stat(), loyalty=stat(),
                            competence=stat(), integrity=stat(), district=d,
                            party=None if winner == INDEPENDENT else winner,
                            seat_safety=safety, age=state.rng.randint(1400, 2600))
                    if winner == INDEPENDENT:
                        state.emit("Newcomer", f"{mp.name}, {mp.age // 52}, wins district {d} "
                                               "as an independent.", mp=next_id, district=d)
                if winner != INDEPENDENT:
                    state.parties[winner].members.add(next_id)
                    state.parties[winner].seated = True
                new_mps[next_id] = mp
                next_id += 1
        for i in unseated:
            remove_mp(state, i)
        kept_ids = [i.id for i in incs if i.id in new_mps]
        # the race as it was run — names, votes, who held the seat
        cand_rows = [{"name": ballot[pid]["name"],
                      "party": pid,
                      "votes": votes.get(pid, 0),
                      "share": votes.get(pid, 0) / max(int(mask.sum()), 1),
                      "incumbent": ballot[pid]["incumbent"],
                      "won": won.get(pid, 0) > 0}
                     for pid in ballot]
        cand_rows.sort(key=lambda c: -c["votes"])
        pname = lambda w: (state.parties[w].name
                           if w != INDEPENDENT else "independent")
        if len(cand_rows) >= 2:
            a, b = cand_rows[0], cand_rows[1]
            what = ("holds" if a["incumbent"] and a["won"]
                    else "gains" if a["won"] else "takes")
            text = (f"District {d}: {a['name']} {a['votes']}, "
                    f"{b['name']} {b['votes']} — "
                    f"{pname(cand_rows[0]['party'])} {what} "
                    f"by {a['votes'] - b['votes']}")
        else:
            text = f"District {d}: " + ", ".join(
                f"{pname(w)} {k}" for w, k in won.items())
        state.emit("DistrictResult", text,
                   district=d, winners=dict(won), candidates=cand_rows,
                   turnout=int(mask.sum()),
                   prev=[i.party if i.party is not None else "ind" for i in incs],
                   flipped=len(kept_ids) < len(incs), margin=float(margin),
                   retained=kept_ids)

    player_lost = state.player_id not in new_mps
    if player_lost:
        state.phase = "over"
        state.emit("SeatLost", "You lost your seat.", district=player_district)
    state.mps = new_mps
    state.government.collapses = 0
    state.government.blocked = set()  # a new parliament, a new bargaining table
    state.government.sacked = set()   # a fresh cabinet may bring anyone back
    for pt in state.parties.values():  # leaders who lost their seat leave a dead reference
        if pt.leader not in state.mps:
            pt.leader = successor(state, pt) if pt.members else None
    state.emit("ElectionResult",
               render(state, "ElectionResult", country=state.country),
               seats={"ind" if k == INDEPENDENT else k: n for k, n in seat_counts.items()},
               votes={"ind" if k == INDEPENDENT else k: n for k, n in nat_votes.items()},
               prev=prev_seats)


def _forecast_rng(state: GameState, d: int) -> random.Random:
    """A stream fork for projections: seeded off the world, never touching
    state.rng — reading a forecast cannot butterfly the run it describes.
    The str seed hashes through sha512, stable across processes."""
    return random.Random(f"{state.seed}:{state.week}:{d}:forecast")


def district_forecast(state: GameState, d: int) -> dict:
    """The race as it would be run today: roster, projected votes, margin.
    Deterministic on world state — a forecast called twice is the same
    projection, and it mutates nothing."""
    v = state.voters
    rnd = _forecast_rng(state, d)
    incs = [m for m in state.mps.values() if m.district == d]
    cand, ballot = _ballot(state, d, incs, rnd)
    nprng = np.random.default_rng(int(rnd.random() * 2**63))
    turnout_hit = nprng.random(len(v.pos)) < np.clip(
        v.turnout + nprng.normal(0, p.TURNOUT_MODEL_NOISE, len(v.pos)), 0, 1)
    mask = (v.district == d) & turnout_hit
    votes: dict[int, int] = {}
    won: dict[int, int] = {}
    margin = 0.0
    if mask.any():
        score, parties = _district_scores(state, mask, cand, incs, rnd,
                                          noise=False)
        picks = score.argmax(axis=1)
        tally = np.bincount(picks, minlength=len(parties))
        votes = {parties[i]: int(tally[i]) for i in range(len(parties))}
        won, margin, _share = _seat_alloc(tally, parties, state.district_magnitude)
    total = max(int(mask.sum()), 1)
    rows = [{"name": ballot[pid]["name"], "party": pid,
             "votes": votes.get(pid, 0), "share": votes.get(pid, 0) / total,
             "incumbent": ballot[pid]["incumbent"],
             "won": won.get(pid, 0) > 0}
            for pid in ballot]
    rows.sort(key=lambda c: -c["votes"])
    return {"district": d, "candidates": rows, "turnout": int(mask.sum()),
            "margin": margin, "winners": won}


def battleground(state: GameState) -> dict:
    """Every district's projection, tightest first, plus the seat forecast —
    the swingometer view: which seats a small shift in support can move."""
    n_districts = int(state.voters.district.max()) + 1
    player_d = state.mps[state.player_id].district if state.player_id in state.mps else None
    rows, seats = [], {}
    for d in range(n_districts):
        f = district_forecast(state, d)
        incs = [m.party if m.party is not None else "ind"
                for m in state.mps.values() if m.district == d]
        for pid, k in f["winners"].items():
            key = "ind" if pid == INDEPENDENT else pid
            seats[key] = seats.get(key, 0) + k
        lead = f["candidates"][0] if f["candidates"] else None
        rows.append({"district": d, "margin": f["margin"],
                     "leader": lead["party"] if lead else None,
                     "you": d == player_d,
                     "held_by": incs})
    rows.sort(key=lambda r: r["margin"])
    return {"districts": rows, "seats": seats, "player_district": player_d}


def poll(state: GameState, outlet=None) -> dict[int, float]:
    """Weekly poll: national vote share of decided voters, turnout-weighted.
    With an outlet, a bounded house effect tilts the result toward parties
    near its slant — a sponsor leans a few points, it doesn't re-elect.
    The ground-truth oracle is `poll(state)` with no outlet."""
    v = state.voters
    decided = v.turnout > 0.3
    ppos = {pid: np.asarray(pt.pub_pos) for pid, pt in state.parties.items()}
    parties = sorted(ppos)
    score = np.empty((int(decided.sum()), len(parties)))
    dpos, dsal = v.pos[decided], v.salience[decided]
    for j, pid in enumerate(parties):
        d = dpos - ppos[pid]
        score[:, j] = -np.sqrt((d * d * dsal).sum(axis=1))
        score[:, j] += p.BRAND_WEIGHT * state.parties[pid].brand
        score[:, j] += p.LOYALTY_WEIGHT * v.loyalty[decided] * (v.last_party[decided] == pid)
        score[:, j] += p.RETRO_WEIGHT * mood(state.conditions) * responsibility(state, pid)
    pick = np.bincount(score.argmax(axis=1), minlength=len(parties))
    total = max(int(decided.sum()), 1)
    shares = {pid: float(pick[i] / total) for i, pid in enumerate(parties)}
    if outlet is None:
        return shares
    # house effect: the tilt direction is slant-affinity, the magnitude is a
    # few points — the number still tracks the real electorate underneath
    aff = {pid: float(np.exp(-float(dist(outlet.slant, ppos[pid])) ** 2
                             / (2 * p.AUDIENCE_AFFINITY_SD ** 2)))
           for pid in parties}
    c = sum(aff.values()) / len(aff)
    tilted = {pid: max(shares[pid] + p.POLL_HOUSE_BIAS * (aff[pid] - c), 0.0)
              for pid in parties}
    t = sum(tilted.values()) or 1.0
    return {pid: s_ / t for pid, s_ in tilted.items()}


def publish_poll(state: GameState) -> None:
    """An outlet prints the week's numbers — a rotating sponsor, a biased
    sample, a stamp. `state.last_poll` is what the country *read*, not what
    the electorate *is* — the snap gate reads the published number."""
    o = state.outlets[state.week % len(state.outlets)] if state.outlets else None
    shares = poll(state, outlet=o)
    state.last_poll = {"shares": shares, "week": state.week,
                       "outlet": o.id if o else None}
    state.emit("PollShift",
               f"{o.name} poll." if o else "Weekly poll.",
               shares=shares, outlet=state.last_poll["outlet"])
