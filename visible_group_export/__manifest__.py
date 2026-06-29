{
    'name': 'Visible Grouped List Export',
    'version': '18.0.1.0.0',
    'summary': 'Export the currently visible grouped list view to XLSX',
    'description': """
Adds an XLSX export option for Odoo list views that exports the rows currently
visible in the browser, including opened/collapsed group headers and group totals.
Enable per action/view by passing context {'visible_group_export': True}.
    """,
    'category': 'Tools',
    'depends': ['web'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'visible_group_export/static/src/js/visible_group_export.js',
            'visible_group_export/static/src/xml/visible_group_export.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
