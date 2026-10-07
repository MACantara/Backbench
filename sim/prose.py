"""Cosmetic wording. Every template draw rides state.prose_rng — the
mechanical stream (state.rng) is untouched, so changing a pool can never
move an election. Call sites hand in slots; wording is all this owns."""
from __future__ import annotations

POOLS: dict[str, list[str]] = {
    "LawEnacted": [
        "{name} becomes law{eff} ({cost_str}){contested}.",
        "Parliament enacts {name}{eff} ({cost_str}){contested}.",
        "{name} passes into law{eff} ({cost_str}){contested}.",
        "The statute book gains {name}{eff} ({cost_str}){contested}.",
    ],
    "VoteResultPass": [
        "{label} passes {yes}-{no} ({abstain} abstain).",
        "{label} carried, {yes} to {no} ({abstain} abstaining).",
        "The house votes {yes}-{no} — {label} passes ({abstain} abstain).",
        "{label} goes through: {yes} aye, {no} no, {abstain} abstain.",
    ],
    "VoteResultFail": [
        "{label} fails {yes}-{no} ({abstain} abstain).{short}",
        "{label} is defeated {yes}-{no} ({abstain} abstain).{short}",
        "The house votes {yes}-{no} — {label} falls ({abstain} abstain).{short}",
        "{label} goes down, {yes} to {no} ({abstain} abstaining).{short}",
    ],
    "CoalitionFormed": [
        "{names} form a government ({bloc} seats).",
        "A coalition takes shape: {names} ({bloc} seats).",
        "{names} strike a coalition deal — {bloc} seats.",
        "After the horse-trading: {names} govern ({bloc} seats).",
    ],
    "MinorityFormed": [
        "{name} forms a minority government ({seats} seats).",
        "{name} governs alone, short of a majority ({seats} seats).",
        "No coalition deal — {name} tries minority rule ({seats} seats).",
        "{name} takes office on sufferance ({seats} seats).",
    ],
    "Headline": [
        '{outlet} leads with "{text}"',
        '{outlet} runs "{text}" above the fold.',
        'Front page of {outlet}: "{text}"',
        '{outlet} splashes: "{text}"',
    ],
    "ElectionResult": [
        "Election resolved.",
        "The count is in — {country} has voted.",
        "Election night in {country}: every district declared.",
        "{country} goes to the polls; the returns are complete.",
    ],
    "ScandalBreaks": [
        "Scandal breaks around {name} ({sev}).",
        "{name}'s scandal surfaces ({sev}).",
        "The {name} scandal breaks ({sev}).",
        "{name} is engulfed by scandal ({sev}).",
    ],
}


def render(state, kind: str, **slots) -> str:
    """One wording for an emit site. Pool choice is cosmetic-only."""
    return state.prose_rng.choice(POOLS[kind]).format(**slots)
