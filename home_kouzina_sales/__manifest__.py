{
    'name': 'Home Kouzina Sales',
    'category': 'Sales',
    'summary': 'Download & Upload Excel Template for Sale Order Creation',
    'version': '18.0',
    'description': """
        Provides two buttons in Sale Orders:
        - Download Template: download a blank Excel template.
        - Upload Template: upload filled Excel and create Sale Orders.
    """,
    'depends': ['base', 'sale_management','sale','product','marketplace'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_view.xml',
        'views/product_views.xml',
        'views/product_packages_views.xml',
        'views/sale_order_line_views.xml',
        'views/stock_picking.xml',
        'views/marketplace_master_views.xml',
        'wizard/marketplace_order_import_wizard_views.xml',
        'wizard/marketplace_template_download_wizard.xml',
    ],
    "assets": {
        "web.assets_backend": [
            "home_kouzina_sales/static/src/js/sale_order_list_button.js",
            "home_kouzina_sales/static/src/xml/web_list_view_button.xml",
        ],
    },
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}
