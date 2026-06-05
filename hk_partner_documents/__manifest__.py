{
    "name": "HK Partner Documents",
    "summary": "Add CIN and other document image uploads on partner form",
    "version": "18.0.1.0.0",
    "category": "Home Kouzina",
    "author": "Home Kouzina",
    "license": "LGPL-3",
    "depends": [
        "account",
        "base",
        "marketplace",
        "odoo_multi_channel_sale",
        "purchase",
        "sale_management",
        "purchase_stock"
    ],
    "data": [
        "views/res_partner_views.xml",
        "views/sale_order_views.xml",
        "views/sale_report_templates.xml",
        # "views/invoice_report_templates.xml",
         "views/new_invoice.xml",

        "views/purchase_order_views.xml",

        "views/purchase_order_views.xml",
        "views/purchase_report_templates.xml",
    ],
    "installable": True,
    "application": False,
}
