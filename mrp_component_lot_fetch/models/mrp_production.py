# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_round


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    show_fetch_component_lots = fields.Boolean(
        string='Show Fetch Component Lots',
        compute='_compute_show_fetch_component_lots',
    )

    def action_confirm(self):
        res = super().action_confirm()
        self._auto_fetch_component_lots_silent()
        return res

    def button_mark_done(self):
        res = super().button_mark_done()
        self._create_finished_product_internal_transfer()
        return res

    def _create_finished_product_internal_transfer(self):
        """On Produce/Produce All, create a draft internal transfer
        (WH/Stock -> WH/Stock) carrying the finished product, so it shows up
        under the standard 'Transfers' smart button. Left in draft for the
        user to edit the destination location and validate. Skips MOs that
        already have one (e.g. a backorder re-triggering this)."""
        for production in self:
            warehouse = production.picking_type_id.warehouse_id
            picking_type = warehouse.int_type_id

            if not picking_type or not warehouse.lot_stock_id:
                continue

            existing = self.env['stock.picking'].search([
                ('picking_type_id', '=', picking_type.id),
                ('origin', '=', production.name),
                ('move_ids.product_id', '=', production.product_id.id),
            ], limit=1)
            if existing:
                continue

            produced_qty = production.qty_producing or production.product_qty

            picking = self.env['stock.picking'].create({
                'picking_type_id': picking_type.id,
                'location_id': warehouse.lot_stock_id.id,
                'location_dest_id': warehouse.lot_stock_id.id,
                'origin': production.name,
                'group_id': production.procurement_group_id.id,
                'move_ids': [(0, 0, {
                    'name': production.product_id.display_name,
                    'product_id': production.product_id.id,
                    'product_uom_qty': produced_qty,
                    'product_uom': production.product_uom_id.id,
                    'location_id': warehouse.lot_stock_id.id,
                    'location_dest_id': warehouse.lot_stock_id.id,
                    'origin': production.name,
                    'group_id': production.procurement_group_id.id,
                })],
            })

    @api.depends(
        'state',
        'move_raw_ids.product_id.tracking',
        'move_raw_ids.state',
        'move_raw_ids.product_uom_qty',
        'move_raw_ids.quantity',
        'move_raw_ids.move_line_ids.quantity',
        'move_raw_ids.move_line_ids.lot_id',
        'move_raw_ids.move_line_ids.lot_name',
    )
    def _compute_show_fetch_component_lots(self):
        for production in self:
            production.show_fetch_component_lots = bool(
                production.state in ('confirmed', 'progress', 'to_close')
                and production._get_component_moves_needing_lots()
            )

    def _get_component_moves_needing_lots(self):
        self.ensure_one()

        return self.move_raw_ids.filtered(
            lambda move:
            move.product_id
            and move.product_id.tracking in ('lot', 'serial')
            and move.state not in ('done', 'cancel')
            and not any(line.lot_id or line.lot_name for line in move.move_line_ids)
            and float_compare(
                self._get_consume_qty_to_assign_in_product_uom(move),
                0.0,
                precision_rounding=move.product_id.uom_id.rounding,
            ) > 0
        )

    def _get_consume_qty_to_assign_in_product_uom(self, move):
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

    def _assign_fifo_lot_for_move(self, move):
        """Fill in the blank move lines of a single raw-material move with
        stock lots picked in strict FIFO order (oldest incoming date first).
        Returns True if at least one lot line was written."""
        qty_to_cover = self._get_consume_qty_to_assign_in_product_uom(move)
        rounding = move.product_id.uom_id.rounding

        quants = self.env['stock.quant'].search([
            ('product_id', '=', move.product_id.id),
            ('location_id', '=', move.location_id.id),
            ('lot_id', '!=', False),
            ('quantity', '>', 0),
        ], order='in_date ASC, id ASC')

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

    def _auto_fetch_component_lots_silent(self):
        """Called automatically after action_confirm. Fills in FIFO lots for
        every component that needs one, without raising errors or notifying -
        MOs with nothing to do (no lot-tracked components, insufficient
        stock, etc.) are simply left as-is for a later manual retry via the
        'Assign Component Lots' button."""
        for production in self:
            if production.state not in ('confirmed', 'progress', 'to_close'):
                continue

            for move in production._get_component_moves_needing_lots():
                production._assign_fifo_lot_for_move(move)

    def action_fetch_component_lots(self):
        generated_count = 0
        skipped_count = 0
        shortage_products = set()

        for production in self:
            if production.state not in ('confirmed', 'progress', 'to_close'):
                raise UserError(_(
                    "You can fetch component lots only on confirmed, "
                    "in progress, or to close Manufacturing Orders."
                ))

            lot_tracked_moves = production.move_raw_ids.filtered(
                lambda move:
                move.product_id
                and move.product_id.tracking in ('lot', 'serial')
                and move.state not in ('done', 'cancel')
            )

            if not lot_tracked_moves:
                raise UserError(_("No lot/serial-tracked component lines were found."))

            moves_to_assign = production._get_component_moves_needing_lots()
            skipped_count += len(lot_tracked_moves - moves_to_assign)

            if not moves_to_assign:
                raise UserError(_(
                    "No component lines need a lot/serial number fetched. "
                    "Existing lot lines were skipped."
                ))

            for move in moves_to_assign:
                assigned, remaining_qty = production._assign_fifo_lot_for_move(move)
                rounding = move.product_id.uom_id.rounding

                if not assigned:
                    shortage_products.add(move.product_id.display_name)
                    continue

                if float_compare(remaining_qty, 0.0, precision_rounding=rounding) > 0:
                    shortage_products.add(move.product_id.display_name)

                generated_count += 1

        message = _('%s component lot line(s) fetched.') % generated_count
        if skipped_count:
            message += _(' %s line(s) skipped because lots were already assigned.') % skipped_count
        if shortage_products:
            message += _(
                ' No available stock lot found (or insufficient quantity) for: %s.'
            ) % ', '.join(sorted(shortage_products))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Component lots fetched'),
                'message': message,
                'type': 'success' if generated_count else 'warning',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                },
            },
        }
