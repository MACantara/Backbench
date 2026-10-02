"""Pygame driver: watch the parliament work. Second driver over the same sim."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame

from sim.actions import Action
from sim.career import final_score
from sim.tick import tick
from sim.worldgen import new_game

from driver.pyg_render import H, INTERRUPTS, W, draw

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
        self.seat_rects = {}        # mp_id -> Rect, rebuilt each draw for hit tests
        self.inspect_mp = None      # mp_id shown in inspect card

    def advance(self, actions: list | None = None) -> None:
        """One week forward; collects events for animation and interrupts."""
        if self.state.phase == "over":
            self.banner = f"Game over — score {final_score(self.state)}"
            self.paused = True
            return
        self.events = tick(self.state, actions or [])
        hit = next((e for e in self.events if e.type in INTERRUPTS), None)
        if hit:
            self.banner = hit.text
            self.paused = True

    def step(self, dt: float) -> None:
        """Advance the auto-run clock; pause/banner blocks progress."""
        if self.paused or self.banner:
            return
        self.week_timer += dt * SPEEDS[self.speed_i]
        if self.week_timer >= BASE_WEEK_SECONDS:
            self.week_timer = 0.0
            self.advance()

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
                else:
                    self.paused = not self.paused
            elif e.key in (pygame.K_EQUALS, pygame.K_PLUS):
                self.speed_i = min(self.speed_i + 1, len(SPEEDS) - 1)
            elif e.key == pygame.K_MINUS:
                self.speed_i = max(self.speed_i - 1, 0)
        elif e.type == pygame.MOUSEBUTTONDOWN and self.banner:
            self.banner = None
            self.paused = False

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
