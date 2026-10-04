"""Every tunable constant in the game. Tuning is the game — touch this file, not logic."""

# --- world ---
N_VOTERS = 10_000
N_DISTRICTS = 120
DISTRICT_GRID = (12, 10)  # cells tiling the [-1,1]^2 ideology square → district ids
# --- party generation (per-seed cleavage-anchored systems; see sim/naming.py) ---
PARTY_COUNT_RANGE = (3, 7)     # starting parties per worldgen
PARTY_MIN_SEPARATION = 0.4     # min pairwise platform distance at worldgen
PARTY_PLATFORM_JITTER = 0.12   # platform noise around archetype anchors
PARTY_PLACE_TRIES = 20         # jitter resamples to satisfy min separation
PARTY_FLANK_EDGE = 0.25        # anchors past this cover an economic flank
ARCHETYPE_BASE_W = 0.2         # draw weight floor per archetype
DESCRIBE_THRESHOLD = 0.25      # |pos| per axis needed to earn a pole word
BILL_NEUTRAL_BAND = 0.2        # |pos| below this → generic bill names
COMPOSED_SURNAME_P = 0.05      # double-barreled surname rate

# --- voters ---
VOTER_POS_SD = 0.45          # clustered-normal spread in ideology space
TURNOUT_MEAN, TURNOUT_SD = 0.65, 0.15
LOYALTY_MEAN, LOYALTY_SD = 0.40, 0.20
SALIENCE_BASE = 1.0          # mean weight per axis
SALIENCE_SD = 0.30

# --- election ---
VOTE_NOISE_SD = 0.20         # per-voter scoring noise
LOYALTY_WEIGHT = 0.60        # bonus to last-voted party
TURNOUT_MODEL_NOISE = 0.05   # extra turnout jitter at election time

# --- MPs ---
MP_POS_JITTER = 0.12         # distance of an MP from their party/district anchor
MP_STAT_SD = 0.20            # ambition/loyalty/competence/integrity spread around means
MP_STAT_MEANS = {"ambition": 0.5, "loyalty": 0.5, "competence": 0.5, "integrity": 0.5}

# --- careers / lifecycle ---
MIN_MP_AGE = 1300            # minimum age to stand (weeks; 25y)
MP_AGE_WORLDGEN = (2080, 3380)   # starting MP age range (40-65y)
MP_SENIORITY_WORLDGEN = (0, 780) # starting seniority range (0-15y)
N_HOPEFULS = 120             # aspiring-politician pool at worldgen
HOPEFUL_AGE = (936, 1248)    # hopeful starting ages (18-24y)
HOPEFULS_PER_WEEK_P = 3 / 52 # pool replenishment (~3 per year)
RETIRE_FLOOR = 2860          # no retirements younger than this (55y)
RETIRE_AGE = 3640            # retirement hazard ramps past this (70y)
RETIRE_BASE_P = 0.0005       # weekly retirement probability below RETIRE_AGE
RETIRE_SLOPE = 0.0002        # added probability per week past RETIRE_AGE
RETIRE_MAX_P = 0.15          # weekly cap
SENIORITY_W = 0.5            # portfolio weight for seniority (per ~100y normalized)

# --- ministerial performance ---
# ministry → the conditions dial it owns (None would be a patronage post)
PORTFOLIO_INDICATOR = {
    "Finance": "growth",
    "Labour": "unemployment",
    "Interior": "crime",
    "Health": "services",
    "Foreign": "inflation",
}
PORTFOLIO_EFFECT = 0.004       # weekly indicator push at competence 1.0
PERF_DECAY = 0.98              # weekly decay on a minister's record — recency rules
MINISTER_TENURE = 16           # weeks before a record is judged
MINISTER_SACK_RECORD = -0.06   # accumulated indicator loss that gets you fired
MINISTER_SACK_BRAND = 0.03     # brand hit when the PM admits a bad pick

# --- voting in parliament ---
W_POLICY = 0.7     # weight on policy distance (higher = more ideological voting)
W_WHIP = 0.8       # weight on party whip instruction
W_REL = 0.4        # weight on relationship with the government/leader
W_SAFETY = 0.6     # weight on district opinion exposure (unsafe seats vote locally)
W_GOV = 0.35       # solidarity bonus for coalition MPs backing their own government's bill
VOTE_NOISE = 0.05  # per-MP ballot noise
BILL_PERSUASION = 0.008  # weekly electorate pull toward gov axis per passed bill

