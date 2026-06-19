"""
Transit Grant Finder & Narrative Drafter
A local-first Streamlit app for small and rural transit agencies.
"""

import html
import os
import re

import streamlit as st
from dotenv import load_dotenv

from services.matcher import rank_grants
from services.provenance import build_context, has_placeholders, list_missing_facts
from services.drafting import draft_narrative
from services.export import export_markdown, export_docx

load_dotenv()

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Transit Grant Finder",
    page_icon="🚌",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Theme-aware CSS
# Streamlit exposes CSS variables that flip automatically between light and
# dark mode — no JS detection needed. We use them to style the narrative box
# and highlight [AGENCY TO PROVIDE: ...] placeholders in amber.
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .narrative-box {
        background-color: var(--secondary-background-color);
        color: var(--text-color);
        padding: 1.25rem 1.5rem;
        border-radius: 8px;
        border: 1px solid rgba(128, 128, 128, 0.25);
        line-height: 1.75;
        font-size: 0.95rem;
        white-space: pre-wrap;
    }
    .narrative-box p {
        margin: 0 0 0.9em 0;
    }
    .narrative-box p:last-child {
        margin-bottom: 0;
    }
    /* Placeholder highlight — amber works in both light and dark themes */
    .narrative-box mark {
        background-color: #f5a623;
        color: #1a1a1a;
        border-radius: 3px;
        padding: 1px 4px;
        font-weight: 600;
        font-style: normal;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_narrative(text: str) -> None:
    """Render a narrative string in a theme-aware box with highlighted placeholders."""
    # Escape HTML first so Claude output can't inject markup
    safe = html.escape(text)
    # Highlight [AGENCY TO PROVIDE: ...] placeholders
    safe = re.sub(
        r"(\[AGENCY TO PROVIDE:[^\]]*\])",
        r"<mark>\1</mark>",
        safe,
    )
    # Convert paragraph breaks and single newlines to HTML
    paragraphs = safe.split("\n\n")
    inner = "".join(
        f"<p>{p.replace(chr(10), '<br>')}</p>"
        for p in paragraphs
        if p.strip()
    )
    st.markdown(f"<div class='narrative-box'>{inner}</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Session state helpers
# ---------------------------------------------------------------------------
STEPS = ["profile", "match", "draft", "export"]

if "step" not in st.session_state:
    st.session_state.step = "profile"
if "profile" not in st.session_state:
    st.session_state.profile = {}
if "selected_grant" not in st.session_state:
    st.session_state.selected_grant = None
if "narrative" not in st.session_state:
    st.session_state.narrative = None
if "draft_meta" not in st.session_state:
    st.session_state.draft_meta = {}


def go_to(step: str) -> None:
    st.session_state.step = step


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("Transit Grant Finder")
st.caption(
    "Helps small and rural transit agencies identify suitable grants and draft "
    "one narrative section. This tool stops at export — it never submits anything."
)

# API key check — show a warning banner but do not block browsing
api_key = os.getenv("ANTHROPIC_API_KEY", "")
if not api_key or api_key == "your-api-key-here":
    st.warning(
        "**Claude API key not configured.** "
        "Add your `ANTHROPIC_API_KEY` to the `.env` file and restart the app. "
        "Steps 1 and 2 work without it; Step 3 (narrative draft) requires it.",
        icon="⚠️",
    )

# ---------------------------------------------------------------------------
# Progress indicator
# ---------------------------------------------------------------------------
step_labels = ["1. Agency Profile", "2. Grant Match", "3. Draft Narrative", "4. Export"]
step_cols = st.columns(4)
step_keys = ["profile", "match", "draft", "export"]
for i, (col, label, key) in enumerate(zip(step_cols, step_labels, step_keys)):
    current = st.session_state.step == key
    col.markdown(
        f"**{label}**" if current else f"<span style='color:grey'>{label}</span>",
        unsafe_allow_html=True,
    )
st.divider()


# ===========================================================================
# STEP 1 — Agency Profile Form
# ===========================================================================
if st.session_state.step == "profile":
    st.subheader("Step 1 — Tell us about your agency")
    st.info(
        "Fill in what you know. Every field is optional — any field you leave blank "
        "will appear as a placeholder in the narrative draft for your team to complete.",
        icon="ℹ️",
    )

    with st.form("profile_form"):
        st.markdown("**Agency basics**")
        agency_name = st.text_input(
            "Agency name",
            placeholder="e.g. Valley Rural Transit",
        )
        col1, col2 = st.columns(2)
        with col1:
            state = st.selectbox(
                "State",
                options=[""] + sorted([
                    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
                    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
                    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
                    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
                    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
                ]),
                format_func=lambda x: "Select state..." if x == "" else x,
            )
        with col2:
            area_type = st.selectbox(
                "Service area type",
                options=["", "rural", "small_urban", "urban"],
                format_func=lambda x: "Select area type..." if x == "" else x.replace("_", "-"),
            )

        st.markdown("**Agency size**")
        col3, col4, col5 = st.columns(3)
        with col3:
            annual_ridership = st.text_input(
                "Annual ridership",
                placeholder="e.g. 45,000",
            )
        with col4:
            fleet_size = st.text_input(
                "Fleet size (vehicles)",
                placeholder="e.g. 12",
            )
        with col5:
            staff_count = st.text_input(
                "Number of staff",
                placeholder="e.g. 8",
            )

        st.markdown("**Project**")
        project_type = st.selectbox(
            "What type of project are you seeking funding for?",
            options=["", "AI Training", "AI Pilot", "Automation / Software", "Other"],
            format_func=lambda x: "Select project type..." if x == "" else x,
        )
        project_description = st.text_area(
            "Brief project description",
            placeholder=(
                "e.g. Implement AI-assisted scheduling software to improve on-demand "
                "service efficiency in our rural service area."
            ),
            height=100,
        )

        st.markdown("**Funding history & capacity**")
        prior_grants = st.text_input(
            "Prior federal grants received (if any)",
            placeholder="e.g. Section 5311 operating grant, 2022",
        )
        budget_match = st.text_input(
            "Estimated local match / budget available",
            placeholder="e.g. $50,000 local match available",
        )
        service_area = st.text_input(
            "Service area description",
            placeholder="e.g. Three rural counties in eastern Washington, ~2,400 sq miles",
        )

        submitted = st.form_submit_button("Find matching grants →", type="primary")

    if submitted:
        st.session_state.profile = {
            "agency_name": agency_name or None,
            "state": state or None,
            "area_type": area_type or None,
            "annual_ridership": annual_ridership or None,
            "fleet_size": fleet_size or None,
            "staff_count": staff_count or None,
            "project_type": project_type or None,
            "project_description": project_description or None,
            "prior_grants": prior_grants or None,
            "budget_match": budget_match or None,
            "service_area": service_area or None,
        }
        go_to("match")
        st.rerun()


# ===========================================================================
# STEP 2 — Grant Matching
# ===========================================================================
elif st.session_state.step == "match":
    profile = st.session_state.profile
    agency_display = profile.get("agency_name") or "Your agency"

    st.subheader("Step 2 — Grant matches for " + agency_display)
    st.markdown(
        "Grants are ranked by fit based on your area type, state, project type, "
        "and each program's alignment with AI and technology projects. "
        "Select one to draft a narrative section."
    )

    results = rank_grants(profile)

    selected_id = None
    for result in results:
        grant = result.grant
        score = result.score

        if result.disqualified:
            badge = "⛔ Not eligible"
        elif score >= 70:
            badge = "🟢 Strong match"
        elif score >= 40:
            badge = "🟡 Moderate match"
        else:
            badge = "🔴 Weak match"

        # Expand eligible grants; collapse disqualified ones
        with st.expander(
            f"{grant.name}  —  {badge}  ({score}/100)",
            expanded=(not result.disqualified and score >= 40),
        ):
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.markdown(f"**Administrator:** {grant.administrator}")
                st.markdown(f"**Federal share:** {grant.federal_share_pct}")
                st.markdown(f"**Eligible areas:** {', '.join(grant.eligible_areas)}")
                st.markdown(f"**Notes:** {grant.notes}")
                if result.disqualified:
                    st.error(result.disqualify_reason)
                else:
                    st.markdown("**Why this score:**")
                    for reason in result.reasons:
                        st.markdown(f"- {reason}")
            with col_b:
                if not result.disqualified:
                    if st.button("Select this grant", key=f"select_{grant.id}"):
                        st.session_state.selected_grant = grant
                        go_to("draft")
                        st.rerun()

    st.divider()
    if st.button("← Back to profile"):
        go_to("profile")
        st.rerun()


# ===========================================================================
# STEP 3 — Narrative Draft
# ===========================================================================
elif st.session_state.step == "draft":
    grant = st.session_state.selected_grant
    profile = st.session_state.profile

    st.subheader(f"Step 3 — Draft narrative for {grant.name}")

    # Build safe context and show any missing facts
    context = build_context(profile)
    missing = list_missing_facts(context)

    if missing:
        st.warning(
            f"**{len(missing)} field(s) not provided.** "
            "The draft will include placeholders for these — your team will need to fill them in:\n\n"
            + "\n".join(f"- {fact}" for fact in missing),
            icon="📝",
        )
    else:
        st.success("All agency facts are available. The draft will use your real data.", icon="✅")

    # Show existing draft or generate
    if st.session_state.narrative:
        st.markdown("### Draft narrative")
        render_narrative(st.session_state.narrative)

        if st.session_state.draft_meta.get("cache_hit"):
            st.caption("⚡ System prompt served from cache — faster response.")

        col_regen, col_next = st.columns([1, 1])
        with col_regen:
            if st.button("↺ Regenerate draft"):
                st.session_state.narrative = None
                st.rerun()
        with col_next:
            if st.button("Continue to export →", type="primary"):
                go_to("export")
                st.rerun()

    else:
        st.markdown(
            "Click **Generate draft** to call Claude. "
            "The narrative will use your agency information above and never invent facts."
        )
        col_gen, col_back = st.columns([1, 1])
        with col_gen:
            generate = st.button("Generate draft", type="primary")
        with col_back:
            if st.button("← Back to grant list"):
                go_to("match")
                st.rerun()

        if generate:
            with st.spinner("Drafting narrative…"):
                try:
                    result = draft_narrative(context, grant.name)
                    st.session_state.narrative = result["narrative"]
                    st.session_state.draft_meta = result
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
                except Exception as exc:
                    st.error(f"API error: {exc}")


# ===========================================================================
# STEP 4 — Export
# ===========================================================================
elif st.session_state.step == "export":
    grant = st.session_state.selected_grant
    profile = st.session_state.profile
    narrative = st.session_state.narrative

    agency_name = profile.get("agency_name") or "[AGENCY TO PROVIDE: agency name]"

    st.subheader("Step 4 — Export your draft")
    st.success(
        "Your draft is ready to download. Review it carefully and fill in all "
        "`[AGENCY TO PROVIDE: ...]` placeholders before using it in an application.",
        icon="✅",
    )

    st.markdown("### Draft preview")
    render_narrative(narrative)

    st.divider()
    st.markdown("### Download")

    col_md, col_docx = st.columns(2)

    with col_md:
        md_bytes = export_markdown(narrative, grant.name, agency_name)
        st.download_button(
            label="Download as Markdown (.md)",
            data=md_bytes,
            file_name="grant_narrative_draft.md",
            mime="text/markdown",
        )

    with col_docx:
        docx_bytes = export_docx(narrative, grant.name, agency_name)
        st.download_button(
            label="Download as Word (.docx)",
            data=docx_bytes,
            file_name="grant_narrative_draft.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    st.caption(
        "This tool stops here. Nothing has been submitted. "
        "All exports are local — no data leaves your machine except the Claude API call."
    )

    st.divider()
    col_back, col_restart = st.columns([1, 1])
    with col_back:
        if st.button("← Back to draft"):
            go_to("draft")
            st.rerun()
    with col_restart:
        if st.button("Start over"):
            for key in ["step", "profile", "selected_grant", "narrative", "draft_meta"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
