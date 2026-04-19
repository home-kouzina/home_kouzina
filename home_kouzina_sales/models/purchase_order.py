from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    regional_language_name = fields.Char("Regional Language Name",related="product_id.regional_language_name")