# --- government ---
COALITION_MAX_DIST = 1.0         # partners won't join a coalition beyond this platform distance
COALITION_WHIP_TOL = 1.2         # gov bill this far from a partner's platform breaks its whip line
CONFIDENCE_THRESHOLD = 0.5       # fraction of parliament needed
MINORITY_GOVT_PENALTY = 0.15     # utility discount on bills under minority government
BUDGET_EVERY_WEEKS = 12          # budget votes double as confidence votes
GOVERNING_WEEKS_PER_TERM = 40    # term length before election is due
CAMPAIGN_WEEKS = 8               # weeks between an election call and the vote

# --- snap elections ---
SNAP_COLLAPSE_MAX = 2            # collapses since last election that force dissolution
SNAP_WINDOW = (20, 32)           # weeks_in_office range where a strategic call is allowed
SNAP_POLL_EDGE = 0.08            # gov poll share must beat its seat share by this much
SNAP_CALL_P = 0.10               # per-week chance while the window + poll gate hold

# --- parties ---
PARTY_COHESION_SPLIT = 0.35      # below this + spread trigger → schism possible
PARTY_SPREAD_SPLIT = 0.8         # intra-party position spread needed for schism
PARTY_FORM_STAY_UTILITY = 0.45   # MP founds party when stay-utility drops below this
PARTY_SCHISM_COOLDOWN = 8        # weeks a party must wait after a schism event
STAY_W_COHESION = 0.35           # stay-utility weight on party cohesion
STAY_W_PROXIMITY = 0.45          # stay-utility weight on platform proximity
STAY_PORTFOLIO = 0.2             # stay-utility bonus for holding a portfolio
STAY_ALIEN_DIST = 0.3            # MP-platform distance where alienation starts to bite
STAY_ALIEN_W = 0.5               # alienation penalty slope past STAY_ALIEN_DIST
STAY_ESTRANGED = 0.15            # stay-utility penalty when the MP's wing is estranged

# --- factions ---
FACTION_SPREAD_MIN = 0.2         # intra-party spread that forms wings
FACTION_MIN_SIZE = 3             # wings smaller than this dissolve back
FACTION_REBEL_DIST = 0.65         # centroid-bill distance where a wing whips its own line
MP_DISTRICT_PULL = 0.003         # weekly drift of an MP toward their district centroid
SECESSION_DIST = 0.3             # centroid-platform distance feeding estrangement
SECESSION_WEEKS = 6              # consecutive estranged weeks before the wing walks
FACTION_LEADER_BONUS = 0.2       # leadership-challenge edge for faction leaders

# --- party dynamism ---
DYNAMIC_GAP_DIST = 0.55          # district centroid this far from every platform is unserved
DYNAMIC_GAP_MIN_SEATS = 6        # contiguous unserved districts needed to support a party
DYNAMIC_ENTRIES_PER_ELECTION = 2 # cap on niche entries/revivals per campaign
DYNAMIC_GRACE_WEEKS = 12         # memberless entrants survive until after their first election
GRAVE_WEEKS = 520                # a dissolved party stays revivable for ~10 terms
GRAVE_MAX = 24                   # the graveyard itself is bounded — most recent kept

# --- player / career ---
ACTIONS_PER_WEEK = 2
LEADERSHIP_COHESION_MIN = 0.45   # leader challengeable below this cohesion
CHALLENGE_AMBITION_MIN = 0.6     # challengers need this much combined ambition

# --- scandal lifecycle ---
DIRTY_GROWTH = 0.002             # weekly dossier growth per unit of (1 - integrity)
LEAK_BASE_P = 0.015              # weekly leak probability per unit of dossier
LEAK_MIN_DOSSIER = 0.1           # below this, dirt never leaks
LEAK_MAX_P = 0.25                # cap on the base rate (election multiplier applies after)
SEVERITY_SERIOUS = 0.5           # dossier separating "embarrassing" from "serious"
LEAK_ELECTION_MULT = 3.0         # October-surprise multiplier near elections
ELECTION_LEAK_WINDOW = 6         # weeks before an election the multiplier applies
SCANDAL_WEEKS = (3, 6)           # active-scandal duration range
RESIGN_BASE_P = 0.02             # weekly resignation probability while burning
RESIGN_DOSSIER_W = 0.15          # added resignation probability per unit of dossier
SACK_THRESHOLD = 1.5             # leader expels members past this dossier size
MINISTER_SACK_FRAC = 0.6         # ministers sacked past this fraction of the threshold
SCANDAL_BRAND_HIT = 0.02         # weekly party brand bleed per active scandal
MINISTER_BRAND_MULT = 2.0        # minister scandals bleed this much harder
PARTY_BLEED_MAX = 0.08           # cap on weekly brand loss per party
SCANDAL_BETRAYAL = 0.05          # weekly district betrayal while a scandal burns
WEATHERED_BURN = 0.5             # dossier fraction spent on surviving a scandal
WEATHERED_BRAND_SCAR = 0.05      # permanent party brand cost of a weathered scandal

