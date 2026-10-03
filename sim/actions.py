"""Player actions — typed, applied at the start of each tick."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import params as p
from .state import GameState, dist


@dataclass
class Action:
    kind: str                    # campaign, constituency, speech, promise, media, dig_dirt, lobby, scheme, platform
    target: int | None = None    # MP id for lobby/dig_dirt
    axis: int | None = None      # 0/1 for speech/promise
    pos: tuple[float, float] | None = None  # for promise


def available_actions(state: GameState) -> list[str]:
    """Context menu for the week."""
    base = ["scheme", "lobby", "media", "dig_dirt"]
    if state.phase == "campaign":
        base += ["campaign", "speech", "promise"]
    else:
        base += ["constituency", "speech"]
    player = state.mps.get(state.player_id)
    if player and player.party is not None and state.parties.get(player.party) and state.parties[player.party].leader == player.id:
        base.append("platform")
    return base


def apply_action(state: GameState, action: Action) -> None:
    player = state.mps[state.player_id]
    v = state.voters
    mask = v.district == player.district
    rng = state.rng

    if action.kind == "campaign":
        # door-knocking: pull district voters slightly toward your party's platform
        plat = np.asarray(state.parties[player.party].platform)
        v.pos[mask] += 0.03 * np.sign(plat - v.pos[mask])
        state.emit("CareerEvent", "You campaign door-to-door.", action="campaign")

    elif action.kind == "constituency":
        # casework: the district remembers you and forgives a little
        v.betrayal[mask] *= 0.85
        v.loyalty[mask] = np.clip(v.loyalty[mask] + 0.02, 0, 1)
        v.last_party[mask] = player.party
        state.emit("CareerEvent", "You hold constituency surgeries.", action="constituency")

    elif action.kind == "speech":
        ax = action.axis if action.axis is not None else rng.randrange(2)
        v.salience[mask, ax] += 0.05
        v.pos[mask, ax] += 0.03 * np.sign(player.pos[ax] - v.pos[mask, ax])
        state.emit("CareerEvent", f"You give a speech on the {'economic' if ax == 0 else 'social'} axis.", action="speech")

    elif action.kind == "promise":
        state.promises.append({"pos": action.pos or player.pos,
                               "party": player.party,
                               "platform_dist": dist(state.parties[player.party].platform, action.pos or player.pos)})
        state.emit("CareerEvent", "You make a public promise.", action="promise")

    elif action.kind == "media":
        pt = state.parties[player.party]
        # how friendly is the outlet landscape to your party?
        friend = 1 - min(1.0, np.mean(
            [dist(o.slant, pt.platform) for o in state.outlets] or [1.0]) / 2)
        if rng.random() < 0.2:
            player.dossier += 0.15
            pt.brand -= 0.05
            state.emit("Scandal", "A gaffe on air — the clip is circulating.", mp=player.id)
        else:
            pt.brand += p.MEDIA_APPEAR_BRAND * (0.5 + friend)
            # friendly coverage pulls the perceived party toward respectability
            pt.pub_pos = tuple(np.asarray(pt.pub_pos)
                               - p.MEDIA_APPEAR_PUBPOS * friend * np.asarray(pt.pub_pos))
            state.emit("CareerEvent", "A solid media appearance.", action="media")

    elif action.kind == "dig_dirt" and action.target in state.mps:
        t = state.mps[action.target]
        t.dossier += 0.25
        if rng.random() < 0.3:
            t.relationships[player.id] = t.relationships.get(player.id, 0) - 0.2
            state.emit("Scandal", f"{t.name} suspects you hired researchers.", mp=t.id)
        else:
            state.emit("CareerEvent", f"You dig up material on {t.name}.", action="dig_dirt")

    elif action.kind == "lobby" and action.target in state.mps:
        t = state.mps[action.target]
        t.relationships[player.id] = t.relationships.get(player.id, 0) + 0.2
        player.relationships[t.id] = player.relationships.get(t.id, 0) + 0.15
        state.emit("CareerEvent", f"You lobby {t.name}.", action="lobby")

    elif action.kind == "scheme":
        # quiet dinners with colleagues — builds support, slightly risky
        pt = state.parties.get(player.party)
        if pt:
            for mid in list(pt.members)[:8]:
                if mid != player.id:
                    state.mps[mid].relationships[player.id] = \
                        state.mps[mid].relationships.get(player.id, 0) + 0.05
        player.dossier += 0.03
        state.emit("CareerEvent", "You scheme discreetly.", action="scheme")

    elif action.kind == "platform":
        # leaders pull the party platform toward their own position
        pt = state.parties[player.party]
        pt.platform = tuple(np.clip(np.asarray(pt.platform) + 0.05 * (np.asarray(player.pos) - np.asarray(pt.platform)), -1, 1))
        state.emit("CareerEvent", f"You nudge {pt.name}'s platform.", action="platform")


def evaluate_promises(state: GameState) -> None:
    """At election: kept promises clear betrayal; broken ones bite your district."""
    player = state.mps.get(state.player_id)
    if not player:
        return
    mask = state.voters.district == player.district
    for pr in state.promises:
        pt = state.parties.get(pr["party"])
        if not pt or pt.id != player.party:
            state.voters.betrayal[mask] += 0.25
            continue
        kept = dist(pt.platform, pr["pos"]) < pr["platform_dist"]
        state.voters.betrayal[mask] += 0.0 if kept else 0.25
        state.emit("CareerEvent", "Voters judge your promise " + ("kept." if kept else "broken."),
                   kept=kept)
    state.promises.clear()
