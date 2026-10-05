"""FPTP district elections: vectorized voter scoring, winner takes the seat."""
from __future__ import annotations

import numpy as np

from . import params as p
from .career import remove_mp
from .conditions import mood, responsibility
from .state import GameState, Hopeful, MP
from .naming import mp_name

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


def _district_scores(state: GameState, mask: np.ndarray, cand_pos: dict, incumbent: MP | None) -> tuple[np.ndarray, list]:
    """score[voter, party] = -salience-weighted dist to perceived pos + brand + loyalty - betrayal + noise."""
    v = state.voters
    dpos, dsal = v.pos[mask], v.salience[mask]
    parties = sorted(cand_pos)
    score = np.empty((dpos.shape[0], len(parties)))
    for j, pid in enumerate(parties):
        if pid == INDEPENDENT:
            # no label, no brand, no loyalty — voters score the person directly
            d = dpos - np.asarray(cand_pos[pid])
            score[:, j] = -np.sqrt((d * d * dsal).sum(axis=1))
            if incumbent and incumbent.party is None:
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
        if incumbent and incumbent.party == pid:
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
    incumbents = {m.district: m for m in state.mps.values()}
    next_id = max(state.mps) + 1

    for d in range(n_districts):
        inc = incumbents.get(d)
        cand, cand_h = {}, {}
        for pid in state.parties:
            cand[pid], cand_h[pid] = _candidate(state, d, pid, inc)
        inc_indep = inc is not None and inc.party is None
        if inc_indep or state.rng.random() < p.INDEPENDENT_P:
            centroid = v.pos[v.district == d].mean(axis=0)
            cand[INDEPENDENT] = (inc.pos if inc_indep else tuple(float(np.clip(
                c + state.rng.gauss(0, p.INDEPENDENT_POS_SD), -1, 1)) for c in centroid))
        mask = (v.district == d) & turnout_hit
        if not mask.any():  # nobody voted — incumbent survives, else district's nearest party
            if inc is not None:
                winner = inc.party if inc.party is not None else INDEPENDENT
                margin = 0.0
            else:
                centroid = v.pos[v.district == d].mean(axis=0)
                winner = min(state.parties.values(),
                             key=lambda pt: float(np.hypot(*(centroid - pt.platform)))).id
                margin = 0.0
        else:
            score, parties = _district_scores(state, mask, cand, inc)
            picks = score.argmax(axis=1)
            tally = np.bincount(picks, minlength=len(parties))
            winner = parties[int(tally.argmax())]
            runner_up = np.sort(tally)[-2] if len(parties) > 1 else 0
            margin = float((tally.max() - runner_up) / max(tally.sum(), 1))
            # loyalty attaches to the party each voter actually backed
            v.last_party[mask] = np.asarray(parties)[picks]
        seat_counts[winner] = seat_counts.get(winner, 0) + 1

        retained = inc is not None and (
            inc.party == winner or (inc.party is None and winner == INDEPENDENT))
        if retained:
            inc.seat_safety = margin
            new_mps[inc.id] = inc
        else:
            if inc is not None:
                remove_mp(state, inc)
            hopeful = cand_h.get(winner)
            if hopeful is not None:
                mp = MP(id=next_id, name=hopeful.name, pos=hopeful.pos,
                        ambition=hopeful.ambition, loyalty=hopeful.loyalty,
                        competence=hopeful.competence, integrity=hopeful.integrity,
                        district=d, party=winner, seat_safety=margin, age=hopeful.age)
                state.hopefuls.remove(hopeful)
                state.emit("Newcomer", f"{mp.name}, {mp.age // 52}, wins their first seat "
                                       f"in district {d} for {state.parties[winner].name}.",
                           mp=next_id, district=d, party=winner, age=mp.age)
            else:
                stat = lambda: min(1, max(0, state.rng.gauss(0.5, p.MP_STAT_SD)))
                mp = MP(id=next_id, name=mp_name(state.rng),
                        pos=cand[winner], ambition=stat(), loyalty=stat(),
                        competence=stat(), integrity=stat(), district=d,
                        party=None if winner == INDEPENDENT else winner,
                        seat_safety=margin, age=state.rng.randint(1400, 2600))
                if winner == INDEPENDENT:
                    state.emit("Newcomer", f"{mp.name}, {mp.age // 52}, wins district {d} "
                                           "as an independent.", mp=next_id, district=d)
            if winner != INDEPENDENT:
                state.parties[winner].members.add(next_id)
                state.parties[winner].seated = True
            new_mps[next_id] = mp
            next_id += 1

    player_lost = state.player_id not in new_mps
    if player_lost:
        state.phase = "over"
        state.emit("SeatLost", "You lost your seat.", district=incumbents[state.player_id].district)
    state.mps = new_mps
    state.government.collapses = 0
    state.government.blocked = set()  # a new parliament, a new bargaining table
    state.government.sacked = set()   # a fresh cabinet may bring anyone back
    for pt in state.parties.values():  # leaders who lost their seat leave a dead reference
        if pt.leader not in state.mps:
            pt.leader = max(pt.members, key=lambda m: state.mps[m].ambition) if pt.members else None
    state.emit("ElectionResult", "Election resolved.",
               seats={"ind" if k == INDEPENDENT else k: n for k, n in seat_counts.items()})


def poll(state: GameState) -> dict[int, float]:
    """Weekly poll: national vote share of decided voters, turnout-weighted."""
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
    return {pid: float(pick[i] / max(decided.sum(), 1)) for i, pid in enumerate(parties)}
