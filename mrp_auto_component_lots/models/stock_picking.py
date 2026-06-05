# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_round


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    show_auto_assign_receipt_lots = fields.Boolean(
        string='Show Auto Assign Receipt Lots',
        compute='_compute_show_auto_assign_receipt_lots',
    )

    @api.depends(
        'state',
        'picking_type_id.code',
        'move_ids.product_id.tracking',
        'move_ids.product_uom_qty',
        'move_ids.quantity',
        'move_ids.move_line_ids.quantity',
        'move_ids.move_line_ids.lot_id',
        'move_ids.move_line_ids.lot_name',
    )
    def _compute_show_auto_assign_receipt_lots(self):
        for picking in self:
            picking.show_auto_assign_receipt_lots = bool(
                picking.picking_type_id.code == 'incoming'
                and picking.state not in ('done', 'cancel')
                and picking._get_receipt_moves_needing_lots()
            )

    def _get_receipt_moves_needing_lots(self):
        self.ensure_one()

        if self.picking_type_id.code != 'incoming':
            return self.env['stock.move']

        return self.move_ids.filtered(
            lambda move:
            move.product_id
            and move.product_id.tracking == 'lot'
            and move.state not in ('done', 'cancel')
            and not any(line.lot_id or line.lot_name for line in move.move_line_ids)
            and float_compare(
                self._get_receipt_qty_to_assign_in_product_uom(move),
                0.0,
                precision_rounding=move.product_id.uom_id.rounding,
            ) > 0
        )

    def _get_receipt_qty_to_assign_in_product_uom(self, move):
        self.ensure_one()

        blank_lines = move.move_line_ids.filtered(
            lambda line: not line.lot_id and not line.lot_name
        )

        qty_in_product_uom = sum(blank_lines.mapped('quantity'))

        if float_compare(
            qty_in_product_uom,
            0.0,
            precision_rounding=move.product_id.uom_id.rounding,
        ) <= 0:
            if 'quantity' in move._fields and move.quantity:
                qty_in_product_uom = move.quantity
            else:
                qty_in_product_uom = move.product_uom._compute_quantity(
                    move.product_uom_qty,
                    move.product_id.uom_id,
                    rounding_method='HALF-UP',
                )

        return float_round(
            qty_in_product_uom,
            precision_rounding=move.product_id.uom_id.rounding,
        )

    def action_auto_assign_receipt_lots(self):
        generated_count = 0
        skipped_count = 0

        for picking in self:
            if picking.picking_type_id.code != 'incoming':
                raise UserError(_("Automatic receipt lot assignment is allowed only on receipts."))

            if picking.state in ('done', 'cancel'):
                raise UserError(_("You cannot assign lots on done or cancelled receipts."))

            lot_tracked_moves = picking.move_ids.filtered(
                lambda move:
                move.product_id
                and move.product_id.tracking == 'lot'
                and move.state not in ('done', 'cancel')
            )

            if not lot_tracked_moves:
                raise UserError(_("No lot-tracked receipt lines were found."))

            moves_to_assign = picking._get_receipt_moves_needing_lots()
            skipped_count += len(lot_tracked_moves - moves_to_assign)

            if not moves_to_assign:
                raise UserError(_("No receipt lines need automatic lot assignment. Existing lot lines were skipped."))

            used_names = set()

            for move in moves_to_assign:
                qty = picking._get_receipt_qty_to_assign_in_product_uom(move)

                if float_compare(
                    qty,
                    0.0,
                    precision_rounding=move.product_id.uom_id.rounding,
                ) <= 0:
                    continue

                lot_name = move.product_id._get_next_auto_lot_name(
                    company=move.company_id,
                    used_names=used_names,
                )
                used_names.add(lot_name)

                lot = move.product_id._get_or_create_auto_stock_lot(
                    lot_name=lot_name,
                    company=move.company_id,
                )

                field_data = [{
                    'lot_id': lot.id,
                    'lot_name': False,
                    'quantity': qty,
                }]

                commands = move._generate_serial_move_line_commands(field_data)
                move.write({'move_line_ids': commands})

                generated_count += 1

        message = _('%s receipt lot line(s) generated.') % generated_count
        if skipped_count:
            message += _(' %s line(s) skipped because lots were already assigned.') % skipped_count

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Receipt lots assigned'),
                'message': message,
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                },
            },
        }