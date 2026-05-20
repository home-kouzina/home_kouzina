from odoo import models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def action_open_uom_change_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Change Product UoM",
            "res_model": "product.uom.change.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_product_tmpl_ids": [(6, 0, self.ids)],
                "default_new_uom_id": self.uom_id.id,
            },
        }
