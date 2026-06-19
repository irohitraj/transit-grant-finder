"""Tests for services/matcher.py — deterministic grant scoring and ranking."""

import pytest

from data.grants import GRANTS
from services.matcher import rank_grants, score_grant, MatchResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def rural_wa_ai_training():
    return {
        "area_type": "rural",
        "state": "WA",
        "project_type": "AI Training",
    }


def urban_tx_ai_pilot():
    return {
        "area_type": "urban",
        "state": "TX",
        "project_type": "AI Pilot",
    }


def empty_profile():
    return {
        "area_type": None,
        "state": None,
        "project_type": None,
    }


# ---------------------------------------------------------------------------
# score_grant — individual grant scoring
# ---------------------------------------------------------------------------

class TestScoreGrant:
    def test_score_is_in_valid_range(self):
        for grant in GRANTS:
            result = score_grant(rural_wa_ai_training(), grant)
            assert 0 <= result.score <= 100, (
                f"Score {result.score} out of range for {grant.id}"
            )

    def test_urban_agency_does_not_match_5311(self):
        grant_5311 = next(g for g in GRANTS if g.id == "5311_rtap")
        result = score_grant(urban_tx_ai_pilot(), grant_5311)
        assert result.score == 0
        assert result.disqualified is True

    def test_urban_agency_does_not_match_wa_consolidated(self):
        grant_wa = next(g for g in GRANTS if g.id == "wa_consolidated")
        result = score_grant(urban_tx_ai_pilot(), grant_wa)
        assert result.score == 0
        assert result.disqualified is True

    def test_5311_explicitly_says_not_eligible_for_non_rural(self):
        grant_5311 = next(g for g in GRANTS if g.id == "5311_rtap")
        result = score_grant(urban_tx_ai_pilot(), grant_5311)
        assert result.disqualified is True
        assert "not eligible" in result.disqualify_reason.lower()
        assert "50,000" in result.disqualify_reason

    def test_non_wa_agency_disqualified_from_wa_grant(self):
        grant_wa = next(g for g in GRANTS if g.id == "wa_consolidated")
        profile_non_wa = {"area_type": "rural", "state": "OR", "project_type": "AI Training"}
        result = score_grant(profile_non_wa, grant_wa)
        assert result.score == 0
        assert result.disqualified is True
        assert "not eligible" in result.disqualify_reason.lower()

    def test_national_grant_gives_state_bonus_to_any_state(self):
        grant_5312 = next(g for g in GRANTS if g.id == "5312_emi")
        for state in ["TX", "FL", "AK", "WA"]:
            profile = {"area_type": "urban", "state": state, "project_type": "AI Pilot"}
            result = score_grant(profile, grant_5312)
            reasons_text = " ".join(result.reasons)
            assert "national" in reasons_text.lower(), (
                f"Expected national program notice for state {state}"
            )

    def test_empty_profile_does_not_raise(self):
        for grant in GRANTS:
            result = score_grant(empty_profile(), grant)
            assert isinstance(result, MatchResult)
            assert 0 <= result.score <= 100

    def test_reasons_are_non_empty(self):
        for grant in GRANTS:
            result = score_grant(rural_wa_ai_training(), grant)
            assert len(result.reasons) > 0

    def test_full_match_wa_rural_ai_training(self):
        """Rural WA agency seeking AI Training should score highest on 5311."""
        grant_5311 = next(g for g in GRANTS if g.id == "5311_rtap")
        result = score_grant(rural_wa_ai_training(), grant_5311)
        assert result.score == 100


# ---------------------------------------------------------------------------
# rank_grants — ordering and stability
# ---------------------------------------------------------------------------

class TestRankGrants:
    def test_results_sorted_descending(self):
        results = rank_grants(rural_wa_ai_training())
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_returns_all_grants(self):
        results = rank_grants(rural_wa_ai_training())
        assert len(results) == len(GRANTS)

    def test_empty_profile_returns_valid_list(self):
        results = rank_grants(empty_profile())
        assert len(results) == len(GRANTS)
        for r in results:
            assert 0 <= r.score <= 100

    def test_5312_ranks_first_for_urban_ai_pilot(self):
        """5312/EMI is the only grant eligible for urban areas — should rank first."""
        results = rank_grants(urban_tx_ai_pilot())
        assert results[0].grant.id == "5312_emi"
