"""The weekly pipeline. tick(state, actions) -> events for the week."""
from __future__ import annotations

import numpy as np

from . import params as p
from .actions import apply_action, evaluate_promises
from .career import (assign_portfolios, leadership_challenge,
                     mp_lifecycle, update_score)
from .election import poll, resolve_election
from .government import confidence_vote, form_government
from .media import media_lifecycle
from .parliament import resolve_vote, table_bill
from .parties import party_lifecycle
from .scandals import scandal_lifecycle
from .state import Event, GameState


def tick(state: GameState, actions: list | None = None) -> list[Event]:
    """One week. Player actions already applied by caller; this drives the world."""
    base = len(state.log)
    state.week += 1

    for action in (actions or []):
        apply_action(state, action)
    if state.phase == "over":
        return state.log[base:]

    if state.phase == "campaign":
        state.weeks_to_election -= 1
        state.emit("PollShift", "Weekly poll.", shares=poll(state))
        if state.weeks_to_election <= 0:
            state.phase = "election"
            evaluate_promises(state)
            resolve_election(state)
            if state.phase != "over":
                update_score(state)
                state.phase = "formation"

    elif state.phase == "formation":
        form_government(state)
        assign_portfolios(state)
        state.phase = "governing"
        state.emit("PollShift", "Post-formation poll.", shares=poll(state))

    elif state.phase == "governing":
        state.government.weeks_in_office += 1
        bill = table_bill(state)
        resolve_vote(state, bill)
        if state.week % p.BUDGET_EVERY_WEEKS == 0:
            confidence_vote(state)
        if state.phase != "over" and state.government.weeks_in_office >= p.GOVERNING_WEEKS_PER_TERM:
            state.emit("ElectionCalled", "Term ends — election called.")
            state.phase = "campaign"
            state.weeks_to_election = 8

    if state.phase != "over":
        mp_lifecycle(state)
        party_lifecycle(state)
        leadership_challenge(state)
        scandal_lifecycle(state)   # last: dirt settles after the week's politics
        media_lifecycle(state, base)  # the press reads the whole week back
    _drift(state)
    return state.log[base:]


def _drift(state: GameState) -> None:
    """Weekly environment drift: voters wander, MPs feel constituency pull, decays."""
    rng = np.random.default_rng(int(state.rng.random() * 2**63))
    state.voters.pos += rng.normal(0, p.VOTER_DRIFT_SD, state.voters.pos.shape)
    np.clip(state.voters.pos, -1, 1, out=state.voters.pos)
    v = state.voters  # agenda-setting lifts salience; it must mean-revert
    v.salience += p.SALIENCE_REVERT * (p.SALIENCE_BASE - v.salience)
    np.clip(v.salience, 0.1, None, out=v.salience)
    for pt in state.parties.values():
        pt.brand = float(np.clip(pt.brand * p.BRAND_DECAY, -1, 1))  # reputation is bounded
        pt.schism_cooldown = max(0, pt.schism_cooldown - 1)
    for mp in state.mps.values():
        if mp.id != state.player_id:  # the player's ideology is theirs to manage
            dcent = state.voters.pos[state.voters.district == mp.district].mean(axis=0)
            mp.pos = tuple(np.clip(np.asarray(mp.pos) + p.MP_DISTRICT_PULL * (dcent - mp.pos), -1, 1))
        for k in mp.relationships:
            mp.relationships[k] *= p.REL_DECAY
