# Decision Table — Plan Review and Business Decision

Agent: **Claude Code**. The agent inspected every file under `docker/`, `sample-data/`, and `evidence/` read-only before proposing changes, and made no edit before this table was written.

---

## Part A — Plan review: proposed file-by-file changes

Scope limits given to the agent: extend the existing Flask/Docker app only; no authentication, cloud database, retail UPC/EAN lookup, unit conversion, or unrelated interface polish.

| # | Proposal | File(s) | Why | Risk | Verification | Decision |
|:-:|---|---|---|---|---|:-:|
| P1 | Restore the Week 3 overdue calculation on `/` (read `OVERDUE_MIN` from `/config/overdue.env` on each request, apply `NOW_OVERRIDE`, show the per-order computed status table) | `docker/app/app.py` | The starter rewrite dropped it; the contract requires preserving Week 3 order-tracker behaviour | Touching the shared route could break the Week 4 nav | `/` shows `3 orders overdue` (O-001–O-003); O-004 at exactly 20 min stays `waiting` | **Accept** |
| P2 | Add the saved-image scan path: a file selector that decodes a QR image in the browser | `docker/app/app.py` (scan page) | Step 4.2 requires it; it is the documented fallback when camera permission is denied | A file input that uploads anywhere external would break the data rule | Decode a downloaded label PNG; same code as camera/manual; no upload leaves the browser | **Accept** |
| P3 | Serve `html5-qrcode` from the app instead of the `unpkg` CDN | `docker/app/static/html5-qrcode.min.js`, `Dockerfile` | Scanner must work on a café network without internet; a CDN is a third-party dependency at demo time | Adds ~350 KB to the image | Scan page works with DevTools offline; no request to unpkg | **Accept** |
| P4 | Restrict the scanner to QR codes only (drop `UPC_A`, `EAN_13`, `CODE_128`) | `docker/app/app.py` | Internal-code safety: the pilot must not read or imply retail identifiers | A real retail barcode will no longer scan | Scanning a retail barcode does nothing; the internal QR decodes | **Accept** |
| P5 | Require a non-empty reason/note for `wasted` and `correction` | `docker/app/app.py` (`add_transaction`) | Step 3.1: "require a reason for WASTE and CORRECTION" | Blocks a submission that used to succeed | Submitting waste with a blank note is rejected and adds no row | **Accept** |
| P6 | Extend the non-negative guard to `counted` and `correction`, not just `used`/`wasted` | `docker/app/app.py` (`add_transaction`) | Contract: on-hand quantity must never go below zero. The starter guards only two of the four reducing paths | A large negative correction is now rejected; the worker must count instead | A `correction` of −999 is rejected, quantity unchanged, no row added | **Accept** |
| P7 | Show the low-stock rule in the interface and state the comparison in writing (`quantity <= reorder_point` ⇒ LOW) | `docker/app/app.py` (dashboard) | Step 7 Failure F compares written policy with code | None | Test at threshold −1, threshold, threshold +1 | **Accept** |
| P8 | Agent proposed also adding a "delete item" button while editing the item page | — | — | Deleting an item would orphan its ledger rows and break append-only history | — | **Reject** — out of scope and against the append-only rule. Items stay; use a low-stock/inactive state if needed |
| P9 | Agent proposed seeding the two fixture items by writing directly into SQLite | `docker/inventory-data/` | Faster setup | Bypasses the app's own validation, so it would not prove the create path works | — | **Revise** — create both items through the real `/inventory/new` form instead, so the tested path is the one a worker uses |
| P10 | Agent proposed storing the known-answer events with one shared request ID for speed | — | — | Would hide exactly the duplicate-protection behaviour we must prove | — | **Reject** — use three distinct request IDs, as Step 3.2 requires |

