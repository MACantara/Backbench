# Roadmap

Phases are ordered by dependency and player-facing value, not chronology guarantees. Each phase lists why it exists and what "done" looks like. Anything listed here is a candidate — nothing is committed until it survives a "does the game need this?" pass.

## Phase 1 — Playable core (built)

The spec implemented end to end. Terminal driver, all checks green, 10 commits on `main`.

- [x] Seeded worldgen: 120 FPTP districts, ~10k voter agents in 2D ideology space, ~120 MP agents
- [x] Elections: spatial voter scoring, turnout, incumbency, polls
- [x] Parliament: weekly bills, per-MP vote utility with named terms, party whips
- [x] Government: coalition formation, confidence votes, term ends -> next election
- [x] Dynamic parties: cohesion tracking, defections, schisms, dissolution
- [x] Player layer: 2 actions/week, career (portfolios, leadership challenges, expulsion), hidden stats, scoring
- [x] Terminal driver + inspector (`inspect <mp_id>`, `why`)

Known gap to keep an eye on: governments lean too stable (median survival = full term). Tune `params.py` if playtests feel calm.

## Phase 2 — See the simulation (next)

The terminal prints text; the game *thinks* in geometry and networks. This phase makes the invisible visible. Driver-only work — the sim core is untouched (that was the point of the architecture).

- [ ] **Textual TUI driver** — a real game HUD in the terminal: event feed, poll ticker, your stats panel, action menu as buttons. The `tick() -> events` contract already supports this; Textual is a second driver, not a rewrite.
- [ ] **Hemicycle seat chart** — parliament rendered as an arc of colored dots by party. Coalition blocs, rebels, and empty seats (dissolved parties) readable at a glance.
- [ ] **Ideology map** — the [-1,1]^2 space with party platforms, MP positions, and your marker. Watch parties drift and schisms form spatially instead of reading about it.
- [ ] **District map** — 12x10 grid of your country, colored by seat holder, margins shown as intensity. Your district highlighted; constituency work visibly changes it.
- [ ] **Hybrid time presentation** — weeks auto-advance on a timer with the polls ticking live; hard pause on interrupt events (confidence lost, scandal, election). The event types and `INTERRUPTS` set already exist — this is presentation polish, not new sim logic.
- [ ] **Event chronicle** — scrollable history of the game so far, filterable by type. "What happened while I wasn't watching" becomes answerable.

Done when: you can watch a coalition collapse *happen* on screen and understand why without reading a scrollback.

## Phase 3 — Richer politics

Depth additions to the sim itself. Each item is separable; reorder freely.

- [ ] **Media layer** — voters observe outlets, not reality. Outlets have bias + audience; events refract before reaching voters. Deferred from the original spec as "v2 stacked on a working base" — the base now works.
- [ ] **Factions inside parties** — named wings (e.g. Labour-left vs Labour-pragmatists) that whip separately and can secede as a bloc. The schism machinery exists; factions give it texture before the break.
- [ ] **Deals and favors** — logrolled votes: promise an MP your vote on their bill for theirs on yours. The relationships dict and favor mechanics are placeholders waiting for this.
- [ ] **Scandal lifecycle** — dossiers currently fire once. Add simmering scandals, opposition research timed to elections, resignation cascades.
- [ ] **Ministerial performance** — portfolios generate outcomes (economy up/down, crisis events) that reflect on competence and feed approval. Right now a portfolio is a title.
- [ ] **Policy salience** — bills and speeches move *which axis* voters care about (economy vs social), not just positions on it. The voter model already weights axes; this gives the player a lever on the weights.

Done when: two consecutive terms feel politically different — different factions matter, different scandals, different salience.

## Phase 4 — A real game around the sim

- [ ] **Save/load** — `GameState` is already a dataclass tree; serialize to JSON/YAML. Cheap because determinism was designed in.
- [ ] **Difficulty and scenarios** — starting situations (safe seat vs marginal, incumbent party vs opposition), parameter presets in `params.py` profiles.
- [ ] **Goals beyond score** — optional win conditions (win a majority as PM, survive N terms, found a party that outlives you) layered on the open-ended career.
- [ ] **Better writing** — event text from a larger template pool with named actors, so the log reads like a political chronicle instead of status lines.
- [ ] **Balance pass** — playtest-driven tuning of everything in `params.py`, informed by the Phase 2 visualizations (you can finally see what's too stable or too chaotic).

## Phase 5 — Beyond the terminal (optional)

- [ ] **Pygame or web driver** — same `tick()` contract, richer rendering: animated ideology scatter, clickable MPs, a real map. Web version enables sharing seeds/runs.
- [ ] **Spectator/analysis mode** — headless autoplay with the visualizations running, for tuning and for just watching the machine grind.
- [ ] **Election night mode** — results resolve district-by-district with a live map and projections. The sim already computes per-district; this is dramaturgy.

## Explicitly not on the roadmap

- **LLM-generated anything** — the game's identity is classical AI. Dialogue and events stay algorithmic.
- **Real-world political data** — fictional country is a feature.
- **Multiplayer** — the MP-agent layer is the opponent.
