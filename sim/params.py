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
INDEPENDENT_P = 0.10   # per-district chance a party-less local stands
INDEPENDENT_POS_SD = 0.35  # eccentric locals — near the centroid, never exactly on it

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
MINISTER_SACK_BRAND = 0.03     # brand hit the PM's party takes for a bad pick
SENIORITY_CAP_WEEKS = 1040     # seniority score saturates ~20y in office

# --- career ladder: standing ---
STANDING_WHIP_YES = 0.02       # credit for voting a whipped line
STANDING_WHIP_NO = 0.04        # rebelling a whipped vote costs more than loyalty earns
STANDING_SERVICE = 0.05        # constituency action — visible party service
STANDING_OFFICE = 0.01         # weekly trickle for holding office
STANDING_SACK_HIT = 0.3        # a sack burns standing
STANDING_SCANDAL_WK = 0.02     # standing bleed per burning scandal week
STANDING_DECAY = 0.98          # drift to neutral — rebels rehabilitate, favor fades
JUNIOR_POSTS = ("Whip", "Spokesperson", "Committee Chair")  # per-party bench posts
STANDING_W = 0.6               # appointment weight on earned standing
BACKING_W = 0.4                # appointment weight on the appointer's relationship
RUNG_W = 0.4                   # appointment weight on junior service
RUNG_CAP_WEEKS = 52            # a full term of bench service pays the rung
LEADERSHIP_STANDING_W = 0.3    # members back proven climbers in challenges

# --- voting in parliament ---
W_POLICY = 0.7     # weight on policy distance (higher = more ideological voting)
W_WHIP = 0.8       # weight on party whip instruction
W_REL = 0.4        # weight on relationship with the government/leader
W_SAFETY = 0.6     # weight on district opinion exposure (unsafe seats vote locally)
W_GOV = 0.35       # solidarity bonus for coalition MPs backing their own government's bill
VOTE_NOISE = 0.05  # per-MP ballot noise
MARGINAL_BAND = 0.15  # |u| under this reads as a swing vote in projections
ABSTAIN_MARGIN = 0.08  # |u| under this → abstain, torn between the whips
STANDING_WHIP_ABSTAIN = 0.02   # abstaining a whipped vote: half a rebel's price
DEAL_REL = 0.10                # counterparty credits you for the promise alone
DEAL_KEPT_REL = 0.15           # …and again when you keep it
DEAL_BROKEN_REL = 0.30         # a broken deal costs double what it banked
DEAL_STANDING = 0.05           # word-keeper standing — visible to the party
ATTEND_BASE = 0.05     # weekly absentee probability
ATTEND_LATE = 0.08     # added when the scheduled election looms
ATTEND_ELECTION_WEEKS = 8  # absenteeism ramps inside this of term end
ATTEND_SCANDAL = 0.10  # added while a scandal burns — the member lies low
ATTEND_AGE = 0.05      # added past RETIRE_AGE
ATTEND_SHOCK_P = 0.04  # some weeks the house is half-empty (flu, a boycott)
ATTEND_SHOCK = 0.45    # shared absence spike when the shock lands
REPEAL_P = 0.12        # weekly chance the government tables a repeal instead
REPEAL_BRAND_HIT = 0.04  # a dismantled law bleeds its authors' brand
SUNSET_WEEKS = 312     # statutes past ~6y may lapse — the book prunes itself
SUNSET_P = 0.03        # weekly lapse roll per aged statute
RETABLE_CD = 26        # weeks before a failed bill can return
RETABLE_P = 0.10       # weekly chance the agenda revives a cool-off failure
FAILED_MAX = 20        # the failed-bill registry is a shallow memory
QUORUM = 0.5           # fraction of the house that must be present to divide
BILL_PERSUASION = 0.008  # weekly electorate pull toward gov axis per passed bill
BUDGET_AXIS_W = 0.15    # agenda econ-axis → posture swing (market cuts, left spends)
BUDGET_DEBT_TIGHT = 0.10  # debt pressure tightens spend regardless of ideology
BUDGET_COST_SCALE = 0.08  # a stimulus posture reads as bill cost — fiscal term bites
SPEND_SERVICES_W = 0.01   # weekly services nudge per unit of over/under-spend
BUDGET_STANCES = {0: (1.00, 0.85),   # austerity — services starve, the books heal
                  1: (1.00, 1.00),   # balanced
                  2: (1.05, 1.15)}   # stimulus — spend now, pay later

# --- government ---
COALITION_MAX_DIST = 1.0         # partners won't join a coalition beyond this platform distance
COALITION_FREE_DIST = 0.35       # partners within this of the proposer join unpriced
CONCESSION_STEP = 0.15           # far partners extract platform shift ∝ distance past free
STANDING_CONCESSION = 0.3        # proposer's members pay standing per platform-distance sold
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

