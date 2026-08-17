from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    vendor_phone = fields.Char(
        string="Vendor Phone",
        compute="_compute_vendor_phone",
    )
    billing_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string="Billing Address",
    )

    picking_type_id = fields.Many2one(
        domain="['|', ('warehouse_id', '=', False), ('warehouse_id.company_id', 'child_of', company_id)]",
    )

    report_shipping_partner_id = fields.Many2one(
        'res.partner',
        string='Report Shipping Address',
        compute='_compute_report_shipping_billing_partner_id',
        help='Delivery-type child contact resolved for the PO report Shipping address.',
    )
    report_billing_partner_id = fields.Many2one(
        'res.partner',
        string='Report Billing Address',
        compute='_compute_report_shipping_billing_partner_id',
        help='Invoice-type child contact resolved for the PO report Billing address.',
    )

    @api.depends("partner_id.phone", "partner_id.mobile")
    def _compute_vendor_phone(self):
        for order in self:
            order.vendor_phone = order.partner_id.phone or order.partner_id.mobile

    @api.depends(
        'dest_address_id',
        'picking_type_id.warehouse_id.partner_id',
        'billing_warehouse_id.partner_id',
    )
    def _compute_report_shipping_billing_partner_id(self):
        for order in self:
            ship_base = order.dest_address_id or order.picking_type_id.warehouse_id.partner_id
            order.report_shipping_partner_id = (
                ship_base.address_get(['delivery'])['delivery'] if ship_base else False
            )

            bill_base = order.billing_warehouse_id.partner_id
            order.report_billing_partner_id = (
                bill_base.address_get(['invoice'])['invoice'] if bill_base else False
            )

    @api.onchange('company_id')
    def _onchange_company_id(self):
        picking_type = self.picking_type_id
        if not (
            picking_type
            and picking_type.code == 'incoming'
            and self._is_allowed_purchase_picking_type_company(picking_type)
        ):
            self.picking_type_id = self._get_picking_type(self.company_id.id)

    @api.onchange('picking_type_id')
    def _onchange_picking_type_id_company(self):
        for order in self:
            order._sync_company_from_picking_type()

    def button_confirm(self):
        for order in self:
            order._sync_company_from_picking_type()
        return super().button_confirm()

    def _sync_company_from_picking_type(self):
        self.ensure_one()
        warehouse_company = self.picking_type_id.warehouse_id.company_id
        if warehouse_company and self.company_id != warehouse_company:
            self.company_id = warehouse_company

    def _is_allowed_purchase_picking_type_company(self, picking_type):
        self.ensure_one()
        warehouse_company = picking_type.warehouse_id.company_id
        while warehouse_company:
            if warehouse_company == self.company_id:
                return True
            warehouse_company = warehouse_company.parent_id
        return not picking_type.warehouse_id
