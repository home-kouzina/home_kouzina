# -*- coding: utf-8 -*-

from odoo import fields, models


class SaleReport(models.Model):
    _inherit = "sale.report"

    marketplace_type = fields.Selection([
        ('flipkart', 'Flipkart'),
        ('amazon', 'Amazon'),
        ('blinkit', 'Blinkit'),
        ('shopify', 'Shopify'),
        ('homekozin', 'HomeKouzina'),
    ], string="Marketplace", readonly=True)

    city = fields.Char(string="City", readonly=True)

    def _select_additional_fields(self):
        res = super()._select_additional_fields()
        res['marketplace_type'] = "s.marketplace_type"
        res['city'] = "partner.city"
        return res

    def _group_by_sale(self):
        res = super()._group_by_sale()
        res += """,
            s.marketplace_type,
            partner.city"""
        return res
