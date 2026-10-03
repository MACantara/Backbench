"""Every tunable constant in the game. Tuning is the game — touch this file, not logic."""

# --- world ---
N_VOTERS = 10_000
N_DISTRICTS = 120
DISTRICT_GRID = (12, 10)  # cells tiling the [-1,1]^2 ideology square → district ids
STARTING_PARTIES = [
    # name, platform (economic, social)
    ("Union Labour", (-0.75, -0.15)),
    ("Green Alliance", (-0.35, -0.70)),
    ("Centre Democrats", (0.0, 0.0)),
    ("Conservative Party", (0.60, 0.50)),
    ("National Front", (0.35, 0.90)),
]

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

# --- voting in parliament ---
W_POLICY = 0.7     # weight on policy distance (higher = more ideological voting)
W_WHIP = 0.8       # weight on party whip instruction
W_REL = 0.4        # weight on relationship with the government/leader
W_SAFETY = 0.6     # weight on district opinion exposure (unsafe seats vote locally)
W_GOV = 0.35       # solidarity bonus for coalition MPs backing their own government's bill
VOTE_NOISE = 0.05  # per-MP ballot noise

# --- government ---
COALITION_MAX_DIST = 1.0         # partners won't join a coalition beyond this platform distance
CONFIDENCE_THRESHOLD = 0.5       # fraction of parliament needed
MINORITY_GOVT_PENALTY = 0.15     # utility discount on bills under minority government
BUDGET_EVERY_WEEKS = 12          # budget votes double as confidence votes
GOVERNING_WEEKS_PER_TERM = 40    # term length before election is due

# --- parties ---
PARTY_COHESION_SPLIT = 0.35      # below this + spread trigger → schism possible
PARTY_SPREAD_SPLIT = 0.8         # intra-party position spread needed for schism
PARTY_FORM_STAY_UTILITY = 0.2    # MP founds party when stay-utility drops below this
PARTY_SCHISM_COOLDOWN = 8        # weeks a party must wait after a schism event

# --- factions ---
FACTION_SPREAD_MIN = 0.45        # intra-party spread that forms wings
FACTION_MIN_SIZE = 3             # wings smaller than this dissolve back
FACTION_REBEL_DIST = 0.65         # centroid-bill distance where a wing whips its own line
MP_DISTRICT_PULL = 0.003         # weekly drift of an MP toward their district centroid
SECESSION_DIST = 0.5             # centroid-platform distance feeding estrangement
SECESSION_WEEKS = 6              # consecutive estranged weeks before the wing walks
FACTION_LEADER_BONUS = 0.2       # leadership-challenge edge for faction leaders

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
COVERAGE_PUBPOS_W = 0.02         # pub_pos pull per covering outlet-week
AGENDA_SALIENCE_W = 0.02         # salience nudge for in-audience voters
AUDIENCE_AFFINITY_SD = 0.5       # ideological sd of an outlet's audience
BRAND_WEIGHT = 0.15              # voter-scoring weight on party brand (bounded ±1)
BILL_PASS_BRAND = 0.005          # weekly competence signal while governing
BILL_FAIL_BRAND = 0.01           # failed bills hurt a bit more
PUB_POS_MIX = 0.5                # candidate-vs-perceived-label blend in scoring
PUB_POS_REVERT = 0.02            # weekly pull of pub_pos back to platform
PRESS_CYCLE_WEEKS = 3            # headline streak that triggers a frenzy

# --- drift ---
VOTER_DRIFT_SD = 0.004           # weekly position noise
BRAND_DECAY = 0.95               # weekly brand multiplier — reputation mean-reverts
REL_DECAY = 0.97                 # relationships decay toward neutral
