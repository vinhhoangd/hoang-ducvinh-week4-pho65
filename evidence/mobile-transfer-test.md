# Mobile Transfer Test (Step 8)

The phone reaches the local app through a **temporary** ngrok HTTPS tunnel. The tunnel is a development aid, not a deployment: fictional data only, open only while testing, stopped with Control+C at the end.

## Credential boundary (required statement)

**The account owner personally configured the ngrok authtoken. The token was not recorded.**

- The AI agent installed the ngrok program with an ordinary non-secret command (`brew install ngrok`, version `3.39.11`) and stopped there.
- The agent did **not** register the account, open the dashboard, see the token, or run `ngrok config add-authtoken`.
- The token appears in no file, prompt, log, screenshot, or submission ZIP.

## Setup used

| Item | Value |
|---|---|
| Tunnel operator (account owner) | Vinh Hoang |
| Local service | `http://localhost:5000` (Docker `pho65-app`) |
| Command | `ngrok http 5000` in its own terminal |
| Health check before tunnelling | `curl -s http://localhost:5000/health` → `{"status":"ok", …}` |
| Forwarding URL | temporary, not recorded here |
| Phone OS / browser |  |
| Tester (did not build this step) |  |
| Date / time |  |

## Results

| # | Check | Expected | Observed | PASS/FAIL |
|:-:|---|---|---|:-:|
| 1 | App page loaded over HTTPS | Padlock shown; page renders | | |
| 2 | Layout readable without horizontal scrolling | No sideways scroll at phone width | | |
| 3 | Buttons usable by touch | Targets at least ~44 px tall; no mis-taps | | |
| 4 | Camera prompt appeared only after a user action | Nothing happens until "Start camera" is pressed | | |
| 5 | Camera decoded the internal QR | Opens Rice noodles (`PHO65-INV-000101`) | | |
| 6 | Saved-image path decoded the same QR | Same item from `evidence/label-images/PHO65-INV-000101.png` | | |
| 7 | Manual path matched the same item | Typing the code opens the same item | | |
| 8 | Decoded string matches stored code character by character | `PHO65-INV-000101` exactly | | |
| 9 | One confirmed transaction created exactly one ledger row | Row count +1, quantity changes once | | |
| 10 | Desktop view showed the same result | Same quantity/average/value on the Mac | | |
| 11 | Camera denied → fallback works (Failure E) | Explanation shown; image/manual still work | | |
| 12 | Retail barcode does not scan | Nothing decodes (QR only) | | |

## Observations

- **First confusion or failure:**
- **Smallest improvement made:**
- **Repeated result after the improvement:**

## Shutdown

- [ ] `Control+C` pressed in the ngrok terminal; forwarding session ended.
- [ ] Reloading the temporary URL on the phone no longer reaches the app.
- [ ] Local Docker app still healthy afterwards (`curl -s http://localhost:5000/health`).

---

## How to run this test (operator checklist)

1. Confirm the app is healthy locally first:
   ```bash
   cd ~/Documents/ADI201/week4-student-starter/project-workspace/docker && docker compose ps && curl -s http://localhost:5000/health
   ```
2. Sign up personally at the ngrok dashboard and copy your authtoken **into a terminal the agent cannot see**:
   ```bash
   ngrok config add-authtoken <YOUR-TOKEN>
   ```
3. Start the tunnel in its own terminal window and leave it running:
   ```bash
   ngrok http 5000
   ```
4. Open the `https://…` forwarding URL on the phone. Go to **Scan / look up** and run all three paths on `PHO65-INV-000101`.
5. Record every row above, then press **Control+C** in the ngrok terminal.
