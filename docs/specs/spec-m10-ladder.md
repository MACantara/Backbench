# Spec M10: The ladder — offices with functions

The party has a leader, three generic bench posts, and a cabinet —
but the posts are labels: the Whip doesn't whip, the Committee Chair
chairs no committee, succession is `max(ambition)`, and the only way
to learn your rank is to lose a pick. Real parliaments run offices
with *functions*: whips enforce, deputies inherit, chairs scrutinize,
speakers transcend. M10 gives every office a mechanical bite, adds
the missing rungs, and makes the whole ladder legible — who holds
what, where you rank, and who would back you in a contest.

Done-when: **every post changes how the game is played for its holder,
succession is a name you can read, and a party card shows the bench,
your rank, and the votes you'd take if the party split today.**

Scope: the payroll vote, senior posts and real succession, the
Speaker as a cross-party summit, the party-card legibility surface,
and checks. Out of scope: committees as a legislative stage,
parliamentary group chairs as a separate office from party leader —
both plausible, both their own milestone.

## 1. The payroll vote — office binds the vote

The deep function of junior office is bought loyalty: whips,
parliamentary secretaries and ministers cannot rebel without
resigning the post. Today `portfolio`/`junior` add a standing
trickle and bind nothing — a Whip can vote against the whip.

Mechanic: an MP who holds a post (`junior` or `portfolio`) and votes
against their party's whipped line **loses the post** on the division
result — `PayrollFall` event (`"You rebelled the whip — the Whip
post is gone"` / `"X is dismissed as Whip for rebellion"`). Standing
already takes the rebel hit; the post is the real price. The whip
holder themselves is exempt — the enforcer can't be sacked by their
own instrument — but not from the standing cost.

For the player the price is *stated, not hidden*: `explain_bill` and
the vote row flag "a rebellion costs your post" when they hold one.
Same rule for every MP — the payroll is why parties discipline
without code that treats the player differently.

## 2. Senior posts — the bench ladders

`JUNIOR_POSTS` (Whip, Spokesperson, Committee Chair) stays the first
rung. A second rung above it, filled by the same `_ranked` candidacy
but only from members *currently on the bench* — you must hold a rung
to reach the next:

- **Chief Whip** — requires the Whip rung. The whips office made
  mechanical: a party's `W_WHIP` term on its members scales with
  `1 + WHIP_BITE` when it has a Whip, `1 + CHIEF_WHIP_BITE` with a
  Chief Whip. Staffing the office is how a leader makes the line
  actually bind — and a weak whip corps is why rebellious parties
  fragment.
- **Deputy Leader** — any bench post qualifies. The *visible heir*:
  on a leader vacancy the deputy succeeds (replacing the silent
  `max(ambition)` pick), and carries a `DEPUTY_HEIR_BONUS` in
  leadership-challenge member votes — the named successor is hard
  to dislodge.

Senior holders keep their `junior` slot semantics — promotion up
vacates the lower rung for a climber, same as cabinet does today.

## 3. The Speaker — the exit office

A cross-party summit that isn't the party's:

- `state.speaker: int | None`. When vacant — parliament formation
  and any departure — the **house elects**: every MP casts for the
  candidate maximizing `relationships + standing + 0.5·competence +
  seniority-weight`, an `Elected` event names the winner. Same
  read-only utility pattern as the challenge vote — visible, not
  ordained.
- The Speaker **renounces**: leaves their party (membership and
  posts gone), sits above the whip — `whip_direction` is 0, they
  never cast except a tie. They can't be challenged, can't hold
  posts, can't defect — the office *is* the job.
- **Uncontested**: by convention no party stands against the chair —
  at elections the Speaker's ballot is the incumbent alone (the
  M9 uncontested path already exists). Becoming Speaker is a
  guaranteed seat for life — at the price of leaving politics.
- Score: a `speaker` score_term — holding the chair is a career
  verdict, the "enough" ending made mechanical.

## 4. Legibility — the party card

`explain_party(state, pid)` — the internal order made visible, on a
new `party` inspect target in terminal and a party-name click/panel
button in pyg:

- **The bench**: leader, deputy, chief whip, whip, spokesperson,
  committee chair — each with its holder's name.
- **The fuse**: `cohesion` shown with the challenge threshold —
  "cohesion 0.41 — the party is fractious" — the one number that
  decides whether a contest can happen.
- **Your rank**: candidacy rank with the `appointment_terms`
  breakdown, pulled out of `explain_mp` where it currently hides.
- **The contest preview**: run the challenge member-vote utility
  read-only — "if the party fractured today: you'd take 6 of 23
  votes — Vale, Brandt, Osei would back you." Lobbying becomes
  legible: every colleague you court moves a countable vote.
- **Regard direction fix**: `explain_mp` shows your→their regard;
  the card adds the leader's→yours — the `backing` term's real
  source, currently unseeable without opening their card.
- Faction rows: name, size, its heir (`faction.leader` — already
  computed, never shown).

Side panel: the player's `junior` post next to `portfolio` — the
always-visible card should name the rung you stand on.

## 5. Bot and checks

- The bot needs no new rules — it lobbies the leader while
  unpromoted and votes the whip already; the payroll makes its own
  case. One guard: a bot holding office never votes against the
  whip (it already doesn't — assert it stays true).
- `check_offices.py`: junior→senior fill order enforced (Chief Whip
  never staffed from outside the bench); deputy succeeds on vacancy;
  `WHIP_BITE` measurably raises member whip terms; payroll rebellion
  vacates the post; speaker is elected, renounces, uncontested, and
  their seat survives elections; `explain_party` renders rank,
  cohesion, and the contest preview.

## Atomic commits

1. `docs: m10 ladder spec`
2. `feat: payroll vote — office binds the whip`
3. `feat: senior posts + deputy succession`
4. `feat: speaker election — the exit office`
5. `feat: party card + contest preview`
6. `polish: bot guard, checks, sweep`
