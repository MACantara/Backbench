"""Scandal lifecycle: latent dirt, leaks, burning weeks, career endings."""
from __future__ import annotations

from . import params as p
from .prose import render
from .career import remove_mp
from .state import GameState


def detonate(state: GameState, mp) -> None:
    """A dossier surfaces into an active scandal — severity, the expel
    threshold, ministerial disgrace. Called by the weekly leak roll and
    by a deliberate `leak` action."""
    pt = state.parties.get(mp.party)
    # leaders expel the dirtiest members outright to contain the damage
    if (mp.id != state.player_id and pt is not None and pt.leader != mp.id
            and mp.dossier > p.SACK_THRESHOLD):
        state.emit("Expelled", f"{pt.name} expels {mp.name} over the scandal.",
                   mp=mp.id, party=pt.id)
        remove_mp(state, mp)
        return
    sev = ("career-ending" if mp.dossier > p.SACK_THRESHOLD
           else "serious" if mp.dossier > p.SEVERITY_SERIOUS
           else "embarrassing")
    mp.scandal_weeks = state.rng.randint(*p.SCANDAL_WEEKS)
    state.emit("ScandalBreaks",
               render(state, "ScandalBreaks", name=mp.name, sev=sev),
               mp=mp.id, party=mp.party, dossier=mp.dossier, severity=sev)
    if mp.portfolio is not None and mp.dossier > p.SACK_THRESHOLD * p.MINISTER_SACK_FRAC:
        state.emit("MinisterSacked", f"{mp.name} is sacked as {mp.portfolio}.",
                   mp=mp.id, party=mp.party, portfolio=mp.portfolio, reason="scandal")
        mp.portfolio, mp.portfolio_weeks = None, 0
        mp.standing -= p.STANDING_SACK_HIT
        state.government.sacked.add(mp.id)   # a reshuffle can't re-hire disgrace


def _game_over(state: GameState, kind: str) -> None:
    state.phase = "over"
    state.emit("SeatLost", f"Your career ends in scandal — {kind}.", mp=state.player_id)


def scandal_lifecycle(state: GameState) -> None:
    """Weekly: dirt grows, leaks surface, scandals burn and end careers."""
    v = state.voters
    rng = state.rng
    player = state.player_id

    for mp in state.mps.values():
        mp.dossier = mp.dossier * (1 - p.DOSSIER_FADE) \
            + p.DIRTY_GROWTH * (1 - mp.integrity)

    # leaks: dossier surfaces into an active scandal (worse near elections)
    near_election = (state.phase == "campaign"
                     and state.weeks_to_election <= p.ELECTION_LEAK_WINDOW)
    for mp in list(state.mps.values()):
        if mp.scandal_weeks > 0 or mp.dossier <= p.LEAK_MIN_DOSSIER:
            continue
        if (mp.dossier > p.SACK_THRESHOLD and mp.id != player
                and mp.party in state.parties
                and state.parties[mp.party].leader != mp.id):
            detonate(state, mp)      # the party purges — no roll
            continue
        pr = min(p.LEAK_MAX_P, p.LEAK_BASE_P * mp.dossier)
        if near_election:
            pr *= p.LEAK_ELECTION_MULT
        if rng.random() < pr:
            detonate(state, mp)

    # burning: brand bleeds, the district turns, careers end or survive
    bleed: dict[int, float] = {}
    for mp in list(state.mps.values()):
        if mp.scandal_weeks <= 0:
            continue
        if mp.party in state.parties:
            bleed[mp.party] = bleed.get(mp.party, 0.0) + p.SCANDAL_BRAND_HIT * (
                p.MINISTER_BRAND_MULT if mp.portfolio else 1.0)
        v.betrayal[v.district == mp.district] += p.SCANDAL_BETRAYAL
        # only serious dirt adds resignation pressure — an embarrassing
        # clip costs standing and brand, not the career
        if rng.random() < p.RESIGN_BASE_P \
                + max(0.0, mp.dossier - p.SEVERITY_SERIOUS) * p.RESIGN_DOSSIER_W:
            if mp.id == player:
                _game_over(state, "you resign")
            else:
                state.emit("Resigned", f"{mp.name} resigns over the scandal.",
                           mp=mp.id, party=mp.party, district=mp.district)
                remove_mp(state, mp)
            continue
        mp.scandal_weeks -= 1
        if mp.scandal_weeks <= 0:
            mp.dossier *= 1 - p.WEATHERED_BURN
            if mp.party in state.parties:
                state.parties[mp.party].brand -= p.WEATHERED_BRAND_SCAR
            state.emit("ScandalWeathered", f"{mp.name} weathers the scandal.",
                       mp=mp.id, party=mp.party)

    for pid, b in bleed.items():
        state.parties[pid].brand -= min(b, p.PARTY_BLEED_MAX)

    # the player's own dirt can surface into expulsion by their party — but
    # only while clean (a burning player can weather below the threshold, like
    # AI MPs), and never as party leader (leaders die by the resignation roll
    # or leadership challenges, not self-expulsion)
    me = state.mps.get(player)
    if me and me.dossier > p.SACK_THRESHOLD and state.phase != "over":
        pt = state.parties.get(me.party)
        if pt is not None and pt.leader != player and me.scandal_weeks <= 0:
            state.emit("Expelled", f"{pt.name} expels you over the scandal.",
                       mp=player, party=pt.id)
            _game_over(state, "expelled")
