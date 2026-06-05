# MRP Auto Component Lots

Adds an **Assign Lots** button on Manufacturing Orders.

## Behavior

- Works only on MO component lines.
- Processes only components with Tracking = By Lots.
- Replaces existing detailed-operation lot lines for each component.
- Generates one lot line per component move.
- Quantity on the generated line is the component quantity to consume.
- Prefix is generated automatically from the product name; the user does not maintain it manually.
  - Amritsari Mirch -> AM
  - Aata Mirch -> AM2 if AM is already assigned to another product
- The generated prefix is stored internally so it remains stable if the product name changes later.
- Lot format: `PREFIX-DDMMYY-001`, for example `AM-190526-001`.
- Reuses Odoo stock move helpers used by the native Generate Serials/Lots flow.

## Install / Upgrade

Copy this folder to your custom addons path, restart Odoo, update apps list, and install or upgrade **MRP Auto Component Lots**.

Command example:

```bash
./odoo-bin -c /path/to/odoo.conf -u mrp_auto_component_lots -d your_db
```
