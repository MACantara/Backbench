"""Procedural names + ideology vocabulary. One source for every generated name:
party systems (cleavage-anchored archetypes), founded parties, bills, MPs."""
from __future__ import annotations

import random

import numpy as np

from . import params as p
from .state import Vec, dist

# --- ideology vocabulary ---
AXIS_LABELS = ("economic", "social")
POLE_LABELS = {0: ("redistribution", "market"), 1: ("libertarian", "authoritarian")}
_AXIS_WORDS = {0: {-1: "left", 1: "right"}, 1: {-1: "libertarian", 1: "traditional"}}


def describe_pos(pos: Vec) -> str:
    """A position in words: 'left', 'traditional', 'left-libertarian', 'centrist'."""
    words = [_AXIS_WORDS[ax][int(np.sign(pos[ax]))]
             for ax in (0, 1) if abs(pos[ax]) >= p.DESCRIBE_THRESHOLD]
    return "-".join(words) if words else "centrist"


# --- party archetypes (Manifesto Project families on Lipset-Rokkan cleavages) ---
CLEAVAGES = ("class", "church", "rural", "periphery")
ARCHETYPES: dict[str, dict] = {
    "social_democrat": {
        "anchor": (-0.65, -0.15), "cleavages": ("class",),
        "names": ["Labour", "Social Democrats", "Workers' Party",
                  "Union of Labour", "Socialist Party"],
    },
    "left_socialist": {
        "anchor": (-0.85, -0.40), "cleavages": ("class",),
        "names": ["Left Alliance", "Socialist Union", "People's Left",
                  "Unity List", "Workers' Alliance"],
    },
    "liberal": {
        "anchor": (0.35, -0.35), "cleavages": ("class", "church"),
        "names": ["Liberal Party", "Free Democrats", "Reform Party",
                  "Progress Alliance", "Civic Union"],
    },
    "conservative": {
        "anchor": (0.55, 0.35), "cleavages": ("class", "church"),
        "names": ["Conservative Party", "National Coalition", "People's Party",
                  "Union Party", "The Union"],
    },
    "christian_democrat": {
        "anchor": (0.10, 0.55), "cleavages": ("church",),
        "names": ["Christian Democrats", "Christian Union", "Centre Democrats",
                  "Covenant Party", "Moral Alliance"],
    },
    "agrarian": {
        "anchor": (-0.05, 0.30), "cleavages": ("rural",),
        "names": ["Farmers' Union", "Agrarian Party", "Centre Party",
                  "Rural Alliance", "Peasants' Party"],
    },
    "green": {
        "anchor": (-0.30, -0.65), "cleavages": ("rural",),
        "names": ["Green Alliance", "The Greens", "Ecology Party",
                  "Green League", "New Ecology"],
    },
    "nationalist": {
        "anchor": (0.40, 0.85), "cleavages": ("periphery",),
        "names": ["National Front", "Homeland Party", "Fatherland Union",
                  "National Alliance", "Sovereign Party"],
    },
    "regionalist": {
        "anchor": (-0.15, 0.60), "cleavages": ("periphery",),
        "names": ["Periphery Alliance", "Regional Party", "Provincial Voice",
                  "Frontier League", "Highland Union"],
    },
}
_ORDINALS = "Second Third Fourth Fifth Sixth Seventh".split()


def _weight(key: str, cleavage: dict[str, float]) -> float:
    return 0.2 + sum(cleavage[c] for c in ARCHETYPES[key]["cleavages"])


def _pick_name(pool: list[str], rng: random.Random, taken: set[str]) -> str:
    """An untaken name from the pool; numbered fallback when the pool is drained."""
    free = [n for n in pool if n not in taken]
    if free:
        name = rng.choice(free)
    else:
        base = rng.choice(pool)
        for ord_ in _ORDINALS:
            if f"{ord_} {base}" not in taken:
                name = f"{ord_} {base}"
                break
        else:
            name = f"New {base}"
    taken.add(name)
    return name


