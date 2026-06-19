"""Tests for services/provenance.py — cite-or-skip placeholder enforcement."""

import pytest

from services.provenance import (
    OPTIONAL_FACTS,
    REQUIRED_FACTS,
    build_context,
    has_placeholders,
    list_missing_facts,
)


# ---------------------------------------------------------------------------
# build_context — None/empty → placeholder, real values → pass-through
# ---------------------------------------------------------------------------

class TestBuildContext:
    def test_no_none_values_in_output(self):
        profile = {k: None for k in REQUIRED_FACTS}
        context = build_context(profile)
        for key, value in context.items():
            assert value is not None, f"Key '{key}' has None value in output"

    def test_missing_key_becomes_placeholder(self):
        context = build_context({})
        for key in REQUIRED_FACTS:
            assert key in context
            assert context[key].startswith("[AGENCY TO PROVIDE:")

    def test_none_value_becomes_placeholder(self):
        context = build_context({"annual_ridership": None})
        assert context["annual_ridership"].startswith("[AGENCY TO PROVIDE:")

    def test_empty_string_becomes_placeholder(self):
        context = build_context({"annual_ridership": ""})
        assert context["annual_ridership"].startswith("[AGENCY TO PROVIDE:")

    def test_whitespace_only_becomes_placeholder(self):
        context = build_context({"annual_ridership": "   "})
        assert context["annual_ridership"].startswith("[AGENCY TO PROVIDE:")

    def test_real_value_passes_through_unchanged(self):
        context = build_context({"annual_ridership": "45,000"})
        assert context["annual_ridership"] == "45,000"

    def test_numeric_value_cast_to_string(self):
        context = build_context({"fleet_size": 12})
        assert context["fleet_size"] == "12"

    def test_extra_key_not_in_required_facts_passes_through(self):
        context = build_context({"area_type": "rural"})
        # area_type is not in REQUIRED_FACTS but should be included
        assert context.get("area_type") == "rural"

    def test_none_extra_key_is_silently_skipped(self):
        context = build_context({"area_type": None})
        assert "area_type" not in context

    def test_full_profile_has_no_placeholders(self):
        full_profile = {k: f"value for {k}" for k in REQUIRED_FACTS}
        context = build_context(full_profile)
        assert not has_placeholders(context)

    def test_placeholder_format_matches_expected_pattern(self):
        context = build_context({"annual_ridership": None})
        placeholder = context["annual_ridership"]
        assert placeholder == "[AGENCY TO PROVIDE: annual ridership]"


# ---------------------------------------------------------------------------
# has_placeholders / list_missing_facts
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_has_placeholders_true_when_missing(self):
        context = build_context({})
        assert has_placeholders(context) is True

    def test_has_placeholders_false_when_full(self):
        full_profile = {k: f"value for {k}" for k in REQUIRED_FACTS}
        context = build_context(full_profile)
        assert has_placeholders(context) is False

    def test_list_missing_facts_returns_correct_labels(self):
        profile = {k: None for k in REQUIRED_FACTS}
        context = build_context(profile)
        missing = list_missing_facts(context)
        assert set(missing) == set(REQUIRED_FACTS.values())

    def test_list_missing_facts_empty_when_full(self):
        full_profile = {k: f"value for {k}" for k in REQUIRED_FACTS}
        context = build_context(full_profile)
        assert list_missing_facts(context) == []

    def test_list_missing_facts_partial(self):
        profile = {k: None for k in REQUIRED_FACTS}
        profile["annual_ridership"] = "45,000"
        context = build_context(profile)
        missing = list_missing_facts(context)
        assert "annual ridership" not in missing
        assert len(missing) == len(REQUIRED_FACTS) - 1


# ---------------------------------------------------------------------------
# OPTIONAL_FACTS — omit when blank, include when present, never placeholder
# ---------------------------------------------------------------------------

class TestOptionalFacts:
    def test_optional_fact_omitted_when_none(self):
        context = build_context({"prior_grants": None})
        assert "prior_grants" not in context

    def test_optional_fact_omitted_when_empty_string(self):
        context = build_context({"prior_grants": ""})
        assert "prior_grants" not in context

    def test_optional_fact_omitted_when_whitespace(self):
        context = build_context({"budget_match": "   "})
        assert "budget_match" not in context

    def test_optional_fact_included_when_present(self):
        context = build_context({"prior_grants": "Section 5311, 2022"})
        assert context["prior_grants"] == "Section 5311, 2022"

    def test_optional_fact_never_becomes_placeholder(self):
        context = build_context({"prior_grants": None, "budget_match": None})
        for key in OPTIONAL_FACTS:
            assert key not in context or not context[key].startswith("[AGENCY TO PROVIDE:")

    def test_all_optional_facts_absent_produces_no_placeholders_for_them(self):
        profile = {k: None for k in OPTIONAL_FACTS}
        context = build_context(profile)
        for key in OPTIONAL_FACTS:
            assert key not in context

    def test_optional_facts_not_in_list_missing_facts(self):
        profile = {k: None for k in {**REQUIRED_FACTS, **OPTIONAL_FACTS}}
        context = build_context(profile)
        missing_labels = list_missing_facts(context)
        for label in OPTIONAL_FACTS.values():
            assert label not in missing_labels
