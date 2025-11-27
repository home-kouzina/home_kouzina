# -*- coding: utf-8 -*-
#################################################################################
#
#    Copyright (c) 2019-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#
#################################################################################
import itertools
from odoo import fields, models, api
import odoo.addons.decimal_precision as dp
import logging
_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    flipkart_fsn = fields.Char(
        string='FSN',
        help="The FSN(Flipkart Serial Number) is the unique product identifier for Flipkart"
    )
    hs_code = fields.Char(string="HS Code", help="Standardized code for international shipping and goods declaration")

# class ProductProduct(models.Model):
#     _inherit = "product.product"

