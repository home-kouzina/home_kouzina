from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def write(self, vals):
        res = super().write(vals)
        if 'date_done' in vals:
            amazon_orders = self.filtered(
                lambda picking: picking.state == 'done'
                and picking.sale_id.amazon_order_ref
            ).mapped('sale_id')
            amazon_orders._amazon_auto_create_invoice()
        return res
