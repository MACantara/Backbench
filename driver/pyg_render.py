"""Pure drawing for the pygame driver. No sim mutation, no input handling."""
from __future__ import annotations

import math

import numpy as np
import pygame

from sim.naming import POLE_LABELS

W, H = 1280, 720
PANEL_X = 980                       # side panel starts here
CX, CY = 470, 600                   # hemicycle center (bottom of the arc)
SEAT_R = 7                          # seat dot radius

BG = (18, 20, 26)
PANEL = (28, 31, 40)
FG = (220, 220, 225)
DIM = (120, 125, 135)
RED = (200, 80, 70)
GREEN = (80, 180, 90)
WHITE = (240, 240, 245)
GOLD = (230, 200, 90)

PARTY_COLORS = [(200, 70, 70), (80, 180, 90), (210, 170, 60), (70, 110, 200), (150, 90, 170),
                (90, 190, 190), (190, 120, 60), (120, 120, 200)]
DEFAULT_COLOR = (140, 140, 150)

INTERRUPTS = {"ConfidenceLost", "CoalitionFormed", "PartyFormed", "Defection",
              "PartyDissolved", "Scandal", "ElectionCalled", "ElectionResult", "SeatLost",
              "ScandalBreaks", "Expelled", "Resigned", "MinisterSacked",
              "PressCycle", "OfferMade", "OfferDeclined", "OfferLapsed",
              "LawRepealed", "LawLapsed", "PmChange", "BudgetSet",
              "AttackLands", "DebtCrisis", "AmbitionMet", "AmbitionFailed",
              "PayrollFall", "Elected"}


def party_color(state, pid) -> tuple:
    return PARTY_COLORS[pid % len(PARTY_COLORS)] if pid in state.parties else DEFAULT_COLOR


def seat_positions(state) -> dict[int, tuple[float, float]]:
    """MP id -> (x, y) on the hemicycle. Parties sorted left-to-right by platform."""
    ordered = sorted(state.parties.values(), key=lambda pt: pt.platform[0])
    mps = [state.mps[i] for pt in ordered for i in sorted(pt.members)]
    mps += [m for m in sorted(state.mps.values(), key=lambda m: m.id) if m.party is None]
    n = len(mps)
    if n == 0:
        return {}
    # a bigger house gets more arcs packed into the same span
    rows = min(9, max(5, math.ceil(n / 40)))
    radii = [150 + i * (192 / (rows - 1)) for i in range(rows)]
    weights = [r / sum(radii) for r in radii]
    counts = [round(n * w) for w in weights]
    counts[-1] += n - sum(counts)     # rounding residue lands in the outermost row
    pos, i = {}, 0
    for r, count in zip(radii, counts):
        for k in range(count):
            if i >= n:
                break
            theta = math.pi - (k + 0.5) / count * math.pi
            pos[mps[i].id] = (CX + r * math.cos(theta), CY - r * math.sin(theta))
            i += 1
    return pos


def district_owners(state) -> dict[int, int | None]:
    tallies: dict[int, dict] = {}
    for m in state.mps.values():
        d = tallies.setdefault(m.district, {})
        d[m.party] = d.get(m.party, 0) + 1
    return {d: max(ps.items(), key=lambda kv: kv[1])[0]
            for d, ps in tallies.items()}


