from odoo import models, fields, api
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        help='Warehouse from which this invoice originated.'
    )

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
        return moves
