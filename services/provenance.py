"""
Cite-or-skip enforcement — skip-only mode.

Every value that flows into a Claude prompt must pass through build_context().
Missing facts are silently omitted from the context; Claude is instructed not
to mention any topic that is absent. No placeholders are ever injected.
"""

from typing import Any, Dict

# All known agency facts. Each entry is included in the context when present,
# silently omitted when blank or None. Claude never receives a placeholder.
ALL_FACTS: Dict[str, str] = {
    "agency_name": "agency name",
    "annual_ridership": "annual ridership",
    "fleet_size": "fleet size (number of vehicles)",
    "staff_count": "number of staff",
    "service_area": "service area description",
    "project_description": "project description",
    "prior_grants": "prior federal grants received",
    "budget_match": "available local match / budget",
}


def _is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def build_context(profile: Dict[str, Any]) -> Dict[str, str]:
    """Return a context dict containing only the facts the agency provided.

    - Present and non-blank → included as a string.
    - Absent / None / blank → key is omitted entirely.

    The returned dict contains no None values and no placeholders.
    """
    context: Dict[str, str] = {}

    for key in ALL_FACTS:
        raw: Any = profile.get(key)
        if not _is_blank(raw):
            context[key] = str(raw).strip()

    # Pass through remaining profile keys (routing keys: area_type, state, etc.)
    for key, value in profile.items():
        if key not in ALL_FACTS and not _is_blank(value):
            context[key] = str(value)

    return context


def list_missing_facts(context: Dict[str, str]) -> list:
    """Return human-readable labels for ALL_FACTS keys absent from the context."""
    return [label for key, label in ALL_FACTS.items() if key not in context]
