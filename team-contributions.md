# Team contributions

Each member completes their own rows. "Helped" and "worked on code" are not contributions. Every row names something checkable: a file, a test run, or a decision.

> Teammate names marked **TBD** must be filled in before submission. Rows for teammate B and C are written by them, not by Vinh.

## Session 1 — 2026-09-22 (connect, define, build core on the host Mac)

| Teammate | Date | Concrete contribution | Evidence or link | Peer confirmation |
|---|---|---|---|---|
| Vinh Hoang | 09-22 | Ran Step 0 tool check; installed ngrok (program only, no account); downloaded and extracted the starter | `ai-use-log.md` rows 2–4 | pending |
| Vinh Hoang | 09-22 | Proved the Week 3 baseline: health, order route, SSH login; installed own public key into `docker/sshd/authorized_keys`; diagnosed and cleared the changed host key after the rebuild | `evidence/regression-test.md` §1 | pending |
| Vinh Hoang | 09-22 | Reviewed the agent's 10-proposal plan: accepted P1–P7, revised P9 (create items through the real form), rejected P8 (delete button, breaks append-only) and P10 (shared request ID) | `evidence/decision-table.md` Part A | pending |
| Vinh Hoang | 09-22 | Restored the Week 3 overdue calculation on `/` (config re-read per request, `NOW_OVERRIDE`, computed status) | `docker/app/app.py`; `/` shows 3 overdue | pending |
| Vinh Hoang | 09-22 | Added the saved-image scan path, QR-only decoding, button-gated camera with stop, locally served scanner library | `docker/app/app.py`, `docker/app/static/` | pending |
| Vinh Hoang | 09-22 | Added the missing guards: reason required for WASTE/CORRECTION; non-negative stock for every reducing action | `docker/app/app.py`; `evidence/failure-recovery-log.md` Part 3 | pending |
| Vinh Hoang | 09-22 | Hand-computed the known answer **before** running it, then ran r-01/r-02/r-03: 8 bags, $2.25, $18.00 | `evidence/quantity-cost-known-answer.md` §1–2 | pending |
| Vinh Hoang | 09-22 | Ran failures A, B, C, F, the waste-reason guard, and the restart persistence test; recorded exact messages | `evidence/failure-recovery-log.md` | pending |
| Vinh Hoang | 09-22 | Verified the QR label encodes exactly `PHO65-INV-000101` (bitmap comparison plus a negative control) | `evidence/failure-recovery-log.md` Part 2 | pending |
| **TBD — teammate B** |  | *Verifier:* independently re-run the known-answer sequence on your own machine and confirm 8 / $2.25 / $18.00 without copying Vinh's numbers |  |  |
| **TBD — teammate B** |  | *Verifier:* run the phone test (camera, saved image, manual) and record every row of the mobile test |  |  |
| **TBD — teammate C** |  | *Business reviewer:* answer the moving-average prompts in your own words and sign the continue/revise/stop decision |  |  |
| **TBD — teammate C** |  | *Business reviewer:* follow the intern handoff uncoached, record where you hesitated, then re-test after the revision |  |  |
| **TBD — teammate C** |  | *Ubuntu machine:* generate your own key, add the `.pub` to `authorized_keys`, and confirm `whoami` → `pho65user` there |  |  |

## Ownership right now (avoid editing the same file at once)

| File | Owner | Status |
|---|---|---|
| `docker/app/app.py` | Vinh | free after Session 1 |
| `evidence/mobile-transfer-test.md` | teammate B | in progress at Step 8 |
| `evidence/intern-workflow-handoff.md` | teammate C | awaiting the uncoached test |
| `evidence/decision-table.md` Part B | teammate C | awaiting each member's own answers |
| `README.md` | Vinh | drafted; business reviewer edits Section 9 |

## Next action

**Owner: Vinh** — hand off to teammate B for the ngrok phone test after teammate B's public key is installed and the app is confirmed healthy locally.

## What each member can explain (fill in before the demo)

| Member | Can explain without notes |
|---|---|
| Vinh Hoang | Why a repeated request cannot apply twice (UNIQUE `request_id` at the database, not just the form); why the average is $2.25 and not $2.50; how the Week 3 overdue check still works |
| **TBD — teammate B** |  |
| **TBD — teammate C** |  |
