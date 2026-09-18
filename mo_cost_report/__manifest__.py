{
    'name': 'MO Cost Report',
    'version': '18.0.1.0.0',
    'summary': 'Manufacturing Orders Cost Report',
    'description': """
        Adds a List View Report under Manufacturing > Reporting > MO Cost Report.
        Displays: Product, MO Number, and Cost per Manufacturing Order.
    """,
    'author': 'Custom',
    'category': 'Manufacturing',
    # mrp_auto_component_lots added: the SQL view now reads
    # mrp.production.requested_date, a field that module defines. Without
    # this dependency, installing mo_cost_report somewhere that module isn't
    # installed would crash the view's CREATE VIEW with a missing-column
    # error and break the whole module.
    'depends': ['mrp', 'mrp_account', 'visible_group_export', 'mrp_auto_component_lots'],
    'data': [
        'security/ir.model.access.csv',
        'views/mo_cost_report_views.xml',
        'views/mo_cost_report_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'mo_cost_report/static/src/css/mo_cost_report.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
