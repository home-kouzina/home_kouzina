# -*- coding: utf-8 -*-

from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    component_available_location_ids = fields.Many2many(
        'stock.location',
        compute='_compute_component_available_location_ids',
        string='Locations With Stock',
    )

    @api.depends('product_id')
    def _compute_component_available_location_ids(self):
        for move in self:
            if not move.product_id:
                move.component_available_location_ids = False
                continue

            quants = self.env['stock.quant'].search([
                ('product_id', '=', move.product_id.id),
                ('quantity', '>', 0),
                ('location_id.usage', '=', 'internal'),
            ])
            move.component_available_location_ids = quants.location_id
