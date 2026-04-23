import logging
from odoo import models

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def button_confirm(self):
        res = super().button_confirm()

        for order in self:
            

            service_lines = order.order_line.filtered(
                lambda l: l.product_id and l.product_id.product_tmpl_id.is_service_cost
            )

            product_lines = order.order_line.filtered(
                lambda l: l.product_id
                and not l.product_id.product_tmpl_id.is_service_cost
            )

            if not service_lines:
                _logger.info("No service lines found.")
                continue

            if not product_lines:
                _logger.info("No product lines found.")
                continue

            total_service_cost = sum(service_lines.mapped("price_subtotal"))
            total_product_amount = sum(product_lines.mapped("price_subtotal"))

            

            if not total_product_amount:
                _logger.warning("Total product amount is zero. Skipping.")
                continue

            for line in product_lines:
                if not line.product_qty:
                    continue
                product = line.product_id

                ratio = line.price_subtotal / total_product_amount
                service_share = ratio * total_service_cost
                final_cost = (line.price_total + service_share) / line.product_qty

                product.standard_price = final_cost


        return res
