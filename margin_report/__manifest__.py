{
    'name': 'Sales Margin Report',
    'version': '18.0.1.0.0',
    'summary': 'Sales Margin Report under Sales > Reporting',
    'description': 'Adds a Margin Report list view under Sales > Reporting with COGS, Gross Margin, SKU, EAN, and invoice details.',
    'category': 'Sales',
    'depends': ['sale_management', 'product', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_margin_report_views.xml',
        'views/sale_margin_report_menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
