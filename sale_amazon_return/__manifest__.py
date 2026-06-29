# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Amazon Returns",
    'summary': "Import Amazon FBM and FBA returns",
    'version': '2.0',
    'category': 'Sales/Sales',
    'license': 'OEEL-1',
    'depends': ['sale_amazon'],
    'data': [
        'security/amazon_return_security.xml',
        'security/ir.model.access.csv',
        'data/amazon_return_cron.xml',
        'views/amazon_return_views.xml',
        'views/amazon_account_views.xml',
    ],
}
