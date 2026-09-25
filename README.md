# Pho65 Week 4 — Mobile Inventory (team project workspace)

A phone-friendly inventory helper built on top of the Week 3 Pho65 order tracker and SSH stack. A café worker identifies an ingredient by camera scan, saved image, or typed code, then records a RECEIVE, USE, WASTE, or CORRECTION event into an append-only SQLite ledger. Quantity and cost are recomputed by replaying that ledger, using a moving weighted average in integer cents.

Everything here is a **development pilot** on fictional data. It is not a production inventory or accounting system.

---

## 1. Team and roles

| Member | Machine | Role this checkpoint | Rotates to |
|---|---|---|---|
| Vinh Hoang | MacBook (build host) | Builder — ledger, Week 3 restore, scan paths | Verifier |
| Yuhe | MacBook | Verifier — independent re-runs | Business reviewer |
|Shiming | Ubuntu | Business reviewer — costing decision, handoff test | Builder |

Roles, the safe-stop rule, and handoff times are in [team-agreement.md](team-agreement.md); individual work is listed in [team-contributions.md](team-contributions.md).

## 2. Safe-data and credential boundary

- **Allowed:** the fictional Pho65 fixtures and internal codes (`PHO65-INV-######`), whole-unit quantities, practice purchase prices.
- **Never:** customer, supplier, or employee data; payment details; passwords; SSH **private** keys.
- **ngrok authtoken:** owned by the student running the tunnel, configured personally in a terminal the AI agent cannot see, and never stored in this repository, a prompt, a screenshot, or the submission ZIP.
- **SSH keys:** each teammate adds only their own **public** key (`.pub`) to `docker/sshd/authorized_keys`.
- The QR labels are internal-use only and are never presented as a retail UPC/EAN/GTIN.

## 3. Quick start

```bash
cd project-workspace/docker
docker compose up -d --build
docker compose ps
```

Both services should report **Up**: `pho65-app` on `5000->5000` and `pho65-sshd` on `2222->22`.

| What to open | Expected |
|---|---|
| `curl -s http://localhost:5000/health` | `{"status":"ok", …, "overdue_min":20, …}` |
| http://localhost:5000/ | Week 3 order tracker — **3 orders overdue** (O-001, O-002, O-003) |
| http://localhost:5000/inventory | Item table with on-hand, average cost, value, low-stock status |
| http://localhost:5000/inventory/scan | Camera, saved-image, and typed-code paths |
| http://localhost:5000/inventory/new | Create an internal item and its QR label |
| http://localhost:5000/inventory/staff | Edit the staff name list (PIN required) |
| `ssh -i <your-private-key> pho65user@localhost -p 2222 whoami` | `pho65user` |

Stop everything with `docker compose down` (never `-v`, which would delete the ledger).

## 4. First-run setup on a second machine (second Mac / Ubuntu)

1. Install Docker Engine + Compose plugin, Git, OpenSSH client, curl, and (for the phone test) ngrok.
2. Generate your own key and install the **public** half:
   ```bash
   ssh-keygen -t ed25519 -C "pho65-<yourname>" -f ~/.ssh/pho65_ed25519
   cat ~/.ssh/pho65_ed25519.pub >> docker/sshd/authorized_keys
   docker compose restart sshd
   ```
3. On the first SSH connection you will be asked to trust the server's key. If you instead see `REMOTE HOST IDENTIFICATION HAS CHANGED`, it is because the image was rebuilt; clear the old entry with `ssh-keygen -R "[localhost]:2222"` **only** when you know a rebuild caused it.
4. The ledger in `docker/inventory-data/` is local to each machine and is never committed.

## 5. Phone test (ngrok)

```bash
curl -s http://localhost:5000/health   # must pass first
ngrok http 5000                        # leave this terminal running
```

Open the temporary `https://…` URL on the phone, run all three identification paths, then press **Control+C** to stop the tunnel. The camera only works on the HTTPS address, never on plain `http://<laptop-ip>:5000`. Full procedure and results: [evidence/mobile-transfer-test.md](evidence/mobile-transfer-test.md).

## 6. How the numbers are produced

