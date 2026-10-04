"""Core state schema. No I/O, no prints — the sim is a pure state machine."""
from __future__ import annotations

import random
from dataclasses import dataclass, field

import numpy as np

Vec = tuple[float, float]


def dist(a: Vec, b: Vec) -> float:
    return float(np.hypot(a[0] - b[0], a[1] - b[1]))


@dataclass
class Voters:
    pos: np.ndarray        # (N, 2) ideology
    turnout: np.ndarray    # (N,) propensity 0..1
    loyalty: np.ndarray    # (N,) stickiness to last-voted party
    betrayal: np.ndarray   # (N,) accumulated broken-promise weight
    salience: np.ndarray   # (N, 2) per-axis attention weights
    district: np.ndarray   # (N,) int district id
    last_party: np.ndarray # (N,) int, -1 = none


@dataclass
class MP:
    id: int
    name: str
    pos: Vec
    ambition: float
    loyalty: float
    competence: float
    integrity: float
    district: int
    party: int | None = None
    faction: int | None = None    # Faction.id within their party, or None
    portfolio: str | None = None
    dossier: float = 0.0            # hidden scandal material
    scandal_weeks: int = 0          # weeks remaining of an active scandal; 0 = clean
    relationships: dict[int, float] = field(default_factory=dict)
    seat_safety: float = 0.5        # last margin, roughly
    age: int = 2600                 # weeks; 2600 = 50y
    seniority: int = 0              # weeks served in parliament


@dataclass
class Hopeful:
    """Aspiring politician below the minimum age — ages into candidacy."""
    name: str
    pos: Vec
    ambition: float
    loyalty: float
    competence: float
    integrity: float
    district: int                   # home district they'll stand in
    party: int                      # party leaning
    age: int                        # weeks


@dataclass
class Faction:
    """A detected ideological wing inside a party."""
    id: int
    name: str
    centroid: Vec
    members: set[int] = field(default_factory=set)
    leader: int | None = None       # highest-ambition member — heir-apparent slot
    estranged: int = 0              # consecutive weeks past secession distance


@dataclass
class Party:
    id: int
    name: str
    platform: Vec
    brand: float = 0.0              # public reputation, decays
    pub_pos: Vec | None = None      # media-constructed perceived position
    members: set[int] = field(default_factory=set)
    leader: int | None = None
    cohesion: float = 1.0           # derived: mean member-platform alignment
    schism_cooldown: int = 0
    founded_week: int = 0           # for the memberless-entrant grace window
    seated: bool = True             # False only for entrants born with no MPs
    factions: list[Faction] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.pub_pos is None:
            self.pub_pos = self.platform


@dataclass
class Grave:
    """A dissolved party remembered by name and platform — revivable for a while."""
    name: str
    platform: Vec
    died: int


@dataclass
class Outlet:
    """A media outlet: editorial slant, audience reach, story preferences."""
    id: int
    name: str
    slant: Vec
    reach: float
    sensationalism: float       # 0 policy broadsheet .. 1 scandal tabloid
    focus_axis: int             # the axis it harps on (agenda-setting)


@dataclass
class Bill:
    pos: Vec
    beneficiary_axis: int           # 0 or 1 — which voter axis it flatters
    cost: float = 0.0
    confidence: bool = False        # a confidence motion — govt parties whip to survive
    name: str = ""                  # domain-flavored name; confidence motions stay blank


@dataclass
class Law:
    """A passed bill in force: leaves a persistent mark on the country."""
    name: str
    pos: Vec
    beneficiary_axis: int
    cost: float
    passed_week: int
    margin: float                   # vote share margin it passed by
    effect: dict[str, float]        # weekly indicator nudges while in force


@dataclass
class Conditions:
    """The country's objective state — what retrospective voters judge."""
    growth: float = 0.0             # -1 contraction .. 1 boom
    unemployment: float = 0.5       # 0..1
    inflation: float = 0.3          # 0..1
    services: float = 0.5           # 0..1, public-service capacity (slow)
    crime: float = 0.3              # 0..1


@dataclass
class Treasury:
    """The public finances: one stock (debt); flows are derived weekly."""
    debt: float = 0.0               # cumulative deficit; floored at 0
    crisis_armed: bool = True       # hysteresis — re-arms when debt < DEBT_WARN


@dataclass
class Event:
    type: str                       # PollShift, VoteResult, Scandal, Defection, ...
    text: str
    data: dict = field(default_factory=dict)


@dataclass
class Government:
    parties: set[int] = field(default_factory=set)
    pm: int | None = None           # MP id
    minority: bool = False
    weeks_in_office: int = 0


@dataclass
class GameState:
    rng: random.Random
    week: int
    phase: str                      # campaign | election | formation | governing | over
    voters: Voters
    mps: dict[int, MP]
    parties: dict[int, Party]
    player_id: int
    hopefuls: list[Hopeful] = field(default_factory=list)
    outlets: list[Outlet] = field(default_factory=list)
    conditions: Conditions = field(default_factory=Conditions)
    laws: list[Law] = field(default_factory=list)  # registry of laws in force
    treasury: Treasury = field(default_factory=Treasury)
    graves: list[Grave] = field(default_factory=list)  # dissolved parties, revivable
    press_subject: int | None = None  # party id of last week's lead story
    press_weeks: int = 0              # consecutive weeks that subject has led
    government: Government = field(default_factory=Government)
    current_bill: Bill | None = None
    weeks_to_election: int = 0
    promises: list[dict] = field(default_factory=list)  # player commitments
    log: list[Event] = field(default_factory=list)
    score_terms: dict[str, int] = field(default_factory=lambda: {"mp": 0, "minister": 0, "pm": 0})
    legacy_bills: int = 0

    def emit(self, type_: str, text: str, **data) -> Event:
        e = Event(type_, text, {"week": self.week, **data})
        self.log.append(e)
        return e
