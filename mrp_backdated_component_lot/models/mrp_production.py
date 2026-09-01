# -*- coding: utf-8 -*-

from odoo import fields, models
from odoo.tools.float_utils import float_compare, float_round


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    def action_confirm(self):
        res = super().action_confirm()
        self._reassign_backdated_buffer_lots()
        return res

    def _reassign_backdated_buffer_lots(self):
        """Core Odoo already reserves raw material moves (picking a lot via
        the standard removal order) as part of action_confirm, before any
        lot-fetch logic runs. For backdated MOs, undo that auto-picked
        reservation and re-reserve from the flagged buffer lot instead -
        only when the move isn't already fully on a buffer lot."""
        for production in self:
            if production.state not in ('confirmed', 'progress', 'to_close') or not production._is_backdated_mo():
                continue

            for move in production.move_raw_ids.filtered(
                lambda m:
                m.product_id
                and m.product_id.tracking in ('lot', 'serial')
                and m.state not in ('done', 'cancel')
            ):
                buffer_quants = production._get_backdated_buffer_quants(move)
                if not buffer_quants:
                    continue

                current_lots = move.move_line_ids.mapped('lot_id')
                if current_lots and set(current_lots.ids) <= set(buffer_quants.lot_id.ids):
                    continue

                move._do_unreserve()
                production._assign_fifo_lot_for_move(move)

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
        given quant recordset (the flagged buffer lots). Quant math (matching
        against quant.quantity/reserved_quantity) is done in the product's own
        unit of measure; the resulting move line quantity is converted back to
        the move's unit of measure so it displays the same way the BOM
        originally expressed it (e.g. grams), instead of always falling back
        to the product's base UoM."""
        rounding = move.product_id.uom_id.rounding
        move_uom = move.product_uom
        product_uom = move.product_id.uom_id

        qty_to_cover = move_uom._compute_quantity(
            move.product_uom_qty, product_uom, rounding_method='HALF-UP',
        )

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
                        'quantity': product_uom._compute_quantity(1, move_uom, rounding_method='HALF-UP'),
                        'product_uom_id': move_uom.id,
                    })
                    qty_to_cover -= 1
            else:
                field_data.append({
                    'lot_id': quant.lot_id.id,
                    'lot_name': False,
                    'quantity': product_uom._compute_quantity(qty_from_quant, move_uom, rounding_method='HALF-UP'),
                    'product_uom_id': move_uom.id,
                })
                qty_to_cover -= qty_from_quant

        if not field_data:
            return False, qty_to_cover

        commands = move._generate_serial_move_line_commands(field_data)
        move.write({'move_line_ids': commands})
        return True, qty_to_cover
