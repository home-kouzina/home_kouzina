{
    'name': 'Warehouse Invoice Sequence',
    'version': '18.0',
    'category': 'Home Kouzina',
    'summary': 'Manage warehouse-wise invoice numbering and streamline logistics cost allocation.',
    'description': """Manage warehouse-wise invoice numbering and streamline logistics cost allocation. """,
    'license': 'LGPL-3',
    'depends': ['base', 'stock','sale','account'],
    'data':[
        'data/warehouse_sequence_manual_cron.xml',
        'views/account_move.xml',
        'views/stock_warehouse.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
