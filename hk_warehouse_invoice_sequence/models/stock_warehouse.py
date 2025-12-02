from odoo import models, fields, api
from odoo.exceptions import ValidationError


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    invoice_prefix_sequence = fields.Char(
        string='Invoice Prefix Sequence',
        help='Prefix used for invoices related to this warehouse.'
    )

    invoice_sequence_id = fields.Many2one(
        'ir.sequence',
        string='Invoice Sequence',
        readonly=True,
        help='Auto-created invoice sequence linked to the warehouse.'
    )

    # ---------------------------------------------------------
    # CREATE WAREHOUSE → CREATE SEQUENCE
    # ---------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('invoice_prefix_sequence'):
                raise ValidationError("Please set Invoice Prefix Sequence before creating warehouse.")
        warehouses = super().create(vals_list)
        for wh in warehouses:
            wh._create_invoice_sequence()
        return warehouses

    def write(self, vals):
        if 'invoice_prefix_sequence' in vals and not vals.get('invoice_prefix_sequence'):
            raise ValidationError("Prefix cannot be empty. Please add Invoice Prefix Sequence.")
        return super().write(vals)

    # Create the sequence for this warehouse
    def _create_invoice_sequence(self):
        self.ensure_one()
        if not self.invoice_prefix_sequence:
            return

        # Prevent duplicate sequence creation
        if self.invoice_sequence_id:
            return

        seq = self.env['ir.sequence'].create({
            'name': f"{self.name} Invoice Sequence",
            'code': f"warehouse.invoice.{self.id}",
            'prefix': self.invoice_prefix_sequence,
            'padding': 6,
            'implementation': 'standard',
            'company_id': self.company_id.id,
        })

        self.invoice_sequence_id = seq.id

    # ---------------------------------------------------------
    # MANUAL ACTION → CREATE MISSING SEQUENCES FOR OLD WAREHOUSES
    # ---------------------------------------------------------
    def action_create_missing_sequences(self):
        for wh in self.search([]):
            if wh.invoice_prefix_sequence and not wh.invoice_sequence_id:
                wh._create_invoice_sequence()
