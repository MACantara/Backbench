# Agent Notes

Local politics sim in pure Python. No LLMs anywhere in the game logic — voters, MPs, parties are classical algorithms (spatial voting, utility functions, rule-based lifecycle).

## Rules that matter

- **`sim/` is a pure state machine.** No prints, no input(), no file I/O. Presentation lives in `driver/`. If you're tempted to print from sim code, emit an `Event` instead.
- **All tunable constants go in `sim/params.py`.** Never scatter magic numbers in logic — tuning this sim is the main development activity.
- **`tick(state, actions) -> list[Event]` is the contract.** Everything a week does happens through it. Drivers consume events; they don't reach into state mutation.
- **Deterministic by seed.** `GameState.rng` is the only randomness source (plus `np.random.default_rng` seeded from it). Don't call bare `random` or unseeded numpy.
- **Vote utility stays decomposed.** `parliament.py` computes named terms so `inspect.py` can explain outcomes. If you add a factor, add it as a named term — don't fold it into an opaque score.

## Verify

No test framework. Run the check for whatever you touched:

```bash
python checks/check_<area>.py     # worldgen|election|parliament|government|parties|player|careers|e2e
python checks/check_sweep.py      # 50-seed stability sweep — run after changing params.py weights
```

A check that passes tells you the subsystem works; a failing assert is the repro.

## Conventions

- Dataclasses for state (`state.py`), functions for behavior. No inheritance hierarchies.
- Events are typed records: `state.emit("TypeName", "human-readable text", **data)`.
- Keep it stdlib. NumPy is the only dependency and only where it's already used (voter math). No new deps without a reason.
- Small files, direct code. The design doc is `docs/spec.md` — if behavior diverges from it, that's a bug or a spec change, decide which.