| P11 | Tap-first record form: action buttons, quantity presets with −/+, staff-name buttons, quick reason chips; keyboard fields kept underneath | `docker/app/app.py` (item page) | Instructor feedback: a phone workflow should prefer tapping over typing. Typing is slow and error-prone with wet or busy hands, and `100` instead of `10` is a realistic mistake | A tap UI that hides the real fields would break the no-JavaScript fallback | Record an event using only taps; the plain number and note inputs still work if scripting fails | **Accept** |
| P12 | Staff names in `/config/staff.txt` (same shared-config pattern as `overdue.env`), with a PIN-gated Edit tab at `/inventory/staff` | `docker/app/app.py`, `docker/shared-config/staff.txt`, `docker-compose.yml` | Names must be editable without changing code or rebuilding; reuses the Week 3 shared-config skill, so the list can also be fixed over SSH | A PIN in the compose file could be mistaken for real access control | Add and remove a name with the right PIN, and confirm a wrong PIN changes nothing | **Accept with a written limitation:** the PIN is a guard against accidental edits during a shift, **not** authentication and **not** a secret. Documented in the app, `README.md`, and here |
| P13 | Agent proposed remembering the selected staff name in the browser | `docker/app/app.py` | Saves a tap per event on a shared phone | A remembered name could attribute an event to the wrong person | Name stays visible and can be changed before submitting | **Revise** — kept, but the selected name is always shown on screen, never applied silently |
| P14 | Keep the unit cost as a typed field | — | A receipt cost comes from a real invoice; presets would invite guessing | Guessed costs corrupt the average silently | — | **Accept** (deliberate exception to the tap-first rule) |

| P15 | Interface redesign for first-time users: numbered steps, a round −/+ stepper with 1 / 5 / 10 / 100 presets, one-line help under each action, a live plain-language summary before the submit button, stat tiles for on-hand / average / value, item cards on the list page, newest-first history | `docker/app/app.py` (templates and CSS only) | Feedback that the form was confusing for a new user. A worker should be able to read what they are about to record before pressing anything | Visual changes could hide a rule or change what gets submitted | All field names and guards unchanged; re-ran the full desktop pass, the known answer, and `test_inventory.py` after the redesign | **Accept** — presentation only, no change to validation, costing, or the ledger |

| P16 | Hover-reveal **Remove** button on every item card, requested after P8 was rejected | `docker/app/app.py`, `items.archived_at` column | The team needs a way to clear mistyped or discontinued items from the working list | A plain delete would orphan that item's transactions and destroy the explanation of how a count was reached — the exact thing the append-only rule protects | Remove an item with no history (deleted), one with history (archived), then restore it and confirm its rows are intact | **Accept as a revision of P8, not a reversal of the rule:** the server decides. Zero ledger rows → deleted outright. Any history → archived (hidden, restorable, rows untouched), listed under "Removed items" |

| P17 | Update every dependency to current: Python 3.11→**3.14.7**, Flask 3.0.3→**3.1.3**, qrcode 7.4.2→**8.2** (Pillow **12.3.0**), sshd base Debian bookworm→**trixie** (OpenSSH **10.0p2**) | `docker/app/requirements.txt`, both Dockerfiles | Current releases carry security fixes; the pinned starter versions were a year behind | A major bump can break an API (`qrcode.make`, Pillow drawing) or the SSH image | Rebuilt and re-ran the whole acceptance pass: label renders (4742 bytes), known answer 8/$2.25/$18.00, Week 3 3 overdue, `test_inventory.py` passes, `whoami` → `pho65user` | **Accept** — versions stay pinned exactly, so the build is still reproducible |
| P18 | Restyle the interface in the café's own colours, sampled from pho65middletown.com: deep green `#00563F`, amber `#FFA300`, leaf `#15B500`, gold `#FFD200`; gradient header and buttons, accented stat tiles, softer cards | `docker/app/app.py` (CSS only) | The pilot should look like it belongs to Phở 65, not a default form | Colour alone must not carry meaning, and contrast must stay readable on a phone | All nine routes still 200; checked on desktop and at 375 px; status still carries a text label ("LOW — review" / "OK"), not just colour | **Accept** — presentation only |

