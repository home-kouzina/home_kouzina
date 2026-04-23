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

            total_product_amount = sum(product_lines.mapped('price_subtotal'))
            if total_product_amount == 0:
                continue

            for line in product_lines:
                if not line.product_uom_qty:
                    continue
                logistic_share = (line.price_subtotal / total_product_amount) * logistic_total
                new_price = (line.price_total + logistic_share) / line.product_uom_qty
                line.product_id.product_tmpl_id.standard_price = new_price
        return res
