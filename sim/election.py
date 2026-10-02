"""FPTP district elections: vectorized voter scoring, winner takes the seat."""
from __future__ import annotations

import numpy as np

from . import params as p
from .state import GameState, MP

_FIRST = "Ash Brook Cole Dawn Elm Fern Gale Hale Iris Jade Kite Lark Moss Nell Onyx Pine Reed Sage Teal Wren".split()
_LAST = "Barton Croft Dale Ellis Frost Grange Holt Ingram Marsh North Pace Quill Rook Shore Vale West York".split()


def _candidate_pos(state: GameState, district: int, party_id: int, incumbent: MP | None) -> tuple[float, float]:
    """Incumbent MP runs again; otherwise a placeholder candidate at the party platform."""
    if incumbent and incumbent.party == party_id:
        return incumbent.pos
    plat = state.parties[party_id].platform
    return (float(np.clip(plat[0] + state.rng.gauss(0, p.MP_POS_JITTER), -1, 1)),
            float(np.clip(plat[1] + state.rng.gauss(0, p.MP_POS_JITTER), -1, 1)))


def _district_scores(state: GameState, mask: np.ndarray, cand_pos: dict, incumbent: MP | None) -> tuple[np.ndarray, list]:
    """score[voter, party] = -salience-weighted distance + loyalty - betrayal + noise."""
    v = state.voters
    dpos, dsal = v.pos[mask], v.salience[mask]
    parties = sorted(cand_pos)
    score = np.empty((dpos.shape[0], len(parties)))
    for j, pid in enumerate(parties):
        d = dpos - np.asarray(cand_pos[pid])
        score[:, j] = -np.sqrt((d * d * dsal).sum(axis=1))
        score[:, j] += p.LOYALTY_WEIGHT * v.loyalty[mask] * (v.last_party[mask] == pid)
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
        inc = incumbents[d]
        cand = {pid: _candidate_pos(state, d, pid, inc) for pid in state.parties}
        mask = (v.district == d) & turnout_hit
        if not mask.any():  # nobody voted — incumbent survives by default
            winner = inc.party
            margin = 0.0
        else:
            score, parties = _district_scores(state, mask, cand, inc)
            tally = np.bincount(score.argmax(axis=1), minlength=len(parties))
            winner = parties[int(tally.argmax())]
            margin = float((tally.max() - np.sort(tally)[-2]) / max(tally.sum(), 1))
        seat_counts[winner] = seat_counts.get(winner, 0) + 1
        v.last_party[v.district == d] = winner

        if inc.party == winner:
            inc.seat_safety = margin
            new_mps[inc.id] = inc
        else:
            state.parties[inc.party].members.discard(inc.id)
            stat = lambda: min(1, max(0, state.rng.gauss(0.5, p.MP_STAT_SD)))
            mp = MP(id=next_id, name=f"{state.rng.choice(_FIRST)} {state.rng.choice(_LAST)}",
                    pos=cand[winner], ambition=stat(), loyalty=stat(),
                    competence=stat(), integrity=stat(), district=d, party=winner,
                    seat_safety=margin)
            state.parties[winner].members.add(next_id)
            new_mps[next_id] = mp
            next_id += 1

    player_lost = state.player_id not in new_mps
    if player_lost:
        state.phase = "over"
        state.emit("SeatLost", "You lost your seat.", district=incumbents[state.player_id].district)
    state.mps = new_mps
    state.emit("ElectionResult", "Election resolved.", seats=seat_counts)


def poll(state: GameState) -> dict[int, float]:
    """Weekly poll: national vote share of decided voters, turnout-weighted."""
    v = state.voters
    decided = v.turnout > 0.3
    plats = {pid: np.asarray(pt.platform) for pid, pt in state.parties.items()}
    parties = sorted(plats)
    score = np.empty((int(decided.sum()), len(parties)))
    dpos, dsal = v.pos[decided], v.salience[decided]
    for j, pid in enumerate(parties):
        d = dpos - plats[pid]
        score[:, j] = -np.sqrt((d * d * dsal).sum(axis=1))
        score[:, j] += p.LOYALTY_WEIGHT * v.loyalty[decided] * (v.last_party[decided] == pid)
    pick = np.bincount(score.argmax(axis=1), minlength=len(parties))
    return {pid: float(pick[i] / max(decided.sum(), 1)) for i, pid in enumerate(parties)}
