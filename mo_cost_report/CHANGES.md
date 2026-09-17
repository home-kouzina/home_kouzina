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
