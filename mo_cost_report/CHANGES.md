# mo_cost_report — Cost column fix (2026-09-17)

## What was wrong

The "Cost" column on the Production Report (Manufacturing > Reporting) summed
`stock_valuation_layer.value` for the Manufacturing Order's done stock moves.
That ledger only gets an entry when the product's category uses **Automated**
inventory valuation. Any product under **Manual** valuation never gets a
valuation layer written, so the sum came back empty and the report showed
₹0.00 — even for completed, real production orders.

## What changed

`models/mo_cost_report.py`, the `mo_cost` column in the SQL view: instead of
summing the valuation ledger, it now shows the product variant's own **Cost
price** (`standard_price` on `product.product`, General Information tab)
directly, as-is:

```
mo_cost = product variant's current Cost price
```

`standard_price` is a company-dependent field stored as a JSON object keyed
by company id (e.g. `{"1": 2.61}`), not a plain column — it's looked up for
the order's own `company_id`.

**Note: this is a flat value, not multiplied by the Quantity column.** Two
orders for the same product will show the identical Cost regardless of
whether one made 1 unit and the other made 300 — this was a deliberate,
explicit instruction, not an oversight. (A qty x Cost "batch total" version
was considered first, since that matched how this field behaved historically
via the old valuation-ledger sum, but the flat per-unit reading is what was
actually asked for.)

## Trade-off to know about

Cost is now always **live** — it reflects *today's* Cost price, not what the
product actually cost on the day that specific order was completed. Real
`stock_valuation_layer` history is no longer consulted by this report at
all. An old, already-completed order's number can change later just because
someone edits the product's Cost afterward.

Flag this to Finance/whoever reads this report before it goes live — old
orders' costs will look different from before, not because anything was
mis-entered, but because the report now always shows a live number instead
of a frozen historical one.

## What this does NOT fix

Several Finished Goods still have stale, un-recomputed `standard_price`
values from before their raw material costs were corrected (a separate,
ongoing data-cleanup effort). This report displays whatever Cost is
currently set on a product — it does not recompute or validate it. Those
products still need someone to click "Compute Price from BoM" before their
numbers here will be accurate.

## Verified

- No other module references `mo.cost.report` or its `mo_cost` field —
  isolated change, self-contained menu/view.
- Column names/types on the view are unchanged, so nothing downstream can
  break from this.
- Confirmed live on the test database: `mo_cost` matches
  `product.standard_price` exactly on every row, and stays identical across
  orders for the same product regardless of quantity (e.g. Bengali Meat
  Masala Retail shows ₹36 whether the order made 100 units or 300).

---

# Three more columns added (2026-09-17, same day)

In plain terms: this report gained two new pieces of information it didn't
have before, and one existing date got renamed to match a change made
elsewhere. Nothing already on this report changed behavior.

## 1. Renamed "Scheduled Date" to "Production Date"

**Why:** the Manufacturing Order form itself just had this same date
renamed to "Production Date" (see `mrp_auto_component_lots`'s own
CHANGES.md). This report's own "Scheduled Date" column reads that exact
same underlying field, so it was renamed to match — otherwise the same
date would confusingly be called two different things depending on
whether you're looking at the MO itself or this report.

**Impact:** cosmetic only — same field, same data, just a different column
header and group-by filter label.

## 2. New column: "Requested Date"

**What:** shows exactly when "Submit for Approval" was clicked on that
MO — pulled straight from the new `requested_date` field added to
`mrp.production` by `mrp_auto_component_lots`.

**Not to be confused with:** the existing "Requested By" column, which is
a completely different thing — that's *who created* the MO, this new one
is *when it was submitted for approval*. Two different pieces of
information that happen to have similar-sounding names.

