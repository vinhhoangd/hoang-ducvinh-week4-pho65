"""Pho65 Week 4: a deliberately small, inspectable inventory ledger.

Week 4 extends the Week 3 order tracker; it does not replace it. The Week 3
overdue calculation is kept intact on "/" as a regression check.
"""
import csv
import io
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

import qrcode
from PIL import Image, ImageDraw
from flask import Flask, abort, flash, jsonify, redirect, render_template_string, request, send_file, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "week4-local-demo-only")

ORDERS_CSV = os.environ.get("ORDERS_CSV", "/data/pho65-orders-valid.csv")
DB_PATH = os.environ.get("INVENTORY_DB", "/inventory-data/pho65-inventory.db")

# --- Week 3 order-tracker settings (regression) -----------------------------
# OVERDUE_MIN is re-read from the shared config file on every request so it can
# still be fixed over SSH without rebuilding, exactly as in Week 3.
OVERDUE_MIN_CONFIG_PATH = os.environ.get("OVERDUE_MIN_CONFIG_PATH", "/config/overdue.env")
OVERDUE_MIN_DEFAULT = int(os.environ.get("OVERDUE_MIN", 20))
NOW_OVERRIDE = os.environ.get("NOW_OVERRIDE") or None

# --- Staff list (tap instead of type) ---------------------------------------
STAFF_CONFIG_PATH = os.environ.get("STAFF_CONFIG_PATH", "/config/staff.txt")
DEFAULT_STAFF = ["Vinh Hoang", "Yuhe", "Shiming"]
# Local pilot PIN: a guard against accidental edits during a shift, NOT
# authentication. It is visible to anyone who can read the compose file.
STAFF_PIN = os.environ.get("STAFF_PIN", "2468")

# Reducing events. Any of these may drive stock down, so all of them are guarded.
REDUCING_ACTIONS = {"used", "wasted", "counted", "correction"}
# Events a worker must explain in writing.
REASON_REQUIRED_ACTIONS = {"wasted", "correction"}
# Tap-able reasons, so a worker rarely has to open the keyboard.
QUICK_REASONS = {
    "wasted": ["spilled", "spoiled", "dropped", "over-prepped"],
    "correction": ["recount after spill", "entry error", "found extra stock"],
}
ACTION_HELP = {
    "received": "A delivery arrived. Add stock and record what it cost per unit.",
    "used": "Stock went into service. Removes from on hand.",
    "wasted": "Spoiled, dropped, or binned. Removes from on hand and needs a reason.",
    "counted": "The shelf count differs. Enter the difference, + or −.",
    "correction": "Fix an earlier mistake. Added as a new row, with a reason.",
}


