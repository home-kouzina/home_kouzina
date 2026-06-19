{
    'name': 'Marketplace Type Bulk Update on Sale Orders',
    'version': '18.0.1.0.0',
    'summary': 'Bulk update Marketplace Type on selected Sale Orders from list view via wizard',
    'description': """
Marketplace Type Bulk Update
=============================
Depends on the existing 'marketplace' module (marketplace.master model and
marketplace_type field already defined on sale.order).

- Adds "Set Marketplace Type" button in Sale Order list view header.
- Select one or more Sale Orders, click the button, pick a Marketplace Type
  in the wizard, and apply it to all selected orders in one go.
""",
    'category': 'Sales',
    'author': 'Your Company',
    'depends': ['sale', 'marketplace'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/marketplace_update_wizard_views.xml',
        'wizard/marketplace_update_wizard_action.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
