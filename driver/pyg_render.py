"""Pure drawing for the pygame driver. No sim mutation, no input handling."""
from __future__ import annotations

import pygame

BG = (18, 20, 26)
PANEL = (28, 31, 40)
FG = (220, 220, 225)
DIM = (120, 125, 135)
RED = (200, 80, 70)

PARTY_COLORS = [(90, 170, 90), (60, 140, 200), (210, 170, 60), (90, 90, 190), (170, 80, 80)]
# matched to params.PARTY_PLATFORMS order: Labour, Green... assigned by party id fallback
DEFAULT_COLOR = (140, 140, 150)

INTERRUPTS = {"ConfidenceLost", "CoalitionFormed", "PartyFormed", "Defection",
              "PartyDissolved", "Scandal", "ElectionCalled", "ElectionResult", "SeatLost"}


def party_color(state, pid) -> tuple:
    if pid in state.parties:
        return PARTY_COLORS[pid % len(PARTY_COLORS)]
    return DEFAULT_COLOR


def draw(drv) -> None:
    """Whole frame. drv exposes .screen .font .big .state .banner .paused .speed_i."""
    s, scr = drv.state, drv.screen
    scr.fill(BG)
    scr.blit(drv.big.render(
        f"Week {s.week}  [{s.phase}]"
        + ("  (paused)" if drv.paused else ""), True, FG), (20, 16))
    y = 60
    for e in drv.events[-10:]:
        c = RED if e.type in INTERRUPTS else FG
        scr.blit(drv.font.render(f"[{e.type}] {e.text}", True, c), (20, y))
        y += 22
    if drv.banner:
        pygame.draw.rect(scr, PANEL, (200, 300, 880, 120))
        pygame.draw.rect(scr, RED, (200, 300, 880, 120), 2)
        scr.blit(drv.big.render(drv.banner[:90], True, FG), (220, 330))
        scr.blit(drv.font.render("Space or click to continue", True, DIM), (220, 380))
