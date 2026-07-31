# -*- coding: utf-8 -*-
{
    'name': 'MRP Component Lot Fetch',
    'version': '18.0.1.0.0',
    'summary': 'Fetch the FIFO stock lot/serial number for MO component lines',
    'description': """
Adds an "Assign Component Lots" button on confirmed Manufacturing Orders.
For each component line whose Lot/Serial Number column is still empty, it
looks up the oldest available stock lot in the source location (FIFO by
incoming date) - the same lot that was generated when that product was
purchased and received into inventory - and fills it in.

This module is standalone and does not modify any existing module or flow.
""",
    'category': 'Manufacturing/Manufacturing',
    'depends': ['mrp', 'stock'],
    'data': [
        'views/mrp_production_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
