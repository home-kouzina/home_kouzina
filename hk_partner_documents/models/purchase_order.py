from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    billing_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string="Billing Address",
        domain="[('company_id', 'child_of', company_id)]",
    )

    picking_type_id = fields.Many2one(
        domain="['|', ('warehouse_id', '=', False), ('warehouse_id.company_id', 'child_of', company_id)]",
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