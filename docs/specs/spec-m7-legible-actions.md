# Spec M7: Legible actions

The world is legible — `why?` decomposes a division, `inspect` opens an
MP, the bench explains its strikes. The one unreadable surface left is
the one the player touches every week: the action row. Buttons are bare
verbs ("scheme", "court", "dig_dirt"), effects are invisible numbers,
feedback is a one-line CareerEvent, and the weekly budget is a pair of
anonymous picks. M7 makes actions explain themselves — what it is, what
it would do now, what it did — and turns the flat two-pick allowance
into a real economy with visible costs.

Done-when: **no action is a mystery — the label says what it is, the
preview says what it does now, the event says what it did, and the
price says what it cost.**

Scope: action points, per-action descriptions, live previews, numeric
event feedback. No new mechanics — the moves don't change, only their
legibility and their price.

## 1. Action points — the week is a budget

`ACTIONS_PER_WEEK = 2` is replaced by `ACTION_POINTS = 3` and an
`ACTION_COST` table in `params.py`. Three tiers:

- **0 — duties and decisions.** `vote`, `amend`, `pick_offer`,
  `decline_offers`, `appoint`, `defect`, `found`, `nothing`. The
  house's business and once-a-career identity moves don't consume the
  week — a division on the floor shouldn't crowd out your casework.
- **1 — routine work.** `campaign`, `constituency`, `speech`,
  `promise`, `lobby`, `scheme`, `court`, `deal`, `budget`, `platform`.
  A morning on doors, a dinner, a phone call.
- **2 — operations.** `media`, `dig_dirt`, `attack`, `challenge`,
  `amendment`, `leak`. A planned effort that takes real days.
- **3 — week-defining.** `table`. Writing and dividing a private
  member's bill is all you did this week.

`cost_of(kind)` lives in `sim/actions.py` and reads the table;
enforcement is driver-side (pacing, not physics — `apply_action` stays
dumb). Drivers grey out what doesn't fit the remaining points; the
bot's `take` spends from the same budget, so a spectator run exercises
the same economy the player faces. The hardcoded `2`s in both drivers
die with the change.

## 2. Descriptions and previews — `explain_action`

`sim/inspect.py` already owns legibility; it gains:

- `ACTION_INFO: dict[str, str]` — a one-line plain-language blurb per
  kind ("scheme — quiet dinners with colleagues: a little regard, a
  little dirt").
- `explain_action(state, kind, target=None, outlet=None) -> str` — a
  live preview with real numbers where the code can compute them:
  attack's current land-chance (mood + minister perf), the leak's trace
  odds per venue (friendly halves, hostile adds half), media's friend
  factor, `found`'s exact follower count, lobby/dig_dirt/court deltas
  against the chosen target. Missing context falls back to the blurb —
  a preview must never lie.

The pyg driver shows the preview on hover (a `hover_bid` tracked via
MOUSEMOTION, rendered in the action panel's prompt line); action
buttons carry a `·N` cost badge and dim when unaffordable. The terminal
prints `kind ·cost — blurb` in its menu.

## 3. Numeric feedback — events carry the delta

`apply_action` already knows every before/after it writes; the emits
start saying them: "Union brand 0.12 → 0.17", "Hale's regard 0.30 →
0.50", "their dossier 0.4 → 0.65". District-scale moves (campaign,
speech) report the measured mean drift. Probabilistic outcomes (attack,
gaffe, traced leak) keep their existing land/whiff text — the number
was previewed before the dice rolled.

## 4. Checks

`checks/check_actions.py`: the cost table is total over
`available_actions` kinds; `explain_action` returns a non-empty string
for every kind (with and without targets); numeric actions emit digits;
the bot never exceeds `ACTION_POINTS` across a simulated run.
