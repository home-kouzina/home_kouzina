from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    cog_before_sale = fields.Float(
        related="product_tmpl_id.cog_before_sale",
        store=True,
        string="COG Before Sale",
        help="Cost of goods before the product is sold.")
    is_finished_good = fields.Boolean(string="Is Finished Good", related="product_tmpl_id.is_finished_good")
    regional_language_name = fields.Char("Regional Language Name",related="product_tmpl_id.regional_language_name")
