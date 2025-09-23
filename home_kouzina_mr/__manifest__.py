{
    'name': 'Material Requisition',
    'category': 'Inventory',
    'summary': 'Streamlined process for requesting and acquiring stock items',
    'version': '18.0',
    'description': """
        This module facilitates a streamlined process for requesting and acquiring stock items from a designated store.
        Key Features:
        - Users can submit material requisition requests.
        - Inventory managers can check for item availability.
        - Approval workflow for requests.
        - Dispatch of approved items to departments.
        - Initiation of procurement process for unavailable items.
        - Tracking of all actions and real-time status updates for users.
    """,
    'depends': ['base', 'stock', 'hr', 'mail','purchase','sale','purchase'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/material_requisition_views.xml',
        'reports/material_requisition_report.xml',
        'wizards/purchase_requisition_report_wizard_views.xml',
    ],
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}