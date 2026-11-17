# -*- coding: utf-8 -*-
{
    'name': 'Inventory SOH Report',
    'version': '18.0.1.1.0',
    'category': 'Inventory/Reporting',
    'summary': 'Inventory Stock on Hand Report with weekly physical count, upload and history',
    'description': """
        Custom Inventory SOH (Stock on Hand) Report for Odoo 18.
        Provides a list view report under Inventory > Reporting showing, for
        the open counting week:
        - Product & Product Type
        - Opening (Actual SOH of the last closed week)
        - Purchased, Consumption, Return, Wastage (this week only)
        - Ideal SOH  = Opening + Purchased - Consumption - Return - Wastage
        - Actual SOH = live on-hand stock (corrected by the physical count)
        - Variance   = Actual SOH - Ideal SOH, and its Value

        Weekly physical count:

        - Upload Physical Inventory: download the report as Excel, type the count into Actual SOH, upload it. Stock is corrected through standard inventory adjustments.
        - Close Week: freezes the full report into SOH Weekly History and starts the next week.
        - SOH Upload Log: every upload, including rejected files.
    """,
    'author': 'Custom',
    'depends': ['stock', 'purchase', 'sale_stock', 'mrp', 'home_kouzina_sales', 'hk_inventory_variation', 'visible_group_export'],
    'external_dependencies': {'python': ['openpyxl', 'xlsxwriter']},
    'data': [
        'security/ir.model.access.csv',
        'wizard/soh_physical_inventory_wizard_views.xml',
        'views/soh_history_by_product_views.xml',
        'views/soh_week_views.xml',
        'views/soh_upload_log_views.xml',
        'views/inventory_soh_report_views.xml',
        'views/inventory_soh_report_menu.xml',
        'data/soh_week_data.xml',
        'data/soh_week_cron.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'inventory_soh_report/static/src/js/soh_report_list_controller.js',
            'inventory_soh_report/static/src/xml/soh_report_list_buttons.xml',
            'inventory_soh_report/static/src/scss/soh_report_list.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
