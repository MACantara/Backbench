# Spec P3.7 — Procedural parties and naming

Module id: `party-variety` (per `docs/specs/capability-map-p3.md`). The same five parties in `STARTING_PARTIES` run every seed — the country is always the same country. Founded parties are all `"{Surname} List"`, factions carry a private mini-vocabulary (`left/right/libertarian/traditional`) that nothing else shares, laws are `Week-42 Act`, and bills table at bare coordinates. This module builds one naming/structure utility — `sim/naming.py` — that generates countries: a per-seed party system grounded in cleavage structure, real party-family name pools, named legislation, a bigger MP name library, and named ideology poles.

## Objective

Every run should open in a *different country* — a three-party class-based system in one seed, a seven-party fragmented system with a regionalist and a Christian democratic anchor in the next. The chronicle should read "the Farmers' Union formed a government" and "the Border Security Act passes", not coordinate soup. All of it stays deterministic by seed and legible — you can see *why* a party is called what it is.

## Mechanics

**Cleavage-anchored party generation (worldgen):**
- Per seed, draw a **cleavage profile**: salience weights on the four Lipset–Rokkan cleavage families — owner–worker (class → axis 0), state–church and centre–periphery (→ axis 1), urban–rural (→ axis 1, agrarian pole). The profile decides which party archetypes exist.
- **Party archetypes** (Manifesto Project families): social democratic, left-socialist, liberal, conservative, Christian democratic, agrarian/centre, green, nationalist, regionalist. Each archetype = a platform anchor region in ideology space + a name formula + the cleavage it expresses. Draw 3–7 parties weighted by cleavage salience; jitter each platform around its anchor; enforce a minimum platform separation (dedupe).
- `STARTING_PARTIES` is replaced by generation — the constant leaves `params.py` (a fixed list contradicts the module's premise; the ranges — count, separation, jitter — become the tunables).
- Voter distribution is unchanged — parties must span the space where the voter mass is; the existing nearest-platform MP assignment rides free.

**Party names from real formulas:** name = family pool pick, e.g. social democratic → "Labour", "Social Democrats", "Workers' Alliance"; conservative → "National Coalition", "People's Party", "The Union"; agrarian → "Farmers' Union", "Centre Party"; nationalist → "National Front", "Homeland"; regionalist → "Periphery Alliance"-style geographic names. Unique within the pool — dedupe + numbered fallback ("Second Reform List") so generation never collides.

**Ideology-flavored names for new parties:** `parties._found` names the party from the *archetype nearest its founding platform* (a seceding left wing of the Conservatives becomes "Social Union", not "Marsh List"). Lone-founder personal vehicles keep `"{Surname} List"` — personal lists are a real convention; the split is: faction secession → archetype name, lone founder → surname list.

**Named ideology poles + `describe_pos`:** `AXIS_LABELS = ("economic", "social")`, `POLE_LABELS` — axis 0: redistribution ↔ market; axis 1: libertarian ↔ authoritarian (GAL–TAN). `describe_pos(pos) -> "left-traditional"` — the one vocabulary `factions._wing_name`, inspect cards, and driver map labels all draw from (the private `_ECON`/`_SOC` dicts are deleted — single source).

**Named bills:** `Bill.name` field; `table_bill` names from domain pools keyed on `beneficiary_axis` + position sign — axis-0 left → "Housing Regeneration Act", "Workers' Rights Act"; axis-0 right → "Enterprise Tax Act", "Deregulation Act"; axis-1 authoritarian → "Public Order Act", "Border Security Act"; axis-1 libertarian → "Civil Liberties Act", "Electoral Reform Act"; near-centre → "Administrative Reform Act". `BillTabled`/`LawEnacted` speak names, not coordinates — `Law.name` takes the bill's name and the `Week-N Act` placeholder dies.

**Bigger MP name pool:** expand `_FIRST`/`_LAST` roughly 3× (~1000 combos) and add a composed-name style (~5% of MPs get `"Vale-Holt"` style double surnames) — enough headroom for the hopefuls pipeline churning 300+ weeks.

## Boundaries

- Always: everything seeded from `state.rng`/worldgen rng; pools and formulas live in `sim/naming.py` (data-driven dicts — params for tunables, not logic); names unique per run; `describe_pos` is the *only* position→words function in the codebase.
- Ask first: removing `STARTING_PARTIES` — it's the tunable most likely to be hand-edited for scenarios; the module replaces it with generation ranges (scenario support returns properly in Phase 4 difficulty/scenarios).
- Never: real-country party names or real-person names (fictional pools only — this is a fictional country, not a parliament-of-the-world mod); cleavages as a *live* system (they're a worldgen scaffold — no cleavage state evolves at runtime); per-district or per-voter cleavage modeling; English-language politics idioms that don't translate to the fiction ("Tory", "GOP").

## Success criteria

- `checks/check_parties.py` / `check_worldgen.py` updated: two different seeds produce different party pools (names + platforms differ); every generated pool has 3–7 parties, unique names, pairwise platform separation ≥ the param; same seed → identical pool (determinism).
- `check_parties.py`: a faction secession produces an archetype-flavored name (not `X List`); a lone-founder `PartyFormed` produces `"{Surname} List"`.
- `check_parliament.py` / `check_treasury.py`: `BillTabled` and `LawEnacted` texts contain a domain-flavored name, not `"+0.xx"` coordinates; `Law.name` carries the bill's name.
- `check_conditions.py` stays green (registry unchanged); `check_e2e.py`, `check_media.py`, `check_sweep.py` stay green — media outlets keep their own naming (already generated, untouched).
- `check_worldgen.py`'s hardcoded "5 parties" assertion updated to the generated range.

## Deferred

- **Generated country name** ("the Republic of X" as a chronicle dateline) — deferred to Phase 5 presentation. Keep the generator's API open to a `country_name` field later; not worth blocking P3.
- **Regional flavor name packs** (Nordic-vs-Mediterranean archetype variants) — Phase 5 texture; one clean pool first.
- Player-facing party founding naming (Phase 4 "Cross the floor" gets the archetype namer free).
- Scenario presets that pin specific party systems (Phase 4 difficulty/scenarios — will want a `party_pool=` override hook; leave the generator's signature compatible).
- Driver map pole labels (the `AXIS_LABELS`/`POLE_LABELS` constants land here; the pygame map reads them whenever Phase 5 presentation polish happens).
