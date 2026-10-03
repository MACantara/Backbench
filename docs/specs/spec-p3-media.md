# Spec: media-layer (P3) — outlets, coverage, and the perceived party

Status: draft for review. Module id `media-layer` in `docs/specs/capability-map-p3.md` (depends on the `v.salience` field, which already exists — see Boundaries for what this folds in).

## Why

Voters today observe reality directly: they score parties on the *true* platform, and two reputation channels already built — `Party.brand` and `v.salience` — are dead or inert:

- `Party.brand` is **write-only**: bills, scandals, and media appearances all adjust it, but no voter ever reads it. Reputation cannot move an election.
- `v.salience` is **static** except player speeches: nobody sets the national agenda. The capability map's separate `salience` module is, in effect, the media layer's job.

The north star wants the country to generate its own narrative. A media layer is where events become *stories*: outlets with editorial slant cover the week's events, amplify what fits their agenda, and over months construct public caricatures of parties that differ from the platforms MPs actually vote on. The chronicle stops being a log and starts being a press.

## Model

### New state

```python
@dataclass
class Outlet:
    id: int
    name: str             # "The Tribune", "Channel 9" — generated, see naming
    slant: Vec            # editorial position in ideology space
    reach: float          # 0..1, fraction of the electorate in its audience
    sensationalism: float # 0..1 — scandal amplification vs policy amplification
    focus_axis: int       # 0 or 1 — the axis it harps on (agenda-setting)
```

- `GameState.outlets: list[Outlet]` — 3–4 per country, generated at worldgen.
  Slants drawn to cover the space (one near each pole cluster, one centrist),
  names from a generated pool (`{The} {City/Nature-word} {Herald/Tribune/Post/Wire}`
  — reuses the party-variety naming machinery).
- `Party.pub_pos: Vec` — the party's *perceived* position, initialized to
  `platform`. This is the core mechanic: **voters score `pub_pos`, not
  `platform`**. What the country believes a party stands for is a media
  construction, drifting weekly under coverage pressure.

### The coverage pass (weekly, in the lifecycle block)

Each week, the week's events are scored for newsworthiness and each outlet
picks its top story:

1. **Newsworthiness**: `ScandalBreaks`/`Resigned`/`Expelled`/`MinisterSacked`
   (sensational stories — weight ∝ outlet `sensationalism`), `VoteResult`,
   `ConfidenceLost`, `CoalitionFormed`, `Secession`/`PartyFormed`,
   `ElectionCalled` (policy stories — weight ∝ `1 - sensationalism`). Outlets
   differ in what they lead with; a tabloid and a broadsheet cover different
   weeks.
2. **Framing**: for each story with a subject party, the outlet's effect
   depends on slant-vs-party distance. Hostile coverage (slant far from the
   party) amplifies damage; friendly coverage damps it.
3. **Effects on the country** (all small, all weekly — media moves polls over
   months, not days):
   - `Party.brand` shifts for story subjects: scandals hit harder through
     hostile outlets, wins land softer through unfriendly ones.
   - `Party.pub_pos` of story subjects is nudged: hostile coverage pushes the
     perceived position *away from the outlet's audience toward the
     caricature* — i.e., exaggerates the party's platform along the slant
     axis (`pub_pos` pulled toward `platform` stretched away from slant);
     friendly coverage pulls `pub_pos` toward the respectable center.
   - `v.salience` on the outlet's `focus_axis` rises for voters in its
     audience — agenda-setting.
4. **Audience**: a voter is in an outlet's audience with probability ∝
   `reach` × ideological affinity (voters near the slant read it; echo
   chambers emerge free). Vectorized over `state.voters`.
5. **Emit** `Headline` — one per week, the highest-reach story:
   `"The Tribune leads with 'Minister in Scandal' — Union bleeds."`
   Chronicle-level, not an interrupt.

### Brand becomes load-bearing

`brand` gains its missing consumer — added as a named term in voter scoring
(`_district_scores`) and `poll`:

