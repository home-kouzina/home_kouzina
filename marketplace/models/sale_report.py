# -*- coding: utf-8 -*-

from odoo import fields, models


class SaleReport(models.Model):
    _inherit = "sale.report"

    def _get_marketplace_type_selection(self):
        marketplaces = self.env['marketplace.master'].sudo().search([], order='name')
        selection = []
        seen_codes = set()
        for marketplace in marketplaces:
            code = marketplace.code or marketplace._normalize_marketplace_code(marketplace.name)
            if not code or code in seen_codes:
                continue
            selection.append((code, marketplace.name))
            seen_codes.add(code)
        return selection or self.env['marketplace.master']._get_default_marketplace_selection()

    marketplace_type = fields.Selection(
        selection='_get_marketplace_type_selection',
        string="Marketplace",
        readonly=True,
    )

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
