---
name: start-development
description: Structured test-driven development workflow following docs/PRD.md and docs/TECH_SPEC.md. Creates small 30-min tasks in docs/TASKS.md, executes them strictly one at a time with tests, student approval, and clean git commits.
---

# Start Development

Execute a structured, test-driven development process following approved PRD and technical specifications.

## Prerequisite

Confirm that `docs/PRD.md` and `docs/TECH_SPEC.md` exist and are approved by the student.
If either is missing, **STOP** and tell the student which earlier step to complete first.

---

## Step 1: Task List Creation

1. Read `docs/TECH_SPEC.md` fully.
2. Create or verify `docs/TASKS.md` with numbered checkbox tasks in logical build order:
   - Setup & project initialization
   - Core data model & store/database
   - API endpoints & business logic
   - Screens & user interface
   - Input validation & error handling
   - Automated tests
3. **Task Format**:
   ```markdown
   ## T-01 — [Task Title]
   - [ ] **Status:** not started
   - **Description:** [Short summary of work]
   - **Files:** `[file1.py]`, `[file2.html]`
   - **Acceptance criteria:** [Exact expected behavior and verification steps]
   - **PRD feature:** [Name of supported PRD feature]
   ```
4. Keep each task small (approx. 30 minutes, one clear verifiable outcome).
5. Show the task list and wait for the student's approval before coding.

---

## Step 2: Code Execution (One Task at a Time)

1. **Pick the first unchecked task** in `docs/TASKS.md`.
2. **Announce which task you are starting.**
3. **Implement ONLY that task**, following the specification exactly. Do not add extra features or refactor unrelated files.
4. **Write or update automated tests** for the task and run them.
5. **Show a short summary**:
   - Files changed
   - What was tested
   - Test execution results
6. **STOP** and wait for the student to review and say "approved".

---

## Step 3: Approval & Commit

1. After approval, mark the task checkbox `[x]` in `docs/TASKS.md`.
2. Make exactly one Git commit per task containing only that task's changes.
3. Use the standardized commit message format:
   ```text
   type: short description (Task ID)
   ```
   *Examples:*
   - `feat: add friend management API (T-04)`
   - `test: verify equal split with leftover cents (T-02)`
   - `fix: handle duplicate friend names with 400 (T-04)`
4. **Allowed commit types**: `feat`, `fix`, `test`, `docs`, `refactor`, `chore`.

---

## Hard Rules

- **NEVER** start task $N+1$ until task $N$ is tested, approved, and committed.
- **NEVER** commit failing tests.
- **NEVER** add features that are not in the PRD or technical spec. If something is missing, ask the student.
- If a task turns out to be too big, split it in `docs/TASKS.md` and ask for approval.
- Maintain a clean Git history: never create vague "misc changes" or "WIP" commits.
