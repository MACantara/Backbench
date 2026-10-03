"""Dynamic party lifecycle: cohesion, defection, founding, schism, death."""
from __future__ import annotations

import numpy as np

from . import params as p
from .factions import update_factions
from .state import GameState, Party, dist


def update_cohesion(state: GameState) -> None:
    """Cohesion = mean ideological alignment of members to platform + leader loyalty."""
    for pt in state.parties.values():
        if not pt.members:
            pt.cohesion = 0.0
            continue
        align = np.mean([1 - dist(state.mps[m].pos, pt.platform) / 2 for m in pt.members])
        loyal = np.mean([state.mps[m].loyalty for m in pt.members])
        pt.cohesion = float(np.clip(align * 0.7 + loyal * 0.3, 0, 1))


def _next_party_id(state: GameState) -> int:
    return max(state.parties, default=-1) + 1


def _found(state: GameState, founder, followers: list[int]) -> int:
    pid = _next_party_id(state)
    name = f"{state.mps[founder].name.split()[-1]} List"
    pt = Party(id=pid, name=name, platform=state.mps[founder].pos, leader=founder)
    for mid in [founder, *followers]:
        old = state.mps[mid].party
        if old is not None and old in state.parties:
            state.parties[old].members.discard(mid)
        state.mps[mid].party = pid
        state.mps[mid].faction = None
        pt.members.add(mid)
    state.parties[pid] = pt
    state.emit("PartyFormed", f"{name} founded by {state.mps[founder].name} ({len(pt.members)} MPs).",
               party=pid, founder=founder, size=len(pt.members))
    return pid


def _stay_utility(state: GameState, mp) -> float:
    """How attractive staying in the current party is."""
    pt = state.parties[mp.party]
    return (pt.cohesion * 0.5
            + max(0, 1 - dist(mp.pos, pt.platform)) * 0.3
            + (0.2 if mp.portfolio else 0.0))


def party_lifecycle(state: GameState) -> None:
    """Weekly: faction wings → cohesion update → defections/foundings → schisms → deaths."""
    update_factions(state)
    update_cohesion(state)

    # lone founder: the single most miserable ambitious MP walks, once per week
    miserable = [
        mp for mp in state.mps.values()
        if mp.party is not None and mp.id != state.player_id
        and mp.ambition > 0.6 and _stay_utility(state, mp) < p.PARTY_FORM_STAY_UTILITY
    ]
    if miserable:
        _found(state, min(miserable, key=lambda m: _stay_utility(state, m)).id, [])

    # schisms: a low-cohesion, high-spread party splits at its ideological fault line
    for pt in list(state.parties.values()):
        if len(pt.members) < 4 or pt.schism_cooldown > 0 or pt.cohesion >= p.PARTY_COHESION_SPLIT:
            continue
        members = list(pt.members)
        positions = np.array([state.mps[m].pos for m in members])
        spread = float(np.linalg.norm(positions - positions.mean(axis=0), axis=1).max())
        if spread < p.PARTY_SPREAD_SPLIT:
            continue
        # the farthest member leads a schism, taking nearby members
        idx = int(np.argmax(np.linalg.norm(positions - positions.mean(axis=0), axis=1)))
        rebel = members[idx]
        followers = [m for m in pt.members
                     if m != rebel and dist(state.mps[m].pos, state.mps[rebel].pos) < 0.4]
        if followers:
            _found(state, rebel, followers)
            pt.schism_cooldown = p.PARTY_SCHISM_COOLDOWN
            state.emit("Defection", f"{pt.name} splits — {state.mps[rebel].name} walks out.",
                       party=pt.id, rebel=rebel)

    # leaders who lost their seat get replaced; empty parties die
    for pid, pt in list(state.parties.items()):
        pt.members &= set(state.mps)
        if not pt.members:
            del state.parties[pid]
            state.emit("PartyDissolved", f"{pt.name} dissolves.", party=pid)
        elif pt.leader not in pt.members:
            pt.leader = max(pt.members, key=lambda m: state.mps[m].ambition)
