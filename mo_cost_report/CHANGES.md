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
