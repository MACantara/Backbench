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
    portfolio: str | None = None
    dossier: float = 0.0            # hidden scandal material
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
class Party:
    id: int
    name: str
    platform: Vec
    brand: float = 0.0              # public reputation, decays
    members: set[int] = field(default_factory=set)
    leader: int | None = None
    cohesion: float = 1.0           # derived: mean member-platform alignment
    schism_cooldown: int = 0


@dataclass
class Bill:
    pos: Vec
    beneficiary_axis: int           # 0 or 1 — which voter axis it flatters
    cost: float = 0.0
    confidence: bool = False        # a confidence motion — govt parties whip to survive


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
