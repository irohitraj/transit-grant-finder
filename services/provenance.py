"""
Cite-or-skip enforcement.

Every value that flows into a Claude prompt must pass through build_context().

REQUIRED_FACTS: missing values become [AGENCY TO PROVIDE: ...] placeholders —
the draft must still reference these facts, so Claude needs to hold the spot.

OPTIONAL_FACTS: supplementary fields that enrich the narrative when present but
are deliberately omitted from the context (and therefore the draft) when left
blank. Claude is told not to mention topics that aren't in the context.
"""

from typing import Any, Dict

# Core facts — always appear in the context.
# If missing, a [AGENCY TO PROVIDE: ...] placeholder is injected so the draft
# keeps a slot for the agency to fill in before submission.
REQUIRED_FACTS: Dict[str, str] = {
    "agency_name": "agency name",
    "annual_ridership": "annual ridership",
    "fleet_size": "fleet size (number of vehicles)",
    "staff_count": "number of staff",
    "service_area": "service area description",
    "project_description": "project description",
}

# Supplementary facts — included in the context only when the user provided them.
# When absent, the key is simply left out of the context dict entirely so Claude
# does not reference or invent these topics in the narrative.
OPTIONAL_FACTS: Dict[str, str] = {
    "prior_grants": "prior federal grants received",
    "budget_match": "available local match / budget",
}

PLACEHOLDER_TEMPLATE = "[AGENCY TO PROVIDE: {fact}]"


def _make_placeholder(fact_label: str) -> str:
    return PLACEHOLDER_TEMPLATE.format(fact=fact_label)


def _is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def build_context(profile: Dict[str, Any]) -> Dict[str, str]:
    """Return a context dict safe to pass to Claude.

    Required facts:
    - Present → passed through as string.
    - Absent / None / blank → replaced with [AGENCY TO PROVIDE: ...] placeholder.

    Optional facts:
    - Present → passed through as string.
    - Absent / None / blank → key is omitted entirely (no placeholder, no mention).

    All other profile keys (e.g. area_type, state) are passed through when
    non-None and silently dropped when None.

    The returned dict is guaranteed to contain no None values.
    """
    context: Dict[str, str] = {}

    for key, label in REQUIRED_FACTS.items():
        raw: Any = profile.get(key)
        if _is_blank(raw):
            context[key] = _make_placeholder(label)
        else:
            context[key] = str(raw).strip()

    for key in OPTIONAL_FACTS:
        raw = profile.get(key)
        if not _is_blank(raw):
            context[key] = str(raw).strip()
        # else: omit entirely — Claude should not mention this topic

    # Pass through remaining profile keys (routing / UI keys like area_type, state)
    all_managed = set(REQUIRED_FACTS) | set(OPTIONAL_FACTS)
    for key, value in profile.items():
        if key not in all_managed and not _is_blank(value):
            context[key] = str(value)

    return context


def has_placeholders(context: Dict[str, str]) -> bool:
    """Return True if any value in the context dict is a placeholder."""
    return any(v.startswith("[AGENCY TO PROVIDE:") for v in context.values())


def list_missing_facts(context: Dict[str, str]) -> list:
    """Return a list of human-readable fact labels that are still placeholders."""
    missing = []
    for key, label in REQUIRED_FACTS.items():
        value = context.get(key, "")
        if value.startswith("[AGENCY TO PROVIDE:"):
            missing.append(label)
    return missing
