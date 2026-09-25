# Inventory Control Matrix (ADI501, Step 10 G1)

Use this document to design internal controls, governance policies, and supervisory escalation triggers for mobile inventory data entry.

> **Instructions for Graduate Students (ADI501):**
> 1. **Identify Operational and Security Risks:** Analyze realistic failure modes associated with worker phone input, network tunnels, and ledger state.
> 2. **Specify Concrete Mitigating Controls:** Detail programmatic checks, physical procedures, and role separation.
> 3. **Designate Accountable Owners:** Assign specific organizational roles responsible for oversight.
> 4. **Define Measurable Verification Evidence:** Cite the log, report, or test verifying control operation.

---

## Internal Controls Matrix

| Operational / Security Risk | Vulnerability Mechanism | Implemented Technical or Physical Control | Responsible Owner | Verification Evidence & Audit Artifact |
|---|---|---|---|---|
| **1. Accidental Duplicate Tap** | Worker double-taps submit button on lagging mobile connection, causing duplicate ledger entry. | Client button disable on tap + unique request UUID enforced as idempotency key in database transactions. | Kitchen Shift Supervisor | Verified by double-tap test script in `evidence/failure-recovery-log.md`; second request returned HTTP 409 Conflict. |
| **2. False Negative Stock State** | Worker attempts to log kitchen consumption before morning delivery receipt is entered into system. | Hard database constraint: `quantity_on_hand - use_quantity >= 0`. System blocks negative balance transactions. | Inventory Control Lead | Unit test in `test_inventory.py`; rejected attempt documented in `evidence/failure-recovery-log.md`. |
| **3. Vendor Purchase Price Shock** | Supplier invoice price surges significantly (e.g. noodle price doubles), distorting inventory valuation. | Alert trigger when entered invoice unit cost deviates by >25% from current weighted average; requires manager PIN override. | Purchasing Manager / Owner | System alert log flagged in `/inventory/audit`; cost calculation verified in `evidence/quantity-cost-known-answer.md`. |
| **4. Unregistered / Corrupted QR Code** | Worker scans damaged packaging barcode or wrong vendor label, returning invalid item code. | Strict regex validation on item codes (`PHO65-[A-Z]+-[0-9]{2}`) against master database catalog before accepting input. | Kitchen Floor Staff | Camera and manual test documented in `evidence/failure-recovery-log.md`; returns clear non-technical error. |
| **5. Tunnel / Credential Exposure** | Public exposure of ngrok URL or authtoken allows unauthorized external parties to modify inventory ledger. | Tunnel runs ephemerally without storing token in repo; HTTPS transport encryption enforced; web UI password protected in production. | Systems Operations Consultant | Verification checklist in `evidence/mobile-transfer-test.md`; no secrets committed in git history. |
