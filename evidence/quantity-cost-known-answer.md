# Quantity and Cost Known-Answer Test (Step 3)

Item under test: **Rice noodles**, internal code `PHO65-INV-000101`, base unit **bag**, low-stock point 8.
Rule under test: moving weighted average, money stored as integer cents.

```
new average = (old quantity × old average + received quantity × receipt unit cost) ÷ new quantity
```

USE and WASTE reduce quantity and leave the average unchanged. Rounding rule: one rule everywhere — `ROUND_HALF_UP` to the nearest whole cent, applied only when a receipt recalculates the average (`app.py`, `inventory_state`).

---

## 1. Hand calculation — written before running the app

| Event | Quantity before | Average before | Event detail | Expected quantity after | Expected average after | Expected value after |
|---|---:|---:|---|---:|---:|---:|
| Receive 1 | 0 | $0.00 | receive 10 at $2.00 | 10 | $2.00 | $20.00 |
| Receive 2 | 10 | $2.00 | receive 10 at $2.50 | 20 | $2.25 | $45.00 |
| Use | 20 | $2.25 | use 12 | 8 | $2.25 | $18.00 |

Arithmetic, in cents so there is no float rounding to argue about:

- After receipt 1: total value = 10 × 200 = 2000 cents; 2000 ÷ 10 = **200 cents** ($2.00).
- After receipt 2: total value = (10 × 200) + (10 × 250) = 4500 cents; 4500 ÷ 20 = **225 cents** ($2.25). A "latest price wins" implementation would wrongly say 250.
- After use: quantity 20 − 12 = **8**; average unchanged at **225 cents**; value = 8 × 225 = **1800 cents** ($18.00).

**Expected final state: 8 bags, $2.25 average, $18.00 value.** This number is not changed to match the app.

---

## 2. Observed result — 2026-09-22, 14:44 local

Each event was submitted through the app's own transaction form with a **different** request ID.

| # | Request ID | Event submitted | Ledger row created | Observed quantity | Observed average | Observed value | Expected | PASS/FAIL |
|:-:|---|---|:-:|---:|---:|---:|---|:-:|
| 1 | `r-01` | received 10, unit cost $2.00, note "first delivery" | yes (`received`, +10, $2.00) | 10 | $2.00 | $20.00 | 10 / $2.00 / $20.00 | **PASS** |
| 2 | `r-02` | received 10, unit cost $2.50, note "second delivery" | yes (`received`, +10, $2.50) | 20 | $2.25 | $45.00 | 20 / $2.25 / $45.00 | **PASS** |
| 3 | `r-03` | used 12, note "lunch service" | yes (`used`, −12, no cost) | **8** | **$2.25** | **$18.00** | 8 / $2.25 / $18.00 | **PASS** |

Final item page line, copied from the app:

```text
PHO65-INV-000101 · internal code · 8 bag on hand · average $2.25 · value $18.00
```

Ledger row count after the sequence: **3**. No fix was needed; the hand calculation and the app agreed on the first run.

### Money stays in cents (A14)

`unit_cost_cents` is an INTEGER column; the form value `2.50` is converted with `Decimal("2.50") * 100` and quantised to a whole cent before it is stored, so 200, 250, and the computed 225 are exact integers. No binary float is used for money anywhere in the calculation.

---

## 3. Correction and persistence (Step 3.3)

Tested on a separate scratch item (**Limes**, `PHO65-INV-000103`, low point 2) so the known-answer item stays at its graded state.

| Step | Action | Observed |
|---|---|---|
| 1 | received 5 at $1.00 (`l-01`) | 5 each, avg $1.00, value $5.00, 1 row |
| 2 | wasted 1, reason "dropped on floor" (`l-03`) | 4 each, avg $1.00, value $4.00, 2 rows |
| 3 | correction −1, reason "recount after spill" (`l-04`) | 3 each, avg $1.00, value $3.00, **3 rows** |
| 4 | history check | rows read `received`, `wasted`, `correction` — the earlier rows are still present and unedited |

The correction is a **new row**. Nothing in the app can update or delete a historical transaction: the only write path is a single `INSERT`.

### Restart persistence (A20)

```text
$ docker compose restart app
 Container pho65-app Restarting
 Container pho65-app Started

item 1 after restart: 8 bag on hand · average $2.25 · value $18.00
ledger rows after restart: 3
host volume: docker/inventory-data/pho65-inventory.db  (20480 bytes)
```

The database lives on the mounted `./inventory-data` volume, so the state survives a container restart and recreation. **PASS**

---

## 3b. What happened to the original item afterwards (kept deliberately)

After the known-answer run was recorded above, the team used **Rice noodles** (`PHO65-INV-000101`, item 1) for hands-on practice on the phone and laptop, adding two more receipts:

| Row | Action | Qty | Unit cost | Note |
|---:|---|---:|---:|---|
| #1 | received | +10 | $2.00 | first delivery *(known-answer run)* |
| #2 | received | +10 | $2.50 | second delivery *(known-answer run)* |
| #3 | used | −12 | — | lunch service *(known-answer run)* |
| #9 | received | +40 | $3.00 | practice entry |
| #10 | received | +20 | $4.00 | practice entry |

Item 1 therefore now reads 68 bags at a $3.21 average. **That is the ledger behaving correctly**, and it is a useful demonstration in itself: the three original rows are still present and unedited, and anyone can replay them to see where each number came from. Nothing was deleted to tidy the number up — deleting history is exactly what this design forbids.

For the demonstration, a clean item was created instead: **Rice noodles (demo)**, `PHO65-INV-000104`, base unit bag, low-stock point 8. The same three events were recorded there with request IDs `d-01`, `d-02`, `d-03`:

```text
PHO65-INV-000104 · internal code · 8 bag on hand · average $2.25 · value $18.00
ledger rows: 3
```

Both items are kept: item 4 shows the clean known answer, and item 1 shows what a real week of entries looks like on top of it.

## 4. Packaged automated check (Step 3, Failure B evidence)

```text
$ docker compose exec app python test_inventory.py
inventory known-answer and guard tests passed
```

Which assertion proves what (from `docker/app/test_inventory.py`):

| Assertion | What it proves |
|---|---|
| `assert (state["quantity"], state["average_cents"], state["value_cents"]) == (8, 225, 1800)` | The same known answer as the hand calculation: 8 units, 225 cents average, 1800 cents value |
| re-calling `add_transaction(..., "r3")` must raise `ValueError` containing `"already recorded"` | A repeated request ID is rejected. If the duplicate had been accepted, the `else:` branch would raise `AssertionError("duplicate request was accepted")` |
| `add_transaction(item_id, "used", -100, ...)` must raise `ValueError` containing `"negative"` | Stock cannot be driven below zero |
| `label.status_code == 200 and label.mimetype == "image/png"` | The internal QR label renders |

This automated check runs against a temporary database, so it does not touch the pilot ledger. It supplements the hand calculation and the interface test; it does not replace them.
