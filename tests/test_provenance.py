"""Tests for services/provenance.py — cite-or-skip (skip-only) enforcement."""

import pytest

from services.provenance import (
    ALL_FACTS,
    build_context,
    list_missing_facts,
)


# ---------------------------------------------------------------------------
# build_context — present facts included, blank/None facts omitted
# ---------------------------------------------------------------------------

class TestBuildContext:
    def test_no_none_values_in_output(self):
        profile = {k: None for k in ALL_FACTS}
        context = build_context(profile)
        for key, value in context.items():
            assert value is not None, f"Key '{key}' has None value in output"

    def test_missing_key_is_omitted(self):
        context = build_context({})
        for key in ALL_FACTS:
            assert key not in context

    def test_none_value_is_omitted(self):
        context = build_context({"annual_ridership": None})
        assert "annual_ridership" not in context

    def test_empty_string_is_omitted(self):
        context = build_context({"annual_ridership": ""})
        assert "annual_ridership" not in context

    def test_whitespace_only_is_omitted(self):
        context = build_context({"annual_ridership": "   "})
        assert "annual_ridership" not in context

    def test_real_value_passes_through_unchanged(self):
        context = build_context({"annual_ridership": "45,000"})
        assert context["annual_ridership"] == "45,000"

    def test_numeric_value_cast_to_string(self):
        context = build_context({"fleet_size": 12})
        assert context["fleet_size"] == "12"

    def test_extra_routing_key_included_when_present(self):
        context = build_context({"area_type": "rural"})
        assert context.get("area_type") == "rural"

    def test_none_routing_key_omitted(self):
        context = build_context({"area_type": None})
        assert "area_type" not in context

    def test_no_placeholders_ever_produced(self):
        profile = {k: None for k in ALL_FACTS}
        context = build_context(profile)
        for value in context.values():
            assert "[AGENCY TO PROVIDE:" not in value

    def test_all_blank_profile_returns_empty_context(self):
        profile = {k: None for k in ALL_FACTS}
        context = build_context(profile)
        # Only non-ALL_FACTS keys from the profile could appear; none here
        assert all(k not in context for k in ALL_FACTS)

    def test_full_profile_returns_all_facts(self):
        full_profile = {k: f"value for {k}" for k in ALL_FACTS}
        context = build_context(full_profile)
        for key in ALL_FACTS:
            assert key in context
            assert context[key] == f"value for {key}"


# ---------------------------------------------------------------------------
# list_missing_facts — reports what was omitted
# ---------------------------------------------------------------------------

class TestListMissingFacts:
    def test_all_missing_when_empty_profile(self):
        context = build_context({})
        missing = list_missing_facts(context)
        assert set(missing) == set(ALL_FACTS.values())

    def test_none_missing_when_full_profile(self):
        full_profile = {k: f"value for {k}" for k in ALL_FACTS}
        context = build_context(full_profile)
        assert list_missing_facts(context) == []

    def test_partial_missing(self):
        profile = {k: None for k in ALL_FACTS}
        profile["annual_ridership"] = "45,000"
        context = build_context(profile)
        missing = list_missing_facts(context)
        assert "annual ridership" not in missing
        assert len(missing) == len(ALL_FACTS) - 1

    def test_prior_grants_and_budget_match_reported_when_absent(self):
        context = build_context({})
        missing = list_missing_facts(context)
        assert "prior federal grants received" in missing
        assert "available local match / budget" in missing
