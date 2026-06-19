# Transit Grant Finder — Notes

## What I Built

A four-step web application that helps small and rural transit agencies identify eligible grants and draft competitive narratives for AI/technology funding. The app guides users through:

1. **Agency Profile** — A form capturing required fields (agency name, state, service area type, project type, and agency size metrics) plus optional details (service area description, project description, prior grants, budget match).
2. **Grant Matching** — Deterministic scoring against 3 grant programs with transparent, per-reason explanations and hard eligibility disqualification.
3. **Narrative Drafting** — Claude-assisted draft generation with strict cite-or-skip enforcement.
4. **Export** — Download the draft as Markdown (.md) or Word (.docx).

### Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Frontend/Backend | Streamlit (Python) | Faster to ship than React for a single-developer prototype. No separate API server needed — the matcher, drafter, and export all live in the same process. |
| LLM | Anthropic Claude API | Mentioned in the brief. Used `claude-opus-4-5`/`claude-sonnet-4-6` with ephemeral prompt caching on the system prompt to reduce latency on repeated drafts. |
| Export | python-docx | Lightest path to a Word file; no server-side rendering needed. |
| Testing | pytest with mocked API | All Claude calls are mocked so tests run offline and deterministically. |
| Deployment | Streamlit Community Cloud | Public URL with zero infrastructure. Each user gets an isolated session — no user sees another's data. Nothing is persisted after the tab closes. |

### Why Not React / Supabase

The production stack (React + Supabase) is the right call for a multi-user product with persistent drafts and accounts. For a time-bound prototype demonstrating the core grant-finding and drafting flow, that stack would have consumed most of the available time on infrastructure rather than on the feature itself. Streamlit let me go from zero to a working, deployable app in a single session. .

---

## What I Cut (and Why)

| Feature | Why Cut |
|---------|---------|
| User authentication | The brief focuses on the core grant-finding flow, not account management. Session isolation is sufficient for a prototype. |
| Database persistence | Local-first approach: nothing is stored after the session ends. I had to "ship fast" hence avoided infra setup. |
| Multiple narrative sections | The brief asks for "one narrative section." Quality over quantity. |
| PDF export | Markdown and DOCX cover the immediate use case. DOCX can be converted to PDF by the agency. Adding PDF generation adds library complexity with no meaningful gain. |
| Real-time streaming | Claude's response streams but the UI waits for the full text. Streaming would improve perceived latency; |

---

## How I Used AI to Build It

### Tools

- **Cursor IDE with Claude Sonnet 4.6** — Used for real-time code generation throughout the session using prompts. Prompted to generate the full module structure (`matcher.py`, `drafting.py`, `export.py`, `provenance.py`) and the Streamlit UI in `app.py`.
- **ChatGPT** — Used for initial problem framing and understanding the grant-writing use case before writing any code.
- **Claude API** — Powers the narrative drafting feature itself.

### What Worked

1. **Module-first design:** Splitting the logic into `matcher.py`, `drafting.py`, `export.py`, and `provenance.py` before writing any of them kept `app.py` focused purely on UI flow and made each service independently testable.

2. **Test-first prompts for cite-or-skip:** Writing the provenance tests before the implementation forced a clean, well-defined contract for `build_context()`. The tests caught edge cases (whitespace-only strings, numeric values, routing keys) that would have been easy to miss.

3. **Prompt caching:** Using Anthropic's `ephemeral` cache control on the system prompt means repeated drafts within a session skip re-sending the ~300-token system prompt, reducing latency noticeably.

4. **Hardcoded grant data:** Three given grants (rural-only, state-restricted, and national) are enough to exercise every branch of the matching logic — area disqualification, state disqualification, scoring, and full eligibility.

### What Didn't Work (and How It Was Fixed)

1. **Narrative highlight false positives:** The first implementation of green highlights used plain substring matching, causing short words like "State" to match mid-word. Fixed with word-boundary regex for short values and a longest-match-first sort to prevent shorter substrings stealing matches from longer ones.

2. **Claude ignoring provided numbers:** Early system prompt versions listed "ridership numbers, fleet size, staff count" as things Claude must never invent. Claude over-applied this and avoided mentioning those topics even when the values were provided. Fixed by explicitly adding: *"When a fact IS provided, you MUST use it — concrete numbers strengthen a grant application."*

3. **System prompt cite-or-skip iterations:** Early versions produced occasional hallucinated facts. The key insight was changing the instruction from "use a placeholder" to "do not mention that topic at all" — removing the invitation to fill the gap entirely.

4. **Form validation and required fields:** The initial form had no field-level validation — all fields were optional, including state, service area type, and agency size metrics that the matcher depends on. Added required-field enforcement for state, service area type, project type, and all three agency size fields (ridership, fleet size, staff count). Changed it to conditionally required: only mandatory when "Other" is selected as the project type, since the named types carry enough context on their own. Agency name is validated to contain letters and spaces only. These changes made the form both more intuitive and ensured the matcher always has the inputs it needs to produce a meaningful score.

---

## How Cite-or-Skip Works (and How I Tested It)

The rule is enforced at two independent layers so neither can be bypassed alone.

### Layer 1 — `provenance.py` (data filtering)

`build_context(profile)` iterates every known fact key. Any value that is `None`, an empty string, or whitespace-only is silently dropped from the dict. The returned context contains **only facts the agency actually provided**, with no `None` values and no placeholder strings. This dict is the only thing passed to Claude.

### Layer 2 — `drafting.py` (system prompt instruction)

The system prompt instructs Claude:
> *"If a piece of information is not present in the agency context: do not mention that topic at all. Do not use a placeholder, bracket, or blank line for it."*

Because Layer 1 already removed absent facts, Claude never sees a blank slot to fill — it simply has fewer facts to work with.

## Future Work

1. **Draft persistence** — Save profiles and narratives to Supabase/Postgres so agencies can return to a draft later.
2. **Narrative section selector** — Let users choose which section to draft (Statement of Need, Project Description, Budget Narrative, Evaluation Plan). Currently only one generic section is generated.
3. **Edit-in-place** — Allow users to tweak the narrative in the browser before export, rather than downloading and editing externally.
4. **Streaming responses** — Show Claude's draft being written in real-time to reduce perceived latency.
5. **More grant programs** — Expand from 3 to 20–30 real federal and state grants with accurate eligibility rules and deadlines.
6. **PDF export** — Add as a third export option alongside Markdown and DOCX.
7. **Collaboration** — Share a draft link with colleagues for review before submission.
8. **Grant calendar** — Surface upcoming deadlines and notify agencies when a matching grant window opens(if we are allwoed to scape these websites)
