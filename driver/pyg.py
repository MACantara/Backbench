"""Pygame driver: watch the parliament work. Second driver over the same sim."""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame

from sim.actions import Action
from sim.career import final_score
from sim.persist import from_json, to_json
from sim.tick import tick
from sim.worldgen import new_game

SAVES = Path(__file__).resolve().parent.parent / "saves"
SETTINGS = SAVES / "settings.json"

from driver.pyg_render import (H, INTERRUPTS, W, district_owners, draw,
                               seat_positions)

BASE_WEEK_SECONDS = 1.5
AUTO_BANNER_SECONDS = 1.5     # auto-play dismisses interrupts itself
AUTOSAVE_WEEKS = 4            # a save costs ~60ms — keep it off the weekly path

SPEEDS = [0.5, 1.0, 2.0, 4.0]


class Driver:
    """Owns pygame + clock + pause state. Sim interaction is advance() only."""

    def __init__(self, seed: int = 0, headless: bool = False, scenario=None,
                 fullscreen: bool = False, menu: bool = False):
        if headless:
            import os
            os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        pygame.init()
        saved = self._load_settings()
        self.fullscreen = fullscreen or saved.get("fullscreen", False)
        flags = pygame.RESIZABLE | (pygame.FULLSCREEN if self.fullscreen else 0)
        self.window = pygame.display.set_mode((W, H), flags)
        self.screen = pygame.Surface((W, H))   # fixed canvas, scaled to the window
        pygame.display.set_caption("Backbench")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 22)
        self.big = pygame.font.Font(None, 34)
        self.mode = "menu" if menu else "game"
        self.seed = seed
        self.save_dir = SAVES
        self.menu_scenario = (scenario if isinstance(scenario, str)
                              else saved.get("scenario", "standard"))
        self.menu_page = "main"     # main | scenarios | settings
        self.autosave_weeks = saved.get("autosave_weeks", AUTOSAVE_WEEKS)
        self._speed_i_saved = saved.get("speed_i", 1)
        self.state = new_game(seed, scenario) if not menu else None
        self.running = True
        self.paused = False
        self.speed_i = self._speed_i_saved
        self.week_timer = 0.0
        self.banner = None          # interrupt event text awaiting dismiss
        self.banner_t = 0.0         # seconds the banner has been up
        self._banner_paused = False # pause state before the banner stole it
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
        self.need_vote = None       # "vote"/"deal" awaiting the column choice
        self.need_offer = False     # pick_offer awaiting an offer button
        self.need_budget = False    # "budget" awaiting a stance pick
        self.need_defect = False    # "defect" awaiting a destination pick
        self.need_law = False       # "challenge" awaiting a statute pick
        self.need_judge = False     # "appoint" awaiting a nominee pick
        self.need_amend = False     # "amendment" awaiting a clause pick
        self.need_outlet = False    # "court" awaiting an outlet pick
        self.leak_outlet = None     # pending leak target awaiting venue pick
        self.why_text = None        # explain_vote output while paused
        self.viz_rng = random.Random(1)  # visuals only — never touches sim rng
        self.district_prev = {}     # district -> party before the latest tick
        self.reveal = None          # {"order": [districts], "t": s} election reveal
        self.results = None         # {"seats", "prev"} — seat-change card
        self.chronicle = {"open": False, "scroll": 0, "filter": None}
        self.menu_open = False      # hamburger dropdown
        self.menu_sub = "main"      # main | settings — which page it shows
        self.menu_rect = None       # popup bounds, set by the renderer
        self.save_picker = None     # "save" | "load" — file-picker modal
        self.picker_rect = None     # its bounds, set by the renderer
        self.auto_play = False      # skip the weekly action pause
        self.autosaved_week = -1    # last week written to autosave.json

    @staticmethod
    def _load_settings() -> dict:
        try:
            return json.loads(SETTINGS.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _save_settings(self) -> None:
        SAVES.mkdir(exist_ok=True)
        SETTINGS.write_text(json.dumps({
            "fullscreen": self.fullscreen,
            "speed_i": self.speed_i,
            "autosave_weeks": self.autosave_weeks,
            "scenario": self.menu_scenario,
        }), encoding="utf-8")

    def _new_game(self) -> None:
        self.state = new_game(self.seed, self.menu_scenario)
        self.mode = "game"
        self._reset_view()

    def advance(self, actions: list | None = None) -> None:
        """One week forward; collects events for animation and interrupts."""
        self.results = None
        if self.state.phase == "over":
            self._autosave()        # the career's final state survives a crash
            from sim.career import epilogue
            self._show_banner(f"Game over — score {final_score(self.state)}")
            self.why_text = "\n".join(epilogue(self.state))
            return
        self.district_prev = district_owners(self.state)
        self.events = tick(self.state, actions or [])
        if any(e.type == "ElectionResult" for e in self.events):
            drs = [e for e in self.events if e.type == "DistrictResult"]
            order = [e.data["district"] for e in drs] or list(self.district_prev)
            self.viz_rng.shuffle(order)
            self.reveal = {"order": order, "t": 0.0,
                           "winners": {e.data["district"]: max(
                               e.data["winners"].items(), key=lambda kv: kv[1])[0]
                               for e in drs},
                           "flips": {e.data["district"]: e.text.split(": ", 1)[-1]
                                     for e in drs if e.data["flipped"]},
                           "seats": {}}
            res = next(e for e in self.events if e.type == "ElectionResult")
            self.results = {"seats": res.data["seats"],
                            "prev": res.data.get("prev", {})}
            self.view = "map"
        vote = next((e for e in self.events if e.type == "VoteResult"), None)
        if vote and "detail" in vote.data:
            pos = seat_positions(self.state)
            order = sorted(vote.data["detail"], key=lambda m: pos.get(m, (0, 0))[0])
            self.vote_anim = {"order": order, "t": 0.0,
                              "votes": {m: {1: "yes", -1: "no"}.get(d.get("cast"), "abs")
                                        for m, d in vote.data["detail"].items()}}
        # ElectionResult gets the map reveal instead of a text banner
        hit = next((e for e in self.events
                    if e.type in INTERRUPTS and e.type != "ElectionResult"), None)
        if hit:
            self._show_banner(hit.text)
        if self.state.week % self.autosave_weeks == 0:
            self._autosave()

    def step(self, dt: float) -> None:
        """Advance animations and the auto-run clock; pause/banner blocks progress."""
        if self.state is None:
            return                  # still on the menu
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
        self.banner_t = self.banner_t + dt if self.banner else 0.0
        if (self.banner and self.auto_play and self.state.phase != "over"
                and self.banner_t > AUTO_BANNER_SECONDS):
            self._dismiss_banner()  # spectators keep watching
        if self.paused or self.banner:
            return
        self.week_timer += dt * SPEEDS[self.speed_i]
        if self.week_timer >= BASE_WEEK_SECONDS:
            self.week_timer = 0.0
            if self.auto_play:
                from sim.bot import auto_actions
                self.advance(auto_actions(self.state))
            else:
                self.action_pause = True   # stop the clock for the weekly decision
                self.paused = True

    def _show_banner(self, text: str) -> None:
        """Interrupt the clock — remembers the pause state to restore on dismiss."""
        self._banner_paused = self.paused
        self.banner = text
        self.paused = True

    def _dismiss_banner(self) -> None:
        self.banner = None
        self.paused = self._banner_paused

    def _space(self) -> None:
        if self.banner:
            self._dismiss_banner()
        elif self.action_pause:
            self.on_button("continue")
        else:
            self.paused = not self.paused

    def _toggle_chronicle(self) -> None:
        c = self.chronicle
        c["open"] = not c["open"]
        if c["open"]:
            c["scroll"] = 10 ** 9      # pin to latest; draw clamps

    def _save_to(self, path: Path) -> None:
        SAVES.mkdir(exist_ok=True)
        path.write_text(to_json(self.state), encoding="utf-8")
        self._show_banner(f"Saved — {path.stem} (week {self.state.week})")

    def _save(self) -> None:
        """Quicksave: the named slot for this week plus latest.json."""
        self._save_to(SAVES / f"s{self.state.seed}-w{self.state.week}.json")
        (SAVES / "latest.json").write_text(to_json(self.state),
                                         encoding="utf-8")

    def _load(self, path: Path | None = None) -> None:
        if path is None:
            saves = [q for q in (SAVES / "latest.json",
                                 SAVES / "autosave.json") if q.exists()]
            if not saves:
                return
            path = max(saves, key=lambda q: q.stat().st_mtime)
        self.state = from_json(path.read_text(encoding="utf-8"))
        self._reset_view()
        self.autosaved_week = self.state.week
        self._show_banner(f"Loaded — week {self.state.week}")

    def _shot(self) -> None:
        Path("shots").mkdir(exist_ok=True)
        pygame.image.save(self.screen, f"shots/week{self.state.week}.png")
        self._show_banner("Screenshot saved")

    def _autosave(self) -> None:
        if self.autosaved_week == self.state.week:
            return                  # idempotent — one write per week
        SAVES.mkdir(exist_ok=True)
        (SAVES / "autosave.json").write_text(to_json(self.state),
                                           encoding="utf-8")
        self.autosaved_week = self.state.week

    def _clear_pending(self) -> None:
        """A fresh action pick drops any half-finished pick — no stacked
        prompts waiting on buttons that no longer render."""
        self.need_target = self.need_axis = self.need_vote = None
        self.need_offer = self.need_budget = self.need_defect = False
        self.need_law = self.need_judge = self.need_amend = False
        self.need_outlet = False
        self.leak_outlet = None

    def _reset_view(self) -> None:
        """A loaded state invalidates every per-week visual — drop them all."""
        self._clear_pending()
        self.picks = []
        self.events = []
        self.vote_anim = None
        self.vote_flash = {}
        self.reveal = None
        self.results = None
        self.inspect_mp = None
        self.why_text = None
        self.week_timer = 0.0
        self.action_pause = False
        self.district_prev = district_owners(self.state)
        self.chronicle["scroll"] = 0
        self.menu_open = False

    def on_button(self, bid: str) -> None:
        from sim.inspect import explain_bench, explain_vote
        if bid.startswith("act:"):
            self._clear_pending()
            kind = bid[4:]
            if kind in ("lobby", "dig_dirt", "leak"):
                self.need_target = kind
            elif kind == "deal":
                self.need_target = kind           # counterparty first, then the column
            elif kind in ("speech", "promise", "table"):
                self.need_axis = kind
            elif kind == "vote":
                self.need_vote = kind
            elif kind == "pick_offer":
                self.need_offer = True
            elif kind == "budget":
                self.need_budget = True
            elif kind == "defect":
                self.need_defect = True
            elif kind == "challenge":
                self.need_law = True
            elif kind == "appoint":
                self.need_judge = True
            elif kind == "amendment":
                self.need_amend = True
            elif kind == "court":
                self.need_outlet = True
            else:
                self.picks.append(Action(kind))
                self._after_pick()
        elif bid.startswith("axis:") and self.need_axis:
            self.picks.append(Action(self.need_axis, axis=int(bid[5:])))
            self.need_axis = None
            self._after_pick()
        elif bid.startswith("col:") and self.need_vote:
            v = int(bid[4:])
            if self.need_vote == "deal" and self.picks:
                self.picks[-1].vote = v           # the deal's promised column
            else:
                self.picks.append(Action("vote", vote=v))
            self.need_vote = None
            self._after_pick()
        elif bid.startswith("offer:") and self.need_offer:
            i = int(bid[6:])
            if 0 <= i < len(self.state.offers):
                self.picks.append(Action("pick_offer", offer=i))
            self.need_offer = False
            self._after_pick()
        elif bid.startswith("bud:") and self.need_budget:
            self.picks.append(Action("budget", axis=int(bid[4:])))
            self.need_budget = False
            self._after_pick()
        elif bid.startswith("dft:") and self.need_defect:
            self.picks.append(Action("defect",
                                     target=None if bid[4:] == "i" else int(bid[4:])))
            self.need_defect = False
            self._after_pick()
        elif bid.startswith("law:") and self.need_law:
            from sim.courts import challengeable
            laws = challengeable(self.state)
            i = int(bid[4:])
            if 0 <= i < len(laws):
                pick = laws[i]
                idx = next(j for j, lw in enumerate(self.state.laws) if lw is pick)
                self.picks.append(Action("challenge", law=idx))
            self.need_law = False
            self._after_pick()
        elif bid.startswith("jdg:") and self.need_judge:
            i = int(bid[4:])
            if 0 <= i < len(self.state.bench_shortlist):
                self.picks.append(Action("appoint", judge=i))
            self.need_judge = False
            self._after_pick()
        elif bid.startswith("amd:") and self.need_amend:
            s = bid[4:]
            if s[:1] == "r" and s[1:].isdigit():
                self.picks.append(Action("amendment", article=int(s[1:])))
            elif len(s) == 3 and s[0] == "e":
                self.picks.append(Action("amendment", entrench=(
                    int(s[1]), 1 if s[2] == "+" else -1)))
            self.need_amend = False
            self._after_pick()
        elif bid.startswith("otl:") and (self.need_outlet
                                         or self.leak_outlet is not None):
            oid = None if bid[4:] == "x" else int(bid[4:])
            if self.leak_outlet is not None:
                self.picks.append(Action("leak", target=self.leak_outlet,
                                         outlet=oid))
                self.leak_outlet = None
            else:
                self.picks.append(Action("court", target=oid))
                self.need_outlet = False
            self._after_pick()
        elif bid == "continue":
            self.action_pause, self.paused = False, False
            self.need_target = self.need_axis = self.need_vote = None
            self.need_offer = self.need_budget = self.need_defect = False
            self.need_law = self.need_judge = self.need_amend = False
            self.need_outlet = False
            self.leak_outlet = None
            picks = [pk for pk in self.picks
                     if pk.kind != "deal" or pk.vote is not None]  # unfinished deal = no deal
            self.picks = []
            self.why_text = None
            self.advance(picks)
        elif bid == "why":
            self.why_text = explain_vote(self.state)
        elif bid == "bench":
            self.why_text = explain_bench(self.state)
        elif bid == "auto":
            self.toggle_auto()
        elif bid.startswith("amb:"):
            from sim.state import Ambition
            self.state.ambition = Ambition(bid[4:])
        elif bid.startswith("flt:"):
            f = bid[4:]
            self.chronicle["filter"] = None if f == "all" or f == self.chronicle["filter"] else f
        elif bid == "close:chr":
            self.chronicle["open"] = False
        elif bid == "close:why":
            self.why_text = None
        elif bid == "close:inspect":
            self.inspect_mp = None
        elif bid == "close:banner":
            self._dismiss_banner()
        elif bid == "menu:pause":
            self._space()
        elif bid == "menu:auto":
            self.toggle_auto()
        elif bid == "menu:spd-":
            self.speed_i = max(self.speed_i - 1, 0)
        elif bid == "menu:spd+":
            self.speed_i = min(self.speed_i + 1, len(SPEEDS) - 1)
        elif bid == "menu:view":
            self.view = "map" if self.view == "parliament" else "parliament"
        elif bid == "menu:chr":
            self._toggle_chronicle()
        elif bid == "menu:save":
            self.save_picker = "save"
        elif bid == "menu:load":
            self.save_picker = "load"
        elif bid == "menu:shot":
            self._shot()
        elif bid == "menu:quit":
            self.running = False
        elif bid == "burger":
            self.menu_open = not self.menu_open
            if self.menu_open:
                self.menu_sub = "main"
        elif bid.startswith("gm:"):
            self.menu_sub = bid[3:]
        elif bid.startswith("pg:"):
            self.menu_page = bid[3:]
        elif bid.startswith("scn:"):
            self.menu_scenario = bid[4:]
            self._save_settings()
        elif bid == "start:new":
            self._new_game()
        elif bid == "start:load":
            self.save_picker = "load"
        elif bid == "pk:close":
            self.save_picker = None
        elif bid == "file:new" and self.save_picker == "save" and self.state:
            self.save_picker = None
            self._save_to(SAVES / f"s{self.state.seed}-w{self.state.week}.json")
        elif bid.startswith("file:") and self.save_picker:
            files = sorted((q for q in SAVES.glob("*.json")
                            if q.name != "settings.json"),
                           key=lambda q: -q.stat().st_mtime)[:12]
            i = int(bid[5:])
            if 0 <= i < len(files):
                mode = self.save_picker
                self.save_picker = None
                if mode == "save":
                    self._save_to(files[i])
                else:
                    self._load(files[i])
                    if self.state is not None:
                        self.mode = "game"
        elif bid == "set:fullscreen":
            pygame.display.toggle_fullscreen()
            self.fullscreen = not self.fullscreen
            self._save_settings()
        elif bid == "set:spd":
            self.speed_i = (self.speed_i + 1) % len(SPEEDS)
            self._save_settings()
        elif bid == "set:auto":
            self.autosave_weeks = {1: 2, 2: 4, 4: 8, 8: 1}[self.autosave_weeks]
            self._save_settings()

    def _after_pick(self) -> None:
        if len(self.picks) >= 2:
            self.on_button("continue")

    def toggle_auto(self) -> None:
        self.auto_play = not self.auto_play
        if self.auto_play and self.action_pause:
            self.on_button("continue")  # flush picks, resume the clock

    def handle_event(self, e) -> None:
        if self.mode == "menu":
            if e.type == pygame.QUIT:
                self.running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    if self.menu_page == "main":
                        self.running = False
                    else:
                        self.menu_page = "main"
                elif e.key == pygame.K_q and self.menu_page == "main":
                    self.running = False
                elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_n):
                    if self.menu_page == "scenarios":
                        self._new_game()
                    else:
                        self.menu_page = "scenarios"
            elif e.type == pygame.MOUSEBUTTONDOWN:
                wx, wy = self.window.get_size()
                pos = (int(e.pos[0] * W / wx), int(e.pos[1] * H / wy))
                for bid, rect in self.buttons.items():
                    if rect.collidepoint(pos):
                        if self.save_picker and not (
                                bid.startswith("file:") or bid == "pk:close"):
                            if not (self.picker_rect
                                    and self.picker_rect.collidepoint(pos)):
                                self.save_picker = None
                            return
                        self.on_button(bid)
                        return
                if self.save_picker:
                    self.save_picker = None
            return
        if e.type == pygame.QUIT:
            self.running = False
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                if self.banner:
                    self._dismiss_banner()
                elif self.chronicle["open"]:
                    self.chronicle["open"] = False
                elif self.menu_open:
                    self.menu_open = False
                elif self.save_picker:
                    self.save_picker = None
                elif self.why_text:
                    self.why_text = None
                elif self.inspect_mp is not None:
                    self.inspect_mp = None
                else:
                    self.running = False
            elif e.key == pygame.K_q and not self.chronicle["open"]:
                self.running = False
            elif e.key in (pygame.K_c, pygame.K_l):
                self._toggle_chronicle()
            elif e.key == pygame.K_a:
                self.toggle_auto()
            elif e.key == pygame.K_PAGEUP and self.chronicle["open"]:
                self.chronicle["scroll"] += 20
            elif e.key == pygame.K_PAGEDOWN and self.chronicle["open"]:
                self.chronicle["scroll"] -= 20
            elif e.key == pygame.K_SPACE:
                self._space()
            elif e.key == pygame.K_TAB:
                self.view = "map" if self.view == "parliament" else "parliament"
            elif e.key in (pygame.K_EQUALS, pygame.K_PLUS):
                self.speed_i = min(self.speed_i + 1, len(SPEEDS) - 1)
            elif e.key == pygame.K_MINUS:
                self.speed_i = max(self.speed_i - 1, 0)
            elif e.key == pygame.K_F5:
                self._save()
            elif e.key == pygame.K_F9:
                self.save_picker = "load"
            elif e.key == pygame.K_F12:
                self._shot()
        elif e.type == pygame.MOUSEWHEEL and self.chronicle["open"]:
            self.chronicle["scroll"] += e.y * 3
        elif e.type == pygame.MOUSEBUTTONDOWN:
            wx, wy = self.window.get_size()
            self.on_click((int(e.pos[0] * W / wx), int(e.pos[1] * H / wy)))

    def on_click(self, pos) -> None:
        if self.banner:
            self._dismiss_banner()
            return
        if self.menu_open:
            hit = next((bid for bid, rect in self.buttons.items()
                        if rect.collidepoint(pos)
                        and (bid == "burger" or bid.startswith("menu:"))), None)
            if hit:
                self.on_button(hit)
                if hit.startswith("menu:"):
                    self.menu_open = False   # dropdown closes on selection
            elif not (self.menu_rect and self.menu_rect.collidepoint(pos)):
                self.menu_open = False       # lightbox: click outside dismisses
            return
        if self.save_picker:
            hit = next((bid for bid, rect in self.buttons.items()
                        if rect.collidepoint(pos)
                        and (bid.startswith("file:") or bid == "pk:close")), None)
            if hit:
                self.on_button(hit)
            elif not (self.picker_rect and self.picker_rect.collidepoint(pos)):
                self.save_picker = None      # lightbox again
            return
        for bid, rect in self.buttons.items():
            if rect.collidepoint(pos):
                # the chronicle overlays everything — only its own controls
                # stay live; buttons beneath it must not fire through it
                if self.chronicle["open"] and not (
                        bid.startswith("flt:")
                        or bid in ("close:chr", "menu:chr")):
                    return
                self.on_button(bid)
                return
        if self.chronicle["open"]:
            return  # overlay swallows seat clicks
        hit = next((m for m, r in self.seat_rects.items() if r.collidepoint(pos)), None)
        if hit is not None and self.need_target:
            if self.need_target == "leak" and hit == self.state.player_id:
                return  # leaking yourself is a silent no-op — don't bind it
            if self.need_target == "leak":
                self.leak_outlet = hit    # venue pick comes next
            else:
                self.picks.append(Action(self.need_target, target=hit))
            if self.need_target == "deal":
                self.need_vote = "deal"   # promised column comes next
            self.need_target = None
            if self.need_vote is None and self.leak_outlet is None:
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
            self.window.blit(pygame.transform.scale(self.screen,
                                                    self.window.get_size()), (0, 0))
            pygame.display.flip()
        pygame.quit()


def run(seed: int = 0, scenario=None, fullscreen: bool = False) -> None:
    Driver(seed, scenario=scenario, fullscreen=fullscreen, menu=True).loop()


if __name__ == "__main__":
    sc = sys.argv[sys.argv.index("--scenario") + 1] \
        if "--scenario" in sys.argv else None
    seed = next((a for a in sys.argv[1:]
                 if not a.startswith("-") and a != sc), None)
    run(int(seed) if seed else 0, sc,
        fullscreen="--fullscreen" in sys.argv)
