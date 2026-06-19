{
    'name': 'Amazon Orders Menu',
    'version': '18.0.1.0.0',
    'summary': 'Adds a dedicated "Amazon Orders" menu under Sales > Orders, showing only orders synced from Amazon.',
    'description': """
Adds a new menu item "Amazon Orders" under Sales > Orders.
It opens the standard Sales Order views (list/kanban/form/...) filtered
to show only orders that came from the Amazon Connector (i.e. orders
linked to an amazon.account record).
""",
    'category': 'Sales/Sales',
    'author': 'Custom',
    'depends': [
        'sale',
        'sale_amazon',   # Odoo's official Amazon Connector module
    ],
    'data': [
        'views/sale_order_amazon_menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
