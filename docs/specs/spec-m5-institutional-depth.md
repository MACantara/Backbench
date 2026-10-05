# Spec M5: Institutional depth

Institutions constrain and shape power. Today the constitution doesn't
exist, the bench is a scalar (`state.court_activism`), and the press is
weather — coverage happens to parties, nobody does anything to outlets.
M5 gives all three bodies: articles a law can breach, justices an appointing
PM stamps and then outlives, and an outlet landscape the player can court,
feed, and read through.

Done-when (roadmap): **a `LawStruck` cites its article; a bench a PM packed
keeps ruling after their term ends.**

Scope: constitution (named clauses replace the risk oracle), court
appointments (a real bench), constitutional amendment (the deferred M4
apex), press relations (outlet warmth, routed leaks, sponsored polls),
player-initiated challenges (deferred from p3-courts — "needs the leader
surface" — unblocked by M4).

## 1. Constitution — articles replace the risk oracle

`legal_risk` is an abstract formula the p3-courts spec always marked as
interim. The constitution is a small set of named clauses, each bounding
what a statute may do:

```python
@dataclass
class Article:
    id: int
    name: str           # "the Property Clause"
    kind: str           # "pos" | "cost" | "margin"
    axis: int = 0       # pos clauses: guarded axis
    pole: int = 0       # pos clauses: -1 or +1 — which pole is fenced
    limit: float = 0.0  # the boundary the clause draws
```

- `violation(article, law) -> float`: `pos` clauses read
  `max(0, pole*pos[axis] - limit)`; `cost` reads `max(0, cost-limit)/COST_BASE`;
  `margin` reads `max(0, limit - margin)`. `legal_risk` keeps its signature
  but becomes a weighted sum over per-article violations plus the surviving
  extremity term — the docket machinery doesn't care which oracle scored it.
- **The strike cites its clause**: `LawStruck` names the worst-breached
  article ("struck down — it offends the Property Clause"). `LawEnacted`
  already stamps `risk=`; it now also names the closest guard it was born
  near. `ReviewOpened` names the clause the challenger pleads.
- **Worldgen writes the country's own constitution**: 4–6 articles —
  always a Fiscal Clause (cost cap) and a Mandate Clause (margin floor),
  plus positional clauses on a seed-chosen subset of the four (axis, pole)
  fences with jittered limits, weighted toward fencing the poles the
  electorate centroid sits far from — centrist countries write symmetric
  guards, lopsided ones write asymmetric constitutions. Clause names come
  from the pole vocabulary (`POLE_LABELS`): the Property Clause (market),
  the Common Provision (redistribution), the Liberty Clause (libertarian),
  the Order Clause (authoritarian), the Fiscal Clause, the Mandate Clause.
- **Player-initiated challenges** — the deferred p3-courts item, now that
  the player surface exists: a `challenge` action targets a law in force;
  same gates as AI filers (`risk >= CHALLENGE_RISK_MIN`, not reviewed, not
  docketed, docket not full). The player becomes `challenger` — the venue
  for losers is a real venue now.

## 2. The bench — court appointments

`court_activism` (one scalar drawn at worldgen) becomes a derived property
of a real bench:

```python
@dataclass
class Justice:
    id: int
    name: str
    pos: Vec            # judicial temperament in ideology space
    activism: float     # 0 deferential .. 1 activist — per-justice doctrine
    age: int
    appointed_by: int   # PM's MP id — the legacy trail
```

- `state.bench: list[Justice]`, `BENCH_SIZE` strong. Worldgen draws the
  inaugural bench around the old `court_activism` seed (activism) and the
  voter centroid + jitter (pos), ages spread across mid-life.
- **The verdict is a bench vote, still a rule not a roll**: each justice
  votes strike when `RISK_W*risk + BENCH_DIST_W*dist(pos, law.pos) >
  BENCH_LINE - activism*COURT_ACTIVISM_W` — a justice doctrinally hostile
  to judicial reach needs more provocation, and one ideologically far from
  the statute finds it easier to strike. Majority carries. The verdict
  event records a per-justice detail list (like `VoteResult.detail`) so
  `inspect` can show *which* justices killed the law — packing the bench
  stays legible.
- **Vacancies**: justices age on the MP hazard curve (`RETIRE` machinery,
  not `remove_mp` — no seat to vacate; death uses the same age hazard).
  `JusticeRetired`/`JusticeDied` events keep the chronicle honest.
- **The PM fills vacancies**:
  - AI PM: same week, appointee `pos` near the government agenda + jitter,
    mid-career age. `JusticeAppointed` names the appointer.
  - Player PM: an `appoint` action on vacancy offers a shortlist of
    `APPOINT_POOL` candidates with visible `pos`/`activism`/`age` — the
    classic tradeoff (a young ideologue rules for decades, an old moderate
    costs little). Pending vacancies persist until filled, so a player can
    deliberate — a caretaker PM cannot appoint (the office holds the
    power, the caretaker doesn't).
- `appointed_by` is the done-when hook: a PM's appointees keep ruling after
  their author leaves office; the bench view names who put each justice
  there.

## 3. Constitutional amendment — change the rules

The M4 apex, deferred until the constitution existed. `Bill.amends`
carries a clause change; amendment bills ride the pending cadence but need
`AMEND_MAJORITY` (two-thirds of ayes cast), not a simple majority — the
constitution is supposed to be hard to move.

- Two shapes: **repeal a clause** ("the Repeal of the Property Clause" —
  opens the statute book past that guard) and **entrench a new clause**
  (a chosen pole/limit — entrenching your own advantage). `ArticleRepealed`
  / `ArticleEntrenched` events.
- **AI trigger is legible**: a government whose law was struck under a
  clause may table that clause's repeal (`AMEND_TABLE_P` weekly while a
  struck-by citation is on record). The closed loop is the drama: court
  strikes flagship citing Article X → government tries to repeal Article
  X → needs two-thirds → the opposition defends the constitution.
- The bench cannot review amendments (the constitution doesn't adjudicate
  its own amendment); repeals of clauses don't touch laws already struck —
  no resurrection.
- Player surfaces: `amendment` action as PM (pick a clause to strike or a
  pole to entrench); a PMB may carry an amendment via `table` (legal,
  near-impossible alone — two-thirds is coalition-scale support, which is
  correct); as a voter the supermajority gate is where `vote`/`deal`
  matter most. `legacy_bills` counts an authored amendment — the ultimate
  legacy object.

## 4. Press relations

The outlet landscape becomes playable. `Outlet` gains mutable warmth:

- `Outlet.warmth: dict[int, float]` — cultivated friendliness per party
  id. Coverage hostility becomes `h = min(1, dist(slant, platform)/2) *
  (1 - warmth)`: editorial slant is the floor, warmth is bought goodwill
  on top. Warmth decays `WARMTH_DECAY` weekly — you keep courting or the
  board forgets.
- **`court` action**: target an outlet, `+COURT_WARMTH` toward your party,
  cost is the action slot; warmth caps at 1.0 — a hostile tabloid courts
  slow, a near-friendly one fast (gain scaled by nothing else; the cap is
  the equalizer).
- **`leak` gains an `outlet=` param** — you choose who breaks it. A warm
  outlet buries the story (its pickup weight on the scandal damped — it
  won't lead with it); a cold or hostile one amplifies and leads. Trace
  asymmetry: `LEAK_TRACE_P * FRIENDLY_TRACE_MULT` through a warm outlet
  (they protect sources), `* HOSTILE_TRACE_MULT` through a cold one (you
  had to approach the enemy). Routing with no outlet keeps current
  behavior.
- **Sponsored polls** — the biased-samples half of the roadmap item:
  `PollShift` gains `outlet=`; a rotating outlet publishes each week and
  the printed shares re-weight voters by audience affinity (`aff`) — a
  friendly outlet's poll flatters you because its readers over-represent
  your voters. The driver names the sponsor ("The Sentinel poll"). The
  sim's oracle stays `poll()` — but the AI snap-call reads
  `state.last_poll`, the *published* number, so a flattered government can
  call a doomed early election on its own press. That's not a bug; that's
  the point.
- **AI courtship stays cheap**: `WARMTH_DRIFT` weekly toward the party
  nearest each outlet's slant, capped below what active courting buys —
  the world moves on its own logic without an AI action economy.

## Boundaries

**Always**: `params.py` for every constant; named terms on verdict detail
(the bench votes with inspectable reasons like MPs do); `state.emit` for
every legibility surface; seeded RNG only; `tick()` is the only mutation
path; verdicts stay rules-not-rolls (justice terms are deterministic given
the case).

**Never**: fabricated stories (needs a truth layer — the p3-media boundary
stands); outlet ownership/`Outlet.owner` (the seam is noted — needs a
favors price, there is no money); injunctions and provision-level strikes
(p3-courts deferrals stand); AI barons; per-district perception; AI
initiating deals (M3 deferral stands); LLM-generated anything.

## Params

```
ARTICLE_LIMIT      = 0.55   # default positional clause fence
ARTICLE_COUNT      = (4, 6) # constitution size at worldgen
BENCH_SIZE         = 7      # justices on the bench
BENCH_DIST_W       = 0.25   # ideology's weight in a justice's strike vote
BENCH_LINE         = 0.6    # doctrinal line (was COURT_STRIKE_BASE)
JUDGE_APPOINT_AGE  = (42,58)# new justices arrive mid-career
APPOINT_POOL       = 3      # shortlist size for the player-PM
AMEND_MAJORITY     = 2/3    # supermajority of ayes cast
AMEND_TABLE_P      = 0.4    # weekly tabling odds while a citation stands
COURT_WARMTH       = 0.15   # warmth per court action
WARMTH_DECAY       = 0.01   # weekly warmth fade
WARMTH_DRIFT       = 0.005  # organic warmth toward nearest party
FRIENDLY_TRACE_MULT = 0.5   # warm outlets protect sources
HOSTILE_TRACE_MULT  = 1.5   # cold outlets burn them
```

## Success criteria

- `check_constitution.py` — an engineered far-market statute breaches the
  Property Clause; `LawStruck`/`ReviewOpened` cite the clause name; a
  centrist law breaches nothing; `challenge` files a case with the player
  as `challenger`.
- `check_bench.py` — a packed bench (appointees at the government's pole)
  upholds a law a hostile bench strikes; a vacancy produces an appointee
  whose `appointed_by` is the sitting PM; the player-PM shortlist offers
  `APPOINT_POOL` choices and the pick lands.
- `check_amendment.py` — a clause-repeal fails at 55% ayes and passes at
  70%; a repealed clause stops appearing in citations; a seeded AI
  government tables a repeal of the clause that struck its law.
- `check_press.py` — `court` raises warmth and softens hostile coverage;
  a warm-outlet leak dampens that outlet's pickup vs a cold-outlet leak;
  trace asymmetry fires; a friendly sponsored poll's printed share
  exceeds `poll()` ground truth for the player's party; the AI snap gate
  reads `state.last_poll`, not the oracle.
- The sweep re-reads: `laws struck` should redistribute across seeds
  (bench ideology now matters); `laws in force` may dip (more strikes) or
  recover (packed courts); watch `debt_max` — still the standing M4 wound.

## Open questions

- Should a justice's `pos` drift with age/tenure (the "Greenhouse effect"
  — justices moderate on the bench)? Cheap (`pos *= 1 - JUDGE_MODERATE`
  weekly) and flavorful, but it weakens the packing payoff; default no,
  flag for the balance pass.
- Should warmth be per-party or per-MP? Per-party matches the coverage
  model (subjects resolve to parties); per-MP personal press relationships
  are a deeper layer, deferred.
- Does the Mandate Clause over-punish PMBs (thin margins are their
  nature)? If checks show PMBs litigated to death, exempt `author`-bearing
  laws or raise its weight only on government bills.
