"""Tests for services/drafting.py — mocked Claude API calls."""

import pytest
from unittest.mock import MagicMock, patch

from services.drafting import draft_narrative, _build_user_message, SYSTEM_PROMPT
from services.provenance import build_context, ALL_FACTS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def full_context():
    return build_context({k: f"test value for {k}" for k in ALL_FACTS})


@pytest.fixture
def sparse_context():
    """Context with only a few facts — simulates a partially filled form."""
    return build_context({"agency_name": "Valley Transit", "fleet_size": "12"})


def _make_mock_response(text: str, cache_read: int = 0):
    """Build a mock anthropic.messages.create() response."""
    usage = MagicMock()
    usage.input_tokens = 200
    usage.output_tokens = 150
    usage.cache_read_input_tokens = cache_read

    content_block = MagicMock()
    content_block.text = text

    response = MagicMock()
    response.content = [content_block]
    response.usage = usage
    return response


# ---------------------------------------------------------------------------
# API key validation
# ---------------------------------------------------------------------------

class TestApiKeyValidation:
    def test_raises_value_error_when_key_missing(self, full_context, monkeypatch):
        # Remove the env var so the fallback path is also empty
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            draft_narrative(full_context, "Test Grant", api_key=None)

    def test_raises_value_error_when_key_empty(self, full_context, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            draft_narrative(full_context, "Test Grant", api_key="")

    def test_raises_value_error_when_key_is_placeholder(self, full_context):
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            draft_narrative(full_context, "Test Grant", api_key="your-api-key-here")


# ---------------------------------------------------------------------------
# Successful mock calls
# ---------------------------------------------------------------------------

class TestDraftNarrative:
    @patch("services.drafting.anthropic.Anthropic")
    def test_returns_non_empty_narrative(self, mock_anthropic_class, full_context):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_mock_response(
            "This is a test narrative."
        )
        mock_anthropic_class.return_value = mock_client

        result = draft_narrative(full_context, "Section 5311", api_key="fake-key")

        assert result["narrative"] == "This is a test narrative."
        assert isinstance(result["narrative"], str)
        assert len(result["narrative"]) > 0

    @patch("services.drafting.anthropic.Anthropic")
    def test_sparse_context_returns_non_empty_narrative(self, mock_anthropic_class, sparse_context):
        """Partial context (only a few facts) still produces a valid narrative."""
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_mock_response(
            "Valley Transit operates 12 vehicles to serve its rural community."
        )
        mock_anthropic_class.return_value = mock_client

        result = draft_narrative(sparse_context, "Section 5311", api_key="fake-key")

        assert "Valley Transit" in result["narrative"]
        assert "[AGENCY TO PROVIDE:" not in result["narrative"]

    @patch("services.drafting.anthropic.Anthropic")
    def test_cache_hit_detected(self, mock_anthropic_class, full_context):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_mock_response(
            "Narrative text.", cache_read=450
        )
        mock_anthropic_class.return_value = mock_client

        result = draft_narrative(full_context, "Section 5311", api_key="fake-key")

        assert result["cache_hit"] is True
        assert result["cache_read_tokens"] == 450

    @patch("services.drafting.anthropic.Anthropic")
    def test_cache_miss_detected(self, mock_anthropic_class, full_context):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_mock_response(
            "Narrative text.", cache_read=0
        )
        mock_anthropic_class.return_value = mock_client

        result = draft_narrative(full_context, "Section 5311", api_key="fake-key")

        assert result["cache_hit"] is False

    @patch("services.drafting.anthropic.Anthropic")
    def test_cache_control_block_is_present_in_request(self, mock_anthropic_class, full_context):
        """Confirm the system prompt is sent with cache_control: ephemeral."""
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_mock_response("ok")
        mock_anthropic_class.return_value = mock_client

        draft_narrative(full_context, "Section 5311", api_key="fake-key")

        call_kwargs = mock_client.messages.create.call_args.kwargs
        system_blocks = call_kwargs["system"]
        assert isinstance(system_blocks, list)
        assert len(system_blocks) == 1
        block = system_blocks[0]
        assert block["type"] == "text"
        assert block["text"] == SYSTEM_PROMPT
        assert block["cache_control"] == {"type": "ephemeral"}

    @patch("services.drafting.anthropic.Anthropic")
    def test_token_counts_returned(self, mock_anthropic_class, full_context):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_mock_response(
            "Narrative.", cache_read=0
        )
        mock_anthropic_class.return_value = mock_client

        result = draft_narrative(full_context, "Section 5311", api_key="fake-key")

        assert result["input_tokens"] == 200
        assert result["output_tokens"] == 150


# ---------------------------------------------------------------------------
# _build_user_message
# ---------------------------------------------------------------------------

class TestBuildUserMessage:
    def test_includes_grant_name(self):
        context = {"agency_name": "Valley Transit"}
        msg = _build_user_message(context, "Section 5311 + RTAP")
        assert "Section 5311 + RTAP" in msg

    def test_includes_all_context_keys(self):
        context = {"agency_name": "Valley Transit", "fleet_size": "12"}
        msg = _build_user_message(context, "Test Grant")
        assert "Valley Transit" in msg
        assert "12" in msg

    def test_placeholder_survives_in_message(self):
        context = {"annual_ridership": "[AGENCY TO PROVIDE: annual ridership]"}
        msg = _build_user_message(context, "Test Grant")
        assert "[AGENCY TO PROVIDE: annual ridership]" in msg
