{
    'name': 'Logistics',
    'version': '18.0',
    'category': 'Home Kouzina',
    'summary': 'Distribute logistic cost across products in Purchase and Sale Orders',
    'description': """Logistics """,
    'license': 'LGPL-3',
    'depends': ['base', 'stock', 'mrp','sale','home_kouzina_sales'],
    'data':[
        'views/stock_picking_views.xml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