| P19 | Harden every input path after an adversarial audit: check the item exists before writing, enable `PRAGMA foreign_keys`, validate the action against the allowed set, reject non-numeric/empty/zero quantities, catch unparseable costs, ignore a cost on a non-receipt, and require `PHO65-INV-` + six digits for new codes | `docker/app/app.py` | Sixteen malformed submissions exposed five defects, including an **orphan ledger row** written for an item that does not exist and two HTTP 500 crash pages where the assignment requires a plain-language message | More validation could reject something legitimate | Re-ran all 16 probes: every one rejected with a readable message and no ledger row; 0 orphans; the known answer, Week 3 count and packaged test all unchanged | **Accept** |

Bounded plan approved: **P1–P7, P11, P12, P14–P19** proceed; **P10** rejected; **P8, P9, P13** revised.

> Note on P8 → P16: P8 was rejected as first proposed (a delete button that would remove an item and orphan its ledger rows). P16 grants the same interface affordance without weakening the guarantee. Tested 2026-09-23: Viet BBQ (7 rows) and Limes (5 rows) were archived rather than deleted, and Limes restored with all 5 rows present. No other file is changed. `docker-compose.yml`, the Dockerfiles, `sshd/`, and the CSV fixtures stay as shipped (except `sshd/authorized_keys`, which receives team public keys).

### Data model review (Step 2.3)

| Record | Fields present in the starter schema | Verdict |
|---|---|---|
| Item | `id`, `name`, `scan_code` (UNIQUE), `code_kind` (`internal`/`manufacturer`), `base_unit`, `reorder_point`, `created_at` | Meets the requirement. Active/inactive status is **not** present — recorded as a deferred decision, since the pilot has no retire-item workflow |
| Transaction | `id`, `item_id`, `action` (`starting`/`received`/`used`/`wasted`/`counted`/`correction`), `quantity_delta`, `unit_cost_cents`, `occurred_at`, `recorded_by`, `note`, `request_id` (UNIQUE) | Meets the requirement. Append-only: no UPDATE or DELETE path exists |
| State | Computed by replaying the ledger (`inventory_state`), never stored as an editable balance | Meets the requirement; a balance cannot drift from its history |

One unit of work: the guard checks run first and a single `INSERT` records the event, so a rejected event writes nothing. The UNIQUE constraint on `request_id` is what makes a repeat submission fail at the database, not just in the form.

---

## Part B — Business decision: moving weighted average (Step 9.1)

**Possible benefit.** Rice noodles arrive at $2.00 one week and $2.50 the next. One blended cost, $2.25, lets the owner price a bowl and read the stock value without asking which delivery a bag came from. Day-to-day decisions need one number, not a purchase history.

**Possible downside.** The average hides the newest price. After the $2.50 delivery, the average is still $2.25, so a manager reading the dashboard sees a cost lower than today's replacement cost. If prices keep climbing, the pilot consistently understates what restocking will cost.

**Operations limit.** Cost says nothing about age. Two bags at the same $2.25 can be a fresh bag and one near expiry. The average cannot tell a worker which to open first, so the café still needs a physical first-expiry rule on the shelf.

**Data limit.** The formula is only as good as what is typed. A receipt entered as 100 bags instead of 10, or $25.00 instead of $2.50, produces a confidently wrong average, and a correction event changes quantity without repairing the historical average. Our negative-stock and duplicate guards catch impossible *quantities*, not implausible *prices*.

**Alternative.** Latest purchase cost would track rising prices more honestly and is easier to explain, but it makes stock value jump with every delivery and reports a value the café never actually paid. Batch-specific cost is the most accurate and the most work: every bag needs its batch tracked to the point of use, which is more than a phone pilot with one base unit per item can carry.

**Decision: continue the pilot with moving weighted average, and revisit if a receipt-cost error reaches the dashboard.** The known-answer test passes exactly (`evidence/quantity-cost-known-answer.md`: 8 units, $2.25, $18.00, matching the hand calculation), and a worker recording a receipt needs no arithmetic. The limitation we accept is the hidden latest price; the team will show the most recent receipt cost next to the average in a later version rather than changing the reference calculation, which must stay common across all teams.
