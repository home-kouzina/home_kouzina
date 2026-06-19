{
    'name': 'HK Purchase Report',
    'version': '18.0.1.1',
    'summary': 'Detailed Purchase Reporting List View with Advanced Filters',
    'description': """
        Provides a comprehensive Purchase Reporting screen under Purchase > Reporting.
        Shows Product, SKU, Vendor, Qty, Unit Price and many more fields.
        Includes advanced filters and group-by options for deep analysis.
    """,
    'category': 'Home Kouzina',
    'author': 'Home Kouzina',
    'depends': ['purchase', 'purchase_stock', 'uom'],
    'data': [
        'security/ir.model.access.csv',
        'views/hk_purchase_report_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hk_purchase_report/static/src/scss/hk_purchase_report_list.scss',
            'hk_purchase_report/static/src/js/lot_pills_field.js',
            'hk_purchase_report/static/src/js/lot_pills_field.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
