{
    "name": "Inventory Stock Update",
    "version": "18.0",
    'category': 'Home Kouzina',
    "depends": ["web","stock"],
    "data": [
        "security/ir.model.access.csv",
        "wizard/inventory_wizard_view.xml"
    ],
    "assets": {
    "web.assets_backend":
        [
        'hk_stock_update/static/src/js/inventory.js',
        ],
    },
    "installable": True,
    "application": True,
}
