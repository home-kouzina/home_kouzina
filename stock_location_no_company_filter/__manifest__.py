# -*- coding: utf-8 -*-
{
    'name': 'Stock Location No Company Filter',
    'version': '18.0.1.0.0',
    'summary': 'Allow selecting Source/Destination locations regardless of company on stock transfers',
    'description': """
By default Odoo restricts the Source/Destination Location fields on stock
transfers (pickings, moves and move lines) to locations belonging to the
current company (or no company). This module removes that restriction so
any location can be selected regardless of company.
""",
    'category': 'Inventory/Inventory',
    'depends': ['stock'],
    'data': [],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
