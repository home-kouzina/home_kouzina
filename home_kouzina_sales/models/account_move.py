from odoo import models, fields

class AccountMove(models.Model):
    _inherit = 'account.move'

    marketplace_invoice_number = fields.Char(string="Marketplace Invoice Number")
    marketplace_invoice_type = fields.Char(string="Invoice Type")
    marketplace_sale_state = fields.Char(string="Sale State")

    def _get_invoice_line_lots(self, line):
        """Finds assigned lot/serial numbers for an invoice line by traversing
        the linked sale order lines and their stock moves."""
        self.ensure_one()

        # Get linked sale order lines
        sale_lines = line.sale_line_ids
        if not sale_lines:
            return []

        # Check if 'Print Lot No' was enabled on any of the originating Sales Orders
        if not any(order.print_lot_no for order in sale_lines.order_id):
            return []

        lot_names = set()
        for sale_line in sale_lines:
            if sale_line.product_id.tracking in ['lot', 'serial']:
                for move in sale_line.move_ids:
                    for move_line in move.move_line_ids:
                        if move_line.lot_id:
                            lot_names.add(move_line.lot_id.name)
                        elif move_line.lot_name:
                            lot_names.add(move_line.lot_name)

        return list(lot_names)