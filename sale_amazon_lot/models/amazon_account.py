# -*- coding: utf-8 -*-

from collections import OrderedDict

from odoo import _, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero


class AmazonAccount(models.Model):
    _inherit = 'amazon.account'

    def _generate_stock_moves(self, order):
        
        customers_location = self.env.ref('stock.stock_location_customers')
        StockMove = self.env['stock.move']
        generated_moves = StockMove

        for order_line in order.order_line.filtered(
            lambda line: line.product_id.type != 'service' and not line.display_type
        ):
            stock_move = StockMove.create({
                'name': _('Amazon move: %s', order.name),
                'company_id': self.company_id.id,
                'product_id': order_line.product_id.id,
                'product_uom_qty': order_line.product_uom_qty,
                'product_uom': order_line.product_uom.id,
                'location_id': self.location_id.id,
                'location_dest_id': customers_location.id,
                'state': 'confirmed',
                'sale_line_id': order_line.id,
            })

            if order_line.product_id.tracking == 'lot':
                self._amazon_lot_set_quantity_done(stock_move, order_line.product_uom_qty)
            else:
                stock_move._set_quantity_done(order_line.product_uom_qty)

            stock_move.picked = True
            stock_move._action_done()
            generated_moves |= stock_move

        return generated_moves

    def _amazon_lot_set_quantity_done(self, stock_move, quantity):
        """Create done move lines with lots selected FIFO from the Amazon location."""
        self.ensure_one()

        product = stock_move.product_id
        product_uom = product.uom_id
        move_uom = stock_move.product_uom
        rounding = product_uom.rounding

        quantity_product_uom = move_uom._compute_quantity(quantity, product_uom)
        if float_is_zero(quantity_product_uom, precision_rounding=rounding):
            return

        lot_lines = self._amazon_lot_get_fifo_lot_lines(product, quantity_product_uom)
        self._amazon_lot_create_move_lines(stock_move, lot_lines)

    def _amazon_lot_get_fifo_lot_lines(self, product, required_qty):
        """Return FIFO lot allocations for a product in the Amazon account location.

        :param product: product.product tracked by lots
        :param required_qty: required quantity in the product's default UoM
        :return: list of dicts with lot, location, and quantity in product UoM
        """
        self.ensure_one()

        StockQuant = self.env['stock.quant']
        rounding = product.uom_id.rounding

        quant_domain = [
            ('product_id', '=', product.id),
            ('location_id', 'child_of', self.location_id.id),
            ('lot_id', '!=', False),
            '|', ('company_id', '=', False), ('company_id', '=', self.company_id.id),
        ]
        quants = StockQuant.search(quant_domain, order='in_date asc, id asc')

        if not quants:
            fallback_lot = self._amazon_lot_get_or_create_fallback_lot(product)
            return [{
                'lot': fallback_lot,
                'location': self.location_id,
                'quantity': required_qty,
            }]

        remaining_qty = required_qty
        allocations = []
        last_selected_quant = False

        for quant in quants:
            if float_compare(remaining_qty, 0.0, precision_rounding=rounding) <= 0:
                break
            if float_compare(quant.quantity, 0.0, precision_rounding=rounding) <= 0:
                continue

            qty_to_take = min(quant.quantity, remaining_qty)
            allocations.append({
                'lot': quant.lot_id,
                'location': quant.location_id,
                'quantity': qty_to_take,
            })
            remaining_qty -= qty_to_take
            last_selected_quant = quant

        if float_compare(remaining_qty, 0.0, precision_rounding=rounding) > 0:
            fallback_quant = last_selected_quant or quants[0]
            allocations.append({
                'lot': fallback_quant.lot_id,
                'location': fallback_quant.location_id,
                'quantity': remaining_qty,
            })

        return self._amazon_lot_merge_allocations(allocations, rounding)

    def _amazon_lot_get_or_create_fallback_lot(self, product):
        
        self.ensure_one()

        StockLot = self.env['stock.lot']
        lot_name = self._amazon_lot_get_fallback_lot_name(product)
        company = self.company_id or self.env.company

        lot_domain = [
            ('name', '=', lot_name),
            ('product_id', '=', product.id),
            '|', ('company_id', '=', False), ('company_id', '=', company.id),
        ]
        lot = StockLot.search(lot_domain, limit=1)
        if lot:
            return lot

        return StockLot.create({
            'name': lot_name,
            'product_id': product.id,
            'company_id': company.id,
        })

    def _amazon_lot_get_fallback_lot_name(self, product):
        product_name = product.with_context(display_default_code=False).display_name or product.name
        return 'AMZ-%s' % product_name.strip()

    def _amazon_lot_merge_allocations(self, allocations, rounding):
        merged = OrderedDict()
        for allocation in allocations:
            key = (allocation['lot'].id, allocation['location'].id)
            if key not in merged:
                merged[key] = allocation.copy()
            else:
                merged[key]['quantity'] += allocation['quantity']

        return [
            allocation for allocation in merged.values()
            if not float_is_zero(allocation['quantity'], precision_rounding=rounding)
        ]

    def _amazon_lot_create_move_lines(self, stock_move, lot_lines):
        StockMoveLine = self.env['stock.move.line']
        line_fields = StockMoveLine._fields

        for lot_line in lot_lines:
            line_qty = stock_move.product_id.uom_id._compute_quantity(
                lot_line['quantity'], stock_move.product_uom
            )
            vals = {
                'move_id': stock_move.id,
                'company_id': stock_move.company_id.id,
                'product_id': stock_move.product_id.id,
                'location_id': lot_line['location'].id,
                'location_dest_id': stock_move.location_dest_id.id,
                'lot_id': lot_line['lot'].id,
            }

            if 'product_uom_id' in line_fields:
                vals['product_uom_id'] = stock_move.product_uom.id

            if 'quantity' in line_fields:
                vals['quantity'] = line_qty
            elif 'qty_done' in line_fields:
                vals['qty_done'] = line_qty
            else:
                raise UserError(_(
                    "Could not set done quantity on stock move line because neither "
                    "'quantity' nor 'qty_done' exists on stock.move.line."
                ))

            if 'picked' in line_fields:
                vals['picked'] = True

            StockMoveLine.create(vals)
