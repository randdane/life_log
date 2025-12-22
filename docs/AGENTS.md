
Purpose
- Provide a minimal, machine-friendly guide so code-generation agents (Codex, Claude Code, etc.) can work productively in this repository.
- Point agents to the authoritative planning and specification artifacts and explain what lives where.

What each key file is
- PROMPT_PLAN.md — The agent-driven, step-by-step prompt plan / implementation checklist. Contains per-step prompts, expected artifacts, tests, rollback and idempotency notes, and a TODO checklist using Markdown checkboxes. This is the primary driver for automated agent work.
- DEV_SPEC.md — The concise developer specification (functional + technical) that defines APIs, data model, acceptance criteria, and Definition of Done for features. Update this if you introduce new public APIs or change behavior.
- ONE_PAGER.md — A short one-page summary of the product idea: problem statement, target audience, core flows, and high-level goals. Useful for context and prioritization.
- AGENTS.md — This file. Contains agent responsibilities, guardrails, and the repo-level testing / TDD policies.

What lives in /designs/
- High-fidelity and low-fidelity design artifacts:
  - Wireframes, mockups, and UI flows (PNG/SVG/PDF).
  - Figma or Adobe XD export files (if available) and a README describing which files map to which screens.
  - Icons, sample images, and design tokens.
  - A short design_notes.md that explains key UX decisions, breakpoints, and assets provenance.
- If designs are large (Figma sources, videos), include a small index file listing filenames and expected viewers/tools. If any design files are missing or unsupported, say so and stop — do not guess.

Include the following section verbatim:

## Repository docs
- 'ONE_PAGER.md' - Captures Problem, Audience, Platform, Core Flow, MVP Features; Non-Goals optional.
- 'DEV_SPEC.md' - Minimal functional and technical specification consistent with prior docs, including a concise **Definition of Done**.
- 'PROMPT_PLAN.md' - Agent-Ready Planner with per-step prompts, expected artifacts, tests, rollback notes, idempotency notes, and a TODO checklist using Markdown checkboxes. This file drives the agent workflow.
- 'AGENTS.md' - This file. 

### Agent responsibility
- After completing any coding, refactor, or test step, **immediately update the corresponding TODO checklist item in 'PROMPT_PLAN.md'**.  
- Use the same Markdown checkbox format ('- [x]') to mark completion.  
- When creating new tasks or subtasks, add them directly under the appropriate section anchor in 'PROMPT_PLAN.md'.  
- Always commit changes to 'PROMPT_PLAN.md' alongside the code and tests that fulfill them.  
- Do not consider work “done” until the matching checklist item is checked and all related tests are green.
- When a stage (plan step) is complete with green tests, update the README “Release notes” section with any user-facing impact (or explicitly state “No user-facing changes” if applicable).
- Even when automated coverage exists, always suggest a feasible manual test path so the human can exercise the feature end-to-end.
- After a plan step is finished, document its completion state with a short checklist. Include: step name & number, test results, 'PROMPT_PLAN.md' status, manual checks performed (mark as complete only after the human confirms they ran to their satisfaction), release notes status, and an inline commit summary string the human can copy & paste.

#### Guardrails for agents
- Make the smallest change that passes tests and improves the code.
- Do not introduce new public APIs without updating 'DEV_SPEC.md' and relevant tests.
- Do not duplicate templates or files to work around issues. Fix the original.
- If a file cannot be opened or content is missing, say so explicitly and stop. Do not guess.
- Respect privacy and logging policy: do not log secrets, prompts, completions, or PII.

#### Deferred-work notation
- When a task is intentionally paused, keep its checkbox unchecked and prepend '(Deferred)' to the TODO label in 'PROMPT_PLAN.md', followed by a short reason.  
- Apply the same '(Deferred)' tag to every downstream checklist item that depends on the paused work.
- Remove the tag only after the work resumes; this keeps the outstanding scope visible without implying completion.

#### When the prompt plan is fully satisfied
- Once every Definition of Done task in 'PROMPT_PLAN.md' is either checked off or explicitly marked '(Deferred)', the plan is considered **complete**.  
- After that point, you no longer need to update PROMPT_PLAN TODOs or reference 'PROMPT_PLAN.md', 'DEV_SPEC.md', 'ONE_PAGER.md', or other upstream docs to justify changes.  
- All other guardrails, testing requirements, and agent responsibilities in this file continue to apply unchanged.

---

## Testing policy (non‑negotiable)
- Tests **MUST** cover the functionality being implemented.
- **NEVER** ignore the output of the system or the tests - logs and messages often contain **CRITICAL** information.
- **TEST OUTPUT MUST BE PRISTINE TO PASS.**
- If logs are **supposed** to contain errors, capture and test it.
- **NO EXCEPTIONS POLICY:** Under no circumstances should you mark any test type as "not applicable". Every project, regardless of size or complexity, **MUST** have unit tests, integration tests, **AND** end‑to‑end tests. If you believe a test type doesn't apply, you need the human to say exactly **"I AUTHORIZE YOU TO SKIP WRITING TESTS THIS TIME"**.

### TDD (how we work)
- Write tests **before** implementation.
- Only write enough code to make the failing test pass.
- Refactor continuously while keeping tests green.

**TDD cycle**
1. Write a failing test that defines a desired function or improvement.  
2. Run the test to confirm it fails as expected.  
3. Write minimal code to make the test pass.  
4. Run the test to confirm success.  
5. Refactor while keeping tests green.  
6. Repeat for each new feature or bugfix.

---

## Important checks
- **NEVER** disable functionality to hide a failure. Fix root cause.  
- **NEVER** create duplicate templates or files. Fix the original.  
- **NEVER** claim something is “working” when any functionality is disabled or broken.  
- If you can’t open a file or access something requested, say so. Do not assume contents.  
- **ALWAYS** identify and fix the root cause of template or compilation errors.  
- If git is initialized, ensure a '.gitignore' exists and contains at least:
  
  .env
  .env.local
  .env.*
  
  Ask the human whether additional patterns should be added, and suggest any that you think are important given the project. 

## When to ask for human input
Ask the human if any of the following is true:
- A test type appears “not applicable”. Use the exact phrase request: **"I AUTHORIZE YOU TO SKIP WRITING TESTS THIS TIME"**.  
- Required anchors conflict or are missing from upstream docs.  
- You need new environment variables or secrets.  
- An external dependency or major architectural change is required.
- Design files are missing, unsupported or over-sized

---

Quick agent starter checklist
- Open PROMPT_PLAN.md first and work the top-most incomplete step.
- For each code change: add/modify tests, run tests locally, update PROMPT_PLAN.md checkbox, commit code + tests + PROMPT_PLAN update together.
- If you cannot open a required file, stop and report exactly which file and why it is inaccessible.
- Preserve secrets: never commit real credentials; never echo secrets in logs or prompts.

If anything in this repository is unclear or a required artifact is missing, stop and ask the human before proceeding.