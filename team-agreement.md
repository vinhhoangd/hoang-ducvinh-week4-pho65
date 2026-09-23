# Team Agreement — Week 4 Pho65 Mobile Inventory

> Names marked **TBD** must be filled in before submission.

## Members and contact

| Member | Machine | Preferred contact | First responsibility |
|---|---|---|---|
| Vinh Hoang | MacBook (build host) | Canvas Inbox / team chat | **Builder** — ledger, Week 3 restore, scan paths |
| **TBD — teammate B** | MacBook | team chat | **Verifier** — independent re-run of the known-answer and failure tests |
| **TBD — teammate C** | Ubuntu | team chat | **Business reviewer** — costing trade-off, intern handoff test |

Responsibilities rotate at the next checkpoint: Vinh → Verifier, B → Business reviewer, C → Builder. Every member speaks during the final demonstration.

## Shared workspace

- Working directory: `week4-student-starter/project-workspace` (built first on Vinh's Mac, then shared with the team).
- The repository/shared folder link goes here once the team creates it: **TBD**.
- The Ubuntu machine runs the same `docker compose up -d --build`; no OS-specific steps are expected. Docker Engine + Compose plugin must be installed there.

## Avoiding edit collisions

- One person owns a file at a time. Ownership is announced in `team-contributions.md` before editing.
- Current ownership: `docker/app/app.py` → Vinh; `evidence/*` → whoever ran that test; `README.md` → Business reviewer.
- Pull or re-sync before starting a new responsibility; stage named files (`git add docker/app/app.py`), never `git add .` without reading every path.
- Small commits, one tested change each. Corrections are new commits; nobody rewrites a teammate's commit.

## Safe stop rule

Stop and message the team **before** doing anything else if:

- the ledger shows a quantity or cost that the known-answer test says is wrong;
- a command would delete files, volumes, or history (`git reset --hard`, `git clean -fd`, force push, `docker compose down -v`);
- a secret (ngrok authtoken, private key, real data) appears in a file, prompt, screenshot, or chat;
- the app writes a transaction that nobody intended, or a duplicate appears;
- Week 3 checks (`/health`, `/`, SSH on 2222) stop passing.

The person who notices stops work and posts what they saw. Nobody "fixes it quietly".

## Credential rules (agreed by all members)

- The ngrok account belongs to the student running the tunnel. The authtoken is configured personally, in a terminal not shared with the AI agent, and is never pasted into a prompt, file, screenshot, or chat.
- Each member generates their **own** SSH keypair and adds only the `.pub` half to `docker/sshd/authorized_keys`. Private keys never leave the machine that made them.
- No real customer, supplier, or employee data. Fictional Pho65 fixtures only.

## Disagreements

Decide by evidence: whoever proposes a change names the test that would show it is right. If a test settles it, we follow the test. If not, we take the smaller, reversible option and record the disagreement in `evidence/decision-table.md`. Unresolved after one working day → ask the instructor.

## Handoffs

| Checkpoint | Date / time | Who hands to whom | Next action recorded in |
|---|---|---|---|
| Session 1 — baseline + plan | 2026-09-22 | Vinh → B | `team-contributions.md` |
| Session 2 — build core | TBD | B → C | `team-contributions.md` |
| Session 3 — break & verify (phone test) | TBD | C → Vinh | `mobile-transfer-test.md` |
| Session 4 — explain & hand off | TBD | all | `intern-workflow-handoff.md` |

At the end of each session: record the exact next action, save evidence, stop services safely (`docker compose down`, Control+C on ngrok), and commit if tests pass.
