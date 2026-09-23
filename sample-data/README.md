# Week 4 sample data — Pho65 inventory and Week 3 regression

Everything in this directory is fictional course data. Do not replace it with customer, supplier, or employee data.

## Inventory fixture

Read [inventory-fixture.md](inventory-fixture.md) first. It contains the two internal Pho65 codes and the cost known answer: receive 10 at $2.00, receive 10 at $2.50, use 12; expect 8 at $2.25 / $18.00. The `PHO65-INV-*` codes are internal QR-label values, not retail UPC/EAN values.

## Retained Week 3 regression data

`pho65-orders-valid.csv` remains a small order-tracker fixture. It proves that extending the application did not discard the earlier route. At the fixed Week 3 time `2026-01-15 12:30`, the original reference has three overdue unclaimed orders. `pho65-orders-edge-cases.csv` retains malformed and boundary examples for a regression discussion.

The Week 4 SQLite ledger is intentionally created in `docker/inventory-data/` when the app runs; no pre-filled database ships in the starter ZIP.

