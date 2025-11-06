from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    payment_details = fields.Char(string="Payment Details")
