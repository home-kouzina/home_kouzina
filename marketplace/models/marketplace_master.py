import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class MarketplaceMaster(models.Model):
    _name = 'marketplace.master'
    _description = 'Marketplace Master'

    name = fields.Char(string='Marketplace Name', required=True)
    code = fields.Char(
        string='Technical Code',
        help='Stored value used by sale orders and reports. Example: blinkit.',
    )
    warehouse_map = fields.Many2one('stock.warehouse', string='Warehouse')
    so_tag = fields.Many2one('crm.tag', string='Default Sales Order Tag')

    @api.model
    def _get_default_marketplace_selection(self):
        return [
            ('flipkart', 'Flipkart'),
            ('amazon', 'Amazon'),
            ('blinkit', 'Blinkit'),
            ('shopify', 'Shopify'),
            ('homekozin', 'HomeKouzina'),
        ]

    @api.model
    def _normalize_marketplace_code(self, name):
        return re.sub(r'[^a-z0-9]+', '_', (name or '').strip().lower()).strip('_')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('code') and vals.get('name'):
                vals['code'] = self._normalize_marketplace_code(vals['name'])
            elif vals.get('code'):
                vals['code'] = self._normalize_marketplace_code(vals['code'])
        return super().create(vals_list)

    @api.onchange('name')
    def _onchange_name_set_code(self):
        for marketplace in self:
            if marketplace.name and not marketplace.code:
                marketplace.code = marketplace._normalize_marketplace_code(marketplace.name)

    def write(self, vals):
        if vals.get('code'):
            vals = dict(vals, code=self._normalize_marketplace_code(vals['code']))
        res = super().write(vals)
        if vals.get('name') and 'code' not in vals:
            for marketplace in self.filtered(lambda record: not record.code):
                marketplace.code = self._normalize_marketplace_code(marketplace.name)
        return res

    @api.constrains('name', 'code')
    def _check_unique_name_code(self):
        for marketplace in self:
            if marketplace.name:
                duplicate_name = self.search_count([
                    ('id', '!=', marketplace.id),
                    ('name', '=ilike', marketplace.name.strip()),
                ])
                if duplicate_name:
                    raise ValidationError("Marketplace name already exists.")

            if marketplace.code:
                duplicate_code = self.search_count([
                    ('id', '!=', marketplace.id),
                    ('code', '=ilike', marketplace.code.strip()),
                ])
                if duplicate_code:
                    raise ValidationError("Marketplace technical code already exists.")
