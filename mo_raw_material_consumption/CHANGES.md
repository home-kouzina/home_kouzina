# mo_raw_material_consumption — new report (2026-09-21)

In plain terms: a brand-new, standalone report — Manufacturing ▶
Reporting ▶ "MO-wise Raw Material Consumption" — with one row per raw
material per Manufacturing Order, showing that MO's own number,
Production Date, and how much of that material it consumed. Because
every row has a real date on it, "Group By → Production Date (Month)"
actually works here — unlike Inventory SOH Report, which cannot support
that. Does not touch Inventory SOH Report, MO Cost Report, or any of
their data.

## Why

Asked: can Inventory SOH Report get a "Group By Month," the way Odoo's
built-in Moves Analysis screen already does? Answer worked through with
the user: no, not on that report as it stands — it's one row per
product, a lifetime snapshot, with no date on any row to group by.

Follow-up ask: change the report's shape to one row per (product + MO)
instead, so Production Date could be added and grouped by month.

Before building that, one thing had to be flagged: of Inventory SOH
Report's 9 numeric columns, only **Consumption** actually has a
meaningful value per MO. On Hand, Purchased, Return, Wastage, Ideal SOH,
Actual SOH, Variance, and Value are all lifetime totals for the product
as a whole — not something that happened "at" a specific MO. Repeating
those 8 columns on every MO-row would either:
- Duplicate the same product-level number on every one of that
  product's MO rows — each cell technically "correct," but any Group By
  / Total on those columns would then silently overcount (e.g. a
  product with 56 MOs would have its On Hand summed 56 times instead of
  once), or
- Leave them blank on MO-detail rows — not "accurate and proper for
  every column" either.

Given the explicit requirement that the data be accurate for every
column, the user chose: build this as a **new, separate report**
containing only the columns that are genuinely accurate at a per-MO
grain (MO Number, Production Date, product identity, Qty Consumed) —
leaving Inventory SOH Report completely untouched, so its own accuracy
is never put at risk.

## What this report is

A new, separate addon module — `mo_raw_material_consumption` — with its
own model (`mo.raw.material.consumption`), its own `_auto=False` SQL
view, its own security rules, and its own menu. Shares no code, model,
or view with `inventory_soh_report` or `mo_cost_report`; neither of
those modules was touched to build this.

- **Grain**: one row per (raw material, Manufacturing Order).
- **Consumption definition**: identical to the "raw materials" half of
  Inventory SOH Report's own `consumption` CTE — a done stock move, from
  an internal location to a non-internal one, linked to a specific
  Manufacturing Order's component consumption
  (`raw_material_production_id`), on a product that isn't a finished
  good — just grouped by `(product, MO)` instead of summed to one
  lifetime total across every MO.
- **Production Date**: `mrp_production.date_start` — the same field and
  label MO Cost Report already uses for "Production Date," for
  consistency between the two reports. Deliberately not
  `mrp_production.requested_date` (a different, unrelated field on the
  same model, added by `mrp_auto_component_lots` — and the exact field
  that was missing its database column and crashing MO screens on this
  very server until that got fixed separately).
- **Units**: the same gram→kg display conversion Inventory SOH Report
  already uses, so the two reports read the same way for the same
  products.
- **Default view**: Pivot — raw materials as rows, Production Date
  grouped by month as columns, Qty Consumed as the measure, with Odoo's
  own built-in totals (works normally here because `qty_consumed` is a
  plain SQL-view field, not a context-dependent compute field). A List
  view (one row per MO) is included as a flat/exportable fallback, and
  the search view has a ready-made "Production Date (Month)" Group By.
- **Menu**: Manufacturing ▶ Reporting ▶ "MO-wise Raw Material
  Consumption," right next to MO Cost Report — a separate entry, not a
  replacement.

## Verified

- Installed cleanly with `-i mo_raw_material_consumption`: 255 modules
  loaded (was 254), no errors.
- Cross-checked "Bedgi Chilly" end to end: this report lists 56 separate
  MO rows for that product, and they sum to exactly 179.45573 — matching
  Inventory SOH Report's own lifetime Consumption figure for the same
  product to the decimal.
- Grouped by "Production Date (Month)" for the same product and got a
  real month-by-month spread (May 2026: 56.534, June: 40.22448, July:
  37.28232, August: 28.96766, September: 16.44727) — genuine monthly
  breakdown, something Inventory SOH Report cannot do.
- Noted for anyone reading these numbers: Production Date here is when
  the *MO itself* was started/scheduled, not necessarily the same month
  the raw material was physically deducted from stock (the stock move's
  own `date`) — for this product, MOs were started anywhere from May
  through September, even though (checked separately) all 56 of the
  actual stock moves were marked "done" within September. Both dates are
  legitimate; they just answer different questions ("when was this order
  started" vs. "when did the stock actually leave"), and this report
  deliberately shows the first one, matching what MO Cost Report already
  calls "Production Date."
- Confirmed Inventory SOH Report and MO Cost Report are both completely
  unaffected: SOH's Bedgi Chilly Powder Consumption (87,521.31) and MO
  Cost Report's row count (316) are unchanged from before this module
  was added.
- Simulated the pivot view's actual `read_group(..., ['product_id',
  'production_date:month'], lazy=False)` call directly — no error,
  166 grouped rows returned.
- Confirmed the new action and menu are registered under Manufacturing ▶
  Reporting, pointing at each other correctly.

---

# kg conversion widened to match inventory_soh_report's fix (2026-09-21)

## In plain terms

Rock salt's `Qty Consumed` here was showing raw gram figures (e.g. 356,
1070, 133400) as if they were plain "Units" — because Rock salt's own
Unit of Measure field says "Units", even though every real transaction
for it was actually recorded in grams. `inventory_soh_report` had this
exact same issue and got fixed first (see its own `CHANGES.md`, same
date) — this report gets the identical fix, so the two never disagree
with each other on the same product.

## What changed

`models/mo_raw_material_consumption.py`: added the same `gram_products`
CTE used in `inventory_soh_report` — detects any product whose real done
stock moves were recorded in grams, regardless of what its own UoM field
says — and the `qty_consumed` conversion now applies the 0.001 kg factor
whenever a product matches either that detection or its own UoM field.

## Impact

92 products (the same set found in `inventory_soh_report`) now show
correctly scaled kg figures here too. E.g. Rock salt's 16 MO rows, which
used to add up to 141,746, now add up to 141.746 — matching
`inventory_soh_report`'s own Consumption figure for Rock salt exactly.

## Verified

- Module upgrade (`-u mo_raw_material_consumption --stop-after-init`)
  loaded cleanly alongside `inventory_soh_report`'s own fix, 255 modules,
  no errors.
- Rock salt: this report's 16 MO rows now sum to 141.746, identical to
  `inventory_soh_report`'s Consumption figure for the same product.
