# Pilot and Support Memo (ADI501, Step 10 G2)

**To:** Pho65 Café Owner & General Manager  
**From:** Lead Agentic Operations Consultant (ADI501 Team)  
**Date:** September 3, 2026  
**Subject:** Mobile Inventory Scanner Pilot Evaluation & Operational Support Plan  

---

## 1. Executive Pilot Recommendation

**Recommendation:** **CONTINUE WITH 30-DAY CONTROLLED PILOT** *(continue / revise / stop)*

**Core Justification (Quantitative Metric):**  
*The mobile scanner reduced dry-storage inventory check time from **25 minutes** (clipboard and manual Excel entry) to **4.5 minutes** per shift, representing an **82% reduction in labor time** while maintaining 100% mathematical accuracy on moving weighted average costs ($2.25/unit verified).*

---

## 2. System Capabilities & Scope Boundaries

### What the Pilot Application Does:
- Enables kitchen staff to record receipts (`RECEIVE`) and cooking consumption (`USE`) via phone camera QR scan, photo upload, or manual code typing.
- Maintains an append-only SQLite transaction ledger tracking timestamps, quantities, transaction costs, and running inventory balances.
- Automatically calculates moving weighted average cost and highlights active `LOW STOCK` warnings when on-hand inventory drops below minimum safety thresholds.
- Preserves the Week 3 Order Tracker and SSH administrative daemon on ports 5000 and 2222.

### What is Intentionally NOT Supported in This Pilot:
- Direct credit card processing or automated supplier electronic ordering (EDI).
- Real-time multi-location synchronization across separate franchises.
- Automatic inventory replenishment without human managerial purchase approval.

---

## 3. Safe Data, Network Tunnel & Credential Boundaries

- **Tunnel Isolation:** Mobile access is delivered via an ephemeral HTTPS ngrok tunnel. Staff phones connect over encrypted TLS without exposing café internal network subnets.
- **Credential Protection:** The ngrok authtoken and SSH private keys remain strictly on the host computer; zero credentials or database connection strings are exposed in the mobile web client.
- **Data Boundary:** Only internal item codes (e.g. `PHO65-NOODLE-01`), unit counts, and invoice dollar amounts are stored. No customer names, phone numbers, or payment tokens enter the database.

---

## 4. Worker Training & Failure Recovery Protocols

- **Onboarding:** Staff require a single 15-minute hands-on walkthrough using the `evidence/intern-workflow-handoff.md` field guide.
- **Scanner Failures:** If phone camera access is blocked or lighting is poor, staff immediately utilize the image upload or manual code entry fallback without manager intervention.
- **Stock Discrepancies:** If a negative stock error occurs, staff physically inspect the storage shelf to verify whether an unrecorded delivery arrived before notifying the supervisor.

---

## 5. Strategic Week 5 Purchasing Questions for Management

As Pho65 transitions from basic inventory logging to predictive supply replenishment in Week 5, leadership must address:

1. **Safety Stock vs. Carrying Cost:** What is the financial cost of stockouts (e.g. turning away soup customers during dinner rush) versus holding excess noodle inventory in limited dry storage space?
2. **Supplier Lead Times & Minimum Order Quantities:** How do supplier delivery schedules (e.g. twice-weekly deliveries with 20-bag minimums) influence the dynamic recalculation of our low-stock alert thresholds?
3. **Menu Margin Analysis:** How should ingredient cost fluctuations captured by our moving weighted average engine feed into periodic menu pricing adjustments?
