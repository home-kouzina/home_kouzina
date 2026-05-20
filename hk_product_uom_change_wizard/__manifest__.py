{
    "name": "HK Product UoM Change Wizard",
    "summary": "Change product unit of measure from a wizard",
    "version": "18.0.1.0.0",
    "category": "Inventory/Inventory",
    "author": "Home Kouzina",
    "depends": ["product", "purchase"],
    "data": [
        "security/ir.model.access.csv",
        "wizard/product_uom_change_wizard_views.xml",
        "views/product_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
