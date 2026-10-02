"""Pure drawing for the pygame driver. No sim mutation, no input handling."""
from __future__ import annotations

import math

import numpy as np
import pygame

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
              "PartyDissolved", "Scandal", "ElectionCalled", "ElectionResult", "SeatLost"}


def party_color(state, pid) -> tuple:
    return PARTY_COLORS[pid % len(PARTY_COLORS)] if pid in state.parties else DEFAULT_COLOR


def seat_positions(state) -> dict[int, tuple[float, float]]:
    """MP id -> (x, y) on the hemicycle. Parties sorted left-to-right by platform."""
    ordered = sorted(state.parties.values(), key=lambda pt: pt.platform[0])
    mps = [state.mps[i] for pt in ordered for i in sorted(pt.members)]
    mps += [m for m in sorted(state.mps.values(), key=lambda m: m.id) if m.party is None]
    mps = mps[:120]
    n = len(mps)
    if n == 0:
        return {}
    rows, radii = 5, [150 + i * 48 for i in range(5)]
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
    return {m.district: m.party for m in state.mps.values()}


def draw_map(drv) -> None:
    s, v = drv.state, drv.state.voters
    gx, gy = 12, 10
    cell, ox, oy = 44, 40, 60
    owners = district_owners(s)
    shown = None
    if drv.reveal:
        k = int(drv.reveal["t"] / 3.0 * len(drv.reveal["order"]))
        shown = set(drv.reveal["order"][:k])
    for m in s.mps.values():
        mask = v.district == m.district
        if not mask.any():
            continue
        cent = v.pos[mask].mean(axis=0)
        col = int(np.clip((cent[0] + 1) / 2 * gx, 0, gx - 1))
        row = int(np.clip((cent[1] + 1) / 2 * gy, 0, gy - 1))
        pid = owners[m.district]
        if shown is not None and m.district not in shown:
            pid = drv.district_prev.get(m.district, pid)  # pre-election holder
        bright = 0.4 + 0.6 * m.seat_safety
        c = tuple(int(x * bright) for x in party_color(s, pid))
        r = pygame.Rect(ox + col * (cell + 2), oy + row * (cell + 2), cell, cell)
        pygame.draw.rect(drv.screen, c, r)
        if m.id == s.player_id:
            pygame.draw.rect(drv.screen, WHITE, r, 2)
    _text(drv, "Districts (FPTP)", (ox, oy - 28), DIM)

    sx, sy, sz = 560, 60, 420
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


def _text(drv, s, xy, color=FG, font=None) -> None:
    drv.screen.blit((font or drv.font).render(s, True, color), xy)


def draw_parliament(drv, pos) -> None:
    s = drv.state
    for mid, (x, y) in pos.items():
        mp = s.mps[mid]
        col = party_color(s, mp.party) if mp.party is not None else DEFAULT_COLOR
        vote = drv.vote_flash.get(mid)  # "yes"/"no" during vote cascade
        if vote:
            col = GREEN if vote == "yes" else RED
        pygame.draw.circle(drv.screen, col, (int(x), int(y)), SEAT_R)
        if mid == s.player_id:
            pygame.draw.circle(drv.screen, WHITE, (int(x), int(y)), SEAT_R + 3, 2)
        if mid == s.government.pm:
            pygame.draw.circle(drv.screen, GOLD, (int(x), int(y) - 14), 3)
    # legend: party, seats
    y = 18
    for pt in sorted(s.parties.values(), key=lambda p: p.platform[0]):
        if not pt.members:
            continue
        pygame.draw.circle(drv.screen, party_color(s, pt.id), (26, y + 8), 6)
        gov = " [gov]" if pt.id in s.government.parties else ""
        _text(drv, f"{pt.name}: {len(pt.members)}{gov}", (40, y))
        y += 20


def draw_panel(drv) -> None:
    s, f = drv.state, drv.font
    pygame.draw.rect(drv.screen, PANEL, (PANEL_X, 0, W - PANEL_X, H))
    x, y = PANEL_X + 16, 14
    _text(drv, f"Week {s.week}   {s.phase}", (x, y), font=drv.big)
    y += 36
    speed = ["0.5x", "1x", "2x", "4x"][drv.speed_i]
    _text(drv, f"{'PAUSED' if drv.paused else 'running'} {speed}   space=pause tab=map q=quit", (x, y), DIM)
    y += 28
    last = next((e for e in reversed(s.log) if e.type == "PollShift"), None)
    if last:
        _text(drv, "Polls", (x, y), DIM)
        y += 20
        for pid, share in sorted(last.data["shares"].items(), key=lambda kv: -kv[1]):
            if pid not in s.parties:
                continue
            pygame.draw.rect(drv.screen, party_color(s, pid), (x, y + 3, int(share * 160), 10))
            _text(drv, f"{s.parties[pid].name} {share:.0%}", (x + 8 + int(share * 160), y), DIM)
            y += 16
        y += 8
    mp = s.mps.get(s.player_id)
    if mp:
        pt = s.parties.get(mp.party)
        _text(drv, f"You: {mp.name}", (x, y))
        y += 20
        _text(drv, f"{pt.name if pt else 'independent'}  d{mp.district}  safety {mp.seat_safety:.0%}", (x, y), DIM)
        y += 20
        _text(drv, f"portfolio: {mp.portfolio or '—'}", (x, y), DIM)
        y += 24
    _text(drv, "Events", (x, y), DIM)
    y += 20
    for e in s.log[-9:]:
        c = RED if e.type in INTERRUPTS else FG
        _text(drv, e.text[:46], (x, y), c)
        y += 18


