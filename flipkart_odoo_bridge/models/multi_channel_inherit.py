# -*- coding: utf-8 -*-
#################################################################################
#
#    Copyright (c) 2019-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#
#################################################################################
from odoo import fields, models, api, _
import logging
_logger = logging.getLogger(__name__)
class WkFeed(models.Model):
    _inherit = "wk.feed"

    @api.model
    def get_product_fields(self):
        res = super(WkFeed, self).get_product_fields()
        res.append('flipkart_fsn')
        return res

class ProductVaraintFeed(models.Model):
    _inherit = 'product.variant.feed'

    flipkart_fsn = fields.Char(
        string='FSN',
    )