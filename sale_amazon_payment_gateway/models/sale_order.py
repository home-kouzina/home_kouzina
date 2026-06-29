# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    amazon_payment_gateway = fields.Char(
        string="Payment Gateway",
        readonly=True,
        copy=False,
        help="The payment method details returned by Amazon, or the general payment method when "
             "details are unavailable.",
    )
