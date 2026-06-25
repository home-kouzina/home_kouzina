# -*- coding: utf-8 -*-
{
    'name': 'MRP Auto Component Lots',
    'version': '18.0.1.0.1',
    'summary': 'Auto-generate receipt lots and finished product lots for manufacturing',
    'description': """ """,
    'category': 'Manufacturing/Manufacturing',
    'depends': ['mrp', 'stock'],
    'data': [
        'views/res_users_views.xml',
        'views/mrp_production_views.xml',
        'views/stock_picking_view.xml',
        'views/product_template_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
