from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_service_cost = fields.Boolean(string="Service Cost Product", help="Tick this box if the product is used for service cost calculation")