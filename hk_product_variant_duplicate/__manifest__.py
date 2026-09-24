# -*- coding: utf-8 -*-
{
    'name': 'Enable Duplicate on Product Variants',
    'version': '18.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Re-enables the "Duplicate" action on Product Variant screens',
    'description': """
Odoo core deliberately removes "Duplicate" from the Product Variant form and
list views (product.product_normal_form_view / product.product_product_tree_view
in the product module), since product.product's own copy() doesn't duplicate a
single variant - it duplicates the whole Product Template and returns the new
template's first variant. See product_views.xml comment: "Variants are
generated depending on the configuration of attributes and values on the
template, so copying them does not make sense."

This module only removes the two views' duplicate="false" flag. The
underlying copy() behavior is untouched - "Duplicate" on a variant still
copies its Product Template, not just that one variant. Explicit user
request, made with that trade-off understood - see CHANGES.md.
""",
    'author': 'Home Kouzina',
    'depends': ['product'],
    'data': [
        'views/product_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
