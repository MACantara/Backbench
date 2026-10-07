"""Terminal driver: print the week, take 2 actions, repeat. The dumb shell around the sim."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # cp1252 consoles

from sim import params as p_mod
from sim.actions import Action, available_actions, cost_of
from sim.career import final_score
from sim.inspect import (explain_action, explain_bench, explain_bill,
                         explain_mp, explain_vote)
from sim.persist import from_json, to_json
from sim.tick import tick
from sim.worldgen import new_game

SAVES = Path(__file__).resolve().parent.parent / "saves"


def _save(state) -> None:
    SAVES.mkdir(exist_ok=True)
    text = to_json(state)
    p = SAVES / f"s{state.seed}-w{state.week}.json"
    p.write_text(text, encoding="utf-8")
    (SAVES / "latest.json").write_text(text, encoding="utf-8")
    print(f"  saved -> {p}")


def _load():
    p = SAVES / "latest.json"
    if not p.exists():
        print("  no save found")
        return None
    st = from_json(p.read_text(encoding="utf-8"))
    print(f"  loaded week {st.week} [{st.phase}]")
    return st

INTERRUPTS = {"ConfidenceLost", "CoalitionFormed", "PartyFormed", "Defection",
              "PartyDissolved", "Scandal", "ElectionCalled", "ElectionResult", "SeatLost",
              "ScandalBreaks", "Expelled", "Resigned", "MinisterSacked",
              "PressCycle", "OfferMade", "OfferDeclined", "OfferLapsed",
              "LawRepealed", "LawLapsed", "PmChange", "BudgetSet",
              "AttackLands", "DebtCrisis", "AmbitionMet", "AmbitionFailed"}

AMBITION_KINDS = ("pm", "majority", "founder", "survivor", "reformer")


def _ask(prompt: str, ok) -> str | None:
    """Re-prompt until ok(input); None on EOF — the pick is abandoned."""
    try:
        while True:
            s = input(prompt).strip()
            if ok(s):
                return s
            print("?")
    except EOFError:
        return None


def prompt_actions(state) -> tuple[list[Action], "object | None"]:
    """Returns (picks, loaded_state) — a `load` abandons the pick and the
    caller swaps in the fresh state without ticking."""
    menu = available_actions(state)
    picks = []
    while True:
        spent = sum(cost_of(a.kind) for a in picks)
        left = p_mod.ACTION_POINTS - spent
        afford = [a for a in menu if cost_of(a) <= left]
        if not afford:
            break
        print(f"\nActions ({left} pts left):",
              ", ".join(f"{i}:{a}" + (f"·{cost_of(a)}" if cost_of(a) else "")
                        for i, a in enumerate(menu)),
              "| inspect <mp_id|bench> | why | save | load")
        try:
            raw = input("action > ").strip()
        except EOFError:
            return picks, None
        if raw == "save":
            _save(state)
            continue
        if raw == "load":
            st = _load()
            if st is not None:
                return [], st
            continue
        if raw == "why":
            print(explain_vote(state))
            continue
        if raw.startswith("inspect"):
            parts = raw.split()
            if len(parts) == 2 and parts[1] == "bench":
                print(explain_bench(state))
            elif len(parts) == 2 and parts[1].isdigit() and int(parts[1]) in state.mps:
                print(explain_mp(state, int(parts[1])))
            continue
        if raw.isdigit() and int(raw) < len(menu):
            kind = menu[int(raw)]
            if cost_of(kind) > left:
                print(f"  {kind} costs {cost_of(kind)} — {left} pts left")
                continue
            print(f"  {explain_action(state, kind)}")
            target = axis = vote = offer = law = judge = None
            article = entrench = outlet = None
            if kind in ("lobby", "dig_dirt", "deal", "leak"):
                s = _ask("target mp id > ",
                         lambda s: s.isdigit() and int(s) in state.mps
                         and (kind != "leak" or int(s) != state.player_id))
                if s is None:
                    continue
                target = int(s)
            if kind == "leak":
                me = state.mps[state.player_id]
                for o in state.outlets:
                    print(f"  {o.id}: {o.name} — warmth "
                          f"{o.warmth.get(me.party, 0.0):.2f} to your party")
                s = _ask("route through outlet id (blank = open market) > ",
                         lambda s: s == "" or (s.isdigit()
                                 and any(o.id == int(s) for o in state.outlets)))
                if s is None:
                    continue
                outlet = int(s) if s else None
            if kind == "court":
                from sim.naming import describe_pos
                me = state.mps[state.player_id]
                for o in state.outlets:
                    print(f"  {o.id}: {o.name} — {describe_pos(o.slant)}, "
                          f"warmth {o.warmth.get(me.party, 0.0):.2f}")
                s = _ask("outlet id > ",
                         lambda s: s.isdigit()
                         and any(o.id == int(s) for o in state.outlets))
                if s is None:
                    continue
                target = int(s)
            if kind == "defect":
                others = [f"{i}:{pt.name}" for i, pt in sorted(state.parties.items())
                          if i != state.mps[state.player_id].party]
                s = _ask(f"to ({' '.join(others)} | i=independent) > ",
                         lambda s: s == "i" or (s.isdigit() and int(s) in state.parties
                                                and int(s) != state.mps[state.player_id].party))
                if s is None:
                    continue
                target = None if s == "i" else int(s)
            if kind == "budget":
                s = _ask("posture 0=austerity 1=balanced 2=stimulus > ",
                         lambda s: s in ("0", "1", "2"))
                if s is None:
                    continue
                axis = int(s)
            if kind in ("speech", "promise", "table"):
                s = _ask("axis 0=economic 1=social > ", lambda s: s in ("0", "1"))
                if s is None:
                    continue
                axis = int(s)
            if kind in ("vote", "deal"):
                print(explain_bill(state))
                s = _ask("vote 1=aye -1=no 0=abstain > ", lambda s: s in ("1", "0", "-1"))
                if s is None:
                    continue
                vote = int(s)
            if kind == "appoint":
                from sim.naming import describe_pos
                for i, j in enumerate(state.bench_shortlist):
                    print(f"  {i}: {j.name} — {describe_pos(j.pos)}, "
                          f"activism {j.activism:.2f}, {j.age // 52}y")
                s = _ask("nominee # > ",
                         lambda s: s.isdigit() and int(s) < len(state.bench_shortlist))
                if s is None:
                    continue
                judge = int(s)
            if kind == "challenge":
                from sim.courts import challengeable, legal_risk
                laws = challengeable(state)
                for i, lw in enumerate(laws):
                    print(f"  {i}: {lw.name} (risk {legal_risk(state, lw):.2f})")
                s = _ask("law # > ",
                         lambda s: s.isdigit() and int(s) < len(laws))
                if s is None:
                    continue
                pick = laws[int(s)]
                law = next(i for i, lw in enumerate(state.laws) if lw is pick)
            if kind == "amendment":
                from sim.worldgen import _CLAUSES
                fenced = {(a.axis, a.pole) for a in state.constitution
                          if a.kind == "pos"}
                for a in state.constitution:
                    print(f"  r{a.id}: repeal {a.name}")
                for ax in (0, 1):
                    for pole in (-1, 1):
                        if (ax, pole) not in fenced:
                            side = "economic" if ax == 0 else "social"
                            print(f"  e{ax}{'+-'[pole > 0]}: entrench "
                                  f"{_CLAUSES[(ax, pole)]} ({side} pole)")
                s = _ask("clause > ",
                         lambda s: (s.startswith("r") and s[1:].isdigit()
                                    and any(a.id == int(s[1:]) for a in state.constitution))
                                   or (s.startswith("e") and len(s) == 3
                                       and s[1] in "01" and s[2] in "-+"
                                       and (int(s[1]), 1 if s[2] == "+" else -1)
                                           not in fenced))
                if s is None:
                    continue
                if s[0] == "r":
                    article = int(s[1:])
                else:
                    entrench = (int(s[1]), 1 if s[2] == "+" else -1)
            if kind == "pick_offer":
                for e in [e for e in state.log if e.type == "OfferMade"][-len(state.offers):]:
                    print(" ", e.text)
                s = _ask("offer # > ", lambda s: s.isdigit() and 1 <= int(s) <= len(state.offers))
                if s is None:
                    continue
                offer = int(s) - 1
            picks.append(Action(kind, target=target, axis=axis, vote=vote,
                                offer=offer, law=law, judge=judge,
                                article=article, entrench=entrench,
                                outlet=outlet))
        else:
            print("?")
    return picks, None


def show_poll(state) -> None:
    last = next((e for e in reversed(state.log) if e.type == "PollShift"), None)
    if last:
        oid = last.data.get("outlet")
        sponsor = next((o.name for o in state.outlets if o.id == oid), None)
        label = f"{sponsor} poll" if sponsor else "polls"
        shares = {state.parties[pid].name: f"{v:.0%}" for pid, v in last.data["shares"].items() if pid in state.parties}
        print(f"  {label}:", "  ".join(f"{k} {v}" for k, v in shares.items()))


def run(seed: int = 0, load: bool = False, scenario=None,
        spectate: bool = False) -> None:
    if load:
        state = _load()
        if state is None:
            return
    else:
        state = new_game(seed, scenario)
    tag = f" [{state.scenario}]" if state.scenario != "standard" else ""
    print(f"=== BACKBENCH - the Republic of {state.country} - seed {state.seed}{tag} ===")
    me = state.mps.get(state.player_id)
    print(f"You are {me.name}, MP for district {me.district}." if me
          else "Your career is already spent — spectating.")
    if not load and state.ambition is None:
        from sim.state import Ambition
        if spectate:
            from sim.bot import bot_pick_ambition
            state.ambition = Ambition(bot_pick_ambition(state))
            print(f"  bot declares: {state.ambition.kind}")
        else:
            s = _ask(f"ambition? {' | '.join(AMBITION_KINDS)} (blank = open career) > ",
                     lambda s: s == "" or s in AMBITION_KINDS)
            if s:
                state.ambition = Ambition(s)
    while state.phase != "over":
        print(f"\n-- Week {state.week} [{state.phase}] {'-' * 40}")
        show_poll(state)
        if spectate:
            from sim.bot import auto_actions
            actions, loaded = auto_actions(state), None
            print("  bot:", ", ".join(a.kind for a in actions))
        else:
            actions, loaded = prompt_actions(state)
        if loaded is not None:
            state = loaded
            continue
        events = tick(state, actions)
        echoes = [e for e in events if e.data.get("echo")]
        called = False
        for e in (e for e in events if not e.data.get("echo")):
            if e.type == "DistrictResult":
                if not called:
                    called = True
                    drs = [x for x in events if x.type == "DistrictResult"]
                    res = next((x for x in events if x.type == "ElectionResult"), None)
                    if res:
                        tally = sorted(res.data["seats"].items(),
                                       key=lambda kv: -kv[1])
                        prev = res.data.get("prev", {})
                        names = {pid: pt.name for pid, pt in state.parties.items()}
                        def _delta(p_, n_):
                            d = n_ - prev.get(p_, 0)
                            return f" ({'+' if d >= 0 else ''}{d})" if d else ""
                        print(f"   called {len(drs)}/{len(drs)} districts — "
                              + " · ".join(f"{names.get(p, p)} {n}{_delta(p, n)}"
                                          for p, n in tally))
                    flips = [x for x in drs if x.data["flipped"]]
                    if flips:
                        print("   flips:", "; ".join(x.text for x in flips[:8])
                              + (f"; +{len(flips) - 8} more" if len(flips) > 8 else ""))
                continue
            mark = "***" if e.type in INTERRUPTS else "   "
            print(f" {mark} {e.text}")
        if echoes:
            print("   you:", "; ".join(e.text[4].lower() + e.text[5:]
                                        if e.text.startswith("You ") else e.text
                                        for e in echoes))
    from sim.career import epilogue, score_breakdown, score_title
    score = final_score(state)
    print(f"\n=== Game over — {score_title(score)} (score {score}) ===")
    for line in epilogue(state):
        print(" ", line)
    print(explain_mp(state, state.player_id) if state.player_id in state.mps else "You are out of parliament.")
    print("\n  career record:")
    for lab, n, wt, pts in score_breakdown(state):
        print(f"    {lab:36} {n:>2} x{wt} = {pts:>3}")
    print(f"    {'total':36} {'':>5} = {score:>3}")
    from driver.fame import record_fame, same_run
    this = {"name": state.mps[state.player_id].name
            if state.player_id in state.mps else "the former member",
            "seed": state.seed, "week": state.week}
    print("\n  hall of fame:")
    for i, e in enumerate(record_fame(state)[:5]):
        you = " <- you" if same_run(e, this) else ""
        print(f"    {i+1}. {e['name']:<24} {e['score']:>3} {e['title']:<16}{you}")


if __name__ == "__main__":
    if "--load" in sys.argv:
        run(load=True, spectate="--spectate" in sys.argv)
    else:
        sc = sys.argv[sys.argv.index("--scenario") + 1] \
            if "--scenario" in sys.argv else None
        seed = next((a for a in sys.argv[1:]
                     if not a.startswith("-") and a != sc), None)
        run(int(seed) if seed else 0, scenario=sc,
            spectate="--spectate" in sys.argv)
