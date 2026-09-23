# Intern Workflow Handoff — Pho65 Mobile Inventory

For a new café intern. No programming needed. Read this once before your first shift with the pilot.

## What this pilot does — and what it does not

**It does:** let you record what came in, what was used, and what was thrown away, from a phone, and it keeps a permanent list of every entry with who recorded it.

**It does not:** order stock, talk to the till or supplier systems, track expiry dates or batches, or convert cases to bottles. It is a pilot, not the café's accounting system. One item = one base unit (a bag, a carton, an each).

## Starting the app

Ask the shift lead to start it; only one person needs to. On the café Mac:

```bash
cd ~/Documents/ADI201/week4-student-starter/project-workspace/docker && docker compose up -d --build
```

**Working means:** `http://localhost:5000/inventory` shows the item table. If the page does not load, Docker Desktop is probably closed. Open it, wait for the whale icon to settle, run the command again, and if it still fails, stop and contact the shift lead.

## Identifying an item — three ways, same result

Open **Scan / look up**. Whichever way you pick, the app shows you the item first and records nothing until you press the record button.

| Way | When to use it | What happens |
|---|---|---|
| **Camera** | Normal case, label is on the shelf | Press **Start camera**, allow the camera once, point at the label. It opens the item page |
| **Saved image** | Camera won't work, permission denied, or the label is damaged but you have a photo | Press **Choose File**, pick the photo of the label. Decoded on the phone, never uploaded |
| **Type the code** | Label is unreadable or the phone camera is broken | Type the code exactly, e.g. `PHO65-INV-000101` |

The camera only works when the page address starts with **https://**. If it refuses, use one of the other two ways instead of hunting for settings.

## Confirming before you record

The item page shows the name, the code, how many are on hand, the average cost, and the value. **Read the name.** If it is not the item in your hand, go back and identify it again. Recording is a separate, deliberate step.

## The four kinds of entry

| Entry | Use it when | Needs |
|---|---|---|
| **Received** | A delivery arrives | Quantity and the unit price paid |
| **Used** | Stock goes into service | Quantity |
| **Wasted** | Stock is dropped, spoiled, or binned | Quantity **and a short reason** |
| **Correction** | The count on the shelf disagrees with the screen | Signed amount (+/−) **and a short reason** |

A correction never erases anything. It is added as a new line, so the history shows both what was recorded and what was corrected. That is deliberate: the owner can always see why a number changed.

## Messages you may see, and what to do

| Message | What it means | What to do |
|---|---|---|
| "Unknown code … Nothing was recorded" | The label is not in the system | Check for a typo. If the item is genuinely new, tell the shift lead. Do not invent a code |
| "That button press was already recorded" | You submitted twice, perhaps a double tap | Nothing. The entry was recorded once. Check the History list to confirm |
| "This would make stock negative" | You are recording more than the screen thinks exists | Count what is physically there and record a **Correction** with a reason, then record the use |
| "A wasted event needs a short written reason" | The reason box was empty | Add a few words, like "spilled crate" |
| Camera "unavailable" or permission denied | The browser blocked the camera | Use the saved-image or typed-code path. Both work fully |

## Why the label says "internal use only"

The QR label is a Pho65 code that means something only inside this café. It is deliberately **not** a shop barcode (UPC/EAN/GTIN). Those are issued by a standards body to real products, and inventing one would put a fake product identifier into the world. Never relabel a supplier product with a Pho65 code as if it were the manufacturer's.

## Stopping the app

```bash
cd ~/Documents/ADI201/week4-student-starter/project-workspace/docker && docker compose down
```

If a phone tunnel is running (a terminal showing `ngrok`), press **Control+C** in that window first. The temporary web address must stop working when testing ends.

## Never put these anywhere

Not in a chat with an AI assistant, not in the project files, not in a screenshot, not in a message to a teammate:

- the ngrok **authtoken** or any password or API key;
- an SSH **private** key (the file **without** `.pub`);
- real customer, supplier, or employee details.

Use only the practice Pho65 data. If a secret does get posted somewhere, say so immediately — it has to be replaced at the provider, and deleting the message is not enough.

## When to ask instead of guessing

Ask the shift lead if a number looks wrong after you record it, a message repeats, the app will not start, or you are unsure which entry type applies. Do not delete anything, do not re-enter the same event "to fix it", and do not edit files.

---

## Uncoached handoff test (Step 9.2)

| Field | Record |
|---|---|
| Tester (did not build this step) |  |
| Date / time |  |
| Time to first correctly recorded transaction |  |
| Hints or interventions needed (count) |  |
| First place the tester hesitated |  |
| Exact instruction that caused it |  |
| Revision made to this document |  |
| Repeat result after the revision |  |

The builder watches without speaking until the tester finishes or stops.
