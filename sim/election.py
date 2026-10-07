"""FPTP district elections: vectorized voter scoring, winner takes the seat."""
from __future__ import annotations

import numpy as np

from . import params as p
from .career import remove_mp
from .conditions import mood, responsibility
from .state import GameState, Hopeful, MP, dist
from .naming import mp_name
from .prose import render

INDEPENDENT = -1  # sentinel pid in the district tally — keeps last_party int-typed


def _candidate(state: GameState, district: int, party_id: int,
               incumbent: MP | None) -> tuple[tuple[float, float], Hopeful | None]:
    """Candidate for a party in a district: incumbent, eligible hopeful, or platform placeholder."""
    if incumbent and incumbent.party == party_id:
        return incumbent.pos, None
    for h in state.hopefuls:
        if h.party == party_id and h.district == district and h.age >= p.MIN_MP_AGE:
            return h.pos, h
    plat = np.asarray(state.parties[party_id].platform)  # the person is real; the label is perceived
    return (float(np.clip(plat[0] + state.rng.gauss(0, p.MP_POS_JITTER), -1, 1)),
            float(np.clip(plat[1] + state.rng.gauss(0, p.MP_POS_JITTER), -1, 1))), None


def _district_scores(state: GameState, mask: np.ndarray, cand_pos: dict,
                     incumbents: list) -> tuple[np.ndarray, list]:
    """score[voter, party] = -salience-weighted dist to perceived pos + brand + loyalty - betrayal + noise."""
    v = state.voters
    dpos, dsal = v.pos[mask], v.salience[mask]
    parties = sorted(cand_pos)
    inc_parties = {i.party for i in incumbents}
    score = np.empty((dpos.shape[0], len(parties)))
    for j, pid in enumerate(parties):
        if pid == INDEPENDENT:
            # no label, no brand, no loyalty — voters score the person directly
            d = dpos - np.asarray(cand_pos[pid])
            score[:, j] = -np.sqrt((d * d * dsal).sum(axis=1))
            if None in inc_parties:
                score[:, j] -= v.betrayal[mask]  # betrayal sticks to the person too
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
        if pid in inc_parties:
            score[:, j] -= v.betrayal[mask]  # broken promises bite the incumbent's party
    score += np.random.default_rng(int(state.rng.random() * 2**63)).normal(0, p.VOTE_NOISE_SD, score.shape)
    return score, parties


def resolve_election(state: GameState) -> None:
    v = state.voters
    n_districts = int(v.district.max()) + 1
    seat_counts: dict[int, int] = {}
    rng = np.random.default_rng(int(state.rng.random() * 2**63))
    turnout_hit = rng.random(len(v.pos)) < np.clip(
        v.turnout + rng.normal(0, p.TURNOUT_MODEL_NOISE, len(v.pos)), 0, 1)
    new_mps: dict[int, MP] = {}
    player_district = state.mps[state.player_id].district
    incumbents: dict[int, list[MP]] = {}
    for m in state.mps.values():
        incumbents.setdefault(m.district, []).append(m)
    next_id = max(state.mps) + 1
    mag = state.district_magnitude

    for d in range(n_districts):
        incs = incumbents.get(d, [])
        cand = {}
        for pid in state.parties:
            inc_p = next((i for i in incs if i.party == pid), None)
            cand[pid] = _candidate(state, d, pid, inc_p)[0]
        inc_indep = next((i for i in incs if i.party is None), None)
        if inc_indep is not None or state.rng.random() < p.INDEPENDENT_P:
            centroid = v.pos[v.district == d].mean(axis=0)
            cand[INDEPENDENT] = (inc_indep.pos if inc_indep is not None else tuple(float(np.clip(
                c + state.rng.gauss(0, p.INDEPENDENT_POS_SD), -1, 1)) for c in centroid))
        mask = (v.district == d) & turnout_hit
        share: dict[int, float] = {}
        if not mask.any():  # nobody voted — incumbents survive, else nearest party takes all
            if incs:
                won: dict[int, int] = {}
                for i in incs:
                    won[i.party if i.party is not None else INDEPENDENT] = \
                        won.get(i.party if i.party is not None else INDEPENDENT, 0) + 1
                while sum(won.values()) < mag:
                    centroid = v.pos[v.district == d].mean(axis=0)
                    near = min(state.parties.values(),
                               key=lambda pt: float(np.hypot(*(centroid - pt.platform)))).id
                    won[near] = won.get(near, 0) + 1
            else:
                centroid = v.pos[v.district == d].mean(axis=0)
                winner = min(state.parties.values(),
                             key=lambda pt: float(np.hypot(*(centroid - pt.platform)))).id
                won = {winner: mag}
            margin = 0.0
        else:
            score, parties = _district_scores(state, mask, cand, incs)
            picks = score.argmax(axis=1)
            tally = np.bincount(picks, minlength=len(parties))
            total = max(int(tally.sum()), 1)
            if mag == 1:
                winner = parties[int(tally.argmax())]
                runner_up = np.sort(tally)[-2] if len(parties) > 1 else 0
                margin = float((tally.max() - runner_up) / total)
                won = {winner: 1}
            else:
                # largest remainder: seats split by vote share, remainders
                # fill the leftover seats — proportionality keeps small
                # parties alive where FPTP starves them
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
                margin = float(exact.max() - np.sort(exact)[-2] if len(parties) > 1 else 0)
                for i, pid in enumerate(parties):
                    share[pid] = float(exact[i]) / mag
            # loyalty attaches to the party each voter actually backed
            v.last_party[mask] = np.asarray(parties)[picks]

        unseated = list(incs)
        unseated.sort(key=lambda i: i.id != state.player_id)  # your seat defends first
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
        state.emit("DistrictResult",
                   f"District {d}: " + ", ".join(
                       f"{state.parties[w].name if w != INDEPENDENT else 'independent'} {k}"
                       for w, k in won.items()),
                   district=d, winners=dict(won),
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
            pt.leader = max(sorted(pt.members), key=lambda m: state.mps[m].ambition) if pt.members else None
    state.emit("ElectionResult",
               render(state, "ElectionResult", country=state.country),
               seats={"ind" if k == INDEPENDENT else k: n for k, n in seat_counts.items()})


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