def _button(drv, bid: str, label: str, rect) -> None:
    pygame.draw.rect(drv.screen, (50, 55, 70), rect)
    pygame.draw.rect(drv.screen, DIM, rect, 1)
    _text(drv, label, (rect.x + 8, rect.y + 6))
    drv.buttons[bid] = rect


def draw_action_panel(drv) -> None:
    from sim.actions import available_actions
    pygame.draw.rect(drv.screen, PANEL, (20, H - 150, 940, 130))
    pygame.draw.rect(drv.screen, DIM, (20, H - 150, 940, 130), 1)
    _text(drv, f"Actions — pick {2 - len(drv.picks)} more "
               f"(or continue): {[a.kind for a in drv.picks]}", (34, H - 140))
    if drv.need_target:
        _text(drv, f"{drv.need_target}: click an MP's seat to target", (34, H - 114), GOLD)
    elif drv.need_axis:
        _text(drv, f"{drv.need_axis}: pick an axis", (34, H - 114), GOLD)
        _button(drv, "axis:0", "economic", pygame.Rect(34, H - 88, 110, 28))
        _button(drv, "axis:1", "social", pygame.Rect(154, H - 88, 110, 28))
    else:
        x = 34
        for kind in available_actions(drv.state):
            w = 8 + 9 * len(kind) + 16
            _button(drv, f"act:{kind}", kind, pygame.Rect(x, H - 110, w, 30))
            x += w + 8
    _button(drv, "continue", "continue >>", pygame.Rect(34, H - 50, 110, 28))
    _button(drv, "why", "why?", pygame.Rect(154, H - 50, 70, 28))


def draw_inspect(drv) -> None:
    from sim.inspect import explain_mp
    if drv.inspect_mp is None or drv.inspect_mp not in drv.state.mps:
        return
    lines = explain_mp(drv.state, drv.inspect_mp).split("\n")
    pygame.draw.rect(drv.screen, PANEL, (700, 40, 260, 30 + 20 * len(lines)))
    pygame.draw.rect(drv.screen, GOLD, (700, 40, 260, 30 + 20 * len(lines)), 1)
    for i, line in enumerate(lines):
        _text(drv, line.strip()[:34], (712, 50 + 20 * i))


def draw_why(drv) -> None:
    if not drv.why_text:
        return
    lines = drv.why_text.split("\n")
    pygame.draw.rect(drv.screen, PANEL, (40, 40, 900, 640))
    pygame.draw.rect(drv.screen, GOLD, (40, 40, 900, 640), 1)
    small = pygame.font.Font(None, 15)
    for i, line in enumerate(lines[1:118]):
        col, row = divmod(i, 59)
        drv.screen.blit(small.render(line[:64], True, FG), (56 + col * 440, 50 + row * 11))
    _text(drv, lines[0][:80], (56, 662), GOLD)


def draw_banner(drv) -> None:
    if not drv.banner:
        return
    pygame.draw.rect(drv.screen, PANEL, (200, 300, 880, 120))
    pygame.draw.rect(drv.screen, RED, (200, 300, 880, 120), 2)
    _text(drv, drv.banner[:90], (220, 330), font=drv.big)
    _text(drv, "Space or click to continue", (220, 380), DIM)


def draw(drv) -> None:
    """Whole frame. drv: .screen .font .big .state .banner .paused .speed_i .vote_flash .view"""
    drv.screen.fill(BG)
    drv.buttons = {}
    drv.seat_rects = {}
    if drv.view == "map":
        draw_map(drv)
    else:
        pos = seat_positions(drv.state)
        drv.seat_rects = {m: pygame.Rect(int(x) - 9, int(y) - 9, 18, 18)
                          for m, (x, y) in pos.items()}
        draw_parliament(drv, pos)
    draw_panel(drv)
    draw_inspect(drv)
    if drv.action_pause:
        draw_action_panel(drv)
    draw_why(drv)
    draw_banner(drv)
