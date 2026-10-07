"""JSON save/load. No file I/O — drivers own saves/; this module is pure.

Refs that Python holds by identity are emitted as {"#law": n},
{"#article": n}, {"#bill": n} against tables built before encoding;
rehydration rebuilds tables first, then fixes refs, so
`deal.bill is state.current_bill` survives the round trip.

Only the table fields are hand-coded — everything else is a field-driven
walk over dataclasses.fields(), so new state fields serialize for free
(and are the reason format bumps die loudly rather than drift silently).
"""
from __future__ import annotations

import json
import random
from dataclasses import fields, is_dataclass

import numpy as np

from .state import (Ambition, Article, Bill, Conditions, CourtCase, Deal,
                    Event, Faction, GameState, Government, Grave, Hopeful,
                    Justice, Law, MP, Outlet, Party, Treasury, Voters)

FORMAT = 1

_TYPES = {c.__name__: c for c in
          (Voters, MP, Hopeful, Faction, Party, Grave, Outlet, Bill, Deal,
           Law, CourtCase, Article, Justice, Conditions, Treasury, Event,
           Government, GameState, Ambition)}


def _enc_body(obj, ctx: dict) -> dict:
    return {"$t": type(obj).__name__,
            **{f.name: _enc(getattr(obj, f.name), ctx) for f in fields(obj)}}


def _enc(v, ctx: dict):
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, np.generic):
        return v.item()
    if isinstance(v, np.ndarray):
        return {"$nd": str(v.dtype), "d": v.tolist()}
    if isinstance(v, random.Random):
        return {"$rng": [list(v.getstate()[1]), v.getstate()[2]]}
    if isinstance(v, Bill):
        return {"#bill": ctx["bills"][id(v)]}
    if isinstance(v, Law):
        i = ctx["laws"].get(id(v))
        return {"#law": i} if i is not None else _enc_body(v, ctx)
    if isinstance(v, Article):
        i = ctx["arts"].get(id(v))
        return {"#article": i} if i is not None else _enc_body(v, ctx)
    if is_dataclass(v):
        return _enc_body(v, ctx)
    if isinstance(v, set):
        return {"$set": [_enc(x, ctx) for x in sorted(v)]}
    if isinstance(v, tuple):
        return {"$tup": [_enc(x, ctx) for x in v]}
    if isinstance(v, list):
        return [_enc(x, ctx) for x in v]
    if isinstance(v, dict):
        if all(isinstance(k, str) for k in v):
            return {k: _enc(x, ctx) for k, x in v.items()}
        return {"$dict": [[_enc(k, ctx), _enc(x, ctx)] for k, x in v.items()]}
    raise TypeError(f"cannot serialize {type(v).__name__}")


def to_json(state: GameState) -> str:
    live, seen = [], set()

    def keep(b):
        if b is not None and id(b) not in seen:
            seen.add(id(b))
            live.append(b)

    keep(state.current_bill)
    keep(state.government.amend_move)
    for d in state.deals:
        keep(d.bill)
    ctx = {"bills": {id(b): i for i, b in enumerate(live)},
           "laws": {id(l): i for i, l in enumerate(state.laws)},
           "arts": {id(a): i for i, a in enumerate(state.constitution)}}
    body = {f.name: _enc(getattr(state, f.name), ctx) for f in fields(GameState)
            if f.name not in ("laws", "constitution")}
    body["laws"] = [_enc_body(l, ctx) for l in state.laws]
    body["constitution"] = [_enc_body(a, ctx) for a in state.constitution]
    out = {"format": FORMAT, "seed": state.seed, "week": state.week,
           "bills": [_enc_body(b, ctx) for b in live],
           "state": body}
    return json.dumps(out, sort_keys=True, separators=(",", ":"))


def _dec(v, ctx: dict):
    if isinstance(v, list):
        return [_dec(x, ctx) for x in v]
    if not isinstance(v, dict):
        return v
    if "$nd" in v:
        return np.asarray(v["d"], dtype=np.dtype(v["$nd"]))
    if "$rng" in v:
        r = random.Random()
        r.setstate((3, tuple(v["$rng"][0]), v["$rng"][1]))
        return r
    if "$set" in v:
        return {_dec(x, ctx) for x in v["$set"]}
    if "$tup" in v:
        return tuple(_dec(x, ctx) for x in v["$tup"])
    if "$dict" in v:
        return {_dec(k, ctx): _dec(x, ctx) for k, x in v["$dict"]}
    if "#law" in v:
        return ctx["laws"][v["#law"]]
    if "#article" in v:
        return ctx["arts"][v["#article"]]
    if "#bill" in v:
        return ctx["bills"][v["#bill"]]
    if "$t" in v:
        cls = _TYPES[v["$t"]]
        return cls(**{f.name: _dec(v[f.name], ctx) for f in fields(cls)
                      if f.name in v})
    return {k: _dec(x, ctx) for k, x in v.items()}


def from_json(text: str) -> GameState:
    j = json.loads(text)
    if j.get("format") != FORMAT:
        raise ValueError(
            f"save format {j.get('format')!r} — this build reads {FORMAT}")
    s = j["state"]
    ctx = {"laws": [], "arts": [], "bills": []}
    ctx["laws"] = [_dec(x, ctx) for x in s["laws"]]
    ctx["arts"] = [_dec(x, ctx) for x in s["constitution"]]
    ctx["bills"] = [_dec(x, ctx) for x in j["bills"]]
    s = dict(s, laws=ctx["laws"], constitution=ctx["arts"])
    return GameState(**{f.name: _dec(s[f.name], ctx) for f in fields(GameState)
                        if f.name in s})
