# -*- coding: utf-8 -*-
{
    'name': 'MRP Retail Skip Approval',
    'version': '18.0.1.0.0',
    'summary': 'Skip the manufacturing approval workflow for retail products',
    'description': """
The "MRP Auto Component Lots" module adds a Submit for Approval / Approve
workflow on Manufacturing Orders before they can be confirmed.

For products flagged as "Is Retail" on the product form, this module hides
those approval buttons entirely, so the Manufacturing Order follows the
standard Odoo flow instead: Draft -> Confirmed -> Done, with no approval
step required. Non-retail products keep the existing approval workflow
untouched.
""",
    'category': 'Manufacturing/Manufacturing',
    'depends': ['mrp', 'mrp_auto_component_lots', 'home_kouzina_sales'],
    'data': [
        'views/mrp_production_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
