from odoo import models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def button_confirm(self):
        res = super().button_confirm()

        for order in self:
            # Get all service cost lines
            service_lines = order.order_line.filtered(
                lambda l: l.product_id.product_tmpl_id.is_service_cost
            )

            total_service_cost = sum(service_lines.mapped('price_unit'))

            for line in order.order_line:
                product = line.product_id
                if not product:
                    continue

                # Skip service products themselves
                if product.product_tmpl_id.is_service_cost:
                    continue

                # Final cost = product price + total service cost
                final_cost = line.price_unit + total_service_cost

                product.standard_price = final_cost

        return res