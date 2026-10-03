# Spec P3.1 — AI Careers (MP lifecycle)

Module id: `ai-careers` (per `docs/capability-map-p3.md`). The largest north-star gap: only the player has a career arc today. This module gives every MP a trajectory — they climb, scheme, age, retire, and get replaced — so the country generates its own politicians.

## Objective

A full term watched via auto-play should produce visible career movement that is *not* about the player: MPs promoted into portfolios, challengers toppling leaders, veterans retiring, newcomers appearing with their own stats and districts.

## Mechanics

**Career state (per MP):**
- `age` (weeks, generated at worldgen: 40–65 randomized ≈ 2080–3380) — increments weekly.
- `seniority` (weeks in parliament) — increments weekly; gates promotion probability.
- `reputation` — derived, not stored: combination of competence, portfolio held, party standing. Already computable from existing fields — no new stat unless needed.

**The pipeline (young politicians):**
- A minimum age to stand for parliament, `P_MIN_MP_AGE` (≈ 25 years = 1300 weeks).
- `GameState` gains a `hopefuls` pool: ~30–50 aspiring politicians generated at worldgen with ages *below* the minimum (18–24) plus stats, a district home, and a party leaning.
- Hopefuls age weekly alongside MPs. Crossing `P_MIN_MP_AGE` makes them *eligible* — they become standing candidates for their party in their home district.
- At election time, challenger candidates are drawn from the eligible pool (preferring pool members over anonymous roll-fresh challengers when one exists for that district+party); `resolve_election`'s fresh-roll path stays as the fallback.
- When a pool member wins their first seat, emit `Newcomer` with their age — so the chronicle reads "Wren Marsh, 26, takes Fern Vale for Labour" and young risers are visible.
- Pool replenishes slowly (a couple of new 18-year-olds per year) so the pipeline never runs dry.

**Climbing:**
- Portfolio assignment (`career.assign_portfolios`) already exists — extend it to weight `seniority` and `competence`, not just party standing, so capable MPs visibly rise.
- Leadership challenges (`career.leadership_challenge`) already fire — ambitious high-reputation challengers should win sometimes: assert in check that leadership changes hands across a long run.

**Aging out:**
- Each week, MP retires with probability `P_RETIRE_BASE` rising steeply past `P_RETIRE_AGE` (e.g., ~70). Event: `Retired`.
- Retirement, expulsion, and seat losses all create the same thing: a vacancy. Resignations fold into the same path (a resignation IS a retirement with a different event type — `Resigned`).

**Replacement:**
- A vacated seat stays empty until the next general election. **By-elections are deferred** (decided — not permanently excluded): a future module can schedule a single-district election ~8 weeks after a vacancy, drawing candidates from the hopefuls pool. The deferral note lives here because scandal-lifecycle will make vacancies more frequent — revisit then if empty seats feel dead.
- New MPs enter only through general elections — `resolve_election` already spawns fresh MP records for challengers (`election.py` lines 69–76); reuse that, no new generation path.
- **Edge case found in verification:** `resolve_election` builds `incumbents` from `mps` and does `inc = incumbents[d]` unconditionally — a mid-term vacancy breaks it. The election path must handle `inc is None` (vacant seat: no incumbent bonus, winner is a new MP).

**Events:** `Retired`, `Resigned`, `Promoted` (portfolio gain), `Newcomer` (pool member's first seat, includes age), `LeaderChanged` (if not already emitted).

## Boundaries

- Always: `params.py` for new constants; `state.emit` for anything a driver should show; named terms if vote utility changes.
- Ask first: changes to `resolve_election` winner→MP flow.
- Never: per-MP action economy like the player's (careers are probabilistic + rule-based, one lifecycle pass per week — cheap); removing the player from `mps` through this path.

## Success criteria

- `checks/check_careers.py` runs 200+ weeks headless and asserts: at least one retirement occurred, parliament refilled or shrank plausibly, at least one leadership change or portfolio promotion fired, the hopeful pool aged at least one member past eligibility, and player mechanics are unaffected.
- `check_player.py`, `check_e2e.py` stay green.
- Median parliament tenure becomes finite and visible in the chronicle.

## Open questions

- Resignation triggers beyond age — scandal pressure comes in `scandal-lifecycle`; keep this module to age/retirement + climbing only.
- Should seat vacancies count against a party's seat total mid-term (they do naturally — `members` shrinks — which affects whip counts and majority math; confirm that's desired: yes, a party losing MPs mid-term *should* weaken).
