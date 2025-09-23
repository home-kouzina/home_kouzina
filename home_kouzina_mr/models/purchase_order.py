from odoo import models, fields


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    requisition_id = fields.Many2one(
        'material.requisition',
        string="Material Requisition",
        ondelete="cascade"
    )
