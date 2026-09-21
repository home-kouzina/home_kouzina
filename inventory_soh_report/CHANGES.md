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

---

# inventory_soh_report — show 3 decimal places instead of whole numbers (2026-09-18)

In plain terms: every quantity/value column on this report was rounding
off to a whole number on screen, hiding real fractional stock (e.g. a
product actually at 1999990.253 on hand showed as 1,999,990). Now shows up
to 3 decimal places.

## What was wrong

`views/inventory_soh_report_views.xml` — every numeric column
(`qty_on_hand`, `qty_inward`, `qty_consumption`, `qty_return`,
`qty_wastage`, `ideal_soh`, `actual_soh`, `variance`, `variance_value`) had
`options="{'digits': [16, 0]}"` on the list view field, which forces the
web client to display 0 decimal places regardless of what's actually
stored. The underlying data already has real decimals (confirmed directly
in Postgres, e.g. `qty_on_hand = 1999990.25329`) — only the on-screen
number was being truncated.

## What changed

Every `'digits': [16, 0]` in that file became `'digits': [16, 3]`, so all
nine columns now render with 3 decimal places. This is a view-only change
— no field definition, no stored value, and no other report or screen in
Odoo is affected (only this list view's arch).

## Impact

Same underlying numbers, just no longer rounded off on screen. Rows that
happened to be exact whole numbers (most of them, since this business
mostly moves stock in whole "Units") show `.000` and look unchanged.
Rows with genuine fractional quantities now show their real value instead
of a rounded integer.

## Verified

Applied with `-u inventory_soh_report` and confirmed the module reloaded
cleanly (254 modules loaded, no errors). Spot-checked in Postgres that
raw stored values (e.g. `1999990.25329`, `9795.16000`) match what now
renders on screen (rounded only to 3 dp, not to 0).

---

# inventory_soh_report — Consumption shown in kg for gram-UoM products (2026-09-18)

In plain terms: about 46 raw-material products (spices, flour, etc.) are
tracked in the system in **grams**, while most other products on this
report are tracked in a unit called "Units" that — due to how Units of
Measure are configured in this database — is numerically equal to a
**kilogram** (1 Units = 1 kg = 1000 g; confirmed from the UoM conversion
factors: `Units` factor 1.0 as the reference, `kg` factor 1.0, `g` factor
1000.0). That mismatch meant the Consumption column mixed two different
scales in the same column — some rows in kg-equivalent Units, some rows
in raw grams — making them impossible to compare at a glance. Now, for
the gram-UoM products only, Consumption is converted to kg for display in
this report, so a row that consumed 45g now reads `0.045`.

## What was wrong

`models/inventory_soh_report.py` — the SQL view's `qty_consumption`
column was a straight pass-through of `stock_move` quantities, which are
recorded in whichever Unit of Measure the product itself uses. For the 46
products whose UoM is "g" (e.g. Coriander seeds, Jeera, Bedgi Chilly, Dry
Ginger Powder), that meant Consumption showed a raw gram count sitting
next to other rows whose "Units" already reads as kg — e.g. Bedgi Chilly
showed `179455.73` while a "Units" product a few rows above might show
`391`, even though both numbers represent roughly the same order of
magnitude of actual stock once you know 1 Units = 1 kg.

## What changed

Added a join to `uom_uom` on the product's UoM, and wrapped the
`qty_consumption` column in a `CASE`: when the product's UoM name is `g`,
divide the raw consumption by 1000 (grams → kg) for display; every other
product's Consumption is untouched. Scope was deliberately kept to just
this one column, on this one report — `ideal_soh` and `actual_soh` still
do their internal arithmetic against the raw (unconverted) gram value, so
those totals stay correct; only the exposed `qty_consumption` column's
number changes for gram-UoM products. No other column (On Hand,
Purchased, Return, Wastage, Ideal/Actual SOH, Variance, Value), no other
report, and no global Settings/Unit of Measure configuration was touched.

## Impact

Only the Consumption column's number changes, and only for the 46
gram-UoM products. Examples, cross-checked directly against the raw
`stock_move` totals in Postgres (raw grams ÷ 1000 = value now shown):

| Product | Raw consumption (g) | Now shown (kg) |
|---|---|---|
| Coriander seeds | 376,710.300 | 376.710 |
| Jeera | 338,063.600 | 338.064 |
| Bedgi Chilly | 179,455.730 | 179.456 |
| Red chilli powder | 86,240.000 | 86.240 |
| Green cardamom | 36,474.140 | 36.474 |
| Dry Ginger Powder | 31,356.200 | 31.356 |
| Radhuni | 30,758.000 | 30.758 |
| Kala Masala | 10,000.000 | 10.000 |
| Cardamom | 6,358.680 | 6.359 |
| Besan (Rajdhani) | 4,895.000 | 4.895 |
| Haldi Powder | 4,157.000 | 4.157 |
| Kashmiri chilli | 2,684.000 | 2.684 |

All 698 "Units"-UoM products and 129 plain-count "Units"-UoM products are
unaffected — their Consumption values are exactly what they were before
this change.

## Verified

Applied with `-u inventory_soh_report`; module reloaded cleanly (254
modules, no errors). Queried the view directly in Postgres for all
non-zero-consumption gram-UoM products and confirmed `shown value x 1000
= raw stock_move total` on every row (table above is a subset of that
check).

---

# inventory_soh_report — kg conversion widened to every quantity column (2026-09-18)

In plain terms: the previous entry above converted grams → kg for gram-UoM
products on the Consumption column only, by deliberate choice at the time.
Asked to widen that — now **every** quantity column on this report (On
Hand, Purchased, Consumption, Return, Wastage, Ideal SOH, Actual SOH,
Variance) shows kg for those same 46 gram-UoM products, not just
Consumption. "Value" is a currency amount, not a physical quantity, so it
stays as-is.

## What was wrong

Only `qty_consumption` was being converted. On Hand, Purchased, Return,
Wastage, Ideal SOH, Actual SOH, and Variance were all still showing raw
gram counts for the same 46 products — e.g. Yellow chilli's On Hand read
`1,998,122` (grams) right next to its now-converted Consumption of
`1.878` (kg), which is arguably more confusing than before: one column
converted, the rest not, on the same row.

## What changed

`models/inventory_soh_report.py` — restructured the SQL view into two
layers instead of converting one column inline:

1. An inner `raw` CTE computes every quantity exactly as before (all in
   the product's own stored UoM), plus one new column, `kg_factor`:
   `0.001` if the product's UoM name is `g`, else `1`.
2. An outer `SELECT ... FROM raw` multiplies `qty_on_hand`, `qty_inward`,
   `qty_consumption`, `qty_return`, `qty_wastage`, `ideal_soh`,
   `actual_soh`, and `variance` by that same `kg_factor`. `variance_value`
   passes through unmultiplied, since it's a currency amount (`Variance x
   Cost-per-UoM-unit`) already correct as computed from the raw variance.

Scaling every term of `ideal_soh`/`actual_soh` by the same factor keeps
their arithmetic correct — `factor x (A + B - C - D - E)` equals
`factor*A + factor*B - factor*C - factor*D - factor*E`, so Ideal SOH and
Actual SOH still equal On Hand + Purchased - Consumption - Return -
Wastage (and - Variance) once every term is read in kg together. Still a
display-only change in this one report's SQL view — no stored stock/move
data, no other report, and no global Settings/Unit of Measure
configuration is touched.

## Impact

For the 46 gram-UoM products, every quantity column now reads in kg
instead of grams. Example (Yellow chilli, before → after this change):

| Column | Before | After |
|---|---|---|
| On Hand | 1,998,122.000 (grams — not yet converted) | 1,998.122 (kg) |
| Consumption | 1.878 (already kg, from the prior entry) | 1.878 (kg — unchanged) |
| Ideal SOH | 1,996,244.000 (grams) | 1,996.244 (kg) |
| Actual SOH | 1,996,244.000 (grams) | 1,996.244 (kg) |

Before this entry, Consumption alone was in kg while On Hand/Ideal
SOH/Actual SOH were still raw grams on the very same row — this entry
brings all of them onto the same kg scale. The Ideal SOH identity still
holds after conversion: `1998.122 (On Hand) - 1.878 (Consumption) =
1996.244 (Ideal SOH)` — same relationship as always, just every term now
in kg. All 827 non-gram products (698 "Units"/Weight + 129 "Units"/count)
are unaffected. Value is untouched on every row.

## Verified

Applied with `-u inventory_soh_report`; module reloaded cleanly (254
modules, no errors). Queried the view directly in Postgres for 8 gram-UoM
products (Citric acid, Mint, Tamrind powder, Dried mint powder, Fennel
powder, Dried mint leaves, Yellow chilli, Imli powder) and confirmed for
each row: `qty_on_hand + qty_inward - qty_consumption - qty_return -
qty_wastage = ideal_soh` holds exactly in the new kg-scaled numbers, and
`variance_value` is unchanged from before this entry.

---

# inventory_soh_report — "Outgoing Inventory" search filter added (2026-09-21)

In plain terms: a new filter, "Outgoing Inventory," in the report's
Filters dropdown — ticking it narrows the list down to only products
that have actually had stock go out (non-zero Consumption). Nothing else
about the report changed.

## Why not also a "Group By: Month"

Also asked for at the same time: a "Group By: Month" alongside this
filter. Not added, and not possible without restructuring this report —
this model is one row per product (a lifetime snapshot), with no date
column on any row at all. Odoo can only group by a field that exists;
there's nothing here to group by month with. Trying to bolt a month
dimension onto this report is the same wall hit twice already
this session (once by making a column context-dependent, which broke
Group By totals with `Cannot convert ... to SQL because it is not
stored`; once by building it as a genuinely separate report with its own
per-month rows, which was built, verified working, and then removed at
the user's own request in favor of Odoo's built-in screens). Given that
history, only the filter — which fits the existing one-row-per-product
shape cleanly — was added here.

## What changed

`views/inventory_soh_report_views.xml` — one new `<filter>` in the
search view, next to the existing "Negative Actual SOH" filter:

```xml
<filter string="Outgoing Inventory"
        name="filter_outgoing_inventory"
        domain="[('qty_consumption', '!=', 0)]"/>
```

Plain domain filter on the existing `qty_consumption` field — no new
field, no view/model restructuring, nothing touched outside this one
line.

## Impact

Ticking "Outgoing Inventory" narrows the report from 767 rows to the 57
rows that have non-zero Consumption (i.e. actually had stock go out, as
either a finished-goods delivery or a raw-material MRP consumption).
Every other filter, column, and the Group By options (Type of Product,
Product Category) are untouched.

## Verified

Applied with `-u inventory_soh_report`; module reloaded cleanly (254
modules, no errors — same count as before, since no field/model changed).
Confirmed in the Odoo shell: the new filter's domain correctly narrows
767 → 57 rows, the filter is present in the saved view's arch, and the
"Group By → Type of Product" totals (Finished Good 1.0, Raw Material
1,357,291.72568, Retail 0.0) are byte-for-byte identical to before this
change.

---

# kg conversion widened to catch products mis-set as "Units" (2026-09-21)

## In plain terms

Some products — Rock salt being the one that surfaced this — had their
own "Unit of Measure" field set to **"Units"**, but every real recipe
(BOM) line and every actual stock transaction for them was entered in
**grams**. The kg-conversion feature only ever looked at that one "Unit
of Measure" field to decide whether to convert a number to kg, so for
these products it did nothing — the report was showing raw gram figures
dressed up as if they were "Units" (e.g. Rock salt's Consumption showed
141,746, when it's really 141,746 grams = 141.746 kg). Checked the whole
database: **92 products** have this exact mismatch, several Finished
Goods among them. All 92 are now converted correctly.

## Why

User pointed out Rock salt's numbers looked far too large to be real
stock, and asked to prove where that number was coming from. Traced it
to the product's own master data: UoM field says "Units", but its BOM
lines (5.35, 6.71, 200, etc.) and every stock move for it were recorded
in grams. Changing the product's UoM field directly in the UI wasn't an
option — Odoo blocks editing a product's UoM once it has been used in
stock moves (all these products already have hundreds of consumed MOs).
So the fix had to live in the report's own logic instead.

Explicitly asked and confirmed with the user: apply this to **all 92**
affected products, including the Finished Goods among them, not just Raw
Materials (the safer, narrower option was offered and declined).

## What changed

`models/inventory_soh_report.py`: a new `gram_products` CTE finds every
product with at least one **done** stock move that was actually recorded
in grams (looking at the move's own `product_uom`, not the product's
master UoM field). The `kg_factor` calculation now converts to kg if
**either** the product's own UoM field says "g" **or** the product shows
up in `gram_products` — so a product transacted in grams gets treated as
grams for this report's display, regardless of what its master UoM field
claims.

This changes the *detection*, not the conversion math itself — still the
same 0.001 factor, applied to the same 8 columns (On Hand, Purchased,
Consumption, Return, Wastage, Ideal SOH, Actual SOH, Variance); Value is
still deliberately left unconverted (currency, not quantity).

`extra_addons/home_kouzina/mo_raw_material_consumption/models/mo_raw_material_consumption.py`
got the identical `gram_products` detection added to its own `qty_consumed`
conversion, so the two reports never disagree with each other on the same
product (they're documented as using "the same gram→kg conversion" —
this keeps that true after today's fix).

## Impact

- 92 products' numbers change today: anything previously showing a
  suspiciously huge "Units" figure that was actually grams now correctly
  shows a realistic kg figure (e.g. Rock salt Consumption: 141,746.000 →
  141.746; On Hand: 1,999,858.254 → 1,999.858).
- On Hand specifically comes from `stock.quant`, which has no per-row
  UoM of its own — for these 92 products, On Hand is now treated as
  grams too, on the working assumption that a product transacted in
  grams everywhere else was also physically counted in grams. This is a
  reasonable assumption, not a mathematical certainty — flagged here in
  case any of these 92 ever turns out to have a genuinely mixed history.
- Every other product (already correctly set to "g", or genuinely
  transacted in "Units"/other UoMs) is completely unaffected.
- The real, underlying fix — correcting these 92 products' actual "Unit
  of Measure" field in Odoo — is still recommended when practical; this
  report-level fix makes the numbers correct today without requiring
  that (which Odoo currently blocks anyway, since they already have
  transaction history).

## Verified

- Module upgrade (`-u inventory_soh_report,mo_raw_material_consumption
  --stop-after-init`) loaded cleanly, 255 modules, no errors.
- Rock salt: Inventory SOH Report Consumption now reads 141.746, and
  MO-wise Raw Material Consumption's own 16 MO rows for Rock salt sum to
  the identical 141.746 — the two reports agree exactly.
- Spot-checked Black Pepper Whole (KG) and Coriander (two of the other
  91 affected products): both now show the correctly scaled-down kg
  figures instead of their previous six-digit "Units" numbers.
- Confirmed products NOT in the 92 (e.g. Cinnamon, whose Consumption is
  genuinely 0) are unaffected.
