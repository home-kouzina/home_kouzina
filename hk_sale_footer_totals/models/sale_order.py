from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    total_discount_rs = fields.Monetary(
        string="Discount",
        compute="_compute_footer_breakdown_amounts",
        currency_field="currency_id",
        tracking=True,
        readonly=True,
    )
    fleet_charges_rs = fields.Monetary(
        string="Fleet Charges",
        compute="_compute_footer_breakdown_amounts",
        currency_field="currency_id",
        tracking=True,
        readonly=True,
    )

    def _iter_priced_lines(self):
        """Return only non-section/non-note lines with a product."""
        self.ensure_one()
        return self.order_line.filtered(lambda line: not line.display_type and line.product_id)

    @api.depends(
        "order_line.display_type",
        "order_line.product_id",
        "order_line.product_id.product_tmpl_id.is_service_cost",
        "order_line.discount",
        "order_line.price_unit",
        "order_line.product_uom_qty",
        "order_line.price_subtotal",
    )
    def _compute_footer_breakdown_amounts(self):
        for order in self:
            discount_amount = 0.0
            fleet_charges_amount = 0.0

            for line in order._iter_priced_lines():
                if line.discount:
                    discount_amount += (line.price_unit * line.product_uom_qty * line.discount) / 100.0
                if line.product_id.product_tmpl_id.is_service_cost:
                    fleet_charges_amount += line.price_subtotal

            order.total_discount_rs = order.currency_id.round(discount_amount)
            order.fleet_charges_rs = order.currency_id.round(fleet_charges_amount)
