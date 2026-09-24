# Week 3 Regression Test (Step 1, repeated in Step 6)

Purpose: prove the Week 3 system is healthy **before** Week 4 changes, so a later failure can be told apart from a pre-existing one.

Team: Vinh Hoang (Mac, build host), Teammate B, Teammate C. Agent: Claude Code.

---

## 1. Baseline — before any Week 4 change (2026-09-22, 14:50 local)

| # | Check | Command | Observed | PASS/FAIL |
|:-:|---|---|---|:-:|
| 1 | Services running | `docker compose up -d --build` then `docker compose ps` | `pho65-app` Up `0.0.0.0:5000->5000/tcp`; `pho65-sshd` Up `0.0.0.0:2222->22/tcp` | PASS |
| 2 | Health | `curl -s http://localhost:5000/health` | `{"inventory_db":"/inventory-data/pho65-inventory.db","status":"ok"}` | PASS |
| 3 | Week 3 order route | `curl -s http://localhost:5000/` | `Pho65 order tracker (Week 3 regression)` — "10 fixture orders still load" | PASS *(but see deviation below)* |
| 4 | Inventory dashboard | `curl -s http://localhost:5000/inventory` | Dashboard renders; 0 items (empty ledger on first run) | PASS |
| 5 | SSH login | `ssh -i <private-key> pho65user@localhost -p 2222 whoami` | `pho65user` | PASS |
| 6 | Packaged test | `docker compose exec app python test_inventory.py` | `inventory known-answer and guard tests passed` | PASS |

### Deviation found at baseline: `/` lost the Week 3 overdue calculation

The Week 4 starter **rewrote** `docker/app/app.py`. Its `/` route only counts rows in the fixture CSV. The Week 3 behaviour — read `OVERDUE_MIN` from `/config/overdue.env`, apply `NOW_OVERRIDE`, and compute each order's status — is gone, so the Week 3 known answer (**3 overdue: O-001, O-002, O-003**) could not be reproduced.

- Team decision: **restore** it (see `evidence/decision-table.md`, row P1). The contract says "Preserve the Week 3 health, order-tracker, Docker, and SSH checks", and the rubric grades "Docker/health/order/SSH checks pass".
- `docker/shared-config/overdue.env` already contains `OVERDUE_MIN=20`, and compose still sets `NOW_OVERRIDE="2026-01-15 12:30"`, so the inputs were present; only the logic was missing.

### Week 3 carry-over: SSH key

`docker/sshd/authorized_keys` shipped **empty** (0 bytes), so no key-based login was possible. We installed the Week 3 public key (`~/.ssh/pho65_ed25519.pub`, fingerprint `SHA256:lT0P…`) and restarted only the `sshd` service. The private key stays in `~/.ssh` and is never copied into the project.

### Host-key change observed (expected, not an attack)

The first SSH attempt after the Week 4 build failed:

```text
@@@ WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED! @@@
Offending ECDSA key in /Users/.../.ssh/known_hosts:9
Host key verification failed.
```

Cause: Week 4 built a **new** `sshd` image, and the SSH host key is created when the image is built, so the server's identity legitimately changed from our Week 3 container. This is the exact case our Week 3 owner README told readers to call the vendor about — here, *we* are the ones who rebuilt it, and the cause is known.

Fix (one command, no files deleted): `ssh-keygen -R "[localhost]:2222"`, then reconnect and accept the new key.

```text
old host key entry removed
ssh ... whoami -> pho65user
new host key: SHA256:zVX3UzPonpXUGepTd7V5xlEPGG9CGHNGac5MWtRCaTE [localhost]:2222 (ED25519)
```

> Teammate note (Ubuntu + second Mac): each machine will see this warning once on first connect, and each teammate needs **their own** public key added to `docker/sshd/authorized_keys`. Never copy a private key between machines.

---

## 2. Re-run after the Week 4 extension (Step 6)

Run 2026-09-24 after the full Week 4 extension **and** the dependency upgrade (P17).

| # | Check | Command | Observed | PASS/FAIL |
|:-:|---|---|---|:-:|
| 1 | Services running | `docker compose ps` | `pho65-app` Up `5000->5000`; `pho65-sshd` Up `2222->22` | PASS |
| 2 | Health | `curl -s http://localhost:5000/health` | `{"inventory_db":"/inventory-data/pho65-inventory.db","orders_csv":"/data/pho65-orders-valid.csv","overdue_min":20,"staff_count":3,"status":"ok"}` | PASS |
| 3 | Week 3 order route + overdue count | `curl -s http://localhost:5000/` | Order table renders; **3 orders overdue**, threshold 20 min, reference time 2026-01-15 12:30 | PASS |
| 4 | Week 3 known answer restored | expect 3 overdue (O-001, O-002, O-003) | 3 overdue, 4 waiting, 3 picked_up — matches the Week 3 hand calculation exactly | PASS |
| 5 | SSH login | `ssh -i <private-key> pho65user@localhost -p 2222 whoami` | `pho65user` | PASS |
| 6 | Packaged test | `docker compose exec app python test_inventory.py` | `inventory known-answer and guard tests passed` | PASS |
| 7 | All Week 4 routes | `/`, `/health`, `/inventory`, `/inventory/scan`, `/inventory/new`, `/inventory/staff`, `/inventory/item/4`, `/inventory/label/4`, unknown-code lookup | every route HTTP 200 | PASS |

### Host key changed again after the base-image upgrade (expected)

Rebuilding `sshd` on Debian trixie produced a new host identity, so the first connection failed with `Host key verification failed`. Same known cause as the first rebuild, same one-line fix: `ssh-keygen -R "[localhost]:2222"`, then reconnect. New key `SHA256:qd9je/HoQvq0xFkQVZXr+bgBy5KHDfabZx/K0kztCXk`. Every teammate will see this once after pulling the upgrade.

### Versions after the upgrade

| Component | Before (starter) | After |
|---|---|---|
| Python | 3.11 | **3.14.7** |
| Flask | 3.0.3 | **3.1.3** |
| qrcode | 7.4.2 | **8.2** |
| Pillow | (transitive) | **12.3.0** |
| sshd base | Debian 12 bookworm | **Debian 13 trixie** |
| OpenSSH server | 9.2 | **10.0p2** |
| html5-qrcode | 2.3.8 | 2.3.8 (already current) |
