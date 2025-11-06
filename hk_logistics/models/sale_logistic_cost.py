from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def _get_logistic_line(self):
        """Helper: returns logistic service order lines if present"""
        return self.order_line.filtered(lambda l: l.product_id.type == 'service' and 'logistic' in l.product_id.name.lower())

    def action_confirm(self):
        """Override to allocate logistic cost per product unit"""
        res = super(SaleOrder, self).action_confirm()

        for order in self:
            logistic_lines = order._get_logistic_line()
            if not logistic_lines:
                continue

            logistic_total = sum(line.price_subtotal for line in logistic_lines)
            product_lines = order.order_line.filtered(lambda l: l.product_id.type != 'service')

            total_qty = sum(product_lines.mapped('product_uom_qty'))
            if total_qty == 0:
                continue

            per_unit_logistic =  total_qty / logistic_total

            for line in product_lines:
                old_price = line.price_unit
                new_price = old_price + per_unit_logistic
                line.product_template_id.standard_price = new_price
        return res