**Impact — one real dependency change:** because this report's SQL view
now reads a column (`requested_date`) that only exists once
`mrp_auto_component_lots` is installed, `mo_cost_report`'s
`__manifest__.py` now formally **depends on** `mrp_auto_component_lots`.
Without adding that dependency, installing this report anywhere that other
module isn't already present would crash outright when the view tries to
be created (referencing a column that doesn't exist). This is the one
change here that isn't purely additive — it changes what this module
requires to install at all.

## 3. New column: "Type of Product"

**What:** shows whether the MO's product is a **Retail**, **Finished
Good**, or **Raw Material** item — the exact same classification logic
already used by the `inventory_soh_report` module, copied over so both
reports agree with each other on how a product is categorized.

**Impact:** purely additive — a new column, doesn't change any existing
number or filter.

## Verified

- Ran a live check on the test database: "Type of Product" correctly
  showed "Finished Good" for FG products and "Retail" for retail products;
  "Requested Date" correctly showed a real timestamp for MOs that went
  through Submit for Approval, and blank for older MOs that never did
  (which is the factually correct answer for those, not a bug).
- Module upgrade loaded cleanly with the new manifest dependency in place,
  no errors.

---

# Cost column changed to order total (2026-09-21)

## In plain terms

The "Cost" column now shows the **total cost for that whole Manufacturing
Order** — unit Cost price × Quantity produced — instead of just the
per-unit Cost price. E.g. a product with a ₹30 Cost price, made in a batch
of 100 units, now shows **₹3,000** for that row instead of ₹30.

## Why

This reverses the earlier, deliberate "flat, not multiplied by quantity"
decision recorded above (2026-09-17 entry) — that was what was explicitly
asked for at the time. The user has now asked for the opposite: the Cost
column should reflect what that specific order actually cost in total, not
just the per-unit rate.

## What changed

`models/mo_cost_report.py`, the `mo_cost` column in the SQL view:

```
mo_cost = product variant's Cost price x mp.product_qty (order total)
```

Nothing else on the view or the report changed — same field name, same
column position, same `widget="monetary"` display with a "Total Cost" sum
at the bottom of the list (that sum will now also read differently, since
it's summing real order totals instead of summing repeated per-unit
prices).

## Impact

- Every row's Cost value goes up by a factor of that order's Quantity
  (e.g. Qty 1 orders are unaffected; Qty 100 orders now show 100x their
  old figure).
- The "Total Cost" footer sum changes accordingly — it now represents the
  sum of real order totals, which is a meaningful number to add up (the
  old per-unit-only sum was not).
- The same live-Cost-price caveat from the 2026-09-17 entry still applies:
  this still reflects *today's* Cost price, not the price on the day the
  order was actually completed.

## Verified

- Module upgrade (`-u mo_cost_report --stop-after-init`) loaded cleanly,
  255 modules, no errors.
- Checked live: `HK_BBM_03` MOs with Qty 100.00 and unit Cost ₹30 now show
  Cost = ₹3,000.00 (30 × 100), across all 5 sampled MOs for that SKU.

---

# Production Date split into two export columns (2026-09-21)

## In plain terms

When exporting the Production Report to Excel, "Production Date" used to
come out as one column with the date and time glued together (e.g.
"2026-09-17 16:36:42"). Two new columns are now available —
**"Production Date (Date)"** and **"Production Date (Time)"** — showing
just the date or just the time on their own, so they can be exported into
two separate spreadsheet columns instead of one combined cell.

## Why

Asked directly: is it possible to have date and time come out as two
separate columns on export, without touching how the report looks
on-screen otherwise? Yes — Odoo's export tool exports whatever a field
holds as one cell, so getting two cells means having two fields.

## What changed

`models/mo_cost_report.py`:

- Two new **non-stored, computed** fields — `production_date_only`
  (Date) and `production_time_only` (Char, "HH:MM:SS") — each derived
  from the existing `date_start` field via a small Python compute method,
  not part of the SQL view itself.
- The split uses `fields.Datetime.context_timestamp(...)` — the exact
  same timezone-conversion Odoo already uses to display "Production
  Date" on screen — so these two new values always match what's shown
  in the existing Production Date column for the same viewer, they're
  not computed from the raw UTC database value.

`views/mo_cost_report_views.xml`: both new fields added to the list view
right after "Production Date", as **hidden-by-default** optional columns
(`optional="hide"`) — nothing currently visible on the report changes
unless someone explicitly turns them on via the column picker (the ⚙/sliders
icon at the top-right of the list) or adds them from the export wizard's
field picker.

## Impact

- Nothing visible changes by default — existing "Production Date" column,
  its data, and every other column are untouched.
- Two new optional columns exist for anyone who wants date/time split on
  export: turn them on via the column picker before exporting (or pick
  them directly in the Export dialog's field list, they don't need to be
  visible in the list view first).
- These two fields are computed on the fly (not stored), so they always
  reflect the current value of Production Date — nothing to keep in sync.

## Verified

- Module upgrade (`-u mo_cost_report --stop-after-init`) loaded cleanly,
  255 modules, no errors.
- Checked live: for MOs with Production Date "2026-09-05 05:43:07" (raw),
  the new fields returned Date = "2026-09-05" and Time = "07:43:07" —
  correctly split and timezone-adjusted the same way the existing
  Production Date column already displays.

---

# Split Date/Time columns made the default, combined column hidden (2026-09-21, same day)

## In plain terms

Turning the new columns on by hand every time (via the column picker) was
one extra step nobody wants to repeat. Flipped the default: **"Production
Date (Date)"** and **"Production Date (Time)"** now show automatically
when the report is opened, and the old combined **"Production Date"**
column is now the one that's hidden (still available via the column
picker or the export field list, just not shown by default anymore).

## What changed

`views/mo_cost_report_views.xml`, only the `optional=` attribute flipped
on three existing `<field>` lines — no new fields, no field removed:

- `date_start` ("Production Date"): `optional="show"` → `optional="hide"`
- `production_date_only` ("Production Date (Date)"): `optional="hide"` → `optional="show"`
- `production_time_only` ("Production Date (Time)"): `optional="hide"` → `optional="show"`

## Impact

- Opening the Production Report now shows Date and Time as two separate
  columns straight away — nothing to turn on manually.
- The combined "Production Date" column is no longer shown by default,
  but the field itself, its data, and its Group By ("Production Date
  (Month)") in the search bar are all untouched — it can still be turned
  back on via the column picker at any time.
- Purely a display-default change; no data, computation, or export
  behavior changed beyond which columns appear out of the box.

## Verified

- Module upgrade (`-u mo_cost_report --stop-after-init`) loaded cleanly,
  255 modules, no errors.
