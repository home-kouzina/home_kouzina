{
    'name': 'Message Wizard',
    'summary': """To show messages/warnings in Odoo""",
    'category': 'Home Kouzina',
    'version': '1.0.0',
    'sequence': 1,
    'license':  'Other proprietary',
    'description': """""",
    'data': [
        'security/ir.model.access.csv',
        'wizard/wizard_message.xml',
    ],

    'images': ['static/description/Banner.png'],
    'application': True,
    'installable': True,
    'pre_init_hook': 'pre_init_check',
}
