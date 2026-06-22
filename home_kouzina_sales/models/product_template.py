from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # ❌ DELETE cog_before_sale from here — it overrides the computed one on product.product
    is_finished_good = fields.Boolean(string="Is Finished Good", help="Tick this box if it is finished goods")
    regional_language_name = fields.Char("Regional Language Name")
    is_labelling = fields.Boolean(string="Is Labelling", help="Tick this box if it is for labelling")
    is_packaging = fields.Boolean(string="Is Packaging", help="Tick this box if it is for packaging")
    is_retail = fields.Boolean(string="Is Retail", help="Tick this box if it is retail")

    def action_create_reorder_point(self):
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