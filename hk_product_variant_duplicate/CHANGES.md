# hk_product_variant_duplicate — new module (2026-09-24)

## In plain terms

The "Duplicate" option is now back on the Product Variant screens
(Inventory/Sales/Manufacturing ▸ Products ▸ Product Variants — both the
list and the individual variant form), where Odoo itself had removed it.

## Why it was missing in the first place

Not a bug, not a permissions issue — checked both directly. Both users
tested had full Create rights on products. It was Odoo core itself:
`product.product_normal_form_view` and `product.product_product_tree_view`
(in `odoo/addons/product/views/product_views.xml`) both set
`duplicate="false"` on purpose.

The reason is in Odoo's own code comment on `product.product.copy()`:

> "Variants are generated depending on the configuration of attributes
> and values on the template, so copying them does not make sense."

Concretely: **duplicating a variant does not duplicate that one variant.**
`product.product.copy()` duplicates the whole **Product Template**
instead (every variant, every attribute combination) and hands back
whichever variant comes out as the new template's "first" one — which
may not even be the specific variant you clicked Duplicate on. That's
why Odoo hides the button by default: showing "Duplicate" on a single
variant but having it actually copy the whole template (and open a
possibly-different variant) is confusing.

## What was asked for, and what this module actually does

Explicitly asked for and confirmed with the user, with that behavior
understood: re-enable the button exactly as Odoo's own code already
behaves elsewhere (e.g. on the Product Template screens) — not a custom
"copy just this one variant" rewrite. This module changes **only the
view flag**, nothing else:

- `views/product_views.xml` — two small view-inheritance records, each
  just flipping `duplicate="false"` → `duplicate="true"` on the existing
  core views (`product.product_normal_form_view` for the form,
  `product.product_product_tree_view` for the list). No Python, no
  `copy()` override, no change to what Duplicate actually *does* —
  only whether the button is shown.

## What to expect when using it

Click Duplicate on any Product Variant (e.g. "Achaar - Amla Retail
(100g)") and Odoo will:
1. Duplicate that variant's entire **Product Template** ("Achaar -
   Amla"), including every one of its variants/attribute combinations.
2. Open **one** of the new template's variants — not necessarily the
   100g Retail one you started from.

This is standard Odoo behavior (same as duplicating from the Product
Template screen) — just no longer hidden on the Variant screen. If a
copy of only one specific variant (not the whole template) turns out to
be what's actually needed later, that's a separate, larger change (a
real `copy()` override) — deliberately not built here, since the
simpler, standard-Odoo-behavior option was what was chosen.

## Verified

- Module installs cleanly (`-i hk_product_variant_duplicate
  --stop-after-init`): 256 modules loaded, no errors.
- Confirmed live via `product.product.get_view()`: both the form and
  list view now resolve with `duplicate="true"` (previously `"false"`).
- Only the `duplicate` attribute changed on both views — nothing else
  in either view's structure, fields, or any other screen was touched.