# --- courts ---
RISK_EXTREMITY_W = 0.6           # radical statutes invite review
RISK_COST_W      = 0.3           # expensive ones more so
RISK_MARGIN_W    = 0.2           # thin mandates are contestable
RISK_RESIDUAL    = 0.35          # uncovered radicalism still draws some review
ARTICLE_LIMIT    = 0.45          # default positional clause fence
ARTICLE_LIMIT_SD = 0.08          # per-clause jitter at worldgen
ARTICLE_MIRROR_P = 0.4           # odds a country guards its own pole too
ARTICLE_COST_CAP = 0.005         # fiscal clause: upkeep beyond this breaches
ARTICLE_MARGIN_FLOOR = 0.62      # mandate clause: thin ayes share breaches
CHALLENGE_RISK_MIN = 0.25        # a real clause breach must clear this
CHALLENGE_DIST   = 0.5           # opposition hostility needed to file
REVIEW_WEEKS     = 12            # a case sits pending a real interval
COURT_DOCKET_MAX = 2             # bench capacity — review stays rare
COURT_STRIKE_BASE  = 0.5         # risk an average court strikes at
COURT_ACTIVISM_W = 0.4           # doctrine swing per justice
BENCH_SIZE       = 7             # justices on the bench
BENCH_DIST_W     = 0.25          # ideology's weight in a justice's strike vote
JUDGE_APPOINT_AGE = (2184, 3016) # new justices arrive mid-career (42-58y)
APPOINT_POOL     = 3             # shortlist size for the player-PM
COURT_BRAND_HIT  = 0.04          # author brand bleed on a strike
AMEND_MAJORITY   = 2 / 3         # votes-cast share an amendment needs
AMEND_TABLE_P    = 0.35          # weekly chance a wounded government answers
AMEND_ENTRENCH_LIMIT = 0.45      # the fence a new clause draws
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
AUDIENCE_AFFINITY_SD = 0.5       # ideological sd of an outlet's audience/lean
POLL_HOUSE_BIAS    = 0.035       # max share tilt a sponsored poll can buy
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
DEBT_CRISIS = 1.8            # insolvency: DebtCrisis + forced confidence vote
DEBT_CRISIS_EVERY = 13       # while insolvent, crises recur on this cooldown
DEBT_BRAND_HIT = 0.15        # one-time brand drop for gov parties on crisis
AUSTERITY_POS = 0.7          # market-ward position of a forced cuts bill
AUSTERITY_SAVING = 0.02      # weekly net revenue a cuts bill returns
W_FISCAL = 0.6               # vote term weight on bill cost × debt pressure
W_SELFPRES = 0.5             # burning MPs distance from their own whip
AMEND_STEP = 0.25            # an amendment drags the pending bill toward the mover
ATTACK_P = 0.10              # base chance a scrutiny attack lands
ATTACK_WEAK_W = 0.5          # each point of government weakness scales it
ATTACK_BRAND = 0.04          # a landed attack dents every coalition party
ATTACK_STANDING = 0.1        # and the attacker's profile rises — party service
ATTACK_WHIFF = 0.05          # a flat attack costs the attacker's standing
DEFECT_BETRAYAL = 0.35       # crossing the floor — the district remembers
DEFECT_REL_HIT = 0.4         # old colleagues burn the bridge
FOUND_REL_MIN = 0.5          # only real loyalty walks out with a founder
COURT_WARMTH       = 0.15     # warmth a court action buys an outlet
WARMTH_DECAY       = 0.01     # weekly warmth fade — keep courting or be forgot
WARMTH_DRIFT       = 0.005    # organic warmth toward the party nearest the slant
WARMTH_DRIFT_CAP   = 0.4      # drift alone never buys what courting buys
COURT_FRIENDLY_MIN = 0.5      # warmth that counts as friendly for routed leaks
LEAK_COLD_BOOST    = 1.5      # a cold outlet leads the leak harder
LEAK_TRACE_P = 0.25          # a planted story can be traced back
FRIENDLY_TRACE_MULT = 0.5    # warm outlets protect their sources
HOSTILE_TRACE_MULT = 1.5     # cold outlets burn them
SNAP_POLL_STALE    = 3       # a snap call rides a poll this fresh, no older
LEAK_TRACE_REL = 0.3         # and the target burns the bridge
LEAK_CAUGHT_DIRT = 0.15      # traced leaking marks the player's own dossier

# --- drift ---
VOTER_DRIFT_SD = 0.004           # weekly position noise
SALIENCE_REVERT = 0.02           # weekly pull of salience back toward base
BRAND_DECAY = 0.95               # weekly brand multiplier — reputation mean-reverts
REL_DECAY = 0.97                 # relationships decay toward neutral

# --- cosmetic prose ---
PROSE_SEED_KEY = 0x5EED  # prose_rng fork — wording draws never touch state.rng

# --- ambitions ---
AMBITION_SURVIVOR_TERMS = 4    # hold your seat through this many elections
AMBITION_REFORMER_LAWS  = 3    # authored statutes on the book
AMBITION_SCORE          = 2    # score_terms entry a met arc banks
CONFIDENCE_WOUND_BRAND = 0.25   # constructive-confidence survival tax

# --- spectator bot ---
BOT_MARGINAL_SAFETY = 0.10   # seat_safety below this gets district defense
BOT_FREE_VOTE_DIST  = 0.6    # free votes: aye inside this ideological range
BOT_AMEND_DIST      = 0.5    # bills farther than this earn an amend
BOT_COURT_WARMTH    = 0.5    # court outlets colder than this
BOT_AUSTERITY_FLOOR = 0.1    # debt above this → austere budget
BOT_STIMULUS_MOOD   = -0.2   # national mood below this → stimulus