def db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS items (
          id INTEGER PRIMARY KEY,
          name TEXT NOT NULL,
          scan_code TEXT NOT NULL UNIQUE,
          code_kind TEXT NOT NULL CHECK(code_kind IN ('manufacturer', 'internal')),
          base_unit TEXT NOT NULL,
          reorder_point INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS inventory_transactions (
          id INTEGER PRIMARY KEY,
          item_id INTEGER NOT NULL REFERENCES items(id),
          action TEXT NOT NULL CHECK(action IN ('starting', 'received', 'used', 'wasted', 'counted', 'correction')),
          quantity_delta INTEGER NOT NULL,
          unit_cost_cents INTEGER,
          occurred_at TEXT NOT NULL,
          recorded_by TEXT NOT NULL,
          note TEXT NOT NULL DEFAULT '',
          request_id TEXT NOT NULL UNIQUE
        );
        """)
        # Archiving column, added without touching existing rows or history.
        columns = [row["name"] for row in con.execute("PRAGMA table_info(items)")]
        if "archived_at" not in columns:
            con.execute("ALTER TABLE items ADD COLUMN archived_at TEXT")


def money(cents):
    return f"${Decimal(cents or 0) / 100:.2f}"


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def short_time(value):
    """2026-09-22T18:44:03+00:00 -> 22 Sep 18:44 (kept simple on purpose)."""
    try:
        moment = datetime.fromisoformat(value)
        return moment.strftime("%d %b %H:%M")
    except (TypeError, ValueError):
        return value


def staff_list():
    """Read the pilot staff names fresh on every request."""
    try:
        with open(STAFF_CONFIG_PATH, "r", encoding="utf-8") as handle:
            names = [line.strip() for line in handle
                     if line.strip() and not line.strip().startswith("#")]
        if names:
            return names
    except FileNotFoundError:
        print(f"Warning: {STAFF_CONFIG_PATH} not found; using the built-in staff list")
    return list(DEFAULT_STAFF)


def save_staff(names):
    os.makedirs(os.path.dirname(STAFF_CONFIG_PATH), exist_ok=True)
    with open(STAFF_CONFIG_PATH, "w", encoding="utf-8") as handle:
        handle.write("# Pho65 pilot staff list. One name per line; blank lines and #comments ignored.\n")
        handle.write("# Edit here, over SSH at /config/staff.txt, or in the app at /inventory/staff (PIN required).\n")
        handle.write("# Fictional class data only - no real employee records.\n")
        handle.write("\n".join(names) + "\n")


def inventory_state(item_id):
    """Replay one item's ledger. Receipts reset the moving weighted average.

    Quantities and costs are integer base units/cents: no binary float surprises.
    """
    with db() as con:
        rows = con.execute("""SELECT * FROM inventory_transactions
                            WHERE item_id=? ORDER BY occurred_at, id""", (item_id,)).fetchall()
    quantity, average_cents = 0, 0
    for row in rows:
        delta = row["quantity_delta"]
        if delta > 0 and row["unit_cost_cents"] is not None:
            total_value = quantity * average_cents + delta * row["unit_cost_cents"]
            quantity += delta
            average_cents = int((Decimal(total_value) / quantity).quantize(Decimal("1"), ROUND_HALF_UP))
        else:
            quantity += delta
    return {"quantity": quantity, "average_cents": average_cents,
            "value_cents": quantity * average_cents, "transactions": rows}


def all_items(archived=False):
    clause = "archived_at IS NOT NULL" if archived else "archived_at IS NULL"
    with db() as con:
        rows = con.execute(f"SELECT * FROM items WHERE {clause} ORDER BY name").fetchall()
    result = []
    for row in rows:
        state = inventory_state(row["id"])
        result.append({**dict(row), **state, "low": state["quantity"] <= row["reorder_point"]})
    return result


def ledger_row_count(item_id):
    with db() as con:
        return con.execute("SELECT COUNT(*) AS n FROM inventory_transactions WHERE item_id=?",
                           (item_id,)).fetchone()["n"]


def add_transaction(item_id, action, quantity_delta, unit_cost_cents, recorded_by, note, request_id):
    if not request_id:
        raise ValueError("Missing request ID. Refresh and try again.")
    state = inventory_state(item_id)
    # Every reducing event is guarded, not only used/wasted: a signed counted or
    # correction event must not drive stock below zero either.
    if quantity_delta < 0 and action in REDUCING_ACTIONS and state["quantity"] + quantity_delta < 0:
        raise ValueError("This would make stock negative. Count what is present or record a correction with an explanation.")
    if action in REASON_REQUIRED_ACTIONS and not (note or "").strip():
        raise ValueError(f"A {action} event needs a short written reason before it can be recorded.")
    if action in {"received", "starting"} and (quantity_delta <= 0 or unit_cost_cents is None or unit_cost_cents < 0):
        raise ValueError("A receipt needs a positive quantity and a non-negative unit purchase cost.")
    with db() as con:
        try:
            con.execute("""INSERT INTO inventory_transactions
                (item_id, action, quantity_delta, unit_cost_cents, occurred_at, recorded_by, note, request_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (item_id, action, quantity_delta, unit_cost_cents, utc_now(), recorded_by, note, request_id))
        except sqlite3.IntegrityError as error:
            if "request_id" in str(error):
                raise ValueError("That button press was already recorded; no duplicate transaction was added.") from error
            raise


def code_for_new_item():
    with db() as con:
        last = con.execute("SELECT scan_code FROM items WHERE scan_code LIKE 'PHO65-INV-%' ORDER BY scan_code DESC LIMIT 1").fetchone()
    number = int(last["scan_code"].rsplit("-", 1)[1]) + 1 if last else 101
    return f"PHO65-INV-{number:06d}"


# --- Week 3 order tracker ---------------------------------------------------

def get_overdue_min():
    """Read OVERDUE_MIN fresh from the shared config file on every call."""
    try:
        with open(OVERDUE_MIN_CONFIG_PATH, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line.startswith("OVERDUE_MIN="):
                    return int(line.split("=", 1)[1].strip())
    except FileNotFoundError:
        print(f"Warning: {OVERDUE_MIN_CONFIG_PATH} not found; using default OVERDUE_MIN={OVERDUE_MIN_DEFAULT}")
        return OVERDUE_MIN_DEFAULT
    except (ValueError, IndexError):
        print(f"Warning: could not parse OVERDUE_MIN from {OVERDUE_MIN_CONFIG_PATH}; using default {OVERDUE_MIN_DEFAULT}")
        return OVERDUE_MIN_DEFAULT
    return OVERDUE_MIN_DEFAULT


def parse_datetime(value):
    if not value or not value.strip():
        return None
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d %H:%M")
    except ValueError:
        return None


def order_now():
    return parse_datetime(NOW_OVERRIDE) if NOW_OVERRIDE else datetime.now()


def order_status(order, overdue_min, now):
    """Week 3 rule: overdue only if unclaimed AND (now - ordered_at) > OVERDUE_MIN."""
    ordered_at = parse_datetime(order.get("ordered_at", ""))
    picked_up_at = parse_datetime(order.get("picked_up_at", ""))
    status = (order.get("status") or "").strip().lower()
    if ordered_at is None:
        return "needs-review"
    if picked_up_at is not None and picked_up_at < ordered_at:
        return "needs-review"
    if status == "picked_up":
        return "picked_up"
    if status == "unclaimed":
        minutes = (now - ordered_at).total_seconds() / 60
        return "overdue" if minutes > overdue_min else "waiting"
    return "needs-review"


BASE = """
<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>
<title>Pho65 Inventory</title><style>
:root{--bg:#eef2f0;--card:#fff;--ink:#16241f;--muted:#5d6d66;--line:#dce4e0;--brand:#0a6a5b;--brand-soft:#e7f1ee;--accent:#0b74d1;--warn:#b3261e;--warn-soft:#fdeceb;--ok:#0f7a3d;--radius:14px}
*{box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--ink);margin:0;padding:0 0 3rem;line-height:1.5}
.wrap{max-width:820px;margin:0 auto;padding:0 1rem}
header.bar{background:var(--brand);color:#fff;padding:.9rem 0;margin-bottom:1.2rem}
header.bar .wrap{display:flex;flex-wrap:wrap;gap:.9rem;align-items:center}
header.bar .brand{font-weight:700;letter-spacing:.02em;margin-right:auto}
nav{display:flex;gap:.4rem;flex-wrap:wrap}
nav a{color:#fff;text-decoration:none;padding:.45rem .8rem;border-radius:999px;font-size:.94rem;background:rgba(255,255,255,.12)}
nav a:hover{background:rgba(255,255,255,.25)}
h1{font-size:1.55rem;margin:.2rem 0 .3rem}h2{font-size:1.1rem;margin:0 0 .6rem}
p{margin:.45rem 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:1.1rem;margin:1rem 0;box-shadow:0 1px 2px rgba(20,40,30,.05)}
.hint{color:var(--muted);font-size:.92rem}
.code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;background:#f1f5f3;padding:.1rem .35rem;border-radius:5px}
.flash{background:#fff7d6;border:1px solid #e8d48a;border-left:5px solid #e0b93c;padding:.8rem 1rem;border-radius:10px;margin:.8rem 0}
table{border-collapse:collapse;width:100%}th,td{padding:.6rem .5rem;border-bottom:1px solid var(--line);text-align:left;font-size:.95rem}
th{font-size:.8rem;text-transform:uppercase;letter-spacing:.04em;color:var(--muted)}
.stats{display:flex;gap:.7rem;flex-wrap:wrap;margin:.8rem 0}
.stat{flex:1 1 140px;background:var(--brand-soft);border-radius:12px;padding:.75rem .9rem}
.stat .k{font-size:.78rem;text-transform:uppercase;letter-spacing:.04em;color:var(--muted)}
.stat .v{font-size:1.5rem;font-weight:700}
.pill{display:inline-block;padding:.2rem .7rem;border-radius:999px;font-size:.82rem;font-weight:600}
.pill.ok{background:#e6f4ec;color:var(--ok)}.pill.low{background:var(--warn-soft);color:var(--warn)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:.9rem}
.itemcard{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:.9rem 1rem;text-decoration:none;color:inherit;display:block}
.itemcard:hover{border-color:var(--brand)}
.itemcard .nm{font-weight:700;font-size:1.05rem}
.itemwrap{position:relative}
.removebtn{position:absolute;top:.55rem;right:.55rem;background:#fff;color:var(--warn);border:1.5px solid var(--line);border-radius:999px;padding:.3rem .75rem;font:inherit;font-size:.85rem;min-height:34px;cursor:pointer;opacity:0;transition:opacity .12s}
.itemwrap:hover .removebtn,.itemwrap:focus-within .removebtn{opacity:1}
.removebtn:hover{border-color:var(--warn);background:var(--warn-soft)}
@media(hover:none){.removebtn{opacity:1}}
.step{display:flex;align-items:center;gap:.6rem;margin:1.4rem 0 .5rem;font-weight:700}
.step .n{background:var(--brand);color:#fff;width:28px;height:28px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-size:.9rem;flex:none}
.taprow{display:flex;flex-wrap:wrap;gap:.5rem;margin:.4rem 0}
.tap{background:#fff;color:var(--ink);border:1.5px solid var(--line);border-radius:999px;padding:.65rem 1.1rem;min-height:48px;font:inherit;cursor:pointer}
.tap:hover{border-color:var(--brand)}
.tap[aria-pressed=true]{background:var(--brand);color:#fff;border-color:var(--brand);font-weight:600}
.stepper{display:flex;align-items:center;justify-content:center;gap:1rem;margin:.6rem 0}
.round{width:58px;height:58px;border-radius:50%;border:2px solid var(--accent);background:#fff;color:var(--accent);font-size:1.7rem;line-height:1;cursor:pointer;display:flex;align-items:center;justify-content:center;flex:none}
.round:hover{background:#eaf3fc}.round:active{transform:scale(.95)}
.qtybox{width:132px;height:58px;text-align:center;font-size:1.5rem;font-weight:700;border:1.5px solid var(--line);border-radius:10px;background:#fff;color:var(--ink)}
input[type=text],input[type=number],input:not([type]),select{font:inherit;padding:.6rem .7rem;border:1.5px solid var(--line);border-radius:10px;background:#fff;color:var(--ink);width:100%;max-width:320px}
label{display:block;margin:.6rem 0;font-size:.95rem}
button.primary{background:var(--brand);color:#fff;border:0;border-radius:12px;padding:1rem 1.3rem;font:inherit;font-weight:700;font-size:1.05rem;width:100%;min-height:56px;cursor:pointer}
button.primary:disabled{background:var(--muted)}
button.ghost{background:#fff;border:1.5px solid var(--line);border-radius:10px;padding:.6rem 1rem;font:inherit;min-height:48px;cursor:pointer}
.summary{background:var(--brand-soft);border-radius:12px;padding:.85rem 1rem;font-size:1.02rem;margin:1.1rem 0 .6rem}
.overdue{color:var(--warn);font-weight:700}.waiting{color:var(--accent)}.picked_up{color:var(--ok)}.needs-review{color:#9a6700}
details summary{cursor:pointer;min-height:44px;color:var(--muted)}
.actionhelp{color:var(--muted);font-size:.92rem;margin:.1rem 0 .3rem}
@media(max-width:560px){h1{font-size:1.35rem}.wrap{padding:0 .8rem}.card{padding:.9rem}.stat .v{font-size:1.3rem}}
</style></head><body>
<header class=bar><div class=wrap><span class=brand>Pho65 Inventory</span>
<nav><a href='/inventory'>Items</a><a href='/inventory/scan'>Scan</a><a href='/inventory/new'>New item</a><a href='/inventory/staff'>Staff</a><a href='/'>Week 3 orders</a></nav></div></header>
<div class=wrap>{% with messages=get_flashed_messages() %}{% for m in messages %}<p class=flash>{{m}}</p>{% endfor %}{% endwith %}{{ body|safe }}</div></body></html>
"""


def page(body, **context):
    return render_template_string(BASE, body=render_template_string(body, **context))


@app.route("/inventory")
def inventory():
    return page("""<h1>Items</h1><p class=hint>Every number is replayed from the ledger. Tap an item to record what happened to it.</p>
    <div class=grid>
    {% for i in items %}<div class=itemwrap>
      <a class=itemcard href='/inventory/item/{{i.id}}'>
      <div class=nm>{{i.name}}</div>
      <div class=hint><span class=code>{{i.scan_code}}</span></div>
      <div class=stats style='margin:.6rem 0 .4rem'>
        <div class=stat><div class=k>On hand</div><div class=v>{{i.quantity}}</div><div class=hint>{{i.base_unit}}</div></div>
        <div class=stat><div class=k>Avg cost</div><div class=v>{{money(i.average_cents)}}</div><div class=hint>value {{money(i.value_cents)}}</div></div>
      </div>
      <span class='pill {{ "low" if i.low else "ok" }}'>{{ "LOW — review" if i.low else "OK" }}</span>
      <span class=hint>low at {{i.reorder_point}}</span>
      </a>
      <form method=post action='/inventory/item/{{i.id}}/remove' onsubmit="return confirm('Remove {{i.name}} from the list?\\n\\nIf it has recorded history it is archived, not deleted — the ledger is kept and you can restore it.');">
        <button class=removebtn type=submit title='Remove from the list'>Remove</button></form>
    </div>{% endfor %}
    </div>
    {% if not items %}<div class=card><p>No items yet. <a href='/inventory/new'>Create the first internal item</a>.</p></div>{% endif %}
    {% if archived %}<details class=card><summary><strong>Removed items ({{archived|length}})</strong> — history kept</summary>
      <table><tr><th>Item</th><th>Code</th><th>Ledger rows</th><th></th></tr>
      {% for a in archived %}<tr><td><a href='/inventory/item/{{a.id}}'>{{a.name}}</a></td><td class=code>{{a.scan_code}}</td><td>{{a.transactions|length}}</td>
      <td><form method=post action='/inventory/item/{{a.id}}/restore'><button class=ghost>Restore</button></form></td></tr>{% endfor %}</table>
      <p class=hint>Items with recorded history are archived rather than deleted, so the ledger stays complete and auditable.</p></details>{% endif %}

    <div class=card><h2>How the numbers work</h2>
    <p class=hint>An item is <strong>LOW</strong> when its quantity is at or below its low-stock point (quantity &lt;= reorder point).</p>
    <p class=hint>Reference costing: receive 10 at $2.00, receive 10 at $2.50, then use 12 → 8 left, $2.25 average, $18.00 value.</p></div>""",
    items=all_items(), archived=all_items(archived=True), money=money)


@app.post("/inventory/item/<int:item_id>/remove")
def remove_item(item_id):
    """Remove an item from the list.

    An item that has never been used is deleted outright. An item with ledger
    history is archived instead: deleting it would orphan its transactions and
    break the append-only rule the whole design rests on.
    """
    with db() as con:
        item = con.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
    if not item:
        abort(404)
    rows = ledger_row_count(item_id)
    with db() as con:
        if rows == 0:
            con.execute("DELETE FROM items WHERE id=?", (item_id,))
            flash(f"Deleted {item['name']}. It had no recorded history, so nothing was lost.")
        else:
            con.execute("UPDATE items SET archived_at=? WHERE id=?", (utc_now(), item_id))
            flash(f"Archived {item['name']}. Its {rows} ledger rows are kept — open 'Removed items' to restore it.")
    return redirect(url_for("inventory"))


@app.post("/inventory/item/<int:item_id>/restore")
def restore_item(item_id):
    with db() as con:
        con.execute("UPDATE items SET archived_at=NULL WHERE id=?", (item_id,))
    flash("Item restored to the list.")
    return redirect(url_for("inventory"))


@app.route("/inventory/lookup")
def lookup():
    code = request.args.get("code", "").strip().upper()
    with db() as con:
        item = con.execute("SELECT id FROM items WHERE scan_code=?", (code,)).fetchone()
    if item:
        return redirect(url_for("item_detail", item_id=item["id"]))
    return page("""<h1>Code not found</h1>
    <div class=card><p><span class=code>{{code}}</span> is not in Pho65 inventory. <strong>Nothing was recorded.</strong></p>
    <p class=hint>Safe next steps:</p>
    <ul class=hint><li>check the label for a typo and try again;</li><li>find the item by name on the <a href='/inventory'>items list</a>;</li><li>create it only if it is genuinely new.</li></ul>
    <p><a class=tap href='/inventory/scan'>Try again</a> <a class=tap href='/inventory/new?code={{code}}'>Create internal item</a></p></div>""",
    code=code or "(blank)")


@app.route("/inventory/scan")
def scan():
    return page("""<h1>Find an item</h1>
    <p class=hint>Three ways, same result. The app shows you the item first — <strong>nothing is recorded by scanning</strong>.</p>

    <div class=card><div class=step><span class=n>1</span> Camera</div>
    <p class=hint>On a phone this page must be open through the <strong>https://</strong> address, or the browser will not allow the camera.</p>
    <button type=button class=primary id=camstart>Start camera</button>
    <button type=button class=ghost id=camstop hidden>Stop camera</button>
    <p id=cammsg class=hint></p><div id=reader></div></div>

    <div class=card><div class=step><span class=n>2</span> Photo of the label</div>
    <p class=hint>Camera blocked or broken? Choose a saved photo. It is read on this device and never uploaded.</p>
    <label>Label image <input type=file accept='image/*' id=imgfile></label>
    <p id=filemsg class=hint></p><div id=filereader hidden></div></div>

    <div class=card><div class=step><span class=n>3</span> Type the code</div>
    <form action='/inventory/lookup'><label>Internal code <input name=code class=code placeholder='PHO65-INV-000101' required></label>
    <button class=primary>Find item</button></form></div>

    <script src='/static/html5-qrcode.min.js'></script><script>
    function found(text){ location.assign('/inventory/lookup?code='+encodeURIComponent(text.trim())); }
    var QR_ONLY = window.Html5QrcodeSupportedFormats ? [Html5QrcodeSupportedFormats.QR_CODE] : undefined;
    var camera = null;
    document.getElementById('camstart').onclick = function(){
      if(!window.Html5Qrcode){ document.getElementById('cammsg').textContent = 'Scanner did not load. Use a photo or type the code.'; return; }
      camera = new Html5Qrcode('reader', { formatsToSupport: QR_ONLY });
      document.getElementById('cammsg').textContent = 'Asking for camera permission…';
      camera.start({ facingMode: 'environment' }, { fps: 10, qrbox: { width: 240, height: 240 } }, function(text){
        camera.stop().then(function(){ found(text); });
      }, function(){}).then(function(){
        document.getElementById('cammsg').textContent = 'Point the camera at a Pho65 label.';
        document.getElementById('camstart').hidden = true; document.getElementById('camstop').hidden = false;
      }).catch(function(err){
        document.getElementById('cammsg').textContent = 'Camera unavailable (' + err + '). Use option 2 or 3 below — both work without the camera.';
      });
    };
    document.getElementById('camstop').onclick = function(){
      if(camera){ camera.stop().then(function(){ camera.clear(); }); }
      document.getElementById('camstart').hidden = false; document.getElementById('camstop').hidden = true;
      document.getElementById('cammsg').textContent = 'Camera stopped.';
    };
    document.getElementById('imgfile').onchange = function(event){
      var file = event.target.files[0]; if(!file) return;
      if(!window.Html5Qrcode){ document.getElementById('filemsg').textContent = 'Scanner did not load. Type the code instead.'; return; }
      var fileScanner = new Html5Qrcode('filereader', { formatsToSupport: QR_ONLY });
      document.getElementById('filemsg').textContent = 'Reading image…';
      fileScanner.scanFile(file, false).then(found).catch(function(err){
        document.getElementById('filemsg').textContent = 'No Pho65 QR code found in that image. Try a clearer photo, or type the code.';
      });
    };
    window.addEventListener('pagehide', function(){ if(camera){ camera.stop().catch(function(){}); } });
    </script>""")


@app.route("/inventory/new", methods=["GET", "POST"])
def new_item():
    suggested = request.args.get("code", "") or code_for_new_item()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        code = request.form.get("scan_code", "").strip().upper()
        unit = request.form.get("base_unit", "each").strip().lower()
        try: point = int(request.form.get("reorder_point", "0"))
        except ValueError: point = -1
        if not name or not code.startswith("PHO65-INV-") or point < 0 or not unit:
            flash("Use a name, non-negative low-stock point, a unit, and a PHO65-INV internal code.")
        else:
            try:
                with db() as con: con.execute("INSERT INTO items (name,scan_code,code_kind,base_unit,reorder_point,created_at) VALUES (?,?,?,?,?,?)", (name, code, "internal", unit, point, utc_now()))
                flash("Internal item created. Print its label — it is not a retail UPC/EAN.")
                return redirect(url_for("item_detail", item_id=con.execute("SELECT id FROM items WHERE scan_code=?", (code,)).fetchone()["id"]))
            except sqlite3.IntegrityError: flash("That code already exists. Do not make a duplicate label.")
    return page("""<h1>New internal item</h1>
    <p class=hint>Pho65 assigns its own QR label for items without a manufacturer code. It is for internal use only and is never a retail UPC/EAN/GTIN.</p>
    <form method=post class=card>
      <label>Name <input name=name placeholder='Rice noodles' required></label>
      <label>Internal code <input class=code name=scan_code value='{{suggested}}' required></label>
      <label>Base unit <input name=base_unit value=each required> <span class=hint>bag, carton, each — one unit per item</span></label>
      <label>Low-stock point <input type=number min=0 name=reorder_point value=0 required> <span class=hint>Flag as LOW at or below this number</span></label>
      <button class=primary>Create item and label</button>
    </form>""", suggested=suggested)


@app.route("/inventory/staff", methods=["GET", "POST"])
def staff_admin():
    names = staff_list()
    if request.method == "POST":
        pin = request.form.get("pin", "").strip()
        add = request.form.get("add_name", "").strip()
        remove = request.form.get("remove_name", "").strip()
        if pin != STAFF_PIN:
            flash("Wrong PIN. The staff list was not changed.")
        elif add:
            if add in names:
                flash(f"{add} is already on the list.")
            else:
                save_staff(names + [add]); flash(f"Added {add} to the staff list.")
        elif remove:
            if remove not in names:
                flash("That name is not on the list.")
            elif len(names) <= 1:
                flash("Keep at least one name on the list.")
            else:
                save_staff([n for n in names if n != remove]); flash(f"Removed {remove} from the staff list.")
        else:
            flash("Type a name to add, or press Remove next to a name.")
        return redirect(url_for("staff_admin"))
    return page("""<h1>Staff list</h1>
    <p class=hint>These names become buttons on the record form, so nobody has to type a name during a shift.</p>
    <div class=card><h2>Current staff</h2>
    <table><tr><th>Name</th><th></th></tr>
    {% for n in names %}<tr><td>{{n}}</td>
    <td><form method=post style='display:flex;gap:.5rem;align-items:center;flex-wrap:wrap'>
      <input type=hidden name=remove_name value='{{n}}'>
      <input name=pin inputmode=numeric autocomplete=off placeholder=PIN required style='max-width:110px'>
      <button class=ghost>Remove</button></form></td></tr>{% endfor %}</table></div>
    <div class=card><h2>Add someone</h2>
    <form method=post><label>Name <input name=add_name placeholder='New teammate' required></label>
    <label>PIN <input name=pin inputmode=numeric autocomplete=off required style='max-width:150px'></label>
    <button class=primary>Add to staff list</button></form></div>
    <div class=card><h2>About the PIN</h2>
    <p class=hint>The PIN only prevents accidental edits during a shift. <strong>It is not a login and not a secret</strong> — it is set in <span class=code>docker-compose.yml</span>, so anyone who can read the project can see it. Never put a real password here. Proper staff accounts are listed as a known limitation in the README.</p>
    <p class=hint>The list is stored at <span class=code>/config/staff.txt</span>, so it can also be edited over SSH, exactly like the Week 3 threshold file.</p></div>""",
    names=names)


@app.route("/inventory/item/<int:item_id>")
def item_detail(item_id):
    with db() as con: item = con.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
    if not item: abort(404)
    state = inventory_state(item_id)
    low = state["quantity"] <= item["reorder_point"]
    return page("""<h1>{{item.name}}</h1>
    <p class=hint><span class=code>{{item.scan_code}}</span> · {{item.code_kind}} code · low at {{item.reorder_point}}
    <span class='pill {{ "low" if low else "ok" }}'>{{ "LOW — review" if low else "OK" }}</span></p>
    <div class=stats>
      <div class=stat><div class=k>On hand</div><div class=v>{{state.quantity}}</div><div class=hint>{{item.base_unit}}</div></div>
      <div class=stat><div class=k>Average cost</div><div class=v>{{money(state.average_cents)}}</div><div class=hint>per {{item.base_unit}}</div></div>
      <div class=stat><div class=k>Stock value</div><div class=v>{{money(state.value_cents)}}</div><div class=hint>{{state.transactions|length}} ledger rows</div></div>
    </div>
    <p class=hint>Check the name above before recording. Looking an item up never changes stock.
    {% if item.code_kind == 'internal' %}<a href='/inventory/label/{{item.id}}'>Print internal QR label</a>{% endif %}</p>

    <form action='/inventory/transaction' method=post class=card>
      <input type=hidden name=item_id value='{{item.id}}'><input type=hidden name=request_id value='{{request_id}}'>

      <div class=step><span class=n>1</span> What happened?</div>
      <div class=taprow id=actionrow>
        <button type=button class=tap data-action=received aria-pressed=true>Received</button>
        <button type=button class=tap data-action=used aria-pressed=false>Used</button>
        <button type=button class=tap data-action=wasted aria-pressed=false>Wasted</button>
        <button type=button class=tap data-action=counted aria-pressed=false>Counted</button>
        <button type=button class=tap data-action=correction aria-pressed=false>Correction</button>
      </div>
      <p class=actionhelp id=actionhelp></p>
      <input type=hidden name=action id=actionfield value=received>

      <div class=step><span class=n>2</span> Quantity</div>
      <div class=stepper>
        <button type=button class=round id=minus aria-label='one fewer'>−</button>
        <input class=qtybox name=quantity id=qtyfield value=1 inputmode=numeric required aria-label='quantity'>
        <button type=button class=round id=plus aria-label='one more'>+</button>
      </div>
      <div class=taprow id=qtyrow style='justify-content:center'>
        <button type=button class=tap data-qty=1>1</button>
        <button type=button class=tap data-qty=5>5</button>
        <button type=button class=tap data-qty=10>10</button>
        <button type=button class=tap data-qty=100>100</button>
      </div>
      <p class=hint style='text-align:center'>Counted and Correction accept a negative number, e.g. −3.</p>

      <div id=costblock><div class=step><span class=n>3</span> Cost per {{item.base_unit}}</div>
      <label><input name=unit_cost id=costfield placeholder='2.50' inputmode=decimal style='max-width:180px'>
      <span class=hint>Copy this from the invoice — never guess it.</span></label></div>

      <div class=step><span class=n id=staffnum>4</span> Who is recording?</div>
      <div class=taprow id=staffrow>{% for n in staff %}<button type=button class=tap data-staff='{{n}}' aria-pressed=false>{{n}}</button>{% endfor %}</div>
      <details><summary>Someone else</summary><label>Name <input id=staffother placeholder='Type a name'></label></details>

      <div class=step><span class=n id=reasonnum>5</span> Reason <span class=hint id=reasonhint></span></div>
      <div class=taprow id=reasonrow></div>
      <label><input name=note id=notefield placeholder='Short reason'></label>
      <input type=hidden name=recorded_by id=stafffield value=''>

      <p class=summary id=summary></p>
      <button class=primary id=submitbtn>Record this event</button>
      <p class=hint style='text-align:center'>One press = one ledger row. A repeat press is refused, never doubled.</p>
    </form>

    <div class=card><h2>History</h2>
    <table><tr><th>When</th><th>What</th><th>Change</th><th>Cost</th><th>Who / reason</th></tr>
    {% for t in state.transactions|reverse %}<tr><td>{{short_time(t.occurred_at)}}</td><td>{{t.action}}</td><td>{{'+' if t.quantity_delta > 0 else ''}}{{t.quantity_delta}}</td><td>{{money(t.unit_cost_cents) if t.unit_cost_cents is not none else '—'}}</td><td>{{t.recorded_by}}{% if t.note %} · {{t.note}}{% endif %}</td></tr>{% endfor %}</table>
    <p class=hint>Newest first. History is append-only: a correction is a new row and never erases the row it corrects.</p></div>

    <script>
    var QUICK = {{ quick_reasons|tojson }}, HELP = {{ action_help|tojson }}, UNIT = {{ item.base_unit|tojson }};
    var actionField = document.getElementById('actionfield'), qty = document.getElementById('qtyfield');
    var costBlock = document.getElementById('costblock'), reasonRow = document.getElementById('reasonrow');
    var note = document.getElementById('notefield'), staffField = document.getElementById('stafffield');
    var summary = document.getElementById('summary'), cost = document.getElementById('costfield');
    function press(row, button){ if(!row) return; row.querySelectorAll('.tap').forEach(function(b){ b.setAttribute('aria-pressed', b === button ? 'true' : 'false'); }); }
    function label(action){ return {received:'Received', used:'Used', wasted:'Wasted', counted:'Counted', correction:'Correction'}[action] || action; }
    function refresh(){
      var action = actionField.value, needsReason = (action === 'wasted' || action === 'correction');
      costBlock.hidden = (action !== 'received');
      document.getElementById('staffnum').textContent = costBlock.hidden ? '3' : '4';
      document.getElementById('reasonnum').textContent = costBlock.hidden ? '4' : '5';
      document.getElementById('actionhelp').textContent = HELP[action] || '';
      document.getElementById('reasonhint').textContent = needsReason ? '(required)' : '(optional)';
      reasonRow.innerHTML = '';
      (QUICK[action] || []).forEach(function(text){
        var chip = document.createElement('button');
        chip.type = 'button'; chip.className = 'tap'; chip.textContent = text;
        chip.onclick = function(){ note.value = text; press(reasonRow, chip); summarise(); };
        reasonRow.appendChild(chip);
      });
      summarise();
    }
    function summarise(){
      var action = actionField.value, n = qty.value || '0', who = staffField.value;
      var text = label(action) + ' ' + n + ' ' + UNIT;
      if(action === 'received' && cost.value){ text += ' at $' + cost.value + ' each'; }
      text += who ? ' · recorded by ' + who : ' · choose who is recording';
      if((action === 'wasted' || action === 'correction') && !note.value){ text += ' · reason needed'; }
      summary.textContent = text;
    }
    document.getElementById('actionrow').onclick = function(event){
      var button = event.target.closest('.tap'); if(!button) return;
      actionField.value = button.dataset.action; press(this, button); refresh();
    };
    document.getElementById('qtyrow').onclick = function(event){
      var button = event.target.closest('.tap'); if(!button) return;
      qty.value = button.dataset.qty; press(this, button); summarise();
    };
    function bump(by){ qty.value = (parseInt(qty.value || '0', 10) + by); press(document.getElementById('qtyrow'), null); summarise(); }
    document.getElementById('minus').onclick = function(){ bump(-1); };
    document.getElementById('plus').onclick = function(){ bump(1); };
    qty.oninput = summarise; cost.oninput = summarise; note.oninput = summarise;
    document.getElementById('staffrow').onclick = function(event){
      var button = event.target.closest('.tap'); if(!button) return;
      staffField.value = button.dataset.staff; press(this, button); summarise();
      try { localStorage.setItem('pho65-staff', button.dataset.staff); } catch(e) {}
    };
    var other = document.getElementById('staffother');
    if(other){ other.oninput = function(){ staffField.value = other.value; press(document.getElementById('staffrow'), null); summarise(); }; }
    try {
      var remembered = localStorage.getItem('pho65-staff');
      if(remembered){ document.querySelectorAll('#staffrow .tap').forEach(function(b){ if(b.dataset.staff === remembered){ b.click(); } }); }
    } catch(e) {}
    document.querySelector('form[action="/inventory/transaction"]').addEventListener('submit', function(){
      var button = document.getElementById('submitbtn');
      setTimeout(function(){ button.disabled = true; button.textContent = 'Recording…'; }, 0);
    });
    refresh();
    </script>""", item=item, state=state, money=money, staff=staff_list(), low=low,
    short_time=short_time, quick_reasons=QUICK_REASONS, action_help=ACTION_HELP,
    request_id=str(uuid.uuid4()))


@app.post("/inventory/transaction")
def transaction():
    item_id, action = int(request.form["item_id"]), request.form["action"]
    raw_quantity = int(request.form["quantity"])
    quantity = -abs(raw_quantity) if action in {"used", "wasted"} else raw_quantity
    raw_cost = request.form.get("unit_cost", "").strip()
    try: cost = int((Decimal(raw_cost) * 100).quantize(Decimal("1"), ROUND_HALF_UP)) if raw_cost else None
    except Exception: cost = -1
    try:
        add_transaction(item_id, action, quantity, cost, request.form.get("recorded_by", "").strip(), request.form.get("note", "").strip(), request.form.get("request_id", ""))
        flash("Recorded once. Check the numbers below.")
    except (ValueError, sqlite3.Error) as error: flash(str(error))
    return redirect(url_for("item_detail", item_id=item_id))


@app.route("/inventory/label/<int:item_id>")
def label(item_id):
    with db() as con: item = con.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
    if not item or item["code_kind"] != "internal": abort(404)
    qr = qrcode.make(item["scan_code"]).convert("RGB")
    label_height = 76
    image = Image.new("RGB", (qr.width, qr.height + label_height), "white")
    image.paste(qr, (0, 0))
    draw = ImageDraw.Draw(image)
    draw.text((10, qr.height + 8), "PHO65 INTERNAL USE ONLY", fill="black")
    draw.text((10, qr.height + 30), item["scan_code"], fill="black")
    draw.text((10, qr.height + 52), "Not a retail UPC/EAN/GTIN", fill="black")
    output = io.BytesIO(); image.save(output, "PNG"); output.seek(0)
    return send_file(output, mimetype="image/png", download_name=f"{item['scan_code']}.png")


# The Week 3 order tracker is preserved here in full, including its overdue
# calculation, so the Week 3 known-answer test still runs against this app.
@app.route("/")
def orders():
    rows = []
    try:
        with open(ORDERS_CSV, newline="", encoding="utf-8") as source: rows = list(csv.DictReader(source))
    except FileNotFoundError: pass
    overdue_min, now = get_overdue_min(), order_now()
    orders = [{**row, "computed_status": order_status(row, overdue_min, now)} for row in rows]
    overdue_count = sum(1 for order in orders if order["computed_status"] == "overdue")
    return page("""<h1>Order tracker <span class=hint>(Week 3 regression)</span></h1>
    <div class=stats>
      <div class=stat><div class=k>Overdue now</div><div class=v>{{overdue_count}}</div><div class=hint>of {{orders|length}} orders</div></div>
      <div class=stat><div class=k>Threshold</div><div class=v>{{overdue_min}} min</div><div class=hint>from /config/overdue.env</div></div>
      <div class=stat><div class=k>Reference time</div><div class=v style='font-size:1.05rem'>{{now}}</div><div class=hint>fixed for testing</div></div>
    </div>
    <div class=card><table><tr><th>Order</th><th>Item</th><th>Ordered</th><th>Picked up</th><th>Status</th><th>Computed</th></tr>
    {% for o in orders %}<tr><td>{{o.order_id}}</td><td>{{o.item}}</td><td>{{o.ordered_at}}</td><td>{{o.picked_up_at}}</td><td>{{o.status}}</td><td class='{{o.computed_status}}'>{{o.computed_status}}</td></tr>{% endfor %}</table>
    <p class=hint>Overdue only when an order is unclaimed and has waited longer than the threshold. The threshold is re-read on every request, so it can still be fixed over SSH.</p></div>
    <p><a class=tap href='/inventory'>Open mobile inventory</a></p>""",
    orders=orders, overdue_count=overdue_count, overdue_min=overdue_min,
    now=now.strftime("%Y-%m-%d %H:%M") if now else "unknown")


@app.route("/health")
def health():
    return jsonify({"status": "ok", "inventory_db": DB_PATH,
                    "overdue_min": get_overdue_min(), "orders_csv": ORDERS_CSV,
                    "staff_count": len(staff_list())})


init_db()
if __name__ == "__main__":
    print(f"Pho65 order tracker started. OVERDUE_MIN={get_overdue_min()} ORDERS_CSV={ORDERS_CSV}")
    app.run(host="0.0.0.0", port=5000)
