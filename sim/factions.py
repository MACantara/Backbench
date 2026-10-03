"""Intra-party factions: detected wings that whip separately and can secede."""
from __future__ import annotations

import numpy as np

from . import params as p
from .naming import describe_pos
from .state import Faction, GameState, dist


def _wing_name(party_name: str, centroid: tuple[float, float], platform: tuple[float, float]) -> str:
    dev = (centroid[0] - platform[0], centroid[1] - platform[1])
    word = "moderate" if max(abs(dev[0]), abs(dev[1])) < 0.2 else describe_pos(dev)
    return f"{party_name}-{word}"


def _next_faction_id(state: GameState) -> int:
    return max((f.id for pt in state.parties.values() for f in pt.factions), default=-1) + 1


def _spread(state: GameState, members: list[int]) -> tuple[float, np.ndarray]:
    positions = np.array([state.mps[m].pos for m in members])
    return float(np.linalg.norm(positions - positions.mean(axis=0), axis=1).max()), positions


def _dissolve(state: GameState, pt, faction: Faction) -> None:
    for m in faction.members:
        if m in state.mps:
            state.mps[m].faction = None
    pt.factions.remove(faction)
    state.emit("FactionDissolved", f"{faction.name} dissolves back into {pt.name}.",
               party=pt.id, faction=faction.id)


def _form_wings(state: GameState, pt, members: list[int], positions: np.ndarray) -> None:
    """Split members into two wings on the max-variance axis at the mean."""
    ax = int(np.argmax(positions.var(axis=0)))
    sides = [[], []]
    for m, pos in zip(members, positions):
        sides[pos[ax] > positions[:, ax].mean()].append(m)
    if min(len(s) for s in sides) < p.FACTION_MIN_SIZE:
        return
    fid = _next_faction_id(state)
    for side in sides:
        centroid = tuple(np.mean([state.mps[m].pos for m in side], axis=0))
        f = Faction(id=fid, name=_wing_name(pt.name, centroid, pt.platform), centroid=centroid,
                    members=set(side),
                    leader=max(side, key=lambda m: state.mps[m].ambition))
        for m in side:
            state.mps[m].faction = fid
        pt.factions.append(f)
        fid += 1
    state.emit("FactionEmerged",
               f"{pt.name} divides into wings: {', '.join(f'{f.name} ({len(f.members)})' for f in pt.factions)}.",
               party=pt.id, factions=[f.id for f in pt.factions])


def update_factions(state: GameState) -> None:
    """Weekly: wings form on ideological spread, track centroids, dissolve on shrink."""
    for pt in state.parties.values():
        members = [m for m in pt.members if m in state.mps]
        if len(members) < 2 * p.FACTION_MIN_SIZE or not members:
            for f in list(pt.factions):
                _dissolve(state, pt, f)
            continue
        spread, positions = _spread(state, members)
        if not pt.factions:
            if spread >= p.FACTION_SPREAD_MIN:
                _form_wings(state, pt, members, positions)
            continue
        if spread < p.FACTION_SPREAD_MIN:
            for f in list(pt.factions):
                _dissolve(state, pt, f)
            continue
        for f in list(pt.factions):
            f.members &= set(members)
        for m in members:  # newcomers join the nearest wing
            if state.mps[m].faction not in {f.id for f in pt.factions}:
                near = min(pt.factions, key=lambda f: dist(state.mps[m].pos, f.centroid))
                near.members.add(m)
                state.mps[m].faction = near.id
        for f in list(pt.factions):
            if len(f.members) < p.FACTION_MIN_SIZE:
                _dissolve(state, pt, f)
                continue
            f.centroid = tuple(np.mean([state.mps[m].pos for m in f.members], axis=0))
            f.leader = max(f.members, key=lambda m: state.mps[m].ambition)
