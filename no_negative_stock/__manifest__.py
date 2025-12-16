{
    "name": "Stock Disallow Negative",
    "version": "18.0.0.0",
    "category": "Home Kouzina",
    "license": "LGPL-3",
    "summary": "Prevents negative stock levels by restricting outgoing stock moves when insufficient inventory is available.",
    "description": "The Stock Disallow Negative module enhances inventory control by blocking any stock operations that "
                   "would result in negative quantities. It ensures that users cannot validate transfers, deliveries, "
                   "or manufacturing moves that would cause product quantities to fall below zero.",
    "depends": ["stock"],
    "data": [
    "views/product_product_views.xml", 
    "views/stock_location_views.xml"
    ],
    'images': ['static/description/banner.jpg'],
    "application": True,
    "installable": True,
}
