{
    'name': 'Inventory Variation',
    'version': '18.0',
    'category': 'Home Kouzina',
    'summary': 'Physical vs System stock variance tracking and reporting',
    'description': """
    Inventory Variation
    ===================
    Allows warehouse staff to:
    - Record physical counts per session
    - Compare them with system stock
    - Compute variances
    - Export results to Excel
    - Create reconciliation adjustments
    """,
    'license': 'LGPL-3',
    'depends': ['base', 'stock', 'mrp','sale'],
    'data': [
        'data/sequence.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/inventory_variation_views.xml',
        'reports/inventory_variation_report.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
