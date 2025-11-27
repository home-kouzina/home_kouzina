from odoo import models, fields

class AccountMove(models.Model):
    _inherit = 'account.move'

    marketplace_invoice_number = fields.Char(string="Marketplace Invoice Number")
    marketplace_invoice_type = fields.Char(string="Invoice Type")
    marketplace_sale_state = fields.Char(string="Sale State")
