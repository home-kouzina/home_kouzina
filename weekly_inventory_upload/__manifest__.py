{
    'name': 'Weekly Inventory Upload',
    'version': '18.0.1.2.0',
    'summary': 'Client-friendly weekly inventory upload by Excel with logs, history, error report and undo.',
    'description': '''
Weekly Inventory Upload
=======================
A simple client-facing stock update workflow:
- Download sample template with product and location dropdowns
- Upload Excel file
- Process inventory counts location-wise
- Track upload history
- Keep line logs
- Download error report
- Undo a processed upload
''',
    'author': 'CSL',
    'license': 'LGPL-3',
    'category': 'Inventory/Inventory',
    'depends': ['stock', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/weekly_inventory_upload_views.xml',
    ],
    'installable': True,
    'application': True,
}
