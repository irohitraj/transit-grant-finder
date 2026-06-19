"""
Claude API narrative drafter.

Calls the Anthropic API with a constrained prompt that enforces cite-or-skip.
The system prompt is cached via Anthropic prompt caching to reduce latency and
cost on repeated drafts within the same session.
"""

import os
from typing import Dict, Optional

import anthropic
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# System prompt — cached after the first API call in a session.
# Instructs Claude to act as a grant writer who never invents facts.
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are an expert grant writer helping small and rural public transit agencies.
Your job is to draft one narrative section for a federal or state transit grant application.

CRITICAL RULE — USE PROVIDED FACTS, NEVER INVENT:
Every specific fact you write must come directly from the agency context provided to you.
This means:
- If annual ridership, fleet size, staff count, budget, or any other figure is provided,
  you MUST weave those exact numbers into the narrative naturally and prominently.
- You must never invent, estimate, or assume a value that is not in the agency context.

If a piece of information is not present in the agency context:
- Do not mention that topic at all.
- Do not use a placeholder, bracket, or blank line for it.
- Do not allude to it or hint that it exists.
- Simply write a complete, coherent narrative using only the facts you have been given.

When facts ARE present, use them. Concrete numbers (ridership figures, fleet size, staff count,
budget amounts) strengthen a grant application — include every number you are given.

Write in a clear, professional tone appropriate for a federal grant application.
Use plain language — the reader may be a non-technical transit program officer.
Length: approximately 300–500 words.
Do not include a title or section heading — just the narrative body.
Do not use contingency language such as "if approved" or "we hope to".
Write as if the project is real and proceeding."""


def _build_user_message(context: Dict[str, str], grant_name: str) -> str:
    """Format the agency context dict and grant name into a prompt message."""
    lines = [
        f"Grant program: {grant_name}",
        "",
        "Agency information:",
    ]
    for key, value in context.items():
        label = key.replace("_", " ").title()
        lines.append(f"  {label}: {value}")
    lines += [
        "",
        "Please draft the project narrative section for this grant application.",
        "Use the agency information above. Preserve all [AGENCY TO PROVIDE: ...] "
        "placeholders exactly as written.",
    ]
    return "\n".join(lines)


def draft_narrative(
    context: Dict[str, str],
    grant_name: str,
    api_key: Optional[str] = None,
) -> Dict:
    """Call Claude to draft a grant narrative section.

    Args:
        context: Safe agency context dict from provenance.build_context().
                 Must contain no None values.
        grant_name: Human-readable name of the selected grant program.
        api_key: Optional override for the API key (used in tests).
                 Defaults to ANTHROPIC_API_KEY environment variable.

    Returns:
        A dict with:
          "narrative": str — the drafted narrative text
          "cache_hit": bool — True if the system prompt was served from cache
          "input_tokens": int
          "output_tokens": int
          "cache_read_tokens": int

    Raises:
        ValueError: If no API key is available.
        anthropic.APIError: On API-level failures (surfaced to the UI).
    """
    resolved_key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not resolved_key or resolved_key.strip() == "" or resolved_key == "your-api-key-here":
        raise ValueError(
            "ANTHROPIC_API_KEY is not set. "
            "Add your Anthropic API key to the .env file and restart the app."
        )

    client = anthropic.Anthropic(api_key=resolved_key)
    user_message = _build_user_message(context, grant_name)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {"role": "user", "content": user_message}
        ],
        temperature=0.3,
    )

    narrative = response.content[0].text
    usage = response.usage

    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0

    return {
        "narrative": narrative,
        "cache_hit": cache_read > 0,
        "input_tokens": getattr(usage, "input_tokens", 0),
        "output_tokens": getattr(usage, "output_tokens", 0),
        "cache_read_tokens": cache_read,
    }
