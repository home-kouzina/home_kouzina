# -*- coding: utf-8 -*-

from odoo import fields, models
from odoo.tools.float_utils import float_compare, float_round


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    def _assign_fifo_lot_for_move(self, move):
        """Backdated MOs (Scheduled Date in the past) draw components from
        quants flagged 'Backdated MO Buffer' first. Everything else -
        on-time/future MOs, and products with no buffer quant flagged -
        falls through to the original FIFO assignment untouched."""
        if self._is_backdated_mo():
            buffer_quants = self._get_backdated_buffer_quants(move)
            if buffer_quants:
                return self._assign_lots_from_quants_for_move(move, buffer_quants)

        return super()._assign_fifo_lot_for_move(move)

    def _is_backdated_mo(self):
        self.ensure_one()
        if not self.date_start:
            return False
        return self.date_start.date() < fields.Date.context_today(self)

    def _get_backdated_buffer_quants(self, move):
        self.ensure_one()
        return self.env['stock.quant'].search([
            ('product_id', '=', move.product_id.id),
            ('location_id', '=', move.location_id.id),
            ('lot_id', '!=', False),
            ('quantity', '>', 0),
            ('use_for_backdated_mo', '=', True),
        ], order='in_date ASC, id ASC')

    def _assign_lots_from_quants_for_move(self, move, quants):
        """Same consumption logic as the FIFO assignment, restricted to the
        given quant recordset (the flagged buffer lots)."""
        qty_to_cover = self._get_consume_qty_to_assign_in_product_uom(move)
        rounding = move.product_id.uom_id.rounding

        field_data = []
        for quant in quants:
            if float_compare(qty_to_cover, 0.0, precision_rounding=rounding) <= 0:
                break

            available_qty = float_round(
                quant.quantity - quant.reserved_quantity,
                precision_rounding=rounding,
            )
            if float_compare(available_qty, 0.0, precision_rounding=rounding) <= 0:
                continue

            qty_from_quant = min(available_qty, qty_to_cover)

            if move.product_id.tracking == 'serial':
                qty_from_quant = float_round(qty_from_quant, precision_rounding=rounding)
                units = int(qty_from_quant)
                for _unit in range(units):
                    field_data.append({
                        'lot_id': quant.lot_id.id,
                        'lot_name': False,
                        'quantity': 1,
                    })
                    qty_to_cover -= 1
            else:
                field_data.append({
                    'lot_id': quant.lot_id.id,
                    'lot_name': False,
                    'quantity': qty_from_quant,
                })
                qty_to_cover -= qty_from_quant

        if not field_data:
            return False, qty_to_cover

        commands = move._generate_serial_move_line_commands(field_data)
        move.write({'move_line_ids': commands})
        return True, qty_to_cover