- **Append-only ledger.** `inventory_transactions` is only ever inserted into. A correction is a new row; nothing edits history.
- **Moving weighted average.** `new average = (old qty × old avg + received qty × receipt cost) ÷ new qty`, in whole cents, rounded half-up, applied only on receipts. USE and WASTE reduce quantity and leave the average alone.
- **Reference known answer:** receive 10 @ $2.00, receive 10 @ $2.50, use 12 → **8 units, $2.25 average, $18.00 value**. Hand calculation and observed run: [evidence/quantity-cost-known-answer.md](evidence/quantity-cost-known-answer.md).
- **Guards:** unique `request_id` (duplicate submissions rejected at the database), no event may drive stock below zero, receipts need a positive quantity and non-negative cost, WASTE and CORRECTION need a written reason.
- **Low-stock rule:** an item is LOW when `quantity <= reorder_point`. The rule is printed on the dashboard.

## 7. Verification

```bash
docker compose exec app python test_inventory.py
# inventory known-answer and guard tests passed
```

This runs the known-answer sequence against a temporary database, then proves the duplicate-request and negative-stock guards. It supplements, and does not replace, the hand calculation and the interface tests.

Evidence lives in `evidence/`: [acceptance-criteria.md](evidence/acceptance-criteria.md) · [decision-table.md](evidence/decision-table.md) · [quantity-cost-known-answer.md](evidence/quantity-cost-known-answer.md) · [failure-recovery-log.md](evidence/failure-recovery-log.md) · [regression-test.md](evidence/regression-test.md) · [mobile-transfer-test.md](evidence/mobile-transfer-test.md) · [intern-workflow-handoff.md](evidence/intern-workflow-handoff.md).

## 8. Troubleshooting

| Symptom | Likely cause | First check | Stop and ask when |
|---|---|---|---|
| `no configuration file provided: not found` | Terminal is not in `project-workspace/docker` | `pwd`, then `cd` into that folder | The folder is missing |
| Page will not load on 5000 | Docker Desktop closed, or the app container is down | `docker compose ps`; restart with `docker compose up -d --build` | A container keeps exiting — read `docker compose logs app` |
| `ssh: connect … Connection refused` on 2222 | sshd container not running or port not published | `docker compose ps` shows `2222->22` | The mapping is missing from `docker-compose.yml` |
| `Permission denied (publickey)` | Your public key is not in `docker/sshd/authorized_keys` | Add your `.pub`, `docker compose restart sshd` | Never send anyone your private key |
| `REMOTE HOST IDENTIFICATION HAS CHANGED` | The sshd image was rebuilt, so the host identity changed | Confirm a rebuild happened, then `ssh-keygen -R "[localhost]:2222"` | Nobody on the team rebuilt it |
| Camera does nothing on the phone | Page is not on HTTPS, or permission was denied | Use the ngrok `https://…` URL; otherwise use saved image or typed code | Both fallback paths also fail |
| "That button press was already recorded" | The same request ID was submitted twice | Nothing — the event recorded once. Check History | The count actually changed twice |
| "This would make stock negative" | The event exceeds what the ledger shows on hand | Count the shelf, record a CORRECTION with a reason, then the use | The physical count keeps disagreeing |
| `0 orders overdue` on `/` | Threshold in the shared config is wrong | Read `docker/shared-config/overdue.env`; it should be `OVERDUE_MIN=20` | Editing it does not change the page |

## 9. Known limitations

1. One base unit per item; case-to-bottle conversion is a deferred business decision.
2. The average hides the most recent purchase price, and it says nothing about which batch expires first.
3. No user accounts: anyone who can open the page can record an event. "Recorded by" is chosen from a staff list, not authenticated. The PIN on the staff Edit tab stops accidental edits during a shift; it is set in `docker-compose.yml`, so anyone who can read the repository can see it. It is **not** access control, and a real deployment would need staff logins.
4. The ngrok URL is a temporary development tunnel, and Flask's development server is not a production deployment.
5. Items cannot be retired or deactivated yet; the schema has no active/inactive flag.
6. Every container built from the same image shares one SSH host key, so a rebuild changes the identity a teammate has already trusted.
