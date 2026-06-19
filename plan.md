You are a senior product engineer helping plan a small local-first Streamlit app.

Project objective:
Build a Streamlit web app that helps small or rural transit agencies find a suitable grant and draft one grant narrative section for AI training, AI pilots, or automation/software projects. The app must stop at export and must never submit anything.

Important product rule:
The app must follow a strict cite-or-skip rule. It must not invent agency facts, numbers, outcomes, dollar amounts, ridership figures, staffing levels, or prior results. If required information is missing, the app must insert a clear placeholder such as:
[AGENCY TO PROVIDE: annual ridership]

Tech direction:
- Use Streamlit, not React.
- Keep the app local-first.
- Use local files and session state where possible.
- Use hardcoded starter grant data only.
- Use Claude API only for LLM-based narrative drafting.
- Keep matching logic deterministic and local.
- Export should support at least Markdown; DOCX is a plus.
- No database unless clearly needed.
- No grant research beyond the provided programs.

Starter grant programs:
1. Section 5311 + RTAP
   - Administered by State DOT
   - Rural agencies only
   - Funds operating, training, and technical assistance
   - Federal share: up to 80% capital, training often higher
   - High fit for AI training

2. WA Consolidated Grant
   - Administered by WSDOT
   - Rural / small-urban agencies in Washington
   - Funds capital, operating, mobility projects
   - Federal share varies by sub-program
   - Medium-high fit for training and small pilots

3. Section 5312 / EMI
   - Administered by FTA directly
   - Agencies pursuing demonstrations / innovation
   - Funds research, demos, demand-response software
   - Federal share varies
   - High fit for AI pilots and automation

Expected app flow:
1. Agency profile form
2. Grant matching and ranking
3. AI-assisted narrative draft
4. Export

Planning instructions:
Create a detailed implementation plan, but only plan one module at a time. Do not write implementation code yet.

For each module, include:
- Purpose
- Files to create or modify
- Main functions/classes
- Inputs and outputs
- How it connects to other modules
- Edge cases
- Tests to write
- Completion checklist

Start with Module 1 only. After finishing the Module 1 plan, stop and ask me to approve before moving to Module 2.

Keep the architecture modular. Suggested modules:
- app.py / Streamlit UI shell
- data/grants.py or data/grants.json
- services/matcher.py
- services/drafting.py
- services/provenance.py
- services/export.py
- tests/

Prioritize:
1. cite-or-skip safety
2. simple end-to-end flow
3. clean modular code
4. local-first implementation
5. readable UX for non-technical transit staff

Output format:
- Brief project architecture overview
- Module 1 detailed plan only
- Risks or assumptions
- Questions only if truly blocking