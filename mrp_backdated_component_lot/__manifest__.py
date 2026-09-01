# -*- coding: utf-8 -*-
{
    'name': 'MRP Backdated Component Lot Assignment',
    'version': '18.0.1.0.0',
    'summary': 'Draw components from a flagged buffer lot when a Manufacturing Order is confirmed with a past scheduled date',
    'description': """
Adds a "Backdated MO Buffer" checkbox on stock quants (visible on the
Location/Product/Lot on-hand quantities list).

When a Manufacturing Order is confirmed and its Scheduled Date is earlier
than today, component lines for products that have a quant flagged as
"Backdated MO Buffer" are assigned that buffer lot instead of the normal
FIFO (oldest incoming date) lot.

Manufacturing Orders whose Scheduled Date is today or in the future, and
products with no buffer lot flagged, keep the existing FIFO behavior
untouched.
""",
    'category': 'Manufacturing/Manufacturing',
    'depends': ['mrp_component_lot_fetch'],
    'data': [
        'views/stock_quant_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
