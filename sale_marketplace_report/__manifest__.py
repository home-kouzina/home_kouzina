{
    'name': 'Sale Marketplace Report',
    'version': '18.0.1.0.0',
    'summary': 'Sales Marketplace Report under Sales > Reporting',
    'description': """
        Adds a List View Report under Sales > Reporting > Marketplace Report.
        Displays: Sale Order, Product, Price, Marketplace Type, Customer,
        Order Date, Quantity, Total Amount, Status and Salesperson.
    """,
    'author': 'Custom',
    'category': 'Sales',
    'depends': ['sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_marketplace_report_views.xml',
        'views/sale_marketplace_report_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'sale_marketplace_report/static/src/css/sale_marketplace_report.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
