# Backbench — Game Specification

Local AI politics sim. Python, stdlib-only sim core, no LLMs. The player is a single MP in a parliament of classical-AI agents, playing through repeated campaign→govern→campaign cycles until they lose their seat or are expelled.

## 1. World Model

### 1.1 Ideology space
All actors live in a 2D ideological plane: economic axis x ∈ [-1, 1] (left↔right), social axis y ∈ [-1, 1] (liberal↔conservative). Distance = Euclidean. Every voter, MP, party platform, and bill has a position in this space.

### 1.2 Districts
120 single-member districts, first-past-the-post. Each district owns a disjoint subset of voters. The player's seat is one specific district; constituency actions target it directly.

### 1.3 Voters (~10,000 agents)
Per voter:

| Field | Type | Notes |
|---|---|---|
| `position` | (x, y) | drifts slowly; events shift salience-weighted axes |
| `turnout` | 0–1 | probability of voting |
| `loyalty` | 0–1 | stickiness to last-voted party |
| `betrayal` | scalar | tracks broken promises by their district's MP |
| `salience` | dict[axis]→weight | which axis the voter currently weights more |

Vote choice: for each party on the ballot in the voter's district, score = `-(distance × salience weighting) + loyalty bonus + noise`. Highest score wins the vote; turnout check gates it. Party entry onto a district ballot requires a candidate (an MP or a generated placeholder candidate of the party's ideology).

### 1.4 MPs (~120 agents)
Per MP (including the player, who shares the schema):

| Field | Type | Notes |
|---|---|---|
| `position` | (x, y) | personal ideology, may diverge from party platform |
| `ambition` | 0–1 | drives leadership challenges, portfolio hunger |
| `loyalty` | 0–1 | resistance to whip pressure; decay on betrayal |
| `competence` | 0–1 | governing outcomes, ministerial performance |
| `integrity` | 0–1 | scandal probability and damage taken |
| `relationships` | dict[mp]→float | per-MP favor/grudge, mutated by lobby/betrayal |
| `party` | Party\|None | independents allowed |
| `seat_safety` | derived | last margin + district drift |
| `portfolio` | ministry\|None | cabinet position |
| `dossier` | hidden | accumulated scandal material, player can't see others' |

Hidden stats exist for all MPs; the player's own dossier is also hidden — revealed only through events.

### 1.5 Parties (dynamic)
A party is not a fixed container. It's:

```
party = { platform: (x,y), members: [MP], brand: float, cohesion: float, leader: MP }
```

- `brand`: accumulated public reputation; decays on broken promises/scandals, grows on delivered bills.
- `cohesion`: mean member alignment to platform + leader loyalty; low cohesion → higher defection probability.
- Elections field the party's candidate in each district where it runs.

**Formation:** an MP (or group) with `ambition` high and utility-of-staying < threshold leaves and founds a party at their own position; nearby independents/fragile-party members may join. **Split:** when intra-party position spread exceeds a threshold and cohesion is low, the minority cluster schisms. **Death:** zero seats → party dissolves. **Mergers:** explicitly v2.

## 2. The Tick

`tick(state, player_actions) -> (new_state, events)`. One tick = one week. Events are typed first-class objects: `PollShift`, `BillTabled`, `VoteResult`, `Scandal`, `Defection`, `PartyFormed`, `CoalitionFormed`, `ConfidenceLost`, `ElectionCalled`, `CareerEvent`. Interrupting events pause presentation for player attention.

Tick order:

1. Player actions resolve (or AI decisions for all non-player MPs in parallel).
2. Scheduled mechanics fire: bill vote if one is tabled, confidence check if triggered, election if due.
3. Environment drift: voter positions/salience shift, relationships decay toward neutral, party brand decays.
4. Event generator rolls: scandals, news events, crises (bounded frequency).
5. Emit event list; update phase state.

## 3. Phases

### 3.1 Campaign (8 weeks before election)
- Player actions: `campaign` (district), `give_speech` (shift salience + profile), `promise` (tracked commitment to a bloc — feeds voter `betrayal` if broken), `media` (visibility, gaffe risk), `dig_dirt` (acquire dossier on rival MP).
- Polls = sample of voter agents with turnout weighting; published weekly with noise.

