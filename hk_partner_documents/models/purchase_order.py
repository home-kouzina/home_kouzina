from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    shipping_address_id = fields.Many2one(
        "res.partner",
        string="Shipping Address",
    )

    @api.onchange("partner_id")
    def _onchange_partner_id_shipping_address(self):
        for order in self:
            if not order.partner_id:
                order.shipping_address_id = False
                continue

            address = order.partner_id.address_get(["delivery"])
            order.shipping_address_id = address.get("delivery") or order.partner_id
