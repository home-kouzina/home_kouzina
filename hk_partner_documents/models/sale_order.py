from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    shipping_gst_number = fields.Char(
        string="GST Number",
        compute="_compute_shipping_gst_number",
    )
    customer_phone = fields.Char(
        string="Customer Phone",
        compute="_compute_customer_phone",
    )

    @api.depends("partner_id.gst_number", "partner_shipping_id.gst_number")
    def _compute_shipping_gst_number(self):
        for order in self:
            order.shipping_gst_number = (
                order.partner_shipping_id.gst_number
                or order.partner_id.gst_number
            )

    @api.depends("partner_id.phone", "partner_id.mobile")
    def _compute_customer_phone(self):
        for order in self:
            order.customer_phone = order.partner_id.phone or order.partner_id.mobile

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    manufacturing_date = fields.Date(
        string="Manufacturing Date"
    )

    expiry_date = fields.Date(
        string="Expiry Date"
    )

    def _prepare_invoice_line(self, **optional_values):
        vals = super()._prepare_invoice_line(**optional_values)

        vals.update({
            'manufacturing_date': self.manufacturing_date,
            'expiry_date': self.expiry_date,
        })

        return vals

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    manufacturing_date = fields.Date(
        string="Manufacturing Date"
    )

    expiry_date = fields.Date(
        string="Expiry Date"
    )