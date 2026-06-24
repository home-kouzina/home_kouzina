{
    'name': 'Inventory Variation Upload',
    'version': '18.0.1.0.0',
    'category': 'Home Kouzina',
    'summary': 'Upload Physical Qty via Excel directly on the Inventory Variation form',
    'description': """
    Inventory Variation Upload
    ==========================
    Extends the Inventory Variation (hk_inventory_variation) form with:

    - Download Template  — pre-filled Excel with Product, Product Type,
      Sale Price, Location, UoM columns. User fills only Physical Qty.
    - Upload Excel File  — attach the filled template directly on the IVR form.
    - Process Inventory Upload — sets Physical Qty on variation lines.
      System Qty and Variation are fetched/computed automatically.
    - Download Error Report — download failed rows as Excel.
    - Upload Logs tab — full log of success/failed rows per upload.
    """,
    'license': 'LGPL-3',
    'depends': ['hk_inventory_variation'],
    'data': [
        'security/ir.model.access.csv',
        'views/inventory_variation_upload_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
