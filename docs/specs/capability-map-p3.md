# Capability Map: Phase 3 — The Country Deepens

Approved module boundaries for Phase 3. Each module gets its own spec (`docs/specs/spec-p3-<module>.md`), plan, and task list, built in dependency order.

| Module id          | Responsibility                                                            | Depends on             |
|--------------------|---------------------------------------------------------------------------|------------------------|
| ai-careers         | MP lifecycle: climb, scheme, age, retire, be replaced                     | —                      |
| scandal-lifecycle  | Simmering dossiers, timed releases, resignation cascades                  | ai-careers (vacancies) |
| factions           | Named wings inside parties: separate whips, feuds, bloc secession         | — (extends parties.py) |
| country-conditions | Living indicators (growth, unemployment, services, crime) → retrospective voting | — (voter scoring) |
| ministerial-perf   | Portfolio outcomes (economy, crises) reflect competence, move approval    | country-conditions     |
| salience           | Which axis voters care about; bills/speeches shift the weights — SUBSUMED by media-layer (outlet agenda-setting is the mechanism) | — (voter model)        |
| media-layer        | Outlets with bias + audience; voters observe media, not reality           | salience               |
| party-variety ✓    | Per-seed starting party pool, generated party names, name library, named bills | — (worldgen + bill emit) |
| independents       | Party-less candidates in FPTP; independents hold balance of power         | — (election machinery) |
| courts             | Judicial review: laws carry legal_risk, get struck or upheld after delay  | country-conditions (registry) |
| treasury           | Government revenue ∝ indicators; bills spend; debt → crisis               | country-conditions           |
| constitution       | Generated entrenched articles; the object judicial review reviews against  | courts                       |
| party-dynamism     | Party births: niche entry on unserved space, retuned founding/faction gates — observed duopoly lock-in by ~week 300 | parties, factions, election |
| snap-elections     | Fallen governments dissolve parliament for early elections                 | government (confidence) |
| fiscal-escalation  | Insolvency recurs: repeated crises, forced austerity — hysteresis re-arm never re-fires once insolvent | treasury |

Build order: ai-careers ✓ → scandal-lifecycle ✓ → factions ✓ → media-layer ✓ → country-conditions ✓ → treasury ✓ → party-variety ✓ → ministerial-perf → courts → constitution. Flexible: `independents`, `snap-elections`, `fiscal-escalation` (order negotiable — small modules); `party-dynamism` should jump the queue — the observed duopoly lock-in is the biggest north-star gap (a 1100-week run ends with two parties, zero births). `salience` was subsumed by media-layer (outlet agenda-setting is the mechanism).

Deferred: by-elections (vacant seats stay empty until general elections; candidate machinery exists via the hopefuls pool — revisited after scandal-lifecycle: steady-state vacancies measured at ~1–5% of districts, real churn but not crisis-level — defer stands).

Rationale: ai-careers is the largest north-star gap and creates the vacancy machinery scandal-lifecycle needs; scandal reuses existing dossier fields; factions extends `parties.py` which is already exercised; ministerial-perf and salience are isolated deltas; media-layer is the most invasive (rewrites voter perception) and benefits from richer events to refract — it is the candidate most likely to be deferred.
