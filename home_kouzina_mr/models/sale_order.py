from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    requisition_id = fields.Many2one(
        'material.requisition',
        string="Material Requisition",
        ondelete="cascade"
    )
