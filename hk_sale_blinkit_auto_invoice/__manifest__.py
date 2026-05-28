{
    'name': 'HK Sale Blinkit Auto Invoice',
    'version': '18.0.1.0.0',
    'summary': 'Automatically create customer invoices for Blinkit B2C sale orders.',
    'category': 'Sales/Sales',
    'depends': [
        'marketplace',
        'account',
        'sale_stock',
        'home_kouzina_sales',
    ],
    'data': [
        'data/ir_cron.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
