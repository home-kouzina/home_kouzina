# Amazon Orders Menu — Installation

## What this does
Adds a new menu item **Amazon Orders** under **Sales → Orders** (next to
Quotations, Orders, Sales Teams, Customers). It shows the normal sale
order list/kanban/form views, filtered to orders where the field
`amazon_order_ref` (label: "Amazon Reference") is set — i.e. orders
that were synced in from Amazon. This field name was confirmed directly
from your database structure (Settings > Technical > Database
Structure > Fields).

## How to install / upgrade
1. Copy the `amazon_orders_menu` folder into your custom addons path
   (the same place your other custom modules live — check `addons_path`
   in your Odoo config file / `odoo.conf`), replacing the previous
   version of this folder if you installed an earlier one.
2. Restart the Odoo service.
3. In Odoo: Settings → Apps Bar → click the dropdown arrow → **Update Apps List**.
4. Search for "Amazon Orders Menu" — click **Upgrade** (if already
   installed) or **Install**.
5. Go to Sales → Orders → you should now see **Amazon Orders** in the dropdown.

## Optional tweak
Your database also has a field `amazon_channel` (Fulfillment Channel —
FBA vs FBM). If you ever want a separate menu for just FBA or just FBM
orders, the domain can be extended, e.g.:

```xml
<field name="domain">[('amazon_order_ref', '!=', False), ('amazon_channel', '=', 'fba')]</field>
```

## Notes
- This module only adds a menu + action (no Python models), so it's
  very low-risk to install/uninstall.
- `sequence="25"` places it between Orders (20) and Sales Teams (30) in
  the dropdown — change that number if you want it elsewhere.
