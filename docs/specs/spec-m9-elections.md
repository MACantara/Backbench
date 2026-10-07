# Spec M9: Elections you can read

`resolve_election` computes a full result — every voter scores every
candidate, tallies, declares a winner — then throws away everything
except the winner and the margin. Candidates are anonymous until they
win, vote counts die in the function, the votes→seats conversion is
invisible, and election night is a three-second map animation. M9
makes the election legible end to end: who ran, how they polled, who
voted for whom, and what a seat actually cost in votes.

Done-when: **before the vote you can see the battleground, on the night
you can watch constituencies call with real numbers, and after it you
can read votes-vs-seats and know exactly why your seat moved.**

Scope: candidate/vote data on results, campaign forecast, election-
night screen, and the mechanics that make FPTP honest — incumbency,
strategic desertion, mobilization.

## 1. The ballot exists — candidate rosters and vote counts

Every district's `DistrictResult` carries its race:

```python
candidates=[{"name", "party", "votes", "share", "incumbent"}]
```

Incumbents and hopefuls already have names; placeholder candidates
(currently anonymous platform jitter) get a drawn `mp_name` at resolve
time — losers exist as named people for the chronicle and nothing
more. `turnout` per district rides along. Multi-member districts
report the same table — winners are the top `magnitude` shares.

The event text gets honest too: `District 41: Vale 612, Brandt 540 —
Labour holds by 72` instead of `District 41: Labour 1`.

## 2. The forecast — the battleground is visible before polling day

`explain_district` already opens a district; M9 adds a projection
layer on the same machinery the count uses:

- `district_poll(state, d)` — score the district's voters against the
  actual candidate slate (incumbent, named hopefuls, platform jitters)
  *without* vote noise, like `explain_bill` projects divisions. A
  forecast, not an oracle: candidate jitters are resolved at election
  time, so it's honest to show as polling, not prophecy.
- `battleground(state)` — every district ranked by projected margin.
  During campaign phase the action panel shows a watchlist: your
  seat's projected margin first, then the N closest districts — the
  FPTP strategic question made concrete ("12 seats inside 4 points").
- The map gets the projection too: during campaign, district tint
  can show projected winner (dimmer than held color) with margins on
  the inspect card.

This is the answer to "how do I gain seats": your campaign moves your
district's voters; party standing moves the national swing; the list
shows where the swing can land.

## 3. Election night — a screen, not a banner

The reveal already staggers district calls; now it runs as a
broadcast:

- **Running scoreboard** — seat totals per party with the majority
  line drawn at `total_seats // 2 + 1`; called count; net change vs
  the previous parliament.
- **District card** — the resolving district shows its candidate
  table: names, parties, votes, shares, margin, incumbent flag, flip
  callout.
- **Your race is staged** — the player's district resolves near the
  end of the reveal (suspense is a design tool; its card is bigger).
- **Summary screen** — after the last call: votes-vs-seats per party
  (the disproportionality made visible — "31% of votes → 58% of
  seats"), national swing, biggest flips, closest race, your district
  card. Dismiss to continue — formation follows.

Terminal gets the same content as text: per-district result lines
with candidate votes, then the summary table.

## 4. Mechanics — FPTP played honestly

Three terms that make the ballot behave like political science says
it should:

- **Incumbency** (`INCUMBENT_BONUS`): the personal vote — an
  incumbent candidate scores above a generic label-bearer. Named
  candidates make it observable: "the incumbent held because the
  voters knew her name."
- **Strategic desertion** (`VIABILITY_W`, capped): voters discount
  hopeless parties — score gains a viability term read from the
  published poll share (`state.last_poll`, or prior-election share).
  Bounded: the term is capped so a niche party bleeds toward
  viability but isn't zeroed — Duvergerian pressure, not instant
  death. This makes wasted-vote reasoning real: piling into a
  hopeless third party genuinely can't win the seat.
- **Mobilization** (`CAMPAIGN_TURNOUT`): the `campaign` action lifts
  district turnout a little — ground game is a real FPTP lever, and
  it makes low-turnout districts flippable in a second way.

All three are named, legible terms on the same scoring expression —
`district_poll` and `explain_district` show them.

## 5. Bot and checks

- The bot's campaign defense reads the forecast instead of only
  `seat_safety` — a projected loss gets more casework than a held
  margin.
- `check_election.py`: candidates carry names/parties/votes and tally
  sums to turnout; incumbency bonus measurable; desertion term moves
  shares toward viability; MMD winners = top-magnitude shares.
- `check_pyg_smoke`: election-night screen renders headless through
  reveal → summary.

## Atomic commits

1. `docs: m9 elections spec`
2. `feat: candidate rosters + vote counts`
3. `feat: district forecast + battleground`
4. `feat: election night screen`
5. `feat: incumbency, desertion, mobilization`
6. `polish: terminal surfaces, checks, sweep`