def draw_map(drv) -> None:
    s, v = drv.state, drv.state.voters
    gx, gy = 12, 10
    cell, ox, oy = 40, 40, 60
    owners = district_owners(s)
    shown = None
    if drv.reveal:
        k = int(drv.reveal["t"] / 3.0 * len(drv.reveal["order"]))
        shown = set(drv.reveal["order"][:k])
    drawn = set()
    for m in s.mps.values():
        if m.district in drawn:
            continue            # multi-member districts draw one cell each
        drawn.add(m.district)
        mask = v.district == m.district
        if not mask.any():
            continue
        cent = v.pos[mask].mean(axis=0)
        col = int(np.clip((cent[0] + 1) / 2 * gx, 0, gx - 1))
        row = int(np.clip((cent[1] + 1) / 2 * gy, 0, gy - 1))
        pid = owners[m.district]
        if shown is not None:
            if m.district in shown:
                pid = drv.reveal["winners"].get(m.district, pid)
            else:
                pid = drv.district_prev.get(m.district, pid)  # pre-election holder
        bright = 0.4 + 0.6 * m.seat_safety
        c = tuple(int(x * bright) for x in party_color(s, pid))
        r = pygame.Rect(ox + col * (cell + 2), oy + row * (cell + 2), cell, cell)
        pygame.draw.rect(drv.screen, c, r)
        if m.id == s.player_id:
            pygame.draw.rect(drv.screen, WHITE, r, 2)
    title = "Districts" if s.district_magnitude > 1 else "Districts (FPTP)"
    if drv.reveal:
        tally: dict = {}
        for d in drv.reveal["order"]:
            if d in shown:
                w = drv.reveal["winners"].get(d)
                tally[w] = tally.get(w, 0) + 1
        lead = "  ".join(
            f"{s.parties[p].name if p in s.parties else 'ind'} {n}"
            for p, n in sorted(tally.items(), key=lambda kv: -kv[1]))
        title += f" — called {len(shown)}/{len(drv.reveal['order'])}: {lead}"
        flips = [f"d{d}: {drv.reveal['flips'][d]}"
                 for d in drv.reveal["order"] if d in shown and d in drv.reveal["flips"]]
        if flips:
            _text(drv, _fit(drv, "flips: " + "; ".join(flips[-3:]), 540),
                  (ox, oy + gy * (cell + 2) + 6), WHITE)
    _text(drv, _fit(drv, title, 540), (ox, oy - 28), DIM)

    if drv.reveal:
        draw_election_night(drv)
        return
    sx, sy, sz = 565, 60, 395
    pygame.draw.rect(drv.screen, PANEL, (sx - 12, sy - 12, sz + 24, sz + 24))
    pygame.draw.rect(drv.screen, DIM, (sx - 12, sy - 12, sz + 24, sz + 24), 1)
    for x_, y_ in v.pos[::7]:                    # ~1400 sampled voters
        px = int(sx + (x_ + 1) / 2 * sz)
        py = int(sy + (1 - (y_ + 1) / 2) * sz)
        drv.screen.set_at((px, py), (95, 95, 108))
    for pt in s.parties.values():
        if not pt.members:
            continue
        px = int(sx + (pt.platform[0] + 1) / 2 * sz)
        py = int(sy + (1 - (pt.platform[1] + 1) / 2) * sz)
        pygame.draw.circle(drv.screen, party_color(s, pt.id), (px, py), 10)
        _text(drv, pt.name[:2].upper(), (px - 7, py - 6), BG)
    for m in s.mps.values():
        px = int(sx + (m.pos[0] + 1) / 2 * sz)
        py = int(sy + (1 - (m.pos[1] + 1) / 2) * sz)
        pygame.draw.circle(drv.screen, party_color(s, m.party), (px, py), 3)
        if m.id == s.player_id:
            pygame.draw.circle(drv.screen, WHITE, (px, py), 6, 1)
    _text(drv, "Ideology space  (voters dim, MPs solid, parties lettered)", (sx, sy - 28), DIM)
    _text(drv, POLE_LABELS[0][0], (sx + 4, sy + sz // 2), DIM)          # left edge
    _text(drv, POLE_LABELS[0][1], (sx + sz - 44, sy + sz // 2), DIM)    # right edge
    _text(drv, POLE_LABELS[1][1], (sx + sz // 2 - 38, sy + 4), DIM)     # top edge
    _text(drv, POLE_LABELS[1][0], (sx + sz // 2 - 32, sy + sz - 18), DIM)  # bottom edge


def _cand_row(drv, x: int, y: int, c: dict, s) -> None:
    """One ballot line: color dot, name, party, votes, share — winner marked."""
    pid = c["party"]
    name = s.parties[pid].name if pid in s.parties else "independent"
    pygame.draw.circle(drv.screen, party_color(s, pid), (x + 6, y + 8), 5)
    _text(drv, _fit(drv, c["name"] + (" (inc)" if c["incumbent"] else ""), 150,
                    drv.small), (x + 16, y), FG if c.get("won") else DIM,
          drv.small)
    _text(drv, _fit(drv, name, 90, drv.small), (x + 172, y), DIM, drv.small)
    _text(drv, f"{c['votes']:>5}", (x + 268, y), FG, drv.small)
    _text(drv, f"{c['share']:.0%}", (x + 326, y),
          GOLD if c.get("won") else DIM, drv.small)


def draw_election_night(drv) -> None:
    """The broadcast panel: staggered calls with running totals and the
    resolving district's ballot, then the votes-to-seats final summary.
    Lives where the ideology scatter sits for the duration of the reveal."""
    s = drv.state
    x0, w, y = 545, 420, 30
    pygame.draw.rect(drv.screen, PANEL, (x0 - 10, y - 8, w + 20, 560))
    pygame.draw.rect(drv.screen, DIM, (x0 - 10, y - 8, w + 20, 560), 1)
    call = drv.election_call or {}
    why = {"strategic": "the government gambled on the polls",
           "confidence": "the government fell",
           "deadlock": "no majority could be formed"}.get(call.get("reason"), "")
    label = (f"snap election — {why}" if call.get("snap")
             else "scheduled election — the term ran out" if call
             else "general election")
    _text(drv, "ELECTION NIGHT", (x0, y + 6), GOLD, drv.big)
    _text(drv, label, (x0, y + 40), DIM)

    res = drv.results or {}
    seats, prev = res.get("seats", {}), res.get("prev", {})
    order, data = drv.reveal["order"], drv.reveal["data"]
    # the house size comes from the ballots themselves — the broadcast must
    # render even if `results` was already replaced by a later week
    total = max(sum(sum(dd["winners"].values()) for dd in data.values()),
                sum(seats.values()), 1)
    majority = total // 2 + 1
    k = len(order) if drv.night_final else int(
        drv.reveal["t"] / 3.0 * len(order))
    called = order[:k]

    run: dict = {}
    for d in called:
        for pid, n in data[d]["winners"].items():
            run[pid] = run.get(pid, 0) + n
    by = y + 66
    acc = 0
    for pid, n in sorted(run.items(), key=lambda kv: -kv[1]):
        wseg = max(int(w * n / total), 1)
        pygame.draw.rect(drv.screen, party_color(s, pid),
                         (x0 + acc, by, wseg, 14))
        acc += wseg
    mx = x0 + int(w * majority / total)
    pygame.draw.line(drv.screen, WHITE, (mx, by - 4), (mx, by + 18))
    _text(drv, f"called {k}/{len(order)}   seats to a majority: {majority}",
          (x0, by + 22), DIM, drv.small)
    lead = "  ".join(f"{s.parties[pid].name[:14] if pid in s.parties else 'ind'} {n}"
                     for pid, n in sorted(run.items(), key=lambda kv: -kv[1])[:4])
    _text(drv, _fit(drv, lead, w, drv.small), (x0, by + 40), FG, drv.small)
    y = by + 64

    if not drv.night_final:
        if not called:
            _text(drv, "polls closing...", (x0, y), DIM)
            return
        d = called[-1]
        dd = data[d]
        _text(drv, _fit(drv,
                        f"district {d}{' — FLIPPED' if dd['flipped'] else ''}   "
                        f"turnout {dd['turnout']}", w, drv.small),
              (x0, y), GOLD if dd["flipped"] else FG, drv.small)
        y += 22
        for c in dd["candidates"]:
            _cand_row(drv, x0, y, c, s)
            y += 18
        if len(order) > k:
            _text(drv, "click to call them all", (x0, y + 14), DIM, drv.small)
        return

    # FINAL — the full table: votes in, seats out
    _text(drv, "votes in, seats out", (x0, y), GOLD)
    y += 24
    votes = res.get("votes", {})
    vtot = max(sum(votes.values()), 1)
    _text(drv, "party               votes    v%   seats   s%    +/-",
          (x0, y), DIM, drv.small)
    y += 18
    for pid in sorted({*seats, *prev}, key=lambda q: -seats.get(q, 0)):
        name = s.parties[pid].name[:16] if pid in s.parties else "independent"
        n, was = seats.get(pid, 0), prev.get(pid, 0)
        v = votes.get(pid, 0)
        delta = f"{'+' if n - was >= 0 else ''}{n - was}" if n != was else ""
        pygame.draw.circle(drv.screen, party_color(s, pid), (x0 + 5, y + 8), 4)
        _text(drv, f"{name:<18}{v:>6} {v / vtot:>6.0%} {n:>6} "
                   f"{n / total:>6.0%} {delta:>5}", (x0 + 14, y), FG, drv.small)
        y += 17
    y += 10

    player_d = drv.player_district
    if player_d is not None and player_d in data:
        dd = data[player_d]
        a = dd["candidates"][0] if dd["candidates"] else None
        held = any(m.district == player_d and m.id == s.player_id
                   for m in s.mps.values())
        b = dd["candidates"][1] if len(dd["candidates"]) > 1 else None
        line = (f"your seat d{player_d}: held — {a['name']}"
                + (f" by {a['votes'] - b['votes']} votes" if b else "")
                if held and a else f"your seat d{player_d}: LOST")
        _text(drv, _fit(drv, line, w, drv.small), (x0, y),
              GREEN if held else RED, drv.small)
        y += 20
    if data:
        close = min(data.items(), key=lambda kv: kv[1]["margin"])
        ca = close[1]["candidates"]
        if len(ca) >= 2:
            _text(drv, _fit(drv,
                            f"closest race: d{close[0]} — "
                            f"{ca[0]['name']} over {ca[1]['name']} "
                            f"by {ca[0]['votes'] - ca[1]['votes']}",
                            w, drv.small), (x0, y), DIM, drv.small)
            y += 18
        flips = [d for d, dd in data.items() if dd["flipped"]]
        _text(drv, f"{len(flips)} districts changed hands", (x0, y), DIM,
              drv.small)
        y += 18
    _text(drv, "click to continue", (x0, y + 12), DIM, drv.small)


def _text(drv, s, xy, color=FG, font=None) -> None:
    drv.screen.blit((font or drv.font).render(s, True, color), xy)


def _fit(drv, text: str, width: int, font=None) -> str:
    """Ellipsis-trim a line to `width` px — for single-line spots like titles."""
    f = font or drv.font
    if f.size(text)[0] <= width:
        return text
    while text and f.size(text + "...")[0] > width:
        text = text[:-1]
    return text + "..."


def _wrap(drv, text: str, width: int, font=None) -> list:
    """Greedy word wrap to `width` px."""
    f = font or drv.font
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if cur and f.size(trial)[0] > width:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines or [""]


def _close(drv, bid: str, x: int, y: int) -> None:
    """Close affordance for overlay panels — small x in the corner."""
    _button(drv, bid, "x", pygame.Rect(x, y, 22, 20))


def draw_parliament(drv, pos) -> None:
    s = drv.state
    r = min(SEAT_R, max(2, int(SEAT_R * 160 / max(len(pos), 1))))
    for mid, (x, y) in pos.items():
        mp = s.mps[mid]
        col = party_color(s, mp.party) if mp.party is not None else DEFAULT_COLOR
        vote = drv.vote_flash.get(mid)  # "yes"/"no"/"abs" during vote cascade
        if vote:
            col = GREEN if vote == "yes" else RED if vote == "no" else DIM
        pygame.draw.circle(drv.screen, col, (int(x), int(y)), r)
        if mid == s.player_id:
            pygame.draw.circle(drv.screen, WHITE, (int(x), int(y)), r + 3, 2)
        if mid == s.government.pm:
            pygame.draw.circle(drv.screen, GOLD, (int(x), int(y) - r - 7), 3)
    # legend: party, seats — independents count alongside the parties
    y = 44                            # clear of the tab strip
    for pt in sorted(s.parties.values(), key=lambda p: p.platform[0]):
        if not pt.members:
            continue
        pygame.draw.circle(drv.screen, party_color(s, pt.id), (26, y + 8), 6)
        gov = " [gov]" if pt.id in s.government.parties else ""
        _text(drv, f"{pt.name}: {len(pt.members)}{gov}", (40, y))
        y += 20
    inds = sum(1 for m in s.mps.values() if m.party is None)
    if inds:
        pygame.draw.circle(drv.screen, DEFAULT_COLOR, (26, y + 8), 6)
        _text(drv, f"independent: {inds}", (40, y))


def draw_panel(drv) -> None:
    s = drv.state
    pygame.draw.rect(drv.screen, PANEL, (PANEL_X, 0, W - PANEL_X, H))
    x, y = PANEL_X + 16, 14
    _text(drv, f"Week {s.week}   {s.phase}", (x, y), font=drv.big)
    y += 36
    speed = ["0.5x", "1x", "2x", "4x"][drv.speed_i]
    mode = "AUTO" if drv.auto_play else ("PAUSED" if drv.paused else "running")
    _text(drv, f"{mode} {speed}", (x, y), DIM)
    y += 28
    last = next((e for e in reversed(s.log) if e.type == "PollShift"), None)
    if last:
        _text(drv, "Polls", (x, y), DIM)
        y += 20
        for pid, share in sorted(last.data["shares"].items(), key=lambda kv: -kv[1]):
            if pid not in s.parties:
                continue
            pygame.draw.rect(drv.screen, party_color(s, pid), (x, y + 3, int(share * 160), 10))
            _text(drv, f"{s.parties[pid].name[:14]} {share:.0%}",
                  (x + 8 + int(share * 160), y), DIM)
            y += 16
        y += 8
    mp = s.mps.get(s.player_id)
    if mp:
        pt = s.parties.get(mp.party)
        _text(drv, f"You: {mp.name}", (x, y))
        y += 20
        _text(drv, f"{pt.name if pt else 'Speaker' if mp.id == s.speaker else 'independent'}"
                   f"  d{mp.district}  safety {mp.seat_safety:.0%}", (x, y), DIM)
        y += 20
        _text(drv, f"portfolio: {mp.portfolio or '—'}", (x, y), DIM)
        y += 20
        if mp.junior:
            _text(drv, f"party post: {mp.junior} ({mp.junior_weeks}wk)", (x, y), DIM)
            y += 20
        y += 4
    if s.phase == "campaign" and mp:
        from sim.election import district_forecast
        key = (s.week, mp.district)
        fc = drv.forecast_cache.get(key)
        if fc is None:
            drv.forecast_cache.clear()       # single-slot — one week, one district
            fc = district_forecast(s, mp.district)
            drv.forecast_cache[key] = fc
        _text(drv, f"d{mp.district} — the race as it stands", (x, y), DIM)
        y += 18
        for c in fc["candidates"][:3]:
            pid = c["party"]
            pygame.draw.circle(drv.screen, party_color(s, pid), (x + 4, y + 6), 4)
            me_pid = mp.party if mp.party is not None else -1
            you = "*" if c["name"] == mp.name and c["party"] == me_pid else ""
            _text(drv, f"{c['name'][:16]}  {c['share']:.0%}{you}",
                  (x + 12, y), GOLD if c["won"] else DIM, drv.small)
            y += 15
        y += 8
    _text(drv, "Events", (x, y), DIM)
    y += 20
    for e in s.log[-9:]:
        c = RED if e.type in INTERRUPTS else FG
        for ln in _wrap(drv, e.text, W - x - 14)[:2]:
            if y > H - 22:
                break
            _text(drv, ln, (x, y), c)
            y += 16


def _button(drv, bid: str, label: str, rect, disabled: bool = False,
            font=None, pad: int = 6) -> None:
    f = font or drv.font
    if disabled:
        pygame.draw.rect(drv.screen, (34, 37, 48), rect)
        pygame.draw.rect(drv.screen, DIM, rect, 1)
        _text(drv, label, (rect.x + 6, rect.y + pad), DIM, f)
        return                          # unregistered — clicks fall through
    pygame.draw.rect(drv.screen, (50, 55, 70), rect)
    pygame.draw.rect(drv.screen, DIM, rect, 1)
    _text(drv, label, (rect.x + 6, rect.y + pad), FG, f)
    drv.buttons[bid] = rect


def draw_action_panel(drv) -> None:
    from sim.actions import available_actions, cost_of
    pygame.draw.rect(drv.screen, PANEL, (20, H - 150, 940, 130))
    pygame.draw.rect(drv.screen, DIM, (20, H - 150, 940, 130), 1)
    _text(drv, f"Actions — {drv.points_left()} pts left "
               f"(or continue): {[a.kind for a in drv.picks]}", (34, H - 140))
    if drv.need_outlet or drv.leak_outlet is not None:
        me = drv.state.mps[drv.state.player_id]
        hb = drv.hover_bid
        if hb and hb.startswith("otl:"):
            from sim.inspect import explain_action
            oid = None if hb == "otl:x" else int(hb[4:])
            line = (explain_action(drv.state, "leak",
                                   target=drv.leak_outlet, outlet=oid)
                    if drv.leak_outlet is not None
                    else explain_action(drv.state, "court", target=oid))
        else:
            line = ("choose the venue" if drv.leak_outlet is not None
                    else "court which editorial board?")
        _text(drv, _fit(drv, line, 920), (34, H - 114), GOLD)
        x = 34
        if drv.leak_outlet is not None:
            _button(drv, "otl:x", "open market", pygame.Rect(x, H - 88, 110, 28))
            x += 118
        for o in drv.state.outlets:
            warm = o.warmth.get(me.party, 0.0)
            lab = f"{o.name[4:14]} {warm:.1f}"
            w = 16 + 9 * len(lab)
            _button(drv, f"otl:{o.id}", lab, pygame.Rect(x, H - 88, w, 28))
            x += w + 8
    elif drv.need_target:
        from sim.inspect import explain_action
        line = (explain_action(drv.state, drv.need_target, target=drv.hover_mp)
                if drv.hover_mp in drv.state.mps else
                f"{drv.need_target}: click an MP's seat to target")
        _text(drv, _fit(drv, line, 920), (34, H - 114), GOLD)
    elif drv.need_axis:
        _text(drv, f"{drv.need_axis}: pick an axis", (34, H - 114), GOLD)
        _button(drv, "axis:0", "economic", pygame.Rect(34, H - 88, 110, 28))
        _button(drv, "axis:1", "social", pygame.Rect(154, H - 88, 110, 28))
    elif drv.need_vote:
        from sim.inspect import explain_bill
        _text(drv, explain_bill(drv.state).split("\n")[0][:95], (34, H - 114), GOLD)
        _button(drv, "col:1", "aye", pygame.Rect(34, H - 88, 90, 28))
        _button(drv, "col:-1", "no", pygame.Rect(134, H - 88, 90, 28))
        _button(drv, "col:0", "abstain", pygame.Rect(234, H - 88, 110, 28))
    elif drv.need_offer:
        _text(drv, "coalitions on the table:", (34, H - 114), GOLD)
        for i, o in enumerate(drv.state.offers[:5]):
            name = drv.state.parties[o["proposer"]].name[:18]
            _button(drv, f"offer:{i}", f"{i+1}. {name} ({o['bloc']})",
                    pygame.Rect(34 + i * 178, H - 88, 170, 28))
    elif drv.need_budget:
        _text(drv, "the posture you signal:", (34, H - 114), GOLD)
        for i, lab in enumerate(("austerity", "balanced", "stimulus")):
            _button(drv, f"bud:{i}", lab, pygame.Rect(34 + i * 120, H - 88, 110, 28))
    elif drv.need_evolve:
        _text(drv, "reposition toward:", (34, H - 114), GOLD)
        me = drv.state.mps.get(drv.state.player_id)
        x = 34
        _button(drv, "evo:d", "the district", pygame.Rect(x, H - 88, 110, 28))
        x += 118
        if me is not None and me.party is not None:
            _button(drv, "evo:p", "the party", pygame.Rect(x, H - 88, 110, 28))
    elif drv.need_defect:
        _text(drv, "cross the floor to:", (34, H - 114), GOLD)
        me = drv.state.mps.get(drv.state.player_id)
        others = sorted((pt for pt in drv.state.parties.values()
                         if me is None or pt.id != me.party),
                        key=lambda pt: -len(pt.members))[:4]
        x = 34
        for pt in others:
            w = 16 + 9 * min(len(pt.name), 12)
            _button(drv, f"dft:{pt.id}", pt.name[:12], pygame.Rect(x, H - 88, w, 28))
            x += w + 8
        _button(drv, "dft:i", "independent", pygame.Rect(x, H - 88, 110, 28))
    elif drv.need_law:
        from sim.courts import challengeable, legal_risk
        _text(drv, "file suit against:", (34, H - 114), GOLD)
        x = 34
        laws = challengeable(drv.state)
        for i, lw in enumerate(laws[:4]):
            lab = f"{lw.name[:20]} {legal_risk(drv.state, lw):.2f}"
            w = 16 + 9 * len(lab)
            _button(drv, f"law:{i}", lab, pygame.Rect(x, H - 88, w, 28))
            x += w + 8
        if len(laws) > 4:
            _text(drv, f"+{len(laws) - 4} more", (x, H - 82), DIM)
    elif drv.need_judge:
        from sim.naming import describe_pos
        _text(drv, "seat the nominee:", (34, H - 114), GOLD)
        x = 34
        for i, j in enumerate(drv.state.bench_shortlist):
            lab = f"{j.name.split()[-1]} {describe_pos(j.pos)[:8]} {j.age // 52}y"
            w = 16 + 9 * len(lab)
            _button(drv, f"jdg:{i}", lab, pygame.Rect(x, H - 88, w, 28))
            x += w + 8
    elif drv.need_amend:
        from sim.worldgen import _CLAUSES
        fenced = {(a.axis, a.pole) for a in drv.state.constitution
                  if a.kind == "pos"}
        _text(drv, "the clause to move:", (34, H - 114), GOLD)
        x, y = 34, H - 88
        def _amd(bid, lab):
            nonlocal x, y
            w = 16 + 9 * len(lab)
            if x + w > W - 30:          # a full book of clauses wraps
                x, y = 34, y - 34
            _button(drv, bid, lab, pygame.Rect(x, y, w, 28))
            x += w + 8
        for a in drv.state.constitution:
            _amd(f"amd:r{a.id}", f"repeal {a.name[4:][:14]}")
        for ax in (0, 1):
            for pole in (-1, 1):
                if (ax, pole) not in fenced:
                    _amd(f"amd:e{ax}{'+' if pole > 0 else '-'}",
                         f"+{_CLAUSES[(ax, pole)][4:][:14]}")
    else:
        small = drv.small
        x, y = 34, H - 112
        left = drv.points_left()
        for kind in available_actions(drv.state):
            cost = cost_of(kind)
            lab = kind if cost == 0 else f"{kind} ·{cost}"
            w = 6 + 7 * len(lab) + 8
            if x + w > 950:                 # wrap inside the panel — two rows max
                x, y = 34, y + 26
            _button(drv, f"act:{kind}", lab, pygame.Rect(x, y, w, 22),
                    disabled=cost > left, font=small, pad=4)
            x += w + 6
        hb = drv.hover_bid
        if hb and hb.startswith("act:"):
            from sim.inspect import explain_action
            _text(drv, _fit(drv, explain_action(drv.state, hb[4:]), 920,
                            small), (34, H - 58), GOLD, small)
        if drv.state.week == 0 and drv.state.ambition is None:
            # the opening pick — pass it by and the career stays open-ended
            _text(drv, "ambition:", (600, H - 138), GOLD, small)
            x = 668
            for k in ("pm", "majority", "founder", "survivor", "reformer"):
                w = 6 + 7 * len(k) + 8
                _button(drv, f"amb:{k}", k, pygame.Rect(x, H - 142, w, 20),
                        font=small, pad=3)
                x += w + 5
    _button(drv, "continue", "continue >>", pygame.Rect(34, H - 50, 110, 28))
    _button(drv, "why", "why?", pygame.Rect(154, H - 50, 70, 28))
    _button(drv, "bench", "bench", pygame.Rect(234, H - 50, 70, 28))
    _button(drv, "party", "party", pygame.Rect(312, H - 50, 70, 28))
    _button(drv, "auto", "auto: " + ("on" if drv.auto_play else "off"), pygame.Rect(390, H - 50, 90, 28))


def draw_inspect(drv) -> None:
    from sim.inspect import explain_mp
    if drv.inspect_mp is None or drv.inspect_mp not in drv.state.mps:
        return
    lines = [ln for line in explain_mp(drv.state, drv.inspect_mp).split("\n")
             for ln in _wrap(drv, line.strip(), 236)]
    h = 30 + 18 * len(lines)
    pygame.draw.rect(drv.screen, PANEL, (700, 40, 260, h))
    pygame.draw.rect(drv.screen, GOLD, (700, 40, 260, h), 1)
    for i, line in enumerate(lines):
        _text(drv, line, (712, 50 + 18 * i))
    _close(drv, "close:inspect", 934, 44)


def draw_why(drv) -> None:
    if not drv.why_text:
        return
    lines = drv.why_text.split("\n")
    pygame.draw.rect(drv.screen, PANEL, (40, 40, 900, 640))
    pygame.draw.rect(drv.screen, GOLD, (40, 40, 900, 640), 1)
    small = pygame.font.Font(None, 15)
    for i, line in enumerate(lines[1:118]):
        col, row = divmod(i, 59)
        drv.screen.blit(small.render(line[:60], True, FG), (56 + col * 440, 50 + row * 11))
    _text(drv, _fit(drv, lines[0], 860), (56, 662), GOLD)
    _close(drv, "close:why", 906, 46)


def draw_chronicle(drv) -> None:
    c = drv.chronicle
    if not c["open"]:
        return
    s = drv.state
    pygame.draw.rect(drv.screen, BG, (16, 16, PANEL_X - 32, H - 32))
    pygame.draw.rect(drv.screen, DIM, (16, 16, PANEL_X - 32, H - 32), 1)
    _text(drv, "Chronicle — wheel/pgup/pgdn scroll, c/esc close", (28, 24), DIM)
    _close(drv, "close:chr", PANEL_X - 74, 22)
    types = sorted({e.type for e in s.log})
    x = 28
    _button(drv, "flt:all", "all", pygame.Rect(x, 46, 50, 24))
    x += 56
    for label, val in (("core", "_core"), ("echoes", "_echoes")):
        _button(drv, f"flt:{val}", label, pygame.Rect(x, 46, 62, 24))
        if c["filter"] == val:
            pygame.draw.rect(drv.screen, GOLD, (x, 46, 62, 24), 2)
        x += 68
    for t in types:
        w = 9 * len(t) + 22
        _button(drv, f"flt:{t}", t.lower(), pygame.Rect(x, 46, w, 24))
        if c["filter"] == t:
            pygame.draw.rect(drv.screen, GOLD, (x, 46, w, 24), 2)
        x += w + 6
        if x > PANEL_X - 140:
            break                        # out of room — types beyond this stay unfilterable
    if c["filter"] == "_core":
        events = [e for e in s.log if not e.data.get("echo")]
    elif c["filter"] == "_echoes":
        events = [e for e in s.log if e.data.get("echo")]
    else:
        events = (s.log if c["filter"] is None
                  else [e for e in s.log if e.type == c["filter"]])
    visible = (H - 110) // 17
    c["scroll"] = max(0, min(c["scroll"], max(0, len(events) - visible)))
    start = max(0, len(events) - visible - c["scroll"])
    y = 80
    for e in events[start:start + visible]:
        col = RED if e.type in INTERRUPTS else FG
        _text(drv, f"w{e.data.get('week', '?'):>3} [{e.type:<16}] {e.text[:62]}", (28, y), col)
        y += 17
    _text(drv, f"{len(events)} events — scroll {c['scroll']} back", (28, H - 30), DIM)


def draw_tabs(drv) -> None:
    """Always-visible command tabs across the top edge of the canvas."""
    tabs = [
        ("menu:pause", "resume" if drv.paused else "pause"),
        ("menu:auto", "auto on" if drv.auto_play else "auto"),
        ("menu:view", "map" if drv.view == "parliament" else "house"),
        ("menu:chr", "log"), ("menu:shot", "shot"),
        ("burger", "menu"),
    ]
    x = 16
    for bid, lab in tabs:
        w = 14 + 9 * len(lab)
        _button(drv, bid, lab, pygame.Rect(x, 6, w, 24))
        x += w + 6


def draw_burger(drv) -> None:
    """The menu popup — save/load/settings/quit behind the menu tab."""
    drv.menu_rect = None
    if not drv.menu_open:
        return
    if drv.menu_sub == "settings":
        speed = ["0.5x", "1x", "2x", "4x"][drv.speed_i]
        items = [
            ("set:spd", f"speed: {speed}"),
            ("set:fullscreen",
             f"fullscreen: {'on' if drv.fullscreen else 'off'}"),
            ("set:auto", f"autosave: every {drv.autosave_weeks}w"),
            ("gm:main", "back"),
        ]
    else:
        items = [
            ("menu:save", "save"), ("menu:load", "load"),
            ("gm:settings", "settings"), ("menu:home", "main menu"),
            ("menu:quit", "quit"),
        ]
    _scrim(drv)
    bw = 320
    bh = 56 + ((len(items) + 1) // 2) * 40 + 16
    box = pygame.Rect(W // 2 - bw // 2, H // 2 - bh // 2, bw, bh)
    drv.menu_rect = box
    pygame.draw.rect(drv.screen, PANEL, box)
    pygame.draw.rect(drv.screen, GOLD, box, 1)
    _text(drv, drv.menu_sub, (box.x + 16, box.y + 14), font=drv.big)
    _close(drv, "menu:close", box.right - 30, box.y + 12)
    for i, (bid, lab) in enumerate(items):
        row, col = divmod(i, 2)
        _button(drv, bid, lab,
                pygame.Rect(box.x + 16 + col * 146, box.y + 52 + row * 40, 136, 32))


def _scrim(drv, alpha: int = 170) -> None:
    """Dim everything under a modal so the popup owns the focus."""
    s = pygame.Surface((W, H), pygame.SRCALPHA)
    s.fill((0, 0, 0, alpha))
    drv.screen.blit(s, (0, 0))


def draw_saves(drv) -> None:
    """File-picker modal — save slot or load target. Lightbox: outside closes."""
    if not drv.save_picker:
        drv.picker_rect = None
        return
    import datetime as _dt
    _scrim(drv)
    files = sorted((q for q in drv.save_dir.glob("*.json")
                    if q.name != "settings.json"),
                   key=lambda q: -q.stat().st_mtime)[:12]
    rows = (1 if drv.save_picker == "save" else 0) + len(files)
    bh = 56 + 30 * max(rows, 1) + 16
    box = pygame.Rect(W // 2 - 220, 160, 440, bh)
    drv.picker_rect = box
    pygame.draw.rect(drv.screen, PANEL, box)
    pygame.draw.rect(drv.screen, GOLD, box, 1)
    _text(drv, f"{drv.save_picker} game", (box.x + 16, box.y + 12), font=drv.big)
    _close(drv, "pk:close", box.right - 30, box.y + 12)
    y = box.y + 52
    if drv.save_picker == "save":
        _button(drv, "file:new", "+ new save", pygame.Rect(box.x + 16, y, 408, 26))
        y += 30
    if not files:
        _text(drv, "no save files yet", (box.x + 16, y + 6), DIM)
    for i, q in enumerate(files):
        when = _dt.datetime.fromtimestamp(q.stat().st_mtime)
        lab = _fit(drv, f"{q.stem}   {when:%Y-%m-%d %H:%M}", 380)
        _button(drv, f"file:{i}", lab, pygame.Rect(box.x + 16, y, 408, 26))
        y += 30


def draw_banner(drv) -> None:
    if not drv.banner:
        return
    _scrim(drv, 140)
    lines = _wrap(drv, drv.banner, 820, drv.big)
    h = 76 + 30 * len(lines)
    pygame.draw.rect(drv.screen, PANEL, (200, 300, 880, h))
    pygame.draw.rect(drv.screen, RED, (200, 300, 880, h), 2)
    for i, ln in enumerate(lines):
        _text(drv, ln, (220, 322 + 30 * i), font=drv.big)
    _text(drv, "Space, click or x to continue", (220, 326 + 30 * len(lines)), DIM)
    _close(drv, "close:banner", 1052, 308)


def _menu_button(drv, bid: str, lab: str, y: int, w: int = 240) -> None:
    _button(drv, bid, lab, pygame.Rect(W // 2 - w // 2, y, w, 36))


def draw_menu(drv) -> None:
    drv.screen.fill(BG)
    drv.buttons = {}
    cx = W // 2
    t = drv.big.render("Backbench", True, FG)
    drv.screen.blit(t, (cx - t.get_width() // 2, 120))
    tag = "a career inside a parliament that runs itself"
    _text(drv, tag, (cx - drv.font.size(tag)[0] // 2, 158), DIM)
    page = drv.menu_page

    if page == "scenarios":
        from sim.worldgen import SCENARIOS
        _text(drv, "pick a starting situation:", (cx - 240, 230), DIM)
        names = list(SCENARIOS)
        for i, name in enumerate(names):
            row, col = divmod(i, 4)
            rect = pygame.Rect(cx - 240 + col * 124, 256 + row * 34, 116, 28)
            _button(drv, f"scn:{name}", name, rect)
            if name == drv.menu_scenario:
                pygame.draw.rect(drv.screen, GOLD, rect, 2)
        desc = SCENARIOS[drv.menu_scenario].desc
        dy = 256 + ((len(names) + 3) // 4) * 34 + 14
        _text(drv, desc, (cx - drv.font.size(desc)[0] // 2, dy), DIM)
        y = dy + 30
        _menu_button(drv, "start:new", f"start — {drv.menu_scenario}", y)
        _menu_button(drv, "pg:main", "back", y + 50, 120)
    elif page == "settings":
        _text(drv, "settings:", (cx - 120, 230), DIM)
        _menu_button(drv, "set:fullscreen",
                     f"fullscreen: {'on' if drv.fullscreen else 'off'}", 260)
        speed = ["0.5x", "1x", "2x", "4x"][drv.speed_i]
        _menu_button(drv, "set:spd", f"speed: {speed}", 310)
        _menu_button(drv, "set:auto",
                     f"autosave: every {drv.autosave_weeks}w", 360)
        _menu_button(drv, "pg:main", "back", 430, 120)
    else:
        _menu_button(drv, "pg:scenarios", "start game", 260)
        saves = [q for q in (drv.save_dir / "latest.json",
                             drv.save_dir / "autosave.json") if q.exists()]
        if saves:
            _menu_button(drv, "start:load", "load saved game", 310)
        else:
            _text(drv, "no saved games yet", (cx - 76, 318), DIM)
        _menu_button(drv, "pg:settings", "settings", 360)
        _menu_button(drv, "menu:quit", "quit", 410)

    hint = {"main": "enter: start · esc: quit",
            "scenarios": "enter: start · esc: back",
            "settings": "esc: back"}[page]
    _text(drv, hint, (cx - drv.font.size(hint)[0] // 2, H - 40), DIM)
    draw_saves(drv)


def draw(drv) -> None:
    """Whole frame. drv: .screen .font .big .state .banner .paused .speed_i .vote_flash .view"""
    drv.screen.fill(BG)
    drv.buttons = {}
    drv.seat_rects = {}
    if drv.mode == "menu":
        draw_menu(drv)
        return
    if drv.view == "map":
        draw_map(drv)
    else:
        pos = seat_positions(drv.state)
        drv.seat_rects = {m: pygame.Rect(int(x) - 9, int(y) - 9, 18, 18)
                          for m, (x, y) in pos.items()}
        draw_parliament(drv, pos)
    draw_panel(drv)
    draw_inspect(drv)
    if drv.action_pause and not drv.chronicle["open"]:
        draw_action_panel(drv)
    draw_why(drv)
    draw_chronicle(drv)
    draw_tabs(drv)
    draw_burger(drv)
    draw_saves(drv)
    draw_banner(drv)
    draw_gameover(drv)


def draw_gameover(drv) -> None:
    """The career record — scorecard, verdict, hall of fame. Replaces the
    old one-line banner; any click hands off to the title menu."""
    if not drv.gameover:
        return
    from sim.career import epilogue, final_score, score_breakdown, score_title
    from driver.fame import same_run
    s = drv.state
    me = s.mps.get(s.player_id)
    name = me.name if me else "the former member"
    score = final_score(s)
    rows = score_breakdown(s)
    obit = epilogue(s)
    this = {"name": name, "seed": s.seed, "week": s.week}

    _scrim(drv)
    bw = 660
    bh = 190 + 17 * len(rows) + 15 * len(obit) + 90
    box = pygame.Rect(W // 2 - bw // 2, H // 2 - bh // 2, bw, bh)
    pygame.draw.rect(drv.screen, PANEL, box)
    pygame.draw.rect(drv.screen, GOLD, box, 1)
    _text(drv, f"{name} — {score_title(score)}",
          (box.x + 24, box.y + 16), GOLD, drv.big)
    _text(drv, "career record", (box.x + 24, box.y + 50), DIM)
    y = box.y + 74
    for lab, n, wt, pts in rows:
        _text(drv, lab, (box.x + 32, y), font=drv.small)
        _text(drv, f"{n} x{wt}", (box.x + 440, y), DIM, drv.small)
        _text(drv, f"{pts:>4}", (box.x + 560, y), font=drv.small)
        y += 17
    pygame.draw.line(drv.screen, DIM, (box.x + 32, y + 2), (box.right - 32, y + 2))
    _text(drv, "final score", (box.x + 32, y + 8), GOLD, drv.small)
    _text(drv, f"{score:>4}", (box.x + 560, y + 8), GOLD, drv.small)
    y += 34
    for ln in obit:
        _text(drv, _fit(drv, ln, bw - 56, drv.small), (box.x + 24, y),
              DIM, drv.small)
        y += 15
    y += 10
    _text(drv, "hall of fame", (box.x + 24, y), DIM)
    y += 18
    for i, e in enumerate(drv.fame[:3]):
        you = " <- you" if same_run(e, this) else ""
        _text(drv, _fit(drv, f"{i+1}. {e['name']} — {e['score']} "
                        f"({e['title']}){you}", bw - 56, drv.small),
              (box.x + 32, y), FG if you else DIM, drv.small)
        y += 15
    _button(drv, "menu:home", "main menu >>",
            pygame.Rect(box.centerx - 70, box.bottom - 40, 140, 28))
