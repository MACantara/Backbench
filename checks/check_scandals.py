"""Check: the scandal lifecycle — dirt, leaks, burn, resign, weather, expel."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sim import params as p
from sim.tick import tick
from sim.worldgen import new_game


def main() -> None:
    # latent: dirt grows on low-integrity MPs, clean MPs stay clean
    s = new_game(1)
    corrupt = min(s.mps.values(), key=lambda m: m.integrity)
    clean = max(s.mps.values(), key=lambda m: m.integrity)
    tick(s)
    assert corrupt.dossier > clean.dossier * 3, "growth should track (1-integrity)"

    # surfacing: a fat dossier eventually leaks into a burning scandal
    s = new_game(2)
    target = next(m for m in s.mps.values()
                  if m.id != s.player_id and s.parties[m.party].leader != m.id)
    target.dossier = 1.0
    target.integrity = 1.0  # isolate: no extra growth muddies the dossier
    broke = None
    for _ in range(60):
        tick(s)
        ev = next((e for e in s.log if e.type in ("ScandalBreaks", "Expelled")
                   and e.data.get("mp") == target.id), None)
        if ev:
            broke = ev
            break
    assert broke is not None, "dossier 1.0 never surfaced"
    if broke.type == "ScandalBreaks":
        assert target.scandal_weeks > 0, "break didn't start the burn"

    # burning: brand bleeds, the district turns, weeks count down
    s = new_game(3)
    mp = next(m for m in s.mps.values() if m.id != s.player_id)
    pt = s.parties[mp.party]
    mp.dossier, mp.scandal_weeks = 0.6, p.SCANDAL_WEEKS[1]
    brand0 = pt.brand
    bet0 = s.voters.betrayal[s.voters.district == mp.district].mean()
    wk0 = mp.scandal_weeks
    tick(s)
    assert pt.brand < brand0, "burning scandal didn't bleed the brand"
    bet1 = s.voters.betrayal[s.voters.district == mp.district].mean()
    assert bet1 > bet0, "burning scandal didn't sour the district"
    if mp.id in s.mps:
        assert mp.scandal_weeks < wk0, "burn didn't count down"

    # expulsion: leaders cut the dirtiest members outright
    s = new_game(4)
    dirty = next(m for m in s.mps.values()
                 if m.id != s.player_id and s.parties[m.party].leader != m.id)
    pid = dirty.party
    dirty.dossier = p.SACK_THRESHOLD + 0.5
    tick(s)
    ev = next((e for e in s.log if e.type == "Expelled"
               and e.data.get("mp") == dirty.id), None)
    assert ev, "dossier past SACK_THRESHOLD didn't trigger expulsion"
    assert dirty.id not in s.mps and dirty.id not in s.parties[pid].members
    assert not any(m.district == dirty.district for m in s.mps.values()), \
        "expulsion should leave a vacancy"

    # ministers get sacked when their scandal breaks
    s = new_game(5)
    minister = next(m for m in s.mps.values()
                    if m.id != s.player_id and s.parties[m.party].leader != m.id)
    minister.portfolio = "Finance"
    minister.dossier = 1.2
    for _ in range(60):
        tick(s)
        if any(e.type == "MinisterSacked" and e.data.get("mp") == minister.id
               for e in s.log):
            break
        if minister.id not in s.mps or minister.scandal_weeks:
            break
    sacked = any(e.type == "MinisterSacked" and e.data.get("mp") == minister.id
                 for e in s.log)
    assert sacked or minister.portfolio is None or minister.id not in s.mps, \
        "ministerial scandal left the minister in post"

    # resolution: burning ends in resignation (vacancy) or weathering (scar)
    s = new_game(6)
    resigned = weathered = 0
    burning = []
    for m in s.mps.values():
        if m.id == s.player_id:
            continue
        m.dossier, m.scandal_weeks = 1.0, p.SCANDAL_WEEKS[0]
        m.integrity = 1.0
        burning.append(m.id)
    for _ in range(p.SCANDAL_WEEKS[1] + 2):
        tick(s)
        if s.phase == "over":
            break
    for e in s.log:
        if e.data.get("mp") in burning:
            resigned += e.type == "Resigned"
            weathered += e.type == "ScandalWeathered"
    assert resigned + weathered >= len(burning) - 20, "burns left unresolved"
    assert resigned > 0 and weathered > 0, "expected both endings in 100 MPs"
    for e in s.log:
        if e.type == "ScandalWeathered":
            m = s.mps[e.data["mp"]]
            assert m.dossier < 1.0, "weathered scandal left no scar burn"
            break

    # election window: leaks cluster near an election (per-tick rates)
    in_win = out_win = in_ticks = out_ticks = 0
    for seed in range(6):
        s = new_game(seed + 20)
        for m in s.mps.values():
            m.dossier, m.integrity = 0.8, 1.0
        for _ in range(250):
            if s.phase == "over":
                break
            in_window = (s.phase == "campaign"
                         and s.weeks_to_election <= p.ELECTION_LEAK_WINDOW)
            before = sum(e.type == "ScandalBreaks" for e in s.log)
            tick(s)
            new = sum(e.type == "ScandalBreaks" for e in s.log) - before
            in_win += new * in_window
            out_win += new * (not in_window)
            in_ticks += in_window
            out_ticks += not in_window
    assert in_win > 0 and out_win > 0, "no leaks in one of the windows"
    rate_in, rate_out = in_win / in_ticks, out_win / out_ticks
    assert rate_in > rate_out * 1.5, \
        f"election window didn't amplify leaks ({rate_in:.4f} vs {rate_out:.4f})"

    # the player burns in the same lifecycle — no instant trapdoor
    s = new_game(7)
    me = s.mps[s.player_id]
    me.dossier, me.integrity = 0.8, 1.0
    tick(s)
    assert s.phase != "over", "moderate dossier shouldn't end the game"
    me2 = new_game(8)
    me2.mps[me2.player_id].dossier = p.SACK_THRESHOLD + 0.5
    tick(me2)
    assert me2.phase == "over", "dirty player should still be expellable"

    print(f"scandals ok: expel+sack+resign+weather all fire "
          f"(leak rate {rate_in:.4f}/wk near election vs {rate_out:.4f} otherwise)")


if __name__ == "__main__":
    main()
