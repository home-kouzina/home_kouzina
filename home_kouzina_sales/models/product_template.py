from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    cog_before_sale = fields.Float(
        string="COG Before Sale",
        help="Cost of goods before the product is sold.")
    is_finished_good = fields.Boolean(string="Is Finished Good", help="Tick this box if it is finished goods")
    regional_language_name = fields.Char("Regional Language Name")

    def action_create_reorder_point(self):
        """Open wizard to create reorder point."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Reorder Point',
            'res_model': 'reorder.point.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_id': self.product_variant_id.id,
            }
        }
