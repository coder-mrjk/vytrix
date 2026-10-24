# AGENTS.md: standing rules for the agent

These rules apply to every task in this repository. `SPEC.md` describes the project. This file describes **how to work**.

## 1. Workflow
- **Plan before code.** For any non-trivial task: restate the goal, list assumptions, propose the approach and alternatives, wait for approval.
- **Grill, don't guess.** If a requirement, input, or constraint is unclear, ask. Ask a small batch of the most blocking questions, not a long form.
- **One milestone at a time** (`SPEC.md` Section 13). Do not start the next one until I approve.
- Keep a running **Task List**. Update it as work completes. Keep an **Implementation Plan** that matches reality.
- Log every significant decision in `DECISIONS.md` (date, decision, alternatives considered, why).
- Small, focused commits with clear messages. Commit at the end of every milestone and after each meaningful working step. Never commit secrets, large binaries, or generated model files (use `.gitignore`, Git LFS, or object storage).

## 2. Truthfulness and verification
- **Never invent** APIs, CLI flags, package names, versions, licence terms, or benchmark numbers. Read the official docs or the installed source. If you cannot verify, write `TODO(verify)` and tell me.
- **Never claim "done" without evidence.** Evidence means test output, logs, screenshots, or browser-agent recordings. Report what was verified and what was not.
- **Evidence-Based Rule:** If you say "done", give the evidence: command output, a screenshot or a log as text/markdown after each prompt work.
- If a step must run on Google Colab (GPU), you can't run it. Provide exact steps, the expected output, and what to send back. Do not pretend it ran.
- If something fails, say so plainly, show the error, and propose a diagnosis before changing approach.
- Pin dependency versions you have verified. Do not silently upgrade or downgrade.

## 3. Code quality
- **Python:** 3.10+ compatible with Colab. Type hints, docstrings on public functions, `ruff` (lint and format), `pytest` for logic (geometry, alignment, scale, bounds). No bare `except`. Use `logging`, not `print`, in library code.
- **TypeScript:** `strict` mode, ESLint and Prettier, no `any` without a comment explaining why. Small modules, no god files.
- **Config over constants:** parameters belong in `config.yaml`, not scattered in code.
- **Idempotent and resumable pipeline stages** with explicit inputs and outputs. Hash-based skip logic. Clear error messages that tell the user what to do next.
- **No placeholder code** left behind (`pass`, fake data, `TODO` without an issue). If something is deferred, record it in the task list.
- Delete dead code. Keep functions short and testable.

## 4. Performance and UX (viewer)
- Measure, don't guess. Profile with the browser performance tools and record results in `docs/PERFORMANCE.md`.
- Never block the main thread during loading. Show real progress. Handle errors visibly.
- Frame-rate-independent movement (delta time). Test on an integrated GPU, not just a discrete one.
- Test in incognito mode and with network throttling before calling anything "deployed".

## 5. Documentation
- Keep `README.md`, `docs/SOP.md`, and `docs/ARCHITECTURE.md` in sync with the code. Documentation is graded.
- Every third-party dependency goes into `THIRD_PARTY.md` (name, version, licence, purpose, URL). **Flag non-commercial or research-only licences and ask me before using them.**
- Setup instructions must work for a stranger on a fresh Colab runtime. Test them that way.

## 6. Safety and privacy
- The public viewer will show my real home. Never publish data containing personal information, faces, screens, or documents without asking me. Remind me during capture and review.
- Never put API keys, tokens, or personal data in the repo or in logs.
- Don't run destructive commands (deleting directories, force pushes, overwriting data) without asking.

## 7. Communication
- Be concise. Lead with the result, then the evidence, then the open questions.
- Explain technical choices in plain language. I am a student and I must be able to defend every part of this project in a live technical Q&A later, so explain **why**, not just what.
- When you change the plan, say what changed and why.

## 8. Competition constraints (always on)
- Solutions must be our own original work. Third-party libraries are allowed if licensed properly and **credited in the technical abstract**.
- All extra links must live inside **one master PDF or Google Doc** in the submission folder.
- Drive folder permission: "Anyone with the link can view".
- Round 1 deliverables: abstract PDF (max 5 pages), PoC with working web-viewer link, 3 to 5 minute demo video, code repo with setup instructions and sample data in a test directory.
- Deadlines: registration 15 Oct 2026, Round 1 31 Oct 2026. Target submission one day early.