def generate_parties(rng: random.Random, np_rng: np.random.Generator) -> list[tuple[str, Vec]]:
    """A per-seed party system: cleavage salience → archetype draw → jittered
    platforms with separation → family names. Returns (name, platform) pairs."""
    n = rng.randint(*p.PARTY_COUNT_RANGE)
    cleavage = {c: rng.random() for c in CLEAVAGES}
    keys = list(ARCHETYPES)
    chosen: list[str] = []
    while len(chosen) < n:
        rest = [k for k in keys if k not in chosen]
        chosen.append(rng.choices(rest, weights=[_weight(k, cleavage) for k in rest])[0])

    # coverage: a viable system needs anchors on both flanks of the class axis
    flanks = {-1: [k for k in keys if ARCHETYPES[k]["anchor"][0] < -0.25],
              1: [k for k in keys if ARCHETYPES[k]["anchor"][0] > 0.25]}
    for sign in (-1, 1):
        if not any(ARCHETYPES[k]["anchor"][0] * sign > 0.25 for k in chosen):
            swap_in = max((k for k in flanks[sign] if k not in chosen),
                          key=lambda k: _weight(k, cleavage), default=None)
            if swap_in is not None:
                weakest = min(chosen, key=lambda k: _weight(k, cleavage))
                chosen[chosen.index(weakest)] = swap_in

    plats: list[Vec] = []
    kept: list[str] = []
    for k in chosen:
        anchor = np.asarray(ARCHETYPES[k]["anchor"])
        for _ in range(20):  # resample jitter until separated
            plat = tuple(np.clip(anchor + np_rng.normal(0, p.PARTY_PLATFORM_JITTER, 2), -1, 1))
            if all(dist(plat, q) >= p.PARTY_MIN_SEPARATION for q in plats):
                break
        else:
            continue  # too crowded — drop this archetype rather than overlap
        plats.append(plat)
        kept.append(k)

    taken: set[str] = set()
    return [(_pick_name(ARCHETYPES[k]["names"], rng, taken), plat)
            for k, plat in zip(kept, plats)]


def party_name_for(pos: Vec, rng: random.Random, taken: set[str]) -> str:
    """Ideology-flavored name for a new party: the archetype nearest its position."""
    nearest = min(ARCHETYPES, key=lambda k: dist(ARCHETYPES[k]["anchor"], pos))
    return _pick_name(ARCHETYPES[nearest]["names"], rng, taken)


# --- legislation ---
_BILL_NAMES = {
    (0, -1): ["Housing Regeneration Act", "Workers' Rights Act",
              "Public Health Expansion Act", "Living Wage Act",
              "Welfare Extension Act", "National Infrastructure Act"],
    (0, 1): ["Enterprise Tax Act", "Deregulation Act", "Competition Reform Act",
             "Trade Liberalisation Act", "Business Rates Act",
             "Private Investment Act"],
    (1, -1): ["Civil Liberties Act", "Privacy Protection Act",
              "Electoral Reform Act", "Freedom of Information Act",
              "Assembly Rights Act", "Secular Education Act"],
    (1, 1): ["Public Order Act", "Border Security Act", "Judicial Powers Act",
             "National Service Act", "Community Standards Act",
             "Sentencing Reform Act"],
}
_BILL_NEUTRAL = ["Administrative Reform Act", "Technical Measures Act",
                 "Consolidation Act", "Appropriations Act",
                 "Statutory Review Act"]


def bill_name(pos: Vec, axis: int, rng: random.Random) -> str:
    """A domain-flavored name from the bill's ideological address."""
    v = pos[axis]
    pool = _BILL_NEUTRAL if abs(v) < 0.2 else _BILL_NAMES[(axis, int(np.sign(v)))]
    return rng.choice(pool)


# --- people ---
_FIRST = ("Ash Brook Cole Dawn Elm Fern Gale Hale Iris Jade Kite Lark Moss Nell Onyx "
          "Pine Reed Sage Teal Wren Aspen Bay Cedar Cliff Dale Echo Flint Glen Harbor "
          "Isla Jasper Knox Linden Maple North Oakley Pearl Quinn River Stone Thorn "
          "Umber Vale Winter Yarrow Zephyr").split()
_LAST = ("Barton Croft Dale Ellis Frost Grange Holt Ingram Marsh North Pace Quill "
         "Rook Shore Vale West York Ashford Blackwood Calder Draper Ellery Fenwick "
         "Gresham Harlow Ives Judd Kerr Loxley Mercer Norwood Oswald Pember Rowan "
         "Stanton Thatcher Underwood Vance Whitfield Yardley").split()


def mp_name(rng: random.Random) -> str:
    """One MP name; ~5% get a composed double surname."""
    last = rng.choice(_LAST)
    if rng.random() < 0.05:
        last = f"{last}-{rng.choice(_LAST)}"
    return f"{rng.choice(_FIRST)} {last}"


def mp_names(rng: random.Random, n: int) -> list[str]:
    """n unique names — the composed-surname pool is large enough to not exhaust."""
    seen: set[str] = set()
    while len(seen) < n:
        seen.add(mp_name(rng))
    return list(seen)
