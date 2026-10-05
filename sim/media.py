"""Media layer: outlets cover the week's events; voters watch the coverage."""
from __future__ import annotations

import numpy as np

from . import params as p
from .state import GameState, dist

# type -> (newsworthiness, sign for the subject party, sensational?)
_NEWS = {
    "ScandalBreaks":    (3.0, -1, True),
    "Resigned":         (3.0, -1, True),
    "Expelled":         (2.5, -1, True),
    "MinisterSacked":   (2.0, -1, True),
    "Scandal":          (1.5, -1, True),
    "ScandalWeathered": (1.5, +1, True),
    "Defection":        (2.0, -1, True),
    "ConfidenceLost":   (2.5, -1, False),
    "PartyDissolved":   (1.5, -1, False),
    "FactionRebels":    (1.5, -1, False),
    "Secession":        (2.0, -1, False),
    "PartyFormed":      (1.5, +1, False),
    "CoalitionFormed":  (1.5, +1, False),
    "ElectionCalled":   (1.0, +1, False),
    "VoteResult":       (1.0,  0, False),  # sign resolved from passed
    "Shock":            (2.5,  0, False),  # sign resolved from good
    "LawEnacted":       (1.0, +1, False),
    "LawStruck":        (2.5, -1, False),  # the bench smacks the authors
    "LawUpheld":        (1.0, +1, False),
    "LawRepealed":      (2.5, -1, False),  # the authors' record dismantled
    "LawLapsed":        (0.5,  0, False),  # quiet pruning barely registers
    "BudgetSet":        (1.5, +1, False),
    "PmChange":         (2.5, -1, True),   # a mid-term succession is a sensation
    "AttackLands":      (1.5, -1, True),
    "DebtCrisis":       (3.0, -1, False),
}


def _subjects(state: GameState, e) -> list[int]:
    """The parties a story is about. Explicit `party=` (stamped at emit time so
    post-removal resolution still works), else the named MP's party, else every
    government party — coalition coverage shouldn't land on one member."""
    pid = e.data.get("party")
    if pid is not None:
        return [pid] if pid in state.parties else []
    pids = e.data.get("parties")   # a story can name a coalition — e.g. a struck law's authors
    if pids is not None:
        alive = [i for i in pids if i in state.parties]
        if alive:
            return alive           # all named parties gone → fall through to government
    mp = state.mps.get(e.data.get("mp", -1))
    if mp is not None:
        return [mp.party] if mp.party in state.parties else []
    return [i for i in state.government.parties if i in state.parties]


def media_lifecycle(state: GameState, base: int) -> None:
    """Weekly: outlets pick their lead story, frame it, and set the agenda."""
    v, rng = state.voters, state.rng
    week = state.log[base:]

    # each outlet leads with its most newsworthy story (tabloids ≠ broadsheets)
    leads = []   # (reach, weighted_w, outlet, event, subject_pids)
    for o in state.outlets:
        best = None
        for e in week:
            if e.type not in _NEWS:
                continue
            w, sign, sens = _NEWS[e.type]
            w = w * (o.sensationalism if sens else 1 - o.sensationalism)
            pids = _subjects(state, e)
            if not pids or (best and w <= best[0]):
                continue
            best = (w, e, pids)
        if best:
            leads.append((o.reach, best[0], o, best[1], best[2]))

    # framing: hostile coverage amplifies damage, friendly coverage heals
    for _, w, o, e, pids in leads:
        for pid in pids:
            pt = state.parties[pid]
            sign = _NEWS[e.type][1] or (1 if e.data.get("passed", e.data.get("good")) else -1)
            h = min(1.0, dist(o.slant, pt.platform) / 2)   # 0 friendly .. 1 hostile
            pt.brand += (sign * p.COVERAGE_BRAND_W * (w / 2)
                         * (0.5 + (h if sign < 0 else 1 - h)))
            plat = np.asarray(pt.platform)
            if sign < 0:   # caricature: the platform stretched away from the outlet
                target = plat + 0.5 * (plat - np.asarray(o.slant))
            else:
                target = plat
            pt.pub_pos = tuple(np.clip(
                np.asarray(pt.pub_pos) + p.COVERAGE_PUBPOS_W * (target - pt.pub_pos),
                -1, 1))

    # agenda-setting: every outlet pushes its axis into its audience's salience
    np_rng = np.random.default_rng(int(rng.random() * 2**63))
    for o in state.outlets:
        aff = np.exp(-((v.pos - np.asarray(o.slant))**2).sum(axis=1)
                     / (2 * p.AUDIENCE_AFFINITY_SD**2))
        audience = np_rng.random(len(v.pos)) < o.reach * aff
        v.salience[audience, o.focus_axis] += p.AGENDA_SALIENCE_W

    # perceived positions slowly drift back toward the real platform
    for pt in state.parties.values():
        pt.pub_pos = tuple(np.asarray(pt.pub_pos)
                           + p.PUB_POS_REVERT * (np.asarray(pt.platform) - pt.pub_pos))

    # the headline: highest-reach lead. The frenzy counter tracks the *party*,
    # not the story — a party generating fresh bad news weekly IS a press cycle.
    if not leads:
        state.press_subject, state.press_weeks = None, 0
        return
    _, _, o, e, pids = max(leads, key=lambda t: t[0])
    pid = pids[0]
    state.press_weeks = state.press_weeks + 1 if pid == state.press_subject else 1
    state.press_subject = pid
    pt = state.parties[pid]
    state.emit("Headline", f"{o.name} leads with \"{e.text}\"",
               outlet=o.id, party=pid, story=e.type)
    if state.press_weeks == p.PRESS_CYCLE_WEEKS:
        state.emit("PressCycle", f"The press will not let go of {pt.name}.",
                   party=pid)
