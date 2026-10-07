"""Procedural names + ideology vocabulary. One source for every generated name:
party systems (cleavage-anchored archetypes), founded parties, bills, MPs."""
from __future__ import annotations

import random

import numpy as np

from . import params as p
from .state import Vec, dist

# --- ideology vocabulary ---
# AXIS_LABELS/POLE_LABELS land now so the Phase 5 driver map can read them
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
    return p.ARCHETYPE_BASE_W + sum(cleavage[c] for c in ARCHETYPES[key]["cleavages"])


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
            name, i = f"New {base}", 2
            while name in taken:
                name, i = f"New {base} {i}", i + 1
    taken.add(name)
    return name


def revival_name(name: str, taken: set[str]) -> str | None:
    """The ordinal successor to a dead name ("Second X" → "Third X").
    None when the ladder is exhausted — the caller falls back to a fresh name."""
    first, _, rest = name.partition(" ")
    base = rest if first in _ORDINALS else name
    for ord_ in _ORDINALS:
        cand = f"{ord_} {base}"
        if cand not in taken:
            taken.add(cand)
            return cand
    return None


def generate_parties(rng: random.Random, np_rng: np.random.Generator,
                     party_pool: list[str] | None = None) -> list[tuple[str, Vec]]:
    """A per-seed party system: cleavage salience → archetype draw → jittered
    platforms with separation → family names. Returns (name, platform) pairs.
    party_pool pins the draw (scenario presets) — the seed still owns the
    platforms, the pool owns the cast."""
    keys = list(ARCHETYPES)
    cleavage = {c: rng.random() for c in CLEAVAGES}
    if party_pool:
        chosen = [k for k in party_pool if k in ARCHETYPES][:p.PARTY_COUNT_RANGE[1]]
    else:
        n = rng.randint(*p.PARTY_COUNT_RANGE)
        chosen = []
        while len(chosen) < n:
            rest = [k for k in keys if k not in chosen]
            chosen.append(rng.choices(rest, weights=[_weight(k, cleavage) for k in rest])[0])

    # coverage: a viable system needs anchors on both flanks of the class axis;
    # never evict the other flank's only representative. A pinned pool is
    # honored as-is — the scenario asked for this cast, lopsided or not.
    flanks = {-1: [k for k in keys if ARCHETYPES[k]["anchor"][0] < -p.PARTY_FLANK_EDGE],
              1: [k for k in keys if ARCHETYPES[k]["anchor"][0] > p.PARTY_FLANK_EDGE]}
    for _ in range(0 if party_pool else 4):
        missing = [s for s in (-1, 1)
                   if not any(ARCHETYPES[k]["anchor"][0] * s > p.PARTY_FLANK_EDGE for k in chosen)]
        if not missing:
            break
        sign = missing[0]
        swap_in = max((k for k in flanks[sign] if k not in chosen),
                      key=lambda k: _weight(k, cleavage), default=None)
        if swap_in is None:
            break
        other = {k for k in chosen if ARCHETYPES[k]["anchor"][0] * -sign > p.PARTY_FLANK_EDGE}
        victims = [k for k in chosen if k not in other]
        weakest = min(victims or chosen, key=lambda k: _weight(k, cleavage))
        chosen[chosen.index(weakest)] = swap_in

    plats: list[Vec] = []
    kept: list[str] = []
    queue = [k for k in keys if k not in chosen]  # replacements if an anchor can't place

    def _replacement(k: str):
        """Prefer a same-flank archetype so coverage survives a placement drop."""
        sign = np.sign(ARCHETYPES[k]["anchor"][0])
        for i, q in enumerate(queue):
            if np.sign(ARCHETYPES[q]["anchor"][0]) == sign:
                return queue.pop(i)
        return queue.pop(0) if queue else None

    for k in chosen:
        while k is not None:
            anchor = np.asarray(ARCHETYPES[k]["anchor"])
            # a flank rep must stay on its side of the axis — jitter can't
            # carry it across and void the coverage guarantee
            flank_sign = np.sign(anchor[0]) if abs(anchor[0]) > p.PARTY_FLANK_EDGE else 0.0
            for _ in range(p.PARTY_PLACE_TRIES):  # resample jitter until it fits
                plat = tuple(np.clip(anchor + np_rng.normal(0, p.PARTY_PLATFORM_JITTER, 2), -1, 1))
                if flank_sign and plat[0] * flank_sign <= 0:
                    continue
                if all(dist(plat, q) >= p.PARTY_MIN_SEPARATION for q in plats):
                    break
            else:
                k = _replacement(k)  # too crowded — try another archetype
                continue
            plats.append(plat)
            kept.append(k)
            break

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
_BILL_AUSTERITY = ["Public Finances Emergency Act", "Spending Restraint Act",
                   "Fiscal Consolidation Act", "Emergency Appropriations Act",
                   "Savings and Efficiencies Act"]


