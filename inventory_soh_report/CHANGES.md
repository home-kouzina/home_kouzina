# inventory_soh_report — "Value" column fix (2026-09-17)

In plain terms: one number on this report ("Value") was being calculated
from the wrong source, making it look bigger than it should for any
product that has labelling or packaging costs attached. Fixed to use the
right source. Nothing else on this report changed.

## What was wrong

The "Value" column was calculated as:

```
Value = Variance x COG Before Sale
```

"COG Before Sale" is a different field on the product (from
`home_kouzina_sales`) that adds together the product's own Cost price
**plus** the cost of whatever product is linked as its labelling, **plus**
the cost of whatever product is linked as its packaging. That's a useful
number for other purposes, but it's not what "Value" here is supposed to
mean — this column exists to answer "how much money is this stock
shortfall/excess actually worth," which should be priced using the raw
stock item's own Cost, not inflated by unrelated labelling/packaging costs
bundled on top.

**Concretely:** for a product like "Tailed Pepper," Cost price is ₹1093
but COG Before Sale was ₹0 (no labelling/packaging linked, or it wasn't
set) — for others like "Black cardamom," the two numbers happened to be
identical by coincidence (no labelling/packaging cost added on top), which
is why this bug wasn't obvious just by spot-checking a few rows.

## What changed

`models/inventory_soh_report.py` — the `variance_value` calculation now
reads the product variant's own **Cost price** (`standard_price`) directly
instead of `cog_before_sale`:

```
Value = Variance x product variant's own Cost price
```

**A wrinkle worth knowing about:** Cost price is stored oddly in the
database — because it's a field that can vary per company, Postgres keeps
it as a small JSON object keyed by company id (e.g. `{"1": 2.61}`), not a
plain number in a column. The fix uses a Postgres function
(`jsonb_each_text`) to pull the number back out. This report doesn't track
which company each row belongs to (it never has), so if a product ever
had a genuinely different Cost price set for more than one company, this
would pick one of them somewhat arbitrarily rather than a specific one.
For this business today (effectively one active company with real data),
that's a non-issue — flagged in the code comment so it's not forgotten if
that ever changes.

## Impact

Only the "Value" column's number changes — no other column, filter, or
sum on this report is touched. Any row where COG Before Sale already
equalled Cost price (most rows with nothing tracked, both are 0; some
happen to match) shows no visible difference. Rows where they diverge
(anything with a linked labelling/packaging cost, or any case where COG
Before Sale had gone stale) will now show a smaller, more correct number.

## Verified

Checked 8 real products with non-zero variance on the test database:
`variance_value` now matches `variance x standard_price` exactly on every
row, confirmed against a manual calculation done outside the report. Also
confirmed several rows where Cost price and COG Before Sale genuinely
differ (e.g. Tailed Pepper, Black pepper (Bold small)), showing the fix is
actually changing the right rows rather than coincidentally landing on the
same numbers as before.
