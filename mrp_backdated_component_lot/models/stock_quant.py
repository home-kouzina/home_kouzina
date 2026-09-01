# -*- coding: utf-8 -*-

from odoo import fields, models


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    use_for_backdated_mo = fields.Boolean(
        string='Backdated MO Buffer',
        help=(
            "When ticked, this lot/location quant is used to cover "
            "Manufacturing Order components whenever the MO is confirmed "
            "with a Scheduled Date earlier than today, instead of the "
            "normal FIFO (oldest incoming date) lot."
        ),
    )
