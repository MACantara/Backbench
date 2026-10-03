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
FACTION_SPREAD_MIN = 0.6         # intra-party spread that forms wings (below schism trigger)
FACTION_MIN_SIZE = 3             # wings smaller than this dissolve back
FACTION_REBEL_DIST = 0.5         # centroid-bill distance where a wing whips its own line
SECESSION_DIST = 0.8             # centroid-platform distance feeding estrangement
SECESSION_WEEKS = 6              # consecutive estranged weeks before the wing walks
FACTION_LEADER_BONUS = 0.2       # leadership-challenge edge for faction leaders

# --- player / career ---
ACTIONS_PER_WEEK = 2
DOSSIER_EXPEL_THRESHOLD = 1.0    # hidden scandal total that forces expulsion
LEADERSHIP_COHESION_MIN = 0.45   # leader challengeable below this cohesion
CHALLENGE_AMBITION_MIN = 0.6     # challengers need this much combined ambition

# --- drift ---
VOTER_DRIFT_SD = 0.004           # weekly position noise
BRAND_DECAY = 0.98               # weekly brand multiplier
REL_DECAY = 0.97                 # relationships decay toward neutral