### 3.2 Election
- Resolve all 120 districts simultaneously via voter scoring. Candidates seated; district margins set `seat_safety`.

### 3.3 Government formation
- Largest party gets first attempt at forming government. Coalition bargaining: party leaders trade portfolios + platform concessions; MP utility over (portfolio value, policy distance, seat safety of result). A government needs confidence majority; failure → second party tries → else minority government tolerated at penalty, or snap election.
- Player at low rank participates by giving/withholding support, extracting concessions.

### 3.4 Governing weeks
- Government tables one bill per week: `{position, beneficiary_bloc, cost}`.
- Whip: party leaders issue a whip position; MPs vote by utility = `w(policy_distance) + w(whip × loyalty) + w(relationship to government) + w(district opinion exposure) + noise`. Whips are instructions, not compulsion — rebelling costs loyalty and leader relationship.
- Passing bills: shifts voter positions of beneficiary bloc toward government, boosts brand and relevant ministers' competence rep. Failing: brand damage, cohesion hit.
- Budget vote every N weeks doubles as confidence vote. Lost confidence → government falls.

### 3.5 Career machinery
- **Ministerial appointments:** leader assigns portfolios on competence + loyalty; player can be appointed, reshuffled, sacked.
- **Leadership challenge:** triggered when leader cohesion < threshold and challengers' combined ambition > threshold; MPs vote on expected-utility of each candidate. Player eligible once standing is high enough.
- **PM/leader powers:** set party platform position, assign portfolios, call election (bounded), direct whip.

## 4. Player Interface

Two actions per week from a context-aware menu. Phase determines menu contents. Every action is a typed `Action` object passed into `tick` — the sim never reads input directly.

## 5. Losing and Scoring

- **Run ends:** lose your seat at an election, or expelled from parliament (dossier reaches public-release threshold). Retiring is voluntary end.
- **Score:** `Σ (office_level × terms_held) + legacy_bills + elections_survived`. Becoming PM and surviving a full term is the informal summit.
- Deaths are legible: the final screen names the causal chain (events that led to the loss).

## 6. Architecture

```
sim/        pure stdlib core — no I/O, no printing, no randomness without the seeded RNG
  state.py    GameState, Voter (numpy arrays), MP, Party, Bill dataclasses
  tick.py     weekly pipeline
  election.py district resolution
  parliament.py votes, whips, coalition bargaining
  parties.py  formation/split/death
  events.py   typed events + interrupt classification
  params.py   every tunable constant in one file — tuning is the game
driver/     thin shells around the core
  terminal.py MVP driver: print state, read 2 actions, loop
  textual.py  later: animated hybrid presentation
```

- `tick` is deterministic given (state, actions, seed) — replays and headless tuning runs.
- All randomness flows through a single `random.Random(seed)` held in state.
- numpy only for voter-array math; MP logic is plain Python (120 agents, no perf concern).

## 7. MVP Acceptance Criteria

1. A headless sim runs a full cycle (campaign → election → formation → 20 governing weeks → next election) without crashes, seeded.
2. Coalition stability is neither frozen nor noise: across 50 seeded runs, government survival distribution has meaningful variance (median 10–40 weeks).
3. Scripted "good play" (aligned promises kept, constituency work in a marginal seat) beats "bad play" on seat survival by a measurable margin across seeds.
4. Any `ConfidenceLost`/`Defection` event can be traced to contributing factors via the inspector (per-MP vote utility breakdown).
5. Terminal driver plays one complete cycle interactively.

## 8. Not Doing (v1)

- Media-filtered electorate, mergers, procedural narrative text beyond a fixed template pool, save/load beyond YAML dump, any graphics, real-world data, multiplayer.

## 9. Build Order (atomic commits sketch)

1. `params.py` + ideology-space scaffolding + seeded RNG harness
2. Voter arrays + district election resolution (+ headless smoke run)
3. MP schema + whip/vote utility + weekly bill loop
4. Government formation + confidence
5. Party dynamics (form/split/die)
6. Campaign actions + promises/betrayal
7. Player career machinery (appointments, challenges, scoring)
8. Terminal driver + inspector
