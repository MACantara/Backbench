"""Runnable check: a hung parliament hands the player a real negotiation —
offers enumerated, picks honored, declines punished, and AI pays the same price."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from sim.actions import Action, available_actions
from sim.state import dist
from sim.tick import tick
from sim.worldgen import new_game


def _at_offers(seed: int):
    """Run until the player's party sits in a viable slate — offers on the table."""
    s = new_game(seed)
    for _ in range(120):
        if s.phase == "over":
            return None
        tick(s)
        if s.offers:
            return s
    return None


def main() -> None:
    # find a seed where formation pauses on the player's leverage
    s = None
    for seed in range(30):
        s = _at_offers(seed)
        if s is not None:
            break
    assert s is not None, "no seed in 30 paused formation on the player"
    offers = list(s.offers)
    pid = s.mps[s.player_id].party
    assert s.phase == "formation", "the table didn't pause for the player's answer"
    assert len(offers) >= 1
    assert any(pid in o["coalition"] for o in offers), \
        "offers pause when the player's party isn't in any — pointless ceremony"
    assert "pick_offer" in available_actions(s) and "decline_offers" in available_actions(s)
    made = [e for e in s.log if e.type == "OfferMade"]
    assert len(made) == len(offers), "not every slate got surfaced"

    # picking a non-default slate seats that coalition
    alt = next((i for i, o in enumerate(offers)
                if o["proposer"] != offers[0]["proposer"]), None)
    assert alt is not None, "every offer had the same proposer — nothing to pick between"
    ev = tick(s, [Action("pick_offer", offer=alt)])
    assert s.phase == "governing"
    assert s.government.parties == offers[alt]["coalition"]
    assert s.government.pm == s.parties[offers[alt]["proposer"]].leader
    assert any(e.type == "OfferTaken" for e in ev)

    # declining all offers sits the player's party out — rival slate or minority
    s2 = None
    for seed in range(30):
        s2 = _at_offers(seed)
        if s2 is not None:
            break
    pid2 = s2.mps[s2.player_id].party
    ev = tick(s2, [Action("decline_offers")])
    assert s2.phase == "governing", "declining left parliament suspended"
    assert pid2 not in s2.government.parties, \
        "the player's party joined a government it declined"
    assert any(e.type == "OfferDeclined" for e in ev)

    # AI-vs-AI haggling: a far partner extracts a platform concession and the
    # negotiated agenda reflects it — not just a distance gate
    found_deal = checked_agenda = False
    for seed in range(20):
        s3 = new_game(seed)
        for _ in range(200):
            if s3.phase == "over":
                break
            tick(s3)
        deals = [e for e in s3.log if e.type == "CoalitionDeal"]
        found_deal |= bool(deals)
        # if the sitting government's own formation week had deals, the
        # agreement should be dragged off the plain coalition mean
        formed_week = s3.week - s3.government.weeks_in_office
        if (s3.government.platform is not None and not s3.government.minority
                and any(d.data.get("week") == formed_week for d in deals)):
            mean = tuple(np.mean([s3.parties[i].platform
                                  for i in s3.government.parties], axis=0))
            assert dist(s3.government.platform, mean) > 0.005, \
                "concessions paid but the agreement never moved"
            checked_agenda = True
            break
    assert found_deal, "no CoalitionDeal fired in 20 runs — joining is still free"
    assert checked_agenda, "deals fired but none belonged to a sitting government's formation"

    print("kingmaking ok: offers enumerated, picks honored, decline punished, "
          "AI pays the price")


if __name__ == "__main__":
    main()
