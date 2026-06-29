# -*- coding: utf-8 -*-
{
    'name': 'Inventory SOH Report',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Reporting',
    'summary': 'Inventory Stock on Hand Report with consumption, inward, return, wastage and variance',
    'description': """
        Custom Inventory SOH (Stock on Hand) Report for Odoo 18.
        Provides a comprehensive list view report under Inventory > Reporting showing:
        - Product & Product Type
        - Current On Hand Qty
        - Consumption (used qty)
        - Inward Qty (successfully received)
        - Return Qty (returned from inventory)
        - Wastage (scrapped qty)
        - Ideal SOH  = Current Stock + Inward - Consumption - Return - Wastage
        - Actual SOH = Ideal SOH - Variance
        - Variance
    """,
    'author': 'Custom',
    'depends': ['stock', 'purchase', 'sale_stock', 'hk_inventory_variation', 'visible_group_export'],
    'data': [
        'security/ir.model.access.csv',
        'views/inventory_soh_report_views.xml',
        'views/inventory_soh_report_menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
