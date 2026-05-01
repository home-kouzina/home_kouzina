from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    shipping_gst_number = fields.Char(
        string="GST Number",
        compute="_compute_shipping_gst_number",
    )

    @api.depends("partner_id.gst_number", "partner_shipping_id.gst_number")
    def _compute_shipping_gst_number(self):
        for order in self:
            order.shipping_gst_number = (
                order.partner_shipping_id.gst_number
                or order.partner_id.gst_number
            )