def bill_name(pos: Vec, axis: int, rng: random.Random) -> str:
    """A domain-flavored name from the bill's ideological address."""
    v = pos[axis]
    pool = _BILL_NEUTRAL if abs(v) < p.BILL_NEUTRAL_BAND \
        else _BILL_NAMES[(axis, int(np.sign(v)))]
    return rng.choice(pool)


def austerity_name(rng: random.Random) -> str:
    return rng.choice(_BILL_AUSTERITY)


# --- country ---
COUNTRIES = ("Aldermoor Brantfoss Carrow Dunverra Esthollow Fenmar Graymarch "
             "Halloway Islesmark Kestrel Langford Merrowgate Norwick Ostmere "
             "Pelham Quillbrook Ravenford Stonebridge Thornvale Uffmoor "
             "Verrenhall Wexley Yarrowgate Zellmark").split()


def country_name(rng: random.Random) -> str:
    return rng.choice(COUNTRIES)


# --- people ---
# regional packs: the seed picks one flavor and names keep to it
_FIRST = ("Ash Brook Cole Dawn Elm Fern Gale Hale Iris Jade Kite Lark Moss Nell Onyx "
          "Pine Reed Sage Teal Wren Aspen Bay Cedar Cliff Dale Echo Flint Glen Harbor "
          "Isla Jasper Knox Linden Maple North Oakley Pearl Quinn River Stone Thorn "
          "Umber Vale Winter Yarrow Zephyr").split()
_LAST = ("Barton Croft Dale Ellis Frost Grange Holt Ingram Marsh North Pace Quill "
         "Rook Shore Vale West York Ashford Blackwood Calder Draper Ellery Fenwick "
         "Gresham Harlow Ives Judd Kerr Loxley Mercer Norwood Oswald Pember Rowan "
         "Stanton Thatcher Underwood Vance Whitfield Yardley").split()
_FIRST_C = ("Aldo Bastien Cosima Dario Elio Fiore Gilda Hugo Ilsa Jonas Katia Leone "
            "Mirko Nadia Otto Pia Quirin Renata Silas Tessa Ulric Vera Willem Xenia "
            "Yves Zora Anton Beatrix Claude Delia Emile Freya Gustav Helga").split()
_LAST_C = ("Albinet Beaumont Castellan Delacroix Engel Fontaine Girard Hoffman "
           "Keller Lambert Moreau Navarro Orsini Petit Rousseau Sartre Thibault "
           "Verdi Wolff Zimmermann Ackermann Bonaventure Carre Dupont Esteve "
           "Faure Grimaldi Huber Ivaldi Laurent").split()
_FIRST_N = ("Ansgar Birgit Dag Einar Freya Gunnar Halvor Ingrid Jorunn Kjell Liv "
            "Magnus Nils Oddrun Peder Ragnhild Sigrun Torsten Ulf Vendla Yngve "
            "Astrid Bjorn Else Lars Mette Oskar Rune Sanna").split()
_LAST_N = ("Aasen Berglund Dahl Eklund Fjell Granberg Haug Iversen Jansen "
           "Knudsen Lindqvist Moe Nyberg Ostlund Pedersen Qvist Ronning "
           "Strandberg Thorvald Ullman Vik Wergeland Ytter Zetterberg").split()
NAME_PACKS = {"insular": (_FIRST, _LAST),
              "continental": (_FIRST_C, _LAST_C),
              "north": (_FIRST_N, _LAST_N)}


def mp_name(rng: random.Random, pack: str = "insular") -> str:
    """One MP name; ~5% get a composed double surname."""
    first, last_pool = NAME_PACKS.get(pack, NAME_PACKS["insular"])
    last = rng.choice(last_pool)
    if rng.random() < p.COMPOSED_SURNAME_P:
        last = f"{last}-{rng.choice(last_pool)}"
    return f"{rng.choice(first)} {last}"


def mp_names(rng: random.Random, n: int, pack: str = "insular") -> list[str]:
    """n unique names, insertion-ordered — set iteration order is hash-seeded
    per process, so a bare set would break cross-process determinism."""
    out, seen = [], set()
    while len(out) < n:
        name = mp_name(rng, pack)
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out
