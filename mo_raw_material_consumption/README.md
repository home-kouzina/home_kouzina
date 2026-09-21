# MO-wise Raw Material Consumption

## What this is

A report — **Manufacturing ▸ Reporting ▸ MO-wise Raw Material
Consumption** — that shows, for every raw material, how much of it was
used in **each individual Manufacturing Order**, along with that order's
own number and Production Date.

One row = one raw material used in one specific MO. For example, if
"Bedgi Chilly" was used in 56 different Manufacturing Orders, this report
has 56 separate rows for it — one per order, each with its own date and
its own quantity.

## Why this report exists

The existing **Inventory SOH Report** shows one row per product — a
lifetime, all-time total. It has no date on it at all, so there's no way
to see "how much did we use *this month*" or group anything by month.

The ask was: make it possible to see raw material consumption broken down
by month. The natural way to do that is to add a date to each row and
group by it — but that only works if each row already represents a single
point in time, like one Manufacturing Order, not a lifetime total.

Changing Inventory SOH Report itself to be "one row per product + MO"
was considered, but it would have broken accuracy: that report has 8
other columns (On Hand, Purchased, Return, Wastage, Ideal SOH, Actual
SOH, Variance, Value) that are only meaningful as **lifetime totals for
the product as a whole** — they don't have a "per MO" value. Repeating
those same lifetime numbers on every one of a product's MO rows would
make any total/sum on those columns wrong (e.g. a product's On Hand
would get added up 56 times instead of once, if it had 56 MOs).

So instead, this is a **new, separate, standalone report** containing
only what's genuinely accurate at a "per MO" level: MO Number,
Production Date, and Qty Consumed. It does not touch, modify, or share
any code with Inventory SOH Report or MO Cost Report — both of those
keep working exactly as before.

## What it shows

| Column | Meaning |
|---|---|
| MO Number | The Manufacturing Order this material was consumed in |
| Production Date | That MO's own start date (same field/label MO Cost Report already uses) |
| Raw Material | The product/material consumed |
| SKU | The material's internal reference code |
| Category | The material's product category |
| Qty Consumed | How much of that material this specific MO used |

Quantities follow the same gram→kg display rule as Inventory SOH Report:
a product measured in grams shows its consumption in kg (e.g. 45g reads
as 0.045), so the two reports read the same way for the same products.

## How to use it

- Default view is a **Pivot**: raw materials down the side, months
  across the top, Qty Consumed as the numbers — a quick way to see a
  material's usage trend month by month.
- A **List** view is also available (one row per MO) if you want to see
  or export the raw detail.
- Use "Group By ▸ Production Date (Month)" in the search bar to bucket
  by month anywhere in the app, not just in the pivot.

## What it deliberately does NOT include

On Hand, Purchased, Return, Wastage, Ideal SOH, Actual SOH, Variance, and
Value — none of these appear here, on purpose. They're lifetime totals
for a product, not something that happened "at" a specific MO, so there
is no accurate way to show them on a per-MO row. For those numbers,
Inventory SOH Report is still the correct place to look.

## Verified

- Bedgi Chilly's 56 MO rows in this report sum to exactly 179.45573 —
  matching Inventory SOH Report's own lifetime Consumption figure for
  the same product, to the decimal.
- Grouping by Production Date (Month) produces a genuine month-by-month
  split that adds up to the same lifetime total.
- Inventory SOH Report and MO Cost Report are both unaffected — neither
  their code, their data, nor their numbers changed when this module was
  added.

See `CHANGES.md` in this folder for the full technical write-up.
