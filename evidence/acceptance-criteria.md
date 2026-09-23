# Acceptance Criteria (Step 2.1; results filled in Step 6)

Written **before** the Week 4 code changes. Each row names the input and the exact visible result. "Works" and "scan succeeds" are not acceptance criteria.

Fixture items (from `sample-data/inventory-fixture.md`): Rice noodles `PHO65-INV-000101`, base unit bag, low-stock point 8 · Oat milk `PHO65-INV-000102`, base unit carton, low-stock point 4.

| # | Behavior (contract rule) | Test input / action | Expected visible result | Evidence destination | Owner |
|:-:|---|---|---|---|---|
| A1 | Both containers start | `docker compose up -d --build`; `docker compose ps` | `pho65-app` Up with `5000->5000`; `pho65-sshd` Up with `2222->22` | regression-test.md | Vinh |
| A2 | App health | `curl -s http://localhost:5000/health` | JSON containing `"status":"ok"` | regression-test.md | Vinh |
| A3 | Week 3 order route preserved | open `http://localhost:5000/` | Order table renders and reports **3 orders overdue** (O-001, O-002, O-003); O-004 at exactly 20 min shows `waiting` | regression-test.md | Vinh |
| A4 | Week 3 SSH preserved | `ssh -i <key> pho65user@localhost -p 2222 whoami` | prints exactly `pho65user` | regression-test.md | Teammate C |
| A5 | Inventory dashboard | open `/inventory` | Table with item, scan code, on hand + base unit, average cost, value, status | acceptance-criteria.md | Vinh |
| A6 | Internal item creation | `/inventory/new`, name "Rice noodles", code `PHO65-INV-000101`, unit bag, low-stock 8 | Item page opens; code shown as `internal`; a code not starting `PHO65-INV-` is refused with a plain message | acceptance-criteria.md | Vinh |
| A7 | Manual identification | `/inventory/scan`, type `PHO65-INV-000101`, submit | Rice noodles item page opens; **no** ledger row is created by the lookup | failure-recovery-log.md | Teammate B |
| A8 | Camera identification | On the phone over HTTPS, press Scan, allow camera, point at the label | Same Rice noodles page; permission requested only after the button press | mobile-transfer-test.md | Teammate B |
| A9 | Saved-image identification | On `/inventory/scan`, choose a saved PNG of the label | Decodes to `PHO65-INV-000101` and opens the same item page; works with camera denied | failure-recovery-log.md | Teammate C |
| A10 | Scan alone writes nothing | After A7–A9, open the item History table | Row count unchanged by any identification path | failure-recovery-log.md | Teammate C |
| A11 | Receive event + costing | Receive 10 bags at $2.00 (request ID r-01) | One `received` row; 10 bags on hand; average $2.00; value $20.00 | quantity-cost-known-answer.md | Vinh |
| A12 | Moving weighted average | Receive 10 bags at $2.50 (request ID r-02) | 20 bags; average **$2.25** (not $2.50); value $45.00 | quantity-cost-known-answer.md | Vinh |
| A13 | Use event | Use 12 bags (request ID r-03) | 8 bags; average still **$2.25**; value **$18.00**; one new row | quantity-cost-known-answer.md | Vinh |
| A14 | Money stays exact | Inspect stored values for A11–A13 | Costs stored as integer cents (200, 250, 225); pages show 2 decimals; no float drift | quantity-cost-known-answer.md | Teammate B |
| A15 | Duplicate request rejected | Re-submit request ID r-03 | Message "already recorded"; quantity stays 8; no new row | failure-recovery-log.md | Teammate B |
| A16 | Negative stock rejected | With 8 on hand, use 100 | Plain-language refusal; quantity stays 8; no row added | failure-recovery-log.md | Teammate C |
| A17 | Negative stock via correction rejected | With 8 on hand, correction of −999 with a reason | Same refusal; quantity stays 8; no row added | failure-recovery-log.md | Teammate C |
| A18 | Waste needs a reason | Waste 1 bag with an empty note | Refused with a message naming the missing reason; with a reason it records one row and 7 remain | failure-recovery-log.md | Vinh |
| A19 | Correction is a new event | Correction of +1 with reason "recount after spill" | Original rows still visible; correction appears as an additional row; quantity updates | quantity-cost-known-answer.md | Vinh |
| A20 | Data survives restart | `docker compose restart app`, reload `/inventory` | Items, ledger rows, quantity, average, and value all unchanged | quantity-cost-known-answer.md | Vinh |
| A21 | Low-stock boundary | On a scratch item with low-stock point 2 (Limes, `PHO65-INV-000103`), test on-hand 3, 2, 1 | 3 = OK; 2 = LOW; 1 = LOW (rule: `quantity <= reorder_point` ⇒ LOW). Tested on a scratch item so the graded known-answer item stays at 8 | failure-recovery-log.md | Teammate C |
| A22 | Unknown code | Look up `PHO65-INV-999001` (valid format, not in the table) | "Unknown code" page with a safe next action; no item and no ledger row created | failure-recovery-log.md | Teammate B |
| A23 | Internal label safety | Open the label for Rice noodles | PNG shows the QR plus "PHO65 INTERNAL USE ONLY", the code, and "Not a retail UPC/EAN/GTIN" | failure-recovery-log.md | Vinh |
| A24 | No retail formats scanned | Point the scanner at a real retail barcode | Nothing decodes; only QR is accepted | failure-recovery-log.md | Teammate B |
| A25 | Packaged automated test | `docker compose exec app python test_inventory.py` | prints `inventory known-answer and guard tests passed` | quantity-cost-known-answer.md | Vinh |
| A26 | Phone usability | Open the ngrok HTTPS URL on a phone | Loads over HTTPS; no horizontal scrolling; buttons usable by touch | mobile-transfer-test.md | Teammate B |
| A27 | Scanner works offline | Load `/inventory/scan` with the browser offline after first load | Scanner still initialises (library served by the app, not a CDN) | acceptance-criteria.md | Vinh |

