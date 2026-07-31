# -*- coding: utf-8 -*-

from odoo import fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    location_id = fields.Many2one(check_company=False)
    location_dest_id = fields.Many2one(check_company=False)
