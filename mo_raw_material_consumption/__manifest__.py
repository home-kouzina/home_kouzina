# -*- coding: utf-8 -*-
{
    'name': 'MO-wise Raw Material Consumption',
    'version': '18.0.1.0.0',
    'category': 'Manufacturing/Reporting',
    'summary': 'Raw material consumption broken down per Manufacturing Order, with Production Date',
    'description': """
        Standalone report, separate from Inventory SOH Report and from
        MO Cost Report, showing raw material consumption one row per
        (raw material, Manufacturing Order) — with the MO's own number
        and Production Date on every row.

        Because it's one row per MO (not per product), the Production
        Date column can be grouped by month like any normal Odoo report
        (Pivot/List "Group By" on a real date field) — something that
        isn't possible on Inventory SOH Report, which is one row per
        product (a lifetime snapshot) with no date on any row.

        Only shows Qty Consumed alongside the MO/Date/product columns —
        deliberately does NOT repeat On Hand, Purchased, Return, Wastage,
        Ideal SOH, Actual SOH, Variance or Value from Inventory SOH
        Report. Those are lifetime totals for the product as a whole,
        not something that happened "at" a specific MO — repeating them
        per MO row would either be misleading (same number shown 50+
        times, and silently wrong if anyone sums the column) or empty.
        Keeping this report to just the one column that's genuinely
        accurate at this grain was a deliberate choice, not an oversight.

        Does not modify Inventory SOH Report, MO Cost Report, or any of
        their data in any way.
    """,
    'author': 'Custom',
    'depends': ['mrp', 'visible_group_export'],
    'data': [
        'security/ir.model.access.csv',
        'views/mo_raw_material_consumption_views.xml',
        'views/mo_raw_material_consumption_menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
