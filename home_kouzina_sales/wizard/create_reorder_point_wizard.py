from odoo import models, fields, api
from odoo.exceptions import UserError


class CreateReorderPointWizard(models.TransientModel):
    _name = 'reorder.point.wizard'
    _description = 'Reorder Point'

    product_id = fields.Many2one('product.product', string='Product', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True)
    product_min_qty = fields.Float(string='Minimum Quantity', required=True, default=5.0)
    product_max_qty = fields.Float(string='Maximum Quantity', required=True, default=20.0)

    def action_confirm_create(self):
        """Create reorder point on confirm."""
        self.ensure_one()

        # Check existing reorder point
        existing = self.env['stock.warehouse.orderpoint'].search([
            ('product_id', '=', self.product_id.id),
            ('warehouse_id', '=', self.warehouse_id.id)
        ], limit=1)

        if existing:
            raise UserError(f"Reorder point already exists for product '{self.product_id.display_name}' in {self.warehouse_id.name}.")

        # Create new reorder point
        vals = {
            'name': f"Reorder {self.product_id.display_name}",
            'product_id': self.product_id.id,
            'product_min_qty': self.product_min_qty,
            'product_max_qty': self.product_max_qty,
            'warehouse_id': self.warehouse_id.id,
            'location_id': self.warehouse_id.lot_stock_id.id,
        }

        self.env['stock.warehouse.orderpoint'].create(vals)
        return {'type': 'ir.actions.act_window_close'}
