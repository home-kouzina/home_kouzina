from odoo import models


class ProductProduct(models.Model):
    _inherit = "product.product"

    def action_open_uom_change_wizard(self):
        self.ensure_one()
        return self.product_tmpl_id.action_open_uom_change_wizard()
