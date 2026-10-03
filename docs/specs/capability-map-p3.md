# Capability Map: Phase 3 — The Country Deepens

Approved module boundaries for Phase 3. Each module gets its own spec (`docs/specs/spec-p3-<module>.md`), plan, and task list, built in dependency order.

| Module id          | Responsibility                                                            | Depends on             |
|--------------------|---------------------------------------------------------------------------|------------------------|
| ai-careers         | MP lifecycle: climb, scheme, age, retire, be replaced                     | —                      |
| scandal-lifecycle  | Simmering dossiers, timed releases, resignation cascades                  | ai-careers (vacancies) |
| factions           | Named wings inside parties: separate whips, feuds, bloc secession         | — (extends parties.py) |
| country-conditions | Living indicators (growth, unemployment, services, crime) → retrospective voting | — (voter scoring) |
| ministerial-perf   | Portfolio outcomes (economy, crises) reflect competence, move approval    | country-conditions     |
| salience           | Which axis voters care about; bills/speeches shift the weights            | — (voter model)        |
| media-layer        | Outlets with bias + audience; voters observe media, not reality           | salience               |
| party-variety      | Per-seed starting party pool, generated party names, bigger name library  | — (worldgen only)      |
| independents       | Party-less candidates in FPTP; independents hold balance of power         | — (election machinery) |

Build order: ai-careers → scandal-lifecycle → factions → country-conditions → ministerial-perf → salience → media-layer. Flexible: `party-variety` (worldgen-only, quick win — fits anywhere) and `independents` (slots after scandal-lifecycle, order negotiable).

Deferred: by-elections (vacant seats stay empty until general elections; candidate machinery exists via the hopefuls pool — revisit during scandal-lifecycle, when vacancies become more frequent).

Rationale: ai-careers is the largest north-star gap and creates the vacancy machinery scandal-lifecycle needs; scandal reuses existing dossier fields; factions extends `parties.py` which is already exercised; ministerial-perf and salience are isolated deltas; media-layer is the most invasive (rewrites voter perception) and benefits from richer events to refract — it is the candidate most likely to be deferred.
