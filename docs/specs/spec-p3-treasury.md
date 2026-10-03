# Spec P3.6 — The treasury

Module id: `treasury` (per `docs/specs/capability-map-p3.md`). Depends on `country-conditions`. Today `Bill.cost` exists but is never set — `table_bill` leaves it at 0, so legislation is free and money is not a dimension of politics. This module adds one number and its flows: a national debt that accumulates when the government's legislative program outspends what the country can pay. A constraint, not a spreadsheet — no sectors, no trade, no monetary instruments.

## Objective

Money should *constrain legislation*: expensive programs are easier to pass in good times and stall when the books are red. Deficits should compound into debt, debt into inflation drag, and insolvency into a political crisis a government can actually fall over — all legible, all derived from the same handful of parameters.

## Mechanics

**State (`Treasury` dataclass on `GameState.treasury`):**
- `debt: float` — the single stock. Starts at `DEBT_START`.
- Weekly flow is derived, not stored: `flow = revenue - upkeep - interest`, shown in inspect.
- `revenue = REV_BASE + REV_GROWTH_W * growth - REV_UE_W * unemployment` — the country pays what it earns (reads `conditions` weekly).
- `upkeep = Σ law.cost for law in state.laws` — laws in force cost money *while they stand*. Repeal (P4) or a court strike (P3 `courts`) stops the drain — fiscal meaning for free in both later modules.
- `interest = debt * DEBT_INTEREST` — the compound squeeze.

**`Bill.cost` becomes real:** `table_bill` assigns `cost = COST_BASE + COST_EXTREMITY_W * |pos[axis]| + jitter` — ambitious programs cost more than housekeeping. `Law.cost` already rides along via `enact`.

**Fiscal constraint on votes (the named `fiscal` term):** `vote_terms` gains `fiscal = W_FISCAL * (-bill.cost) * debt_pressure` where `debt_pressure = min(1, debt / DEBT_WARN)`. In surpluses MPs shrug at expensive bills; as debt mounts, cost-shyness enters the utility — expensive legislation gets harder to pass exactly when it should. Applies to all MPs, not just the coalition (parliaments get stingy, not just governments).

**Debt → inflation drag:** while `debt > DEBT_WARN`, the conditions lifecycle adds `DEBT_INFLATION_W * (debt - DEBT_WARN)` to `inflation` weekly — debt feeds the indicators that feed `mood`, closing the loop into retrospective voting.

**Insolvency → crisis:** `debt > DEBT_CRISIS` triggers `DebtCrisis` (interrupt-tier): government parties take a `DEBT_BRAND_HIT` and a `confidence_vote` is forced immediately — a government can fall on the books, not just the polls. Re-arms only after debt drops back below `DEBT_WARN` (hysteresis — no crisis spam every week).

**Placement:** `treasury_lifecycle(state)` runs in `tick` after `conditions_lifecycle` (revenue reads this week's indicators), before `media_lifecycle` (a `DebtCrisis` is a story — added to `_NEWS`).

**Events:** `DebtCrisis` (debt level, forced confidence outcome rides the existing `ConfidenceLost`/survival events). Flow numbers surface via inspect — a treasury line on the player card, plus `Law.cost` shown on enactment.

## Boundaries

- Always: constants in `params.py`; `state.rng` only; `fiscal` stays a named `vote_terms` component; every flow inspectable (revenue formula, upkeep per-law, interest — no hidden drags).
- Ask first: the `fiscal` term touches `vote_utility` — same class of change as `retro` on confidence; spec'd deliberately as the constraint channel (the alternative — refusing to table unaffordable bills — is a pipeline rule, not politics).
- Never: player budget levers (Phase 4 "Budget power" tables the annual budget as a votable bill — this module is the world-side substrate it manipulates); taxes or spending categories (one revenue formula, one upkeep sum); monetary policy, interest-rate instruments, trade/balance of payments; regional or per-district accounts.

## Success criteria

- `checks/check_treasury.py`: fixture high `growth` → `revenue` exceeds fixture-crash `revenue` measurably; pass an expensive bill → `upkeep` rises by its `cost`, `debt` climbs faster than the no-law control; `debt > DEBT_WARN` → `inflation` drifts up vs control; `debt > DEBT_CRISIS` → `DebtCrisis` fires, brand drops, `confidence_vote` runs; an indebted parliament passes fewer high-cost bills than a solvent control on identical bills (`fiscal` term measurably negative); `DebtCrisis` reaches `Headline`; determinism (same seed → same debt trajectory).
- `check_conditions.py`, `check_parliament.py`, `check_e2e.py`, `check_sweep.py` stay green — fiscal term is ~0 at `DEBT_START`.
- Sweep watch: crisis-driven confidence losses should add early government ends without p10 collapse — debt crises should be *occasional*, not every term.

## Open questions

- Should `cost` also price `Shock`-scale laws (a "stimulus" bill that costs a lot but boosts growth)? Deferred — `law_effect` already maps position → indicator; letting bills buy conditions back is the treasury↔conditions coupling Phase 4 budget power will exploit.
- Should the opposition's `fiscal` shyness differ (opposition MPs posture as deficit hawks)? Same term for all MPs keeps it simple; if it plays flat, a `populism` modifier on `fiscal` is a cheap later add.

## Deferred

- Player-facing budget bills (P4 "Budget power" — the votable annual budget).
- Fiscal meaning of repeal (P4 legislative legacy — cutting upkeep by repealing laws).
- Court strikes ending upkeep (P3 `courts` — rides free once review removes laws).
- `MINORITY_GOVT_PENALTY` is defined but currently unused in `vote_terms` — unrelated dead constant; flag for a cleanup pass, not this module.
