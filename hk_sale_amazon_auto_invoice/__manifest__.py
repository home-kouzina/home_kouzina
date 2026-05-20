{
    'name': 'HK Sale Amazon Auto Invoice',
    'version': '18.0.1.0.0',
    'summary': 'Automatically create invoices for Amazon orders imported by sale_amazon.',
    'category': 'Sales/Sales',
    'depends': [
        'sale_amazon',
        'account',
    ],
    'data': [
        'data/ir_cron.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
