"""The weekly pipeline. tick(state, actions) -> events for the week."""
from __future__ import annotations

import numpy as np

from . import params as p
from .actions import apply_action, evaluate_promises
from .career import (assign_portfolios, check_ambition, junior_lifecycle,
                     leadership_challenge, ministerial_lifecycle, mp_lifecycle,
                     speaker_election, update_score)
from .conditions import conditions_lifecycle
from .courts import courts_lifecycle
from .election import publish_poll, resolve_election
from .government import (call_election, collapse, resolve_formation,
                         strategic_call)
from .media import media_lifecycle
from .parliament import resolve_vote, table_bill
from .parties import party_lifecycle
from .scandals import scandal_lifecycle
from .state import Event, GameState
from .treasury import treasury_lifecycle


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
        publish_poll(state)
        if state.weeks_to_election <= 0:
            state.phase = "election"
            evaluate_promises(state)
            resolve_election(state)
            if state.phase != "over":
                update_score(state)
                state.phase = "formation"

    elif state.phase == "formation":
        if resolve_formation(state, actions or []):
            assign_portfolios(state)
            state.phase = "governing"
            publish_poll(state)
        # else: offers on the table — the house bargains one more week

    elif state.phase == "governing":
        state.government.weeks_in_office += 1
        # the pending division resolves first — the player saw it all week;
        # then the government tables next week's business
        pv = next((a.vote for a in (actions or [])
                   if a.kind == "vote" and a.vote is not None), None)
        if state.current_bill is not None:
            bill = state.current_bill
            res = resolve_vote(state, bill, player_vote=pv)
            if res is False and bill.confidence:
                # a lost confidence/supply division falls the government —
                # a stall (None) carries the bill, not the cabinet
                collapse(state, "supply" if bill.budget else "confidence")
        # a stalled division carries — no new bill; a fallen government
        # tables nothing (collapse drops current_bill and the phase together)
        if state.current_bill is None and state.phase == "governing":
            table_bill(state)
        # insolvency's forced confidence fires from treasury_lifecycle — immediate
        if state.phase == "governing":
            publish_poll(state)     # a sponsor prints the week's numbers
            strategic_call(state)   # the PM reads the published poll
        if state.phase == "governing" and state.government.weeks_in_office >= p.GOVERNING_WEEKS_PER_TERM:
            call_election(state, snap=False, reason="scheduled")

    if state.phase != "over":
        mp_lifecycle(state)
        party_lifecycle(state)
        leadership_challenge(state)
        scandal_lifecycle(state)   # last: dirt settles after the week's politics
        ministerial_lifecycle(state)  # reshuffles sweep up every kind of vacancy
        junior_lifecycle(state)       # party benches refill — in power or out
        speaker_election(state)       # a vacant chair goes to a house vote
        courts_lifecycle(state)    # the bench sits even when parliament doesn't
        conditions_lifecycle(state)  # the country drifts before the press reads it
        treasury_lifecycle(state)    # the books settle on this week's conditions
        media_lifecycle(state, base)  # the press reads the whole week back
    check_ambition(state)          # resolves on the fatal week too
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