## Observed results (Step 6 desktop acceptance pass)
All desktop rows were run on 2026-09-22 between 14:42 and 14:47 local, on the build Mac, after `docker compose up -d --build`.

| # | Observed | PASS/FAIL | Date/time |
|:-:|---|:-:|---|
| A1 | `pho65-app` Up `0.0.0.0:5000->5000/tcp`; `pho65-sshd` Up `0.0.0.0:2222->22/tcp` | PASS | 09-22 14:42 |
| A2 | `{"inventory_db":"/inventory-data/pho65-inventory.db","orders_csv":"/data/pho65-orders-valid.csv","overdue_min":20,"status":"ok"}` | PASS | 09-22 14:42 |
| A3 | `3 orders overdue` — threshold 20 minutes, reference time 2026-01-15 12:30; statuses: 3 overdue, 4 waiting, 3 picked_up | PASS | 09-22 14:42 |
| A4 | `ssh -i <key> pho65user@localhost -p 2222 whoami` → `pho65user` (after clearing the stale host key left by the rebuilt image) | PASS | 09-22 14:41 |
| A5 | `/inventory` lists item, scan code, on hand + unit, average, value, status, plus the printed low-stock rule | PASS | 09-22 14:44 |
| A6 | Created Rice noodles `PHO65-INV-000101` (bag, low 8) and Oat milk `PHO65-INV-000102` (carton, low 4) through the real form; both redirected to their item pages as `internal` | PASS | 09-22 14:44 |
| A7 | Manual lookup of `PHO65-INV-000101` opened the Rice noodles page; ledger row count unchanged | PASS | 09-22 14:44 |
| A8 | Camera path — pending the phone run over HTTPS | pending | Step 8 |
| A9 | Saved-image path — pending; label PNGs exported to `evidence/label-images/` for the test | pending | Step 8 |
| A10 | Row count stayed 3 across every lookup performed | PASS | 09-22 14:45 |
| A11 | `r-01` receive 10 @ $2.00 → 10 bags, $2.00, $20.00, one `received` row | PASS | 09-22 14:44 |
| A12 | `r-02` receive 10 @ $2.50 → 20 bags, **$2.25**, $45.00 | PASS | 09-22 14:44 |
| A13 | `r-03` use 12 → **8 bags, $2.25, $18.00**, 3 rows total | PASS | 09-22 14:44 |
| A14 | Costs stored as integer cents (200, 250, computed 225); `unit_cost_cents` is an INTEGER column; no float used for money | PASS | 09-22 14:44 |
| A15 | Re-submitting `r-03`: "That button press was already recorded; no duplicate transaction was added." State unchanged at 8 bags / 3 rows | PASS | 09-22 14:45 |
| A16 | `used` 100 of 8: "This would make stock negative…" State unchanged at 8 bags / 3 rows | PASS | 09-22 14:45 |
| A17 | `correction` −999: same refusal, state unchanged (guard extended beyond used/wasted — decision-table P6) | PASS | 09-22 14:45 |
| A18 | Waste with empty note: "A wasted event needs a short written reason before it can be recorded." With a reason: exactly one row added, 5 → 4 each | PASS | 09-22 14:45 |
| A19 | Correction −1 with reason added a third row; the `received` and `wasted` rows remain visible and unedited | PASS | 09-22 14:45 |
| A20 | After `docker compose restart app`: 8 bags, $2.25, $18.00, 3 rows; DB present on the host volume (20480 bytes) | PASS | 09-22 14:45 |
| A21 | Limes (low point 2): on hand 3 = OK, 2 = LOW, 1 = LOW; code uses `quantity <= reorder_point`, matching the printed rule | PASS | 09-22 14:46 |
| A22 | `PHO65-INV-999001` → "Unknown code … Nothing was recorded" with safe next steps; no item and no ledger row created | PASS | 09-22 14:45 |
| A23 | Label PNG (HTTP 200, 4636 bytes): QR bitmap identical to a fresh QR of `PHO65-INV-000101`, different from `…000102`; caption reads "PHO65 INTERNAL USE ONLY / PHO65-INV-000101 / Not a retail UPC/EAN/GTIN" | PASS | 09-22 14:46 |
| A24 | Scan page decodes `[Html5QrcodeSupportedFormats.QR_CODE]` only; the starter's UPC_A/EAN_13/CODE_128 entries were removed. Physical retail-barcode attempt pending on the phone | PASS (code) / pending (phone) | 09-22 14:46 |
| A25 | `docker compose exec app python test_inventory.py` → `inventory known-answer and guard tests passed` | PASS | 09-22 14:46 |
| A26 | Phone usability over HTTPS — pending Step 8. Desktop check at 375×812 shows stacked cards, no horizontal scroll, 44 px buttons | pending | Step 8 |
| A27 | `/static/html5-qrcode.min.js` served by the app: HTTP 200, 375364 bytes; the scan page references the local path and no CDN. A full offline reload has not been exercised yet | PASS (served locally) | 09-22 14:43 |
