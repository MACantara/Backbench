# Spec M3 — Strategic Politics

Milestone spec (see `ROADMAP.md` milestones). Scope: **decisive explanations, conscience votes, abstention & attendance, independents, kingmaking, deals & favors**. Done-when: a hung parliament hands the player a real negotiation, and a whipped division is a real decision with readable stakes.

## Objective

The player moves parliamentary outcomes. Today the weekly division resolves on autopilot (`player_vote` hook exists but nothing calls it), government formation is a spectator sport, and the vote explanation lists six weights without saying which one *mattered*. M3 wires the decisions in — in a dependency order where each item makes the next one worth having.

## Build order inside the milestone

Legibility first, then the franchise, then the franchise's leverage: **explanations → conscience votes + abstention/attendance → independents → kingmaking → deals**. Deals go last because the vote machinery is what gives a favor somewhere to be spent.

## 1. Decisive explanations — the odds before the bet

- `VoteResult.detail` already carries per-MP terms; add **decisive extraction**: for each MP, the term whose removal flips the sign of `u` (largest marginal contribution toward the outcome) is *the* decider. `explain_vote` annotates it: "rebelled — `fwhip` −0.42 beat `whip` +0.31" instead of a ranked list.
- A pre-vote stakes surface: `explain_bill(state)` — the projected tally (terms minus `noise`), the marginal MPs (|u| under a band), and each marginal's deciding term. This is the screen the player reads before committing — without it, conscience voting is a coin flip with extra steps.
- Noise handling: the projection strips `terms["noise"]` (or a `with_noise` flag) — it must never consume `state.rng`; inspect is read-only.

## 2. Vote your conscience — the division becomes a decision

- Wire `player_vote` to a `vote` action (+1/−1/0): each governing week the player picks yes, no, or abstain on `current_bill` — with `explain_bill` stakes in front of them.
- Consequences are situational, not automatic — the terms already model them: defying the whip costs `standing` (M2 already accrues it) and `relationships[leader]`; backing a toxic bill preserves leadership support while the district term records the exposure. Rebellion is a choice with a price tag, legible on both sides.
- `VoteResult` gains `player=` vote so the chronicle remembers the player's record ("you broke the whip").

## 3. Abstention & attendance — the house isn't always full

- Third state lands: `|u| < ABSTAIN_MARGIN` → abstain (counted in neither column). `u <= 0` currently means "no" — this changes every vote margin in the sim; checks with hardcoded yes/no expectations retune.
- Weekly attendance roll: `mp` absent with probability rising in campaign weeks, burning-scandal weeks, and late career (`RETIRE_AGE` region). Absent MPs vote nothing.
- **Quorum**: below `QUORUM` fraction of the house present → the division can't stand; the bill carries to next week (a stalled week is the event: `DivisionStalled`). Mostly a formality, dramatic exactly when attendance craters — scandal weeks, election season.
- Player abstention rides the same state — `player_vote=0` is a real choice now, not a quiet no.

## 4. Independents — seats without parties

- `MP.party=None` is already half-supported (inspect shows 'independent', whip=0). FPTP needs a candidate path: `INDEPENDENT_P` per district per election fields a party-less challenger positioned near the district centroid (a true local candidate — no brand, no loyalty coattails; they win on proximity in crowded fields).
- An elected independent: no whip, no standing accrual (no party to stand in), no bench posts, no climb — but their vote is pure policy+district, and in a hung parliament their single seat is worth a ministry's weight in drama. The lone kingmaker is the payoff; the seat math already makes it possible.
- Election code guards `party=None` — `members.add`, `Newcomer` text, `ElectionResult.seats` ("ind") all handle the no-party case.

## 5. Kingmaking — formation is a negotiation

- When the player's party holds the balance — a coalition forms *with* them or a different one forms *without* — `resolve_formation` pauses: the player sees the viable offers (each = proposer, coalition, bloc, per-partner concession) and picks one, or declines all → minority government or prolonged formation. Silence accepts the default slate, so autoplay is never punished.
- **The deal has a price**: a junior partner joining far from the proposer *extracts* — the coalition's negotiated **agreement** (`government.platform`, set at formation) shifts `CONCESSION_STEP`-scaled distance toward the partner, and the proposer's members pay `standing` for the compromise. The concession lives on the agreement, not the manifesto: bills anchored to the dragged agenda strain the proposer's own whip line — the sell-out is mechanical, not narrative. `government.py`'s distance-threshold stub is replaced — `_will_join` → `_join_price`: far partners demand concessions, near partners come free. **AI parties pay the same price** — a small kingmaker AI extracts concessions too, or the player is the only negotiator in town.
- The deal outlives the handshake — on machinery that already exists: propping up a distant partner costs `standing` and cohesion inside the player's party (members watch their leader sign away the platform); the government's record bleeds the player's party through `responsibility` and retro voting. No new punishment machinery — the consequences ride existing channels.

## 6. Deals & favors — logrolling starts small

- `Deal` record: counterparty, the promise, due, honored. One shape only: the player promises their vote on the *next* division in exchange for a named consideration — backing (`relationships` credit with that MP, which feeds appointment `backing` and leadership votes), or their whip-defiance on a bill of the player's choosing.
- Honoring is recorded: a kept deal banks `relationships` + `standing` (word-keeper is visible); a broken one emits `DealBroken` — betrayal with a name on it.
- Player→MP only this milestone; AI-initiated deals need the ask-side UI and wait for the deal economy to have two directions.

## Boundaries

- Always: `params.py` for constants; named terms (decisive extraction is inspect-side — the terms stay honest); `state.emit` for every legibility surface; seeded RNG only.
- Ask first: changing the `yes/no` → `yes/no/abstain` tally semantic (touches every vote-count consumer); independents holding the balance (that's the point, but the fallout lands in kingmaking).
- Never: a deal economy beyond the one promise shape; AI-player negotiation dialogue (choice lists, not dialogue trees); player-tabled bills (M4 budget power owns that); strategic whip-timing by the AI PM.

## Success criteria

- `checks/check_ladder.py`-style: `check_conscience.py` — the player's vote flips a thin division (forced fixture), abstention actually splits the tally, quorum stalls a division on empty benches.
- `check_kingmaking.py` — a hung-parliament fixture where the player's party is pivotal: offers enumerated, picked offer forms the government, declined → minority/another election path; AI-vs-AI haggling fires (concession emitted for a far partner).
- `check_independents` path inside election checks: an independent can win and sits with `party=None`.
- The invariant sweep keeps passing — abstention shifts every margin; the turnover/watch rows get re-read, not re-assumed.
- Done-when checkable: scripted pivotal-party run shows the negotiation; a scripted thin-division shows the player's vote deciding.

## Open questions

- Where does the kingmaking choice surface in drivers — a blocking formation phase with options, or an election-week menu? (Driver-side; the sim emits `OfferMade`/`OfferTaken`/`OfferDeclined` either way.)
- Does a declined negotiation freeze formation for a week (bargaining time) or resolve immediately to minority? Propose: one `formation` week of bargaining, then resolution — a hung parliament should feel like a hung parliament.
