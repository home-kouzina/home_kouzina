import re

from odoo import models, fields, api
from odoo.exceptions import ValidationError


BILL_SEQUENCE_PATTERN = re.compile(r'^BILL/([^/]+)/[^/]+/(\d+)$')


class AccountMove(models.Model):
    _inherit = 'account.move'

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        help='Warehouse from which this invoice originated.'
    )

    def _get_vendor_bill_name_without_month(self):
        self.ensure_one()
        if self.move_type != 'in_invoice' or not self.name:
            return False

        match = BILL_SEQUENCE_PATTERN.match(self.name)
        if not match:
            return False

        return f'BILL/{match.group(1)}/{match.group(2)}'

    def _remove_month_from_vendor_bill_names(self):
        for move in self:
            name_without_month = move._get_vendor_bill_name_without_month()
            if name_without_month and name_without_month != move.name:
                move.with_context(skip_vendor_bill_month_removal=True).name = name_without_month

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)

        for move in moves:

            # -------------------------------------------------------
            # 1. Fetch warehouse from Sale Order (if invoice from SO)
            # -------------------------------------------------------
            sale_orders = move.invoice_line_ids.mapped('sale_line_ids.order_id')
            if sale_orders and not move.warehouse_id:
                wh = sale_orders[0].warehouse_id
                if wh:
                    move.warehouse_id = wh

            # -------------------------------------------------------
            # 2. Fetch warehouse from Delivery Picking (if exists)
            # -------------------------------------------------------
            pickings = move.invoice_line_ids.mapped('sale_line_ids.order_id.picking_ids')
            if pickings and not move.warehouse_id:
                wh = pickings[0].picking_type_id.warehouse_id
                if wh:
                    move.warehouse_id = wh

            # -------------------------------------------------------
            # 3. APPLY CORRECT SEQUENCE LOGIC
            # -------------------------------------------------------
            if move.warehouse_id and not move.warehouse_id.invoice_prefix_sequence:
                raise ValidationError(
                    f"Please set Invoice Prefix Sequence for warehouse '{move.warehouse_id.name}' first."
                )
            # CASE A → Warehouse exists and has sequence → use warehouse sequence
            if move.warehouse_id and move.warehouse_id.invoice_sequence_id:
                next_number = move.warehouse_id.invoice_sequence_id.next_by_id()
                if next_number:
                    move.name = next_number
        moves._remove_month_from_vendor_bill_names()
        return moves

    def write(self, vals):
        res = super().write(vals)
        if (
            not self.env.context.get('skip_vendor_bill_month_removal')
            and {'name', 'move_type'} & set(vals)
        ):
            self._remove_month_from_vendor_bill_names()
        return res

    def action_post(self):
        res = super().action_post()
        self._remove_month_from_vendor_bill_names()
        return res
