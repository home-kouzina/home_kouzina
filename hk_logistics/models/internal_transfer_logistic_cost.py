from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    logistic_id = fields.Many2one(
        'product.product',
        string="Logistic Service",
        domain="[('type', '=', 'service')]",
        help="Select the logistic service used for this transfer."
    )
    logistic_amount = fields.Float(
        string="Logistic Amount",
        help="Total cost of logistics to be distributed across products.",
        related='logistic_id.cog_before_sale',
        readonly=False
    )

    @api.model
    def _get_logistic_line(self):
        """Helper: returns logistic service lines (if any exist)"""
        return self.move_ids_without_package.filtered(
            lambda m: m.product_id.type == 'service' and 'logistic' in m.product_id.name.lower()
        )

    def button_validate(self):
        """Override to allocate logistic cost per product unit during internal transfer"""
        res = super(StockPicking, self).button_validate()

        for picking in self:
            # Only internal transfers should apply logistic cost allocation
            if picking.picking_type_id.code != 'internal':
                continue

            logistic_total = 0.0

            # Priority 1: take manually entered logistic_amount
            if picking.logistic_amount:
                logistic_total = picking.logistic_amount
            else:
                # Priority 2: fallback to service move line amount (if available)
                logistic_lines = picking._get_logistic_line()
                logistic_total = sum(m.value for m in logistic_lines if m.value)

            if logistic_total <= 0:
                continue

            # Get product moves (non-service)
            product_moves = picking.move_ids_without_package.filtered(
                lambda m: m.product_id.type != 'service'
            )

            product_values = {
                move: move.product_id.standard_price * move.product_uom_qty
                for move in product_moves
                if move.product_uom_qty
            }
            total_product_value = sum(product_values.values())
            if total_product_value == 0:
                continue

            # Update standard price for each product using value-weighted allocation.
            for move in product_moves:
                if move not in product_values:
                    continue
                product = move.product_id
                old_cost = product.standard_price
                logistic_share = (product_values[move] / total_product_value) * logistic_total
                per_unit_logistic = logistic_share / move.product_uom_qty
                new_cost = old_cost + per_unit_logistic
                product.standard_price = new_cost

                # Optional: add a chatter note
                picking.message_post(
                    body=f"Updated {product.display_name} cost from {old_cost:.2f} to {new_cost:.2f} "
                         f"due to logistic cost allocation ({per_unit_logistic:.2f}/unit)."
                )

        return res
