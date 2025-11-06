{
    'name': 'HK Inventory Report',
    'version': '18.0',
    'category': 'Home Kouzina',
    'depends': ['stock', 'base'],
    'data': [
        'security/ir.model.access.csv',
        'views/hk_inventory_report.xml',
        'report/hk_inventory_pdf_template.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
