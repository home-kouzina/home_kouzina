# -*- coding: utf-8 -*-

from odoo import fields, models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    location_id = fields.Many2one(check_company=False)
    location_dest_id = fields.Many2one(check_company=False)
