from odoo import models, fields, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def update_package_quantities(self):
        for picking in self:
            # Loop through all moves that are linked to sale order lines
            for move in picking.move_ids.filtered(lambda m: m.sale_line_id):
                sale_line = move.sale_line_id

                # Get package products linked to this sale order line
                package_products = sale_line.package_ids.mapped('product_id')
                if not package_products:
                    continue

                # Calculate total quantity of main products in the picking
                main_products_qty = picking.move_ids.filtered(
                    lambda m: m.product_id not in package_products
                ).mapped('quantity')
                total_main_qty = sum(main_products_qty)

                # Update all package product moves in this picking
                package_moves = picking.move_ids.filtered(
                    lambda m: m.product_id in package_products
                )
                for pkg_move in package_moves:
                    pkg_move.quantity = total_main_qty
        return True
