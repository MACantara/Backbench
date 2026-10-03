# Roadmap

## North star

**A living fictional country that runs on classical AI — where you build a career inside politics the world generates itself.**

The world is the star: elections, coalitions, schisms, and realignments run whether or not anyone plays — auto-play is the country's heartbeat made visible. You are a politician inside that world, not the center of it. Three pillars, equal weight: the career climb (backbencher to PM), the emergent drama (betrayals and collapses nobody scripted), and strategic depth (whipping and kingmaking against worthy opponents). A run succeeds when the world does something unscripted, it mattered to your career, and the why traces to legible algorithmic causes — not a scripted twist, not an LLM, not a dice roll.

Constraints: classical AI only, local, deterministic by seed, self-consistent without a player. Audience: me. Out of scope forever: LLMs, real-world data, multiplayer, online services.

**Market context** (Oct 2026): emergent politics sims exist — UK Politics Simulator (20k NPC career sim, closed commercial), Lawmaker (modelled voters, but multiplayer), Democracy 3/4 (bloc voters, you are the government not a career MP), Absolute Majority (LLM-driven). The gap this occupies: fully *local* + *deterministic* + *legible* + open code, and parties that genuinely form, split, and die.

## Phases

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

## Phase 2 — See the simulation (built)

The terminal prints text; the game *thinks* in geometry and networks. This phase made the invisible visible. Driver-only work — the sim core is untouched (that was the point of the architecture).

- [x] **Pygame driver** (`driver/pyg.py` + `pyg_render.py`) — real window, replacing the planned Textual step: we went straight to graphics.
- [x] **Hemicycle seat chart** — parliament as an arc of colored dots, parties sorted left-to-right by platform, coalition members tagged, player ringed, PM crowned.
- [x] **Ideology map** — sampled voter point cloud, party platform markers, MP dots; Tab to toggle.
- [x] **District map** — 12x10 grid colored by seat holder, brightness = margin, player district ringed.
- [x] **Hybrid time** — auto-run weeks (1.5s, speeds 0.5–4x), interrupt banners hard-pause, weekly action panel with click-to-target MPs, click any seat to inspect, `why?` overlay explains the last vote term-by-term.
- [x] **Election reveal** — districts resolve one by one on the map when an election lands.
- [x] **Event chronicle** — C opens a scrollable full-history overlay with week stamps and per-type filter buttons; A toggles auto-play so the sim runs hands-free.

Done when met: a coalition collapse is *watchable* — vote cascade, banner pause, party colors rearranging.

## Phase 3 — The country deepens

The north star says the world is the star — so the next phase is everything that makes the country feel alive *without the player touching it*. Auto-play should already be worth watching at the end of this phase.

- [ ] **AI careers** — the biggest north-star gap: only the player has a career arc. MPs should climb (backbencher → minister → leader), scheme, age, retire, and be replaced by rising challengers. The country generates its own politicians; a PM you never met should fall to a rival you watched grow.
- [ ] **Factions inside parties** — named wings (Labour-left vs Labour-pragmatists) that whip separately, feud, and can secede as a bloc. The schism machinery exists; factions give it texture before the break.
- [ ] **Scandal lifecycle** — dossiers currently fire once. Simmering scandals, opposition research timed to elections, resignation cascades. Careers should end in flames sometimes — AI ones too.
- [ ] **Media layer** — voters observe outlets, not reality. Outlets have bias + audience; events refract before reaching voters. Deferred from the original spec as "v2 stacked on a working base" — the base now works.
- [ ] **Ministerial performance** — portfolios generate outcomes (economy up/down, crises) that reflect on competence and feed approval. Right now a portfolio is a title; under the north star a bad minister should *matter* to the country.
- [ ] **Policy salience** — bills and speeches move *which axis* voters care about (economy vs social), not just positions on it. The voter model already weights axes.

Done when: run auto-play for a full term and the chronicle reads like a country's history — governments rose and fell, careers started and ended, and you weren't in it.

## Phase 4 — Your career inside it

The three pillars made playable: climb, drama, strategy. These are player-facing systems layered on the now-living world.

- [ ] **Deals and favors** — logrolled votes: promise an MP your vote on their bill for theirs on yours. The relationships dict and favor mechanics are placeholders waiting for this. The core of strategic depth.
- [ ] **Opposition role** — today the player mostly matters in government. Shadow scrutiny, amendment attacks, coordinated rebellion — being out of power should be a playable position, not dead time.
- [ ] **Scandal as a weapon** — dig_dirt currently produces dossiers mechanically. Timing releases, trading silence, deciding when your own dirt is survivable.
- [ ] **Goals beyond score** — optional arcs layered on the open-ended career (win a majority as PM, found a party that outlives you, survive N terms) — roguelike structure without a fixed ending.
- [ ] **Save/load** — `GameState` is a dataclass tree; serialize to JSON. Cheap because determinism was designed in.
- [ ] **Difficulty and scenarios** — starting situations (safe seat vs marginal, incumbent vs opposition), `params.py` profiles.
- [ ] **Balance pass** — playtest-driven tuning of `params.py`, informed by actually watching the sim run.

Done when: you choose to act most weeks — not because the game demands input, but because the world gave you something to exploit.

## Phase 5 — Watchability and reach (optional)

The world is already watchable; this is presentation depth and sharing.

- [ ] **Better writing** — event text from a larger template pool with named actors, so the chronicle reads like political history instead of status lines.
- [ ] **Election night mode** — districts resolve with projections and swing callouts during the reveal. The sim computes per-district; this is dramaturgy.
- [ ] **Spectator/analysis mode** — headless auto-play with visualizations, for tuning and for watching the machine grind.
- [ ] **Web driver** — same `tick()` contract, browser rendering. Enables sharing seeds and runs — only if "just me" ever widens.

## Explicitly not on the roadmap

- **LLM-generated anything** — the game's identity is classical AI. Dialogue and events stay algorithmic.
- **Real-world political data** — fictional country is a feature.
- **Multiplayer** — the MP-agent layer is the opponent.
