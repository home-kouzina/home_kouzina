# -*- coding: utf-8 -*-
{
    'name': 'Marketplace Integration',
    'version': '1.0',
    'summary': 'Integrate custom fields for different marketplaces in Sales Orders.',
    'category': 'Home Kouzina',
    'depends': [
        'sale_management',
        'stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_report_view.xml',
        'views/sale_order_view.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
