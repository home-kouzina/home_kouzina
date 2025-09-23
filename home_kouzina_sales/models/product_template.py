from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    cog_before_sale = fields.Float(
        string="COG Before Sale",
        help="Cost of goods before the product is sold.")
    is_finished_good = fields.Boolean(string="Is Finished Good", help="Tick this box if it is finished goods")
