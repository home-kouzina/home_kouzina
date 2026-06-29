# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Amazon Payment Gateway",
    'summary': "Show the Amazon payment method on sales orders",
    'version': '1.0',
    'category': 'Sales/Sales',
    'license': 'OEEL-1',
    'depends': ['sale_amazon'],
    'data': [
        'views/sale_order_views.xml',
    ],
}
