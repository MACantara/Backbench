"""Dynamic party lifecycle: cohesion, defection, founding, schism, death."""
from __future__ import annotations

import numpy as np

from . import params as p
from .factions import update_factions
from .naming import party_name_for
from .state import GameState, Grave, Party, dist


def update_cohesion(state: GameState) -> None:
    """Cohesion = mean ideological alignment of members to platform + leader loyalty."""
    for pt in state.parties.values():
        if not pt.members:
            pt.cohesion = 0.0
            continue
        align = np.mean([1 - dist(state.mps[m].pos, pt.platform) / 2
                         for m in sorted(pt.members)])
        loyal = np.mean([state.mps[m].loyalty for m in sorted(pt.members)])
        pt.cohesion = float(np.clip(align * 0.7 + loyal * 0.3, 0, 1))


def _next_party_id(state: GameState) -> int:
    return max(state.parties, default=-1) + 1


def _found(state: GameState, founder, followers: list[int]) -> int:
    pid = _next_party_id(state)
    if followers:
        # a bloc secession names itself for where it stands ideologically
        bloc = np.mean([state.mps[m].pos for m in [founder, *followers]], axis=0)
        taken = {pt.name for pt in state.parties.values()}
        name = party_name_for(tuple(bloc), state.rng, taken)
    else:
        name = f"{state.mps[founder].name.split()[-1]} List"  # a lone founder's vehicle
    pt = Party(id=pid, name=name, platform=state.mps[founder].pos, leader=founder,
               founded_week=state.week, founded_by=founder)
    for mid in [founder, *followers]:
        old = state.mps[mid].party
        if old is not None and old in state.parties:
            state.parties[old].members.discard(mid)
        state.mps[mid].party = pid
        state.mps[mid].faction = None
        state.mps[mid].junior, state.mps[mid].junior_weeks = None, 0  # the post died with the party tie
        pt.members.add(mid)
    state.parties[pid] = pt
    state.emit("PartyFormed", f"{name} founded by {state.mps[founder].name} ({len(pt.members)} MPs).",
               party=pid, founder=founder, size=len(pt.members),
               kind="secession" if followers else "founder")
    return pid


def _stay_utility(state: GameState, mp) -> float:
    """How attractive staying in the current party is. Proximity carries the
    weight — a portfolio-less misfit far from the platform must score low."""
    pt = state.parties[mp.party]
    f = next((f for f in pt.factions if f.id == mp.faction), None)
    d = dist(mp.pos, pt.platform)
    return (pt.cohesion * p.STAY_W_COHESION
            + max(0, 1 - d) * p.STAY_W_PROXIMITY
            + (p.STAY_PORTFOLIO if mp.portfolio else 0.0)
            - p.STAY_ALIEN_W * max(0, d - p.STAY_ALIEN_DIST)  # alienation bites
            - (p.STAY_ESTRANGED if f is not None and f.estranged > 0 else 0.0))


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

    # secessions: an estranged wing walks out as a bloc (multi-MP splits only via factions)
    for pt in list(state.parties.values()):
        if pt.schism_cooldown > 0:
            continue
        for f in list(pt.factions):
            if dist(f.centroid, pt.platform) > p.SECESSION_DIST:
                f.estranged += 1
            else:
                f.estranged = 0
            if f.estranged < p.SECESSION_WEEKS:
                continue
            walkers = sorted(f.members - {state.player_id})
            if not walkers:
                f.estranged = 0
                continue
            founder = f.leader if f.leader in walkers else walkers[0]
            state.emit("Secession", f"{f.name} secedes — {len(walkers)} MPs walk out of {pt.name}.",
                       party=pt.id, faction=f.id, size=len(walkers))
            _found(state, founder, [m for m in walkers if m != founder])
            pt.factions.remove(f)
            pt.schism_cooldown = p.PARTY_SCHISM_COOLDOWN
            if state.player_id in f.members:
                state.mps[state.player_id].faction = None
                state.emit("CareerEvent",
                           f"Your wing {f.name} secedes — you stay with {pt.name}.", party=pt.id)
            break  # one bloc walks per week

    # leaders who lost their seat get replaced; empty parties die (and are buried)
    state.graves = [g for g in state.graves if state.week - g.died < p.GRAVE_WEEKS][-p.GRAVE_MAX:]
    for pid, pt in list(state.parties.items()):
        pt.members &= set(state.mps)
        if not pt.members:
            if not pt.seated and state.week - pt.founded_week <= p.DYNAMIC_GRACE_WEEKS:
                continue  # a born-memberless entrant gets until after its first election
            state.graves.append(Grave(name=pt.name, platform=pt.platform, died=state.week))
            state.emit("PartyDissolved", f"{pt.name} dissolves.", party=pid)
            state.government.parties.discard(pid)
            del state.parties[pid]
        elif pt.leader not in pt.members:
            from .career import successor
            pt.leader = successor(state, pt)

    # differentiation: outside government a party follows its own voters —
    # the opposition's structural advantage is the space fatigue opens
    v = state.voters
    pids = list(state.parties)
    if len(pids) > 1:
        plats = np.array([state.parties[pid].platform for pid in pids])
        near = np.argmin(np.linalg.norm(
            v.pos[:, None, :] - plats[None, :, :], axis=2), axis=1)
        for i, pid in enumerate(pids):
            if pid in state.government.parties:
                continue
            base = v.pos[near == i]
            if len(base):
                pt = state.parties[pid]
                pt.platform = tuple(np.clip(
                    np.asarray(pt.platform) + p.PLATFORM_BASE_PULL
                    * (base.mean(axis=0) - np.asarray(pt.platform)), -1, 1))
