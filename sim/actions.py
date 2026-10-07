"""Player actions — typed, applied at the start of each tick."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import params as p
from .conditions import mood
from .naming import bill_name
from .state import Bill, GameState, dist


@dataclass
class Action:
    kind: str                    # campaign, constituency, speech, promise, media, dig_dirt,
                                 # lobby, scheme, platform, vote, deal, pick_offer,
                                 # decline_offers, budget, attack, amend, table,
                                 # defect, found, challenge, appoint, amendment,
                                 # court
    target: int | None = None    # MP id for lobby/dig_dirt/leak; party id for
                                 # defect; outlet id for court
    axis: int | None = None      # 0/1 for speech/promise/table; 0-2 stance for budget
    pos: tuple[float, float] | None = None  # for promise/evolve
    vote: int | None = None      # +1/-1/0 on the pending division
    offer: int | None = None     # pick_offer: index into state.offers
    law: int | None = None       # challenge: index into state.laws
    judge: int | None = None     # appoint: index into state.bench_shortlist
    article: int | None = None   # amendment: constitution article id to repeal
    entrench: tuple[int, int] | None = None  # amendment: (axis, pole) to fence
    outlet: int | None = None    # leak: route the story through this outlet


def cost_of(kind: str) -> int:
    """Points a pick spends — the table lives in params."""
    return p.ACTION_COST.get(kind, 1)


def available_actions(state: GameState) -> list[str]:
    """Context menu for the week."""
    player = state.mps.get(state.player_id)
    if player is not None and player.id == state.speaker:
        # the chair sits above the fray — casework, the press, the quiet
        # rooms; no whip to read, no table to write on, no party to make
        menu = ["scheme", "lobby", "media", "dig_dirt", "leak", "court",
                "constituency", "speech"]
        from .courts import challengeable
        if challengeable(state):
            menu.append("challenge")
        return menu
    base = ["scheme", "lobby", "media", "dig_dirt", "leak", "evolve"]
    if player is not None and player.party is not None:
        base.append("court")         # cultivate an editorial board
    if state.offers:
        base += ["pick_offer", "decline_offers"]  # a hung parliament is a decision
    if state.phase == "campaign":
        base += ["campaign", "speech", "promise"]
    else:
        base += ["constituency", "speech"]
        if state.phase == "governing" and player is not None \
                and player.party not in state.government.parties:
            base.append("table")       # private member's bill — backbench legacy
            if state.government.parties:
                base.append("attack")  # scrutiny — lands only on a weak government
        if state.current_bill is not None:
            base += ["vote", "deal"]   # a pending division is a decision — and currency
            if not state.current_bill.amended:
                base.append("amend")   # drag the bill toward your ground — once
    if player and player.party is not None and state.parties.get(player.party) and state.parties[player.party].leader == player.id:
        base.append("platform")
    if state.phase == "governing" and state.government.pm == state.player_id:
        base.append("budget")        # the PM writes the fiscal posture
        if state.bench_shortlist:
            base.append("appoint")   # a judicial vacancy waits on your pick
        base.append("amendment")     # the PM can move the constitution itself
                                     # — entrenchment works on an empty book
    if player is not None and state.phase in ("governing", "formation"):
        if player.party is not None:
            base.append("defect")    # cross the floor — to a party, or none
        base.append("found")         # walk out and name a vehicle
    if player is not None and state.phase != "over":
        from .courts import challengeable
        if challengeable(state):
            base.append("challenge") # the venue for losers takes your filing too
    return base


def apply_action(state: GameState, action: Action) -> None:
    player = state.mps[state.player_id]
    if player.id == state.speaker and action.kind in (
            "found", "defect", "table", "attack", "deal", "amend", "vote",
            "promise", "platform", "budget", "appoint", "amendment",
            "pick_offer", "evolve"):
        return      # the chair doesn't do politics — the menu gates, this walls
    v = state.voters
    mask = v.district == player.district
    rng = state.rng

    if action.kind == "campaign":
        # door-knocking: pull district voters slightly toward your platform —
        # an independent's platform is their own ground
        pt = state.parties.get(player.party)
        plat = np.asarray(pt.platform if pt else player.pos)
        v.pos[mask] += 0.03 * np.sign(plat - v.pos[mask])
        # the ground game gets your people to the polls — turnout is a lever
        v.turnout[mask] = np.clip(v.turnout[mask] + p.GOTV_LIFT, 0, 1)
        d = float(np.dot(v.pos[mask].mean(axis=0) - plat,
                         plat / max(np.linalg.norm(plat), 1e-9)))
        state.emit("CareerEvent",
                   f"You campaign door-to-door — the district sits "
                   f"{abs(d):.2f} from your platform and the base is stirred.",
                   action="campaign")

    elif action.kind == "constituency":
        # casework: the district remembers you and forgives a little
        v.betrayal[mask] *= 0.85
        v.loyalty[mask] = np.clip(v.loyalty[mask] + 0.02, 0, 1)
        if player.party is not None:
            v.last_party[mask] = player.party
        old = player.standing
        player.standing = float(np.clip(player.standing + p.STANDING_SERVICE, -1, 1))
        state.emit("CareerEvent",
                   f"You hold constituency surgeries — standing "
                   f"{old:.2f} -> {player.standing:.2f}.",
                   action="constituency")

    elif action.kind == "speech":
        ax = action.axis if action.axis is not None else rng.randrange(2)
        v.salience[mask, ax] += 0.05
        v.pos[mask, ax] += 0.03 * np.sign(player.pos[ax] - v.pos[mask, ax])
        gap = float(abs(v.pos[mask, ax].mean() - player.pos[ax]))
        state.emit("CareerEvent",
                   f"You give a speech on the {'economic' if ax == 0 else 'social'} "
                   f"axis — the district is {gap:.2f} from you on it.",
                   action="speech")

    elif action.kind == "evolve":
        # reposition — a lerp toward the anchor, priced in the district's
        # mistrust per unit covered and the whip's read of the direction
        old = np.asarray(player.pos)
        tgt = np.asarray(action.pos) if action.pos is not None else (
            v.pos[mask].mean(axis=0) if mask.any() else old)
        new = np.clip(old + p.EVOLVE_STEP * (tgt - old), -1, 1)
        moved = float(np.linalg.norm(new - old))
        if moved < 1e-12:
            return      # standing still isn't a news event
        player.pos = (float(new[0]), float(new[1]))
        v.betrayal[mask] += p.EVOLVE_BETRAYAL_W * moved
        pt = state.parties.get(player.party)
        trim = ""
        if pt is not None:
            d_old, d_new = dist(tuple(old), pt.platform), dist(tuple(new), pt.platform)
            player.standing = float(np.clip(
                player.standing + p.EVOLVE_STANDING_W * (d_old - d_new), -1, 1))
            if d_new < d_old:
                trim = ", the whip notes the trim"
            elif d_new > d_old:
                trim = ", the whip notes the wobble"
        state.emit("CareerEvent",
                   f"You edge to ({new[0]:+.2f},{new[1]:+.2f}) — moved {moved:.2f}; "
                   f"the voters notice (+{p.EVOLVE_BETRAYAL_W * moved:.2f} mistrust){trim}.",
                   action="evolve", moved=moved)

    elif action.kind == "promise":
        pt = state.parties.get(player.party)
        pos = action.pos or player.pos
        pdist = dist(pt.platform, pos) if pt else 0.0
        state.promises.append({"pos": pos,
                               "party": player.party,
                               "platform_dist": pdist})
        state.emit("CareerEvent",
                   f"You make a public promise — {pdist:.2f} off "
                   f"{'the party line' if pt else 'any platform'}.",
                   action="promise")

    elif action.kind == "media":
        pt = state.parties.get(player.party)
        # how friendly is the outlet landscape to you — or your party?
        ref = np.asarray(pt.platform) if pt else np.asarray(player.pos)
        friend = 1 - min(1.0, np.mean(
            [dist(o.slant, ref) for o in state.outlets] or [1.0]) / 2)
        if rng.random() < 0.2:
            player.dossier += 0.15
            if pt is not None:
                pt.brand -= 0.05
            state.emit("Scandal", "A gaffe on air — the clip is circulating.", mp=player.id)
        else:
            if pt is not None:
                old = pt.brand
                pt.brand += p.MEDIA_APPEAR_BRAND * (0.5 + friend)
                # friendly coverage pulls the perceived party toward respectability
                pt.pub_pos = tuple(np.asarray(pt.pub_pos)
                                   - p.MEDIA_APPEAR_PUBPOS * friend * np.asarray(pt.pub_pos))
                state.emit("CareerEvent",
                           f"A solid media appearance — {pt.name} brand "
                           f"{old:.2f} -> {pt.brand:.2f}.", action="media")
            else:
                old = player.standing
                player.standing = float(np.clip(player.standing + 0.02, -1, 1))
                state.emit("CareerEvent",
                           f"A solid media appearance — your standing "
                           f"{old:.2f} -> {player.standing:.2f}.",
                           action="media")

    elif action.kind == "dig_dirt" and action.target in state.mps:
        t = state.mps[action.target]
        old = t.dossier
        t.dossier += 0.25
        if rng.random() < 0.3:
            t.relationships[player.id] = t.relationships.get(player.id, 0) - 0.2
            state.emit("Scandal", f"{t.name} suspects you hired researchers.", mp=t.id)
        else:
            state.emit("CareerEvent",
                       f"You dig up material on {t.name} — their dossier "
                       f"{old:.2f} -> {t.dossier:.2f}.", action="dig_dirt")

    elif action.kind == "leak" and action.target in state.mps \
            and action.target != player.id:
        # detonate a dirty dossier on your schedule — deniable, not free.
        # Routed through an outlet: a friend buries it and protects the
        # source; an enemy leads with it and may burn you.
        from .scandals import detonate
        t = state.mps[action.target]
        o = next((x for x in state.outlets if x.id == action.outlet), None)
        if t.dossier > p.LEAK_MIN_DOSSIER and t.scandal_weeks <= 0:
            detonate(state, t)
            if o is not None:
                broke = next((e for e in reversed(state.log)
                              if e.type in ("ScandalBreaks", "Expelled")
                              and e.data.get("mp") == t.id), None)
                if broke is not None:
                    broke.data["routed"] = o.id   # coverage reads the venue
            warm = o.warmth.get(player.party, 0.0) if o is not None else -1.0
            mult = 1.0 if o is None else (
                p.FRIENDLY_TRACE_MULT if warm >= p.COURT_FRIENDLY_MIN
                else p.HOSTILE_TRACE_MULT)
            if rng.random() < p.LEAK_TRACE_P * mult:
                t.relationships[player.id] = t.relationships.get(player.id, 0.0) \
                    - p.LEAK_TRACE_REL
                player.dossier += p.LEAK_CAUGHT_DIRT   # fingerprints in the dirt
                state.emit("Scandal", f"{t.name} traces the leak to you.", mp=t.id)
        else:
            state.emit("CareerEvent",
                       f"Nothing on {t.name} will move the press — "
                       f"their dossier sits at {t.dossier:.2f}.", action="leak")

    elif action.kind == "court" and action.target is not None \
            and player.party is not None:
        o = next((x for x in state.outlets if x.id == action.target), None)
        if o is None:
            state.emit("CareerEvent", "No such desk to court.", action="court")
        else:
            old = o.warmth.get(player.party, 0.0)
            o.warmth[player.party] = min(1.0, old + p.COURT_WARMTH)
            state.emit("CareerEvent",
                       f"You wine and dine the editors of {o.name} — "
                       f"warmth {old:.2f} -> {o.warmth[player.party]:.2f}.",
                       action="court", outlet=o.id)

    elif action.kind == "lobby" and action.target in state.mps:
        t = state.mps[action.target]
        old = t.relationships.get(player.id, 0.0)
        t.relationships[player.id] = old + 0.2
        player.relationships[t.id] = player.relationships.get(t.id, 0) + 0.15
        state.emit("CareerEvent",
                   f"You lobby {t.name} — their regard {old:.2f} -> "
                   f"{t.relationships[player.id]:.2f}.", action="lobby")

    elif action.kind == "scheme":
        # quiet dinners with colleagues — builds support, slightly risky
        pt = state.parties.get(player.party)
        warmed = 0
        if pt:
            for mid in sorted(pt.members)[:8]:
                if mid != player.id:
                    state.mps[mid].relationships[player.id] = \
                        state.mps[mid].relationships.get(player.id, 0) + 0.05
                    warmed += 1
        player.dossier += 0.03
        state.emit("CareerEvent",
                   f"You scheme discreetly — {warmed} colleagues warmed; "
                   f"your dossier grows to {player.dossier:.2f}.",
                   action="scheme")

    elif action.kind == "deal" and action.target in state.mps \
            and action.target != state.player_id \
            and action.vote in (-1, 0, 1) \
            and state.current_bill is not None:
        # promise your vote on the pending division; the counterparty banks it now
        from .state import Deal
        t = state.mps[action.target]
        v = int(np.sign(action.vote))
        state.deals = [d for d in state.deals if d.mp != t.id]  # one promise per head
        state.deals.append(Deal(mp=t.id, vote=v, bill=state.current_bill))
        old = t.relationships.get(player.id, 0.0)
        t.relationships[player.id] = old + p.DEAL_REL
        col = {1: "aye", -1: "no", 0: "abstention"}[v]
        state.emit("DealMade", f"You promise {t.name} your {col} on the "
                               f"{state.current_bill.name} — their regard "
                               f"{old:.2f} -> {t.relationships[player.id]:.2f}.",
                   mp=t.id, vote=v)

    elif action.kind == "attack" and player.party not in state.government.parties \
            and state.government.parties:
        # scrutiny lands only on a weak government — a slump or a failing
        # minister opens the wound; a popular one shrugs it off
        ministers = [m for m in state.mps.values() if m.portfolio is not None]
        weak = -mood(state.conditions) - min((m.perf for m in ministers), default=0.0)
        if rng.random() < float(np.clip(p.ATTACK_P + p.ATTACK_WEAK_W * weak, 0.02, 0.9)):
            for pid in state.government.parties:
                if pid in state.parties:
                    state.parties[pid].brand -= p.ATTACK_BRAND
            old = player.standing
            player.standing = float(np.clip(player.standing + p.ATTACK_STANDING, -1, 1))
            state.emit("AttackLands",
                       f"Your attack lands — coalition brand −{p.ATTACK_BRAND:.2f} "
                       f"each, your standing {old:.2f} -> {player.standing:.2f}.",
                       mp=player.id)
        else:
            old = player.standing
            player.standing = float(np.clip(player.standing - p.ATTACK_WHIFF, -1, 1))
            state.emit("CareerEvent",
                       f"Your attack on the government falls flat — standing "
                       f"{old:.2f} -> {player.standing:.2f}.", action="attack")

    elif action.kind == "amend" and state.current_bill is not None \
            and not state.current_bill.amended:
        # one amendment per bill — the mover drags it toward their own ground
        bill = state.current_bill
        old = np.asarray(bill.pos)
        bill.pos = tuple(np.clip(old + p.AMEND_STEP
                                 * (np.asarray(player.pos) - old), -1, 1))
        bill.amended = True
        d = float(np.linalg.norm(np.asarray(bill.pos) - old))
        state.emit("AmendMoved",
                   f"You amend the {bill.name} — it moves {d:.2f} toward "
                   f"your ground.", bill=bill.name)

    elif action.kind == "table" and state.phase == "governing" \
            and player.party not in state.government.parties:
        # a private member's bill — your name on it, divided at once
        from .parliament import resolve_vote
        ax = action.axis if action.axis is not None else rng.randrange(2)
        amends = None
        if action.article is not None:
            amends = next((a for a in state.constitution if a.id == action.article),
                          None)
        bill = Bill(pos=tuple(player.pos), beneficiary_axis=ax,
                    cost=float(max(0.0, p.COST_BASE + p.COST_EXTREMITY_W * abs(player.pos[ax])
                                   + rng.gauss(0, p.COST_JITTER))),
                    amends=amends,
                    name=bill_name(player.pos, ax, rng), author=player.id)
        state.emit("BillTabled",
                   f"You table the {bill.name} — a private member's bill, "
                   "divided at once.", bill=bill.name, pos=bill.pos,
                   beneficiary_axis=ax, cost=bill.cost,
                   austerity=False, repeals=None,
                   amends=bill.amends.id if bill.amends else None,
                   entrenches=bill.entrenches.name if bill.entrenches else None)
        resolve_vote(state, bill, player_vote=1)

    elif action.kind == "budget" and state.government.pm == player.id \
            and action.axis in p.BUDGET_STANCES:
        # the PM signals the next budget's posture — austerity, balance, stimulus
        state.government.budget_stance = action.axis
        state.emit("CareerEvent",
                   f"You signal a {['austerity', 'balanced', 'stimulus'][action.axis]} budget.",
                   action="budget", stance=action.axis)

    elif action.kind == "defect" and player.party is not None \
            and action.target != player.party:
        _leave_party(state, player)
        if action.target in state.parties:
            pt = state.parties[action.target]
            pt.members.add(player.id)
            pt.seated = True            # a mid-term joiner makes the shell real
            player.party = action.target
            state.emit("Defection",
                       f"You cross the floor to {state.parties[action.target].name}.",
                       party=action.target)
        else:
            state.emit("Defection",
                       "You resign the whip — you sit as an independent.")

    elif action.kind == "found":
        # you walk, and whoever really loves you walks too — a vehicle is born
        from .parties import _found, _stay_utility
        old_pid = player.party
        followers = [] if old_pid is None else [m.id for m in state.mps.values()
                     if m.party == old_pid and m.id != player.id
                     and m.id != state.government.pm
                     and m.relationships.get(player.id, 0.0) >= p.FOUND_REL_MIN
                     and _stay_utility(state, m) < p.PARTY_FORM_STAY_UTILITY]
        _leave_party(state, player, exclude=followers)
        pid = _found(state, player.id, followers)
        for mid in followers:   # they pay the same price you did
            m = state.mps[mid]
            state.voters.betrayal[state.voters.district == m.district] += p.DEFECT_BETRAYAL
            m.portfolio, m.portfolio_weeks = None, 0
            m.standing = 0.0
        state.emit("CareerEvent",
                   f"You found {state.parties[pid].name} — "
                   f"{len(followers)} walk out with you.",
                   action="found", party=pid, size=len(followers) + 1)

    elif action.kind == "amendment" and state.government.pm == player.id \
            and state.phase == "governing":
        # move the constitution itself: repeal a clause, or entrench a fence
        # on an open pole — the move queues, then rides the pending cadence
        from .worldgen import _CLAUSES
        bill = None
        if action.article is not None:
            art = next((a for a in state.constitution if a.id == action.article), None)
            if art is not None:
                bill = Bill(pos=tuple(player.pos), beneficiary_axis=0,
                            amends=art, name=f"Repeal of {art.name}")
        elif action.entrench is not None:
            ax, pole = action.entrench
            if ax in (0, 1) and pole in (-1, 1) and not any(
                    a.kind == "pos" and a.axis == ax and a.pole == pole
                    for a in state.constitution):
                from .state import Article
                art = Article(-1, _CLAUSES[(ax, pole)], "pos", axis=ax,
                              pole=pole, limit=p.AMEND_ENTRENCH_LIMIT)
                bill = Bill(pos=tuple(player.pos), beneficiary_axis=0,
                            entrenches=art, name=f"Entrenchment of {art.name}")
        if bill is None:
            state.emit("CareerEvent", "That amendment cannot be moved.",
                       action="amendment")
        else:
            if state.government.amend_move is not None:
                state.emit("CareerEvent",
                           "Your earlier move is withdrawn — "
                           "the house sees only the new one.",
                           action="amendment")
            if bill.amends is not None:
                # one swing per clause per term — the player doesn't get
                # around the memory the AI keeps
                state.government.amend_attempted.add(bill.amends.id)
            state.government.amend_move = bill   # the house sees it this week
            what = (f"the repeal of {bill.amends.name}" if bill.amends
                    else f"the entrenchment of {bill.entrenches.name}")
            state.emit("CareerEvent",
                       f"You prepare a constitutional amendment — {what}.",
                       action="amendment")

    elif action.kind == "appoint" and action.judge is not None \
            and state.government.pm == player.id:
        from .courts import appoint
        if not appoint(state, action.judge):
            state.emit("CareerEvent", "The nomination is off the table.",
                       action="appoint")

    elif action.kind == "challenge" and action.law is not None \
            and 0 <= action.law < len(state.laws):
        # sue the statute book — the player files personally, so the AI
        # filers' party gates (opposition, hostility) don't bind them;
        # the court's own gates (risk floor, res judicata, docket) do
        from .courts import challengeable, file_case
        law = state.laws[action.law]
        if any(l is law for l in challengeable(state)):
            file_case(state, law, player.party, by_player=True)
        else:
            state.emit("CareerEvent",
                       f"No court will hear a case against the {law.name}.",
                       action="challenge")

    elif action.kind == "platform":
        # leaders pull the party platform toward their own position
        pt = state.parties[player.party]
        old = np.asarray(pt.platform)
        pt.platform = tuple(np.clip(old + 0.05 * (np.asarray(player.pos) - old), -1, 1))
        d = float(np.linalg.norm(np.asarray(pt.platform) - old))
        state.emit("CareerEvent",
                   f"You nudge {pt.name}'s platform — it moves {d:.2f} "
                   f"toward you.", action="platform")


def _leave_party(state: GameState, player, exclude=()) -> None:
    """Floor-crossing bookkeeping: the district calls it betrayal, old
    colleagues burn the bridge, posts and standing die with the tie —
    and a PM who crosses forfeits the office. exclude: members walking
    with you — they don't burn a bridge they're crossing."""
    old = state.parties.get(player.party)
    if old is not None:
        state.voters.betrayal[state.voters.district == player.district] += p.DEFECT_BETRAYAL
        old.members.discard(player.id)
        for mid in old.members - set(exclude):
            if mid in state.mps:
                state.mps[mid].relationships[player.id] = \
                    state.mps[mid].relationships.get(player.id, 0.0) - p.DEFECT_REL_HIT
        if old.leader == player.id:
            stayers = old.members - set(exclude)   # walkers can't inherit the chair
            if stayers:
                from .career import successor
                old.leader = successor(state, old, stayers)
    player.faction = None
    player.junior, player.junior_weeks = None, 0
    player.portfolio, player.portfolio_weeks = None, 0   # stripped at once
    player.standing = 0.0                                # no borrowed standing
    was_pm = state.government.pm == player.id and state.phase == "governing"
    player.party = None
    if was_pm:
        state.government.budget_stance = None   # your signals leave with you
        state.government.amend_move = None      # and your pending amendment
        state.bench_shortlist = []              # and your pending nominees lapse
        # you can't lead a coalition you left — the office follows the
        # largest coalition party's leader; nobody legitimate -> it falls.
        # Successors must be *staying* members — a pending walker can't
        # inherit an office in a coalition they're about to leave.
        largest = max(sorted(i for i in state.government.parties if i in state.parties),
                      key=lambda i: len(state.parties[i].members), default=None)
        pool = (state.parties[largest].members - set(exclude) - {player.id}
                if largest is not None else set())
        succ = (state.parties[largest].leader
                if pool and state.parties[largest].leader in pool
                else (max(sorted(pool), key=lambda m: state.mps[m].ambition) if pool else None))
        if succ is not None and succ in state.mps:
            state.government.pm = succ
            # the premiership vacates any held ministry — one chair per head
            state.mps[succ].portfolio, state.mps[succ].portfolio_weeks = None, 0
            state.mps[succ].junior, state.mps[succ].junior_weeks = None, 0
            state.emit("PmChange",
                       f"{state.mps[succ].name} succeeds you as Prime Minister "
                       f"— {state.parties[largest].name} keeps the coalition.",
                       mp=succ)
        else:
            from .government import collapse
            collapse(state, "defection")


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