# --- media layer ---
OUTLET_COUNT = (3, 4)            # outlets per worldgen
OUTLET_REACH = (0.25, 0.55)      # audience fraction range
OUTLET_SLANT_JITTER = 0.15       # noise on editorial positions
OUTLET_CENTRIST = True           # guarantee one centrist outlet
COVERAGE_BRAND_W = 0.015         # brand shift per unit of newsworthiness/2, per outlet
COVERAGE_PUBPOS_W = 0.05         # pub_pos pull per covering outlet-week
AGENDA_SALIENCE_W = 0.02         # salience nudge for in-audience voters
AUDIENCE_AFFINITY_SD = 0.5       # ideological sd of an outlet's audience
BRAND_WEIGHT = 0.15              # voter-scoring weight on party brand (bounded ±1)
BILL_PASS_BRAND = 0.005          # weekly competence signal while governing
BILL_FAIL_BRAND = 0.01           # failed bills hurt a bit more
PUB_POS_MIX = 0.5                # candidate-vs-perceived-label blend in scoring
PUB_POS_REVERT = 0.02            # weekly pull of pub_pos back to platform
PRESS_CYCLE_WEEKS = 3            # headline streak that triggers a frenzy
MEDIA_APPEAR_BRAND = 0.05        # player media appearance → brand
MEDIA_APPEAR_PUBPOS = 0.05       # player media appearance → pub_pos toward center

# --- country conditions ---
COND_BASE = {"growth": 0.0, "unemployment": 0.5, "inflation": 0.3,
             "services": 0.5, "crime": 0.3}     # mean-reversion baselines
COND_REVERT = 0.02           # weekly pull toward baseline
COND_JITTER_SD = 0.04        # worldgen spread around baseline per seed
COND_NOISE_SD = 0.01         # weekly indicator noise
COUPLE_GROWTH_UE = 0.03      # growth↑ → unemployment↓
COUPLE_UE_CRIME = 0.02       # unemployment↑ → crime↑
COUPLE_SVC_CRIME = 0.01      # services↑ → crime↓ (slow)
SHOCK_P = 1 / 80             # weekly shock probability (~one per term)
SHOCK_MAG = (0.15, 0.35)     # jump magnitude range
SHOCK_INTERRUPT = 0.25       # shocks at least this big interrupt auto-play
LAW_EFFECT_SCALE = 0.02      # weekly push rate per unit extremity (diminishing near bounds)
MOOD_W = {"growth": 0.4, "services": 0.2, "unemployment": 0.3,
          "inflation": 0.2, "crime": 0.15}      # positive signs on the good ones
RETRO_WEIGHT = 0.5           # voter-scoring weight on mood × responsibility
RETRO_PM_SHARE = 0.6         # the PM's party takes this share of credit/blame
W_RETRO_CONF = 0.3           # confidence-vote term: coalition MPs feel the slump

# --- treasury ---
REV_BASE = 0.10              # weekly revenue at baseline conditions
REV_GROWTH_W = 0.05          # revenue swing per unit of growth
REV_UE_W = 0.04              # revenue drag per unit of unemployment
DEBT_INTEREST = 0.005        # weekly interest rate on the debt stock
COST_BASE = 0.002            # a bill's minimum weekly upkeep
COST_EXTREMITY_W = 0.008     # ambitious programs cost more
COST_JITTER = 0.001          # noise on bill cost
LAW_COST_DECAY = 0.98        # programs normalize into baseline spending over time
DEBT_WARN = 1.0              # debt above this drags inflation + tightens fiscal votes
DEBT_INFLATION_W = 0.01      # weekly inflation push per unit of debt past WARN
DEBT_CRISIS = 2.0            # insolvency: DebtCrisis + forced confidence vote
DEBT_BRAND_HIT = 0.15        # one-time brand drop for gov parties on crisis
W_FISCAL = 0.6               # vote term weight on bill cost × debt pressure

# --- drift ---
VOTER_DRIFT_SD = 0.004           # weekly position noise
SALIENCE_REVERT = 0.02           # weekly pull of salience back toward base
BRAND_DECAY = 0.95               # weekly brand multiplier — reputation mean-reverts
REL_DECAY = 0.97                 # relationships decay toward neutral
