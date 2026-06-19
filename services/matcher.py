"""
Deterministic grant matching and ranking.

No LLM is used here. Scores are computed from the agency profile alone.
The scoring rubric is transparent and shown to the user as reason strings.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List

from data.grants import GRANTS, GrantProgram

# Score weights — must sum to 100 for full marks.
WEIGHT_AREA = 30
WEIGHT_STATE = 20
WEIGHT_PROJECT_TYPE = 30
WEIGHT_AI_FIT = 20

# Maps user-facing project type selections to grant fund_type values.
PROJECT_TYPE_TO_FUND_TYPES: Dict[str, List[str]] = {
    "AI Training": ["training", "technical_assistance", "operating"],
    "AI Pilot": ["demo", "research", "automation"],
    "Automation / Software": ["automation", "demand_response", "demo"],
    "Other": [],  # falls back to ai_fit score only
}

AI_FIT_SCORES: Dict[str, int] = {
    "high": WEIGHT_AI_FIT,
    "medium_high": int(WEIGHT_AI_FIT * 0.75),
    "medium": WEIGHT_AI_FIT // 2,
    "low": 0,
}


@dataclass
class MatchResult:
    grant: GrantProgram
    score: int
    reasons: List[str] = field(default_factory=list)
    disqualified: bool = False
    disqualify_reason: str = ""


def _check_eligibility(
    area_type: str, state: str, grant: GrantProgram
) -> tuple:
    """Return (disqualified: bool, reason: str).

    Hard disqualification fires when:
    - area_type is provided and not in the grant's eligible_areas, OR
    - state is provided and the grant is state-restricted and the state doesn't match.
    Both conditions are checked independently; either alone is enough to disqualify.
    """
    if area_type and area_type not in grant.eligible_areas:
        if grant.id == "5311_rtap":
            return True, (
                "Your agency is not eligible for this grant. "
                "Section 5311 is restricted to rural areas (under 50,000 population). "
                f"Your area type is {area_type.replace('_', '-')}."
            )
        return True, (
            f"Your agency is not eligible for this grant. "
            f"This program requires a service area type of "
            f"{' or '.join(grant.eligible_areas)} — your area type is "
            f"{area_type.replace('_', '-')}."
        )

    if state and grant.eligible_states and state not in grant.eligible_states:
        eligible = ", ".join(grant.eligible_states)
        return True, (
            f"Your agency is not eligible for this grant. "
            f"This program is only available in: {eligible}. "
            f"Your state is {state}."
        )

    return False, ""


def score_grant(profile: Dict[str, Any], grant: GrantProgram) -> MatchResult:
    """Score a single grant against the agency profile.

    Returns a MatchResult with score in [0, 100] and human-readable reasons.
    Hard eligibility failures (area type mismatch, state restriction) result in
    score=0 and disqualified=True — no partial credit is awarded.
    """
    area_type: str = (profile.get("area_type") or "").lower().replace("-", "_")
    state: str = (profile.get("state") or "").strip().upper()
    project_type: str = profile.get("project_type") or ""

    # Hard eligibility check — return immediately if disqualified
    disqualified, disqualify_reason = _check_eligibility(area_type, state, grant)
    if disqualified:
        return MatchResult(
            grant=grant,
            score=0,
            reasons=[disqualify_reason],
            disqualified=True,
            disqualify_reason=disqualify_reason,
        )

    score = 0
    reasons: List[str] = []

    # Area type match (+30)
    if area_type:
        score += WEIGHT_AREA
        reasons.append(
            f"Your service area type ({area_type.replace('_', '-')}) is eligible for this grant."
        )
    else:
        reasons.append("Area type not provided — area match not scored.")

    # State match (+20)
    if not grant.eligible_states:
        score += WEIGHT_STATE
        reasons.append("This is a national program available in all states.")
    elif state:
        # If we reached here, state already passed the eligibility check above
        score += WEIGHT_STATE
        reasons.append(f"Your state ({state}) is eligible for this grant.")
    else:
        reasons.append("State not provided — state match not scored.")

    # Project type match (+30)
    fund_types_for_project = PROJECT_TYPE_TO_FUND_TYPES.get(project_type, [])
    if fund_types_for_project:
        overlap = set(fund_types_for_project) & set(grant.fund_types)
        if overlap:
            score += WEIGHT_PROJECT_TYPE
            reasons.append(
                f"Your project type ({project_type}) aligns with this grant's "
                f"funded activities ({', '.join(sorted(overlap))})."
            )
        else:
            reasons.append(
                f"Your project type ({project_type}) does not directly align with "
                f"this grant's funded activities."
            )
    else:
        reasons.append("No project type selected — project match not scored.")

    # AI fit (+20)
    fit_score = AI_FIT_SCORES.get(grant.ai_fit, 0)
    score += fit_score
    fit_label = {
        "high": "strong",
        "medium_high": "medium-high",
        "medium": "moderate",
        "low": "limited",
    }.get(grant.ai_fit, grant.ai_fit)
    reasons.append(f"This grant has {fit_label} alignment with AI/technology projects.")

    return MatchResult(grant=grant, score=min(score, 100), reasons=reasons)


def rank_grants(profile: Dict[str, Any]) -> List[MatchResult]:
    """Score all grants against the profile and return them sorted highest-first.

    Stable sort: ties preserve the original GRANTS list order.
    Never raises — an empty or all-None profile returns a valid ranked list.
    """
    results = [score_grant(profile, grant) for grant in GRANTS]
    results.sort(key=lambda r: r.score, reverse=True)
    return results
