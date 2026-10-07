# Spec M12: Entropy — the late game keeps churning

A long run converges to an absorbing state: the electorate herds
toward the surviving platforms (campaign pulls are directional and
weekly; voter noise is symmetric), MPs follow their districts in,
parties converge, cohesion stays high, no faction estranges, no
schism fires, `niche_entry` finds no unserved ground — and a
grand coalition holding most seats can never lose confidence.
Week 988: two parties, both in government, nobody else anywhere.
Every entropy source in the sim is downstream of electorate
convergence, and nothing pushes back.

Done-when: **governments bleed support over time, junior partners
can walk out, rookies bring new ideology in, and opposition
parties differentiate — so a sealed cartel government is a phase,
not an ending.**

Scope: four world-side mechanics + their legibility. Out of
scope: player actions (none needed — these are forces, not
levers), changing the coalition *formation* logic, and any
direct counter-force on the player's own seat beyond what the
voters' fatigue already does to everyone.

## 1. Governing fatigue — the cost of ruling

In `_drift`, voters drift *away* from the government agenda,
scaled by time in office:

```python
if gov.platform is not None:
    step = GOV_FATIGUE_W * min(gov.weeks_in_office, GOV_FATIGUE_CAP)
    v.pos += step * unit(v.pos - agenda)   # per-voter unit vector
```

- `GOV_FATIGUE_W = 0.0006` per week-of-office. At cap
  (`GOV_FATIGUE_CAP = 104` weeks ≈ 2 years) this is ~0.06/week of
  divergence — comparable to the campaign pull it must beat, but
  always-on and direction-free: it opens space *away* from
  wherever the government stands, which is exactly where
  `niche_entry` looks.
- The term is on the agenda (`state.government.platform`), the
  thing voters judge — not each member party; junior partners
  feel it through the coalition brand they're chained to, which
  is precisely why they'd want out (see §2).
- Voters sitting exactly on the agenda get no push (zero vector
  → skip; the normal `VOTER_DRIFT_SD` wanders them off anyway).
- The player isn't exempt: fatigue hits every government,
  including yours. Governing is supposed to cost.

## 2. Coalition exit — partners can walk

Weekly, inside the governing phase (before `strategic_call`, so
a walk-out can trigger the same week's collapse path): each
non-PM party in `gov.parties` evaluates leaving. Two named
conditions, both inspectable:

- **Strain**: `dist(pt.platform, gov.platform) > COAL_EXIT_DIST`
  (0.5) — the agenda is too far from what they sold.
- **Bleeding**: the last published poll shows the party below its
  seat share (`last_poll.shares[pid] < seats_share`) — staying is
  costing them voters.

Both must hold, plus a grace `weeks_in_office >= COAL_EXIT_GRACE`
(26 weeks — a honeymoon). On exit: the party leaves `gov.parties`,
its ministers lose portfolios, `CoalitionExit` event fires. If the
remaining bloc no longer commands a majority →
`collapse(state, "defection")`, which already routes to a
successor slate or dissolution. If the rump still commands, it
governs on alone — a majority government with a visible grudge.

## 3. Generational replacement — rookies arrive from the frontier

`make_hopeful` currently clones the consensus (platform +
jitter). With probability `ROOKIE_FRONTIER_P = 0.35`, a new
hopeful instead samples their position from an *unserved*
district centroid + jitter — "the young enter where the consensus
doesn't reach." They still lean to the nearest party (the
`party=` field is unchanged) — they arrive as misfits, which is
what estranged factions and schisms are made of. `mp_lifecycle`
passes the voters through; worldgen hopefuls keep the platform
draw (the starting world should begin coherent).

## 4. Differentiation — opposition follows its own base

In `party_lifecycle`, each party *outside* government lerps its
platform toward the mean position of voters for whom it is the
nearest platform — follow your base, not the coalition mean:

```python
if pid not in gov.parties and base_mask.any():
    pt.platform += PLATFORM_BASE_PULL * (base_mean - pt.platform)
```

`PLATFORM_BASE_PULL = 0.01`/week. Governing parties are chained
to the agenda — differentiating is the opposition's structural
advantage, and it's what keeps the map from collapsing to one
point: the government's base shrinks (§1) while the opposition's
grows into the opened space.

## 5. Legibility

- `CoalitionExit` event names the party, the strain distance, and
  the bleed: `"Union walks out of the government — the agenda sits
  0.6 from their platform and the polls have them bleeding."`
- `explain_party` gains a "leaving-risk" line for junior partners:
  strain and bleed values, the same expressions the exit check
  evaluates.
- No player-facing surface for fatigue — it's a background force,
  visible as the electorate drifting away on the scatter (and in
  your own falling poll share — the published numbers tell it).

## 6. Checks

`check_entropy.py`: fatigue pushes voters away from the agenda
and grows with tenure; exit fires only when strain AND bleed both
hold (forced fixtures); a frontier hopeful's pos sits far from
all platforms at the param rate; an opposition platform drifts
toward its own base over ~200 weeks; determinism. Then the
50-seed sweep — the metric that matters is the party system at
week 200+: parties-at-end should rise, governments should
*change*, and no seed should park at a permanent all-seat cartel.

## Atomic commits

1. `docs: m12 entropy spec`
2. `feat: governing fatigue — the cost of ruling`
3. `feat: coalition exit — partners walk`
4. `feat: frontier rookies + base differentiation`
5. `polish: check_entropy + sweep`
