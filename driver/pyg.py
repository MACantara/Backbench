"""Pygame driver: watch the parliament work. Second driver over the same sim."""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame

from sim.actions import Action
from sim.career import final_score
from sim.tick import tick
from sim.worldgen import new_game

from driver.pyg_render import (H, INTERRUPTS, W, district_owners, draw,
                               seat_positions)

BASE_WEEK_SECONDS = 1.5

SPEEDS = [0.5, 1.0, 2.0, 4.0]


class Driver:
    """Owns pygame + clock + pause state. Sim interaction is advance() only."""

    def __init__(self, seed: int = 0, headless: bool = False):
        if headless:
            import os
            os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        pygame.init()
        self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption("Backbench")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 22)
        self.big = pygame.font.Font(None, 34)
        self.state = new_game(seed)
        self.running = True
        self.paused = False
        self.speed_i = 1
        self.week_timer = 0.0
        self.banner = None          # interrupt event text awaiting dismiss
        self.events = []            # events from latest tick, for animation
        self.view = "parliament"    # or "map" (Tab)
        self.vote_flash = {}        # mp_id -> "yes"/"no" during vote cascade
        self.vote_anim = None       # {"order": [...], "votes": {...}, "t": seconds}
        self.seat_rects = {}        # mp_id -> Rect, rebuilt each draw for hit tests
        self.buttons = {}           # button id -> Rect, rebuilt each draw
        self.inspect_mp = None      # mp_id shown in inspect card
        self.action_pause = False   # modal: waiting for weekly action picks
        self.picks = []             # actions chosen this week
        self.need_target = None     # action kind awaiting a seat click
        self.need_axis = None       # action kind awaiting an axis button
        self.why_text = None        # explain_vote output while paused
        self.viz_rng = random.Random(1)  # visuals only — never touches sim rng
        self.district_prev = {}     # district -> party before the latest tick
        self.reveal = None          # {"order": [districts], "t": s} election reveal

    def advance(self, actions: list | None = None) -> None:
        """One week forward; collects events for animation and interrupts."""
        if self.state.phase == "over":
            self.banner = f"Game over — score {final_score(self.state)}"
            self.paused = True
            return
        self.district_prev = district_owners(self.state)
        self.events = tick(self.state, actions or [])
        if any(e.type == "ElectionResult" for e in self.events):
            order = list(self.district_prev)
            self.viz_rng.shuffle(order)
            self.reveal = {"order": order, "t": 0.0}
            self.view = "map"
        vote = next((e for e in self.events if e.type == "VoteResult"), None)
        if vote and "detail" in vote.data:
            pos = seat_positions(self.state)
            order = sorted(vote.data["detail"], key=lambda m: pos.get(m, (0, 0))[0])
            self.vote_anim = {"order": order, "t": 0.0,
                              "votes": {m: ("yes" if d["u"] > 0 else "no")
                                        for m, d in vote.data["detail"].items()}}
        # ElectionResult gets the map reveal instead of a text banner
        hit = next((e for e in self.events
                    if e.type in INTERRUPTS and e.type != "ElectionResult"), None)
        if hit:
            self.banner = hit.text
            self.paused = True

    def step(self, dt: float) -> None:
        """Advance animations and the auto-run clock; pause/banner blocks progress."""
        if self.reveal:
            self.reveal["t"] += dt
            if self.reveal["t"] > 4.5:
                self.reveal = None
        if self.vote_anim:
            self.vote_anim["t"] += dt
            k = int(self.vote_anim["t"] / 0.007)
            if self.vote_anim["t"] > 2.0:
                self.vote_anim, self.vote_flash = None, {}
            else:
                self.vote_flash = {m: self.vote_anim["votes"][m]
                                   for m in self.vote_anim["order"][:k]}
        if self.paused or self.banner:
            return
        self.week_timer += dt * SPEEDS[self.speed_i]
        if self.week_timer >= BASE_WEEK_SECONDS:
            self.week_timer = 0.0
            self.action_pause = True   # stop the clock for the weekly decision
            self.paused = True

    def on_button(self, bid: str) -> None:
        from sim.inspect import explain_vote
        if bid.startswith("act:"):
            kind = bid[4:]
            if kind in ("lobby", "dig_dirt"):
                self.need_target = kind
            elif kind in ("speech", "promise"):
                self.need_axis = kind
            else:
                self.picks.append(Action(kind))
                self._after_pick()
        elif bid.startswith("axis:") and self.need_axis:
            self.picks.append(Action(self.need_axis, axis=int(bid[5:])))
            self.need_axis = None
            self._after_pick()
        elif bid == "continue":
            self.action_pause, self.paused = False, False
            picks, self.picks = self.picks, []
            self.why_text = None
            self.advance(picks)
        elif bid == "why":
            self.why_text = explain_vote(self.state)

    def _after_pick(self) -> None:
        if len(self.picks) >= 2:
            self.on_button("continue")

    def handle_event(self, e) -> None:
        if e.type == pygame.QUIT:
            self.running = False
        elif e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_ESCAPE, pygame.K_q):
                self.running = False
            elif e.key == pygame.K_SPACE:
                if self.banner:
                    self.banner = None
                    self.paused = False
                elif self.action_pause:
                    self.on_button("continue")
                else:
                    self.paused = not self.paused
            elif e.key == pygame.K_TAB:
                self.view = "map" if self.view == "parliament" else "parliament"
            elif e.key in (pygame.K_EQUALS, pygame.K_PLUS):
                self.speed_i = min(self.speed_i + 1, len(SPEEDS) - 1)
            elif e.key == pygame.K_MINUS:
                self.speed_i = max(self.speed_i - 1, 0)
            elif e.key == pygame.K_F12:
                Path("shots").mkdir(exist_ok=True)
                pygame.image.save(self.screen, f"shots/week{self.state.week}.png")
        elif e.type == pygame.MOUSEBUTTONDOWN:
            self.on_click(e.pos)

    def on_click(self, pos) -> None:
        if self.banner:
            self.banner, self.paused = None, False
            return
        for bid, rect in self.buttons.items():
            if rect.collidepoint(pos):
                self.on_button(bid)
                return
        hit = next((m for m, r in self.seat_rects.items() if r.collidepoint(pos)), None)
        if hit is not None and self.need_target:
            self.picks.append(Action(self.need_target, target=hit))
            self.need_target = None
            self._after_pick()
        else:
            self.inspect_mp = hit  # seat -> card, empty space -> close

    def draw(self) -> None:
        draw(self)

    def loop(self) -> None:
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            for e in pygame.event.get():
                self.handle_event(e)
            self.step(dt)
            self.draw()
            pygame.display.flip()
        pygame.quit()


def run(seed: int = 0) -> None:
    Driver(seed).loop()


if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 0)