```
score[voter, party] = -salience-weighted distance to pub_pos
                    + BRAND_WEIGHT * party.brand
                    + loyalty - betrayal + noise
```

Scandal brand-bleed (already shipped) now bites at the ballot box through
coverage. `brand` still decays (`BRAND_DECAY`) — yesterday's story fades;
`pub_pos` does *not* fully decay (it mean-reverts slowly toward `platform`
at `PUB_POS_REVERT`), so sustained caricature outlasts any single story.

## Events

| Event | When | Interrupt? |
|---|---|---|
| `Headline` | weekly — the lead story, with framing | no — chronicle only |
| `PressCycle` | a story spans 3+ consecutive weeks of headlines (a feeding frenzy around a burning scandal) | yes — rare, signals a storm |

No per-outlet event spam: one `Headline` a week regardless of outlet count.

## Player touchpoints

- `media` action stays one slot but its effect is now *routed through the
  outlet landscape*: a national appearance boosts `pub_pos` toward your
  favor and `brand`, magnitude scaled by how friendly the reachable outlets
  are to your party; the gaffe chance feeds a hostile-coverage spike (your
  dossier story becomes everyone's headline).
- `speech` gains a subtlety: it raises `v.salience` on the axis you choose —
  you are contesting the agenda outlets set.
- Inspect: `explain_mp`/party panel shows `pub_pos` vs `platform` divergence
  ("Union is seen as (+0.4, +0.1), platform (+0.2, +0.3)") — the gap is the
  media's verdict on the party.
- Phase 4 hooks (spec'd, not built): `dig_dirt` released *through* a chosen
  outlet (friendly outlet buries it, hostile leads with it) — the
  scandal-as-a-weapon roadmap item; courting editorial boards.

## Boundaries

- **Folds in the `salience` module's core**: agenda-setting on `v.salience`
  is the media layer's mechanism; what remains of the separate `salience`
  row (bills/speeches shifting weights) already partially exists via the
  `speech` action. Recommend marking `salience` as subsumed — decision for
  the capability map on merge.
- **No per-voter perception layer.** `pub_pos` is national: the media
  environment constructs one caricature per party, weighted by reach.
  Per-district or per-voter perceived positions are a deeper rewrite for a
  later phase if ever.
- **No misinformation/fake events.** Outlets refract real chronicle events;
  they don't invent stories. Fabricated scandals would need a truth-tracking
  layer — out of scope.
- **No AI media actions.** Parties don't buy coverage; the press is an
  independent institution like the court will be. Player-media relationships
  are Phase 4.
- **Deterministic**: all rolls through `state.rng`; NumPy generators seeded
  from it.
- **Poll stays ground-truth**: polls report the real electorate (media moves
  the fields, the poll reads them). Biased polls per outlet are a flavor
  idea, not this module.

## Success criteria

- Over a 300-week unscripted run: `pub_pos` diverges measurably from
  `platform` for parties under hostile coverage (target ≥0.1 gap for the
  most-covered party), and `Headline` events attribute the movement.
- Scandals now move polls: a `ScandalBreaks` on a governing party produces a
  measurable poll dip within ~6 weeks (previously brand-bleed was cosmetic).
- Agenda-setting is visible: sustained `focus_axis` coverage shifts
  electorate salience weights enough to flip marginal districts across an
  election cycle.
- Echo chambers: audience membership correlates with voter-outlet affinity
  — no uniform national effect.
- No headline spam: ≤1 `Headline`/week, `PressCycle` only on multi-week
  storms.
- Deterministic by seed; sweep stays healthy (media adds variance but
  governments shouldn't collapse on news cycles — brand effects are slow).

## Tuning surface (`params.py`)

`OUTLET_COUNT`, `OUTLET_REACH`, `OUTLET_SLANT_SPREAD`, `COVERAGE_BRAND_W`,
`COVERAGE_PUBPOS_W`, `AGENDA_SALIENCE_W`, `AUDIENCE_AFFINITY_SD`,
`BRAND_WEIGHT` (voter term), `PUB_POS_REVERT`, `PRESS_CYCLE_WEEKS`.
