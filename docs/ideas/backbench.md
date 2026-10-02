# Local AI Politics Sim — "Backbench" (working title)

## Problem Statement
HMW build a Python politics game where a human politician navigates a multiparty parliament of classical-AI actors through campaign→govern→campaign cycles?

## Recommended Direction
Two-layer agent model, zero LLMs:

- Layer 1: ~10k voter agents in 2D ideological space (economic × social). Each has position, turnout propensity, loyalty, and attention. Elections = weighted nearest-party choice + noise + events shifting issue salience.
- Layer 2: ~120 MP agents with ambition, ideology, loyalty-to-party, grudges, and a utility function over (portfolio, policy distance, career safety). Coalition formation via bargaining rounds; confidence votes via expected-utility whip counts.
- The player is one MP: pick positions, make promises, trade portfolios, whip or rebel. Everything else is the sim.

## Key Assumptions to Validate

- [ ] Emergent MP behavior stays in the interesting band (not noise, not frozen) — test: headless sim runs, measure coalition stability distribution
- [ ] Player choices measurably move outcomes — test: scripted "good" vs "bad" play and compare seat trajectories
- [ ] The loop is legible — test: can you answer "why did the coalition collapse" from the inspection tools?

## MVP Scope
One election cycle end-to-end: campaign phase (position choice, 3–4 events) → election → coalition bargaining → one governing term (3 policy votes, approval feedback) → next election. Terminal output + ASCII seats chart. ~120 MPs, 10k voters, fixed fictional parties.

## Not Doing (and Why)

- Media-filtered electorate — great mechanic, it's v2 stacked on a working base
- Procedural events/narrative flavor — small fixed template pool first
- Any UI beyond terminal — sim core must be UI-agnostic anyway
- Real-world data/countries — fictional keeps politics abstract and safe
- Save/load — YAML dump of state, only if it's free

## Decisions

- **Tick model: hybrid.** The sim is discrete (weekly ticks) underneath — agents only act on tick boundaries. Presentation is real-time: each week visibly "plays" (polls drift, events scroll by), but the game hard-stops at player decision points and whenever an interrupting event fires. Interrupts = typed events in a pause set.
- **Events are first-class.** Every `tick(state, actions)` returns `(new_state, [events])` — never just mutated state. This is what makes interrupts and the real-time presentation possible later, and it costs nothing now.
- **Architecture consequence:** sim core exposes `tick` as a pure-ish function; the driver loop (timer + interrupt checks vs input-blocking) is a thin replaceable shell.
- **Stack: stdlib-first, upgrade to Textual later.** `sim/` is pure Python (`dataclasses`, `random`, `numpy` for the voter vector math). First driver is a plain terminal loop printing weeks — every early hour goes into sim tuning, not UI. Textual drops in as driver #2 once the loop is proven fun; pygame/web stay possible off the same `tick` API.

## Open Questions

- Voter memory: do voters remember broken promises? (one "betrayal" scalar first)
