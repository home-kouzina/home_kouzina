# -*- coding: utf-8 -*-

import re

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    auto_component_lot_prefix = fields.Char(
        string='Auto Lot Prefix',
        copy=False,
        help=(
            "Internal prefix used by automatic lot assignment on receipts "
            "and manufacturing orders. Users do not need to maintain this manually."
        ),
    )


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _get_or_create_auto_lot_prefix(self):
        self.ensure_one()

        template = self.product_tmpl_id
        if template.auto_component_lot_prefix:
            return template.auto_component_lot_prefix

        base_prefix = self._build_auto_lot_prefix()
        prefix = base_prefix
        counter = 2

        ProductTemplate = self.env['product.template'].sudo()
        while ProductTemplate.search_count([
            ('id', '!=', template.id),
            ('auto_component_lot_prefix', '=', prefix),
        ]):
            prefix = '%s%s' % (base_prefix, counter)
            counter += 1

        template.sudo().write({
            'auto_component_lot_prefix': prefix,
        })
        return prefix

    def _build_auto_lot_prefix(self):
        self.ensure_one()

        name = self.product_tmpl_id.name or self.name or self.display_name or ''
        name = re.sub(r'^\s*\[[^\]]+\]\s*', '', name)
        words = re.findall(r'[A-Za-z0-9]+', name)

        if len(words) >= 2:
            prefix = ''.join(word[0] for word in words[:2])
        elif words:
            prefix = words[0][:2]
        else:
            prefix = 'LT'

        prefix = re.sub(r'[^A-Za-z0-9]', '', prefix).upper()
        return prefix or 'LT'

    def _get_auto_lot_date_token(self):
        today = fields.Date.context_today(self)
        return today.strftime('%y%j')

    def _get_next_auto_lot_name(self, company, used_names=None):
        self.ensure_one()

        used_names = used_names or set()

        prefix = self._get_or_create_auto_lot_prefix()
        date_token = self._get_auto_lot_date_token()
        base_name = '%s-%s' % (prefix, date_token)

        next_number = self._get_next_auto_lot_sequence(
            base_name=base_name,
            company=company,
            used_names=used_names,
        )

        raw_lot_name = '%s-%03d' % (base_name, next_number)

        return self.env['stock.lot'].generate_lot_names(raw_lot_name, 1)[0]['lot_name']

    def _get_next_auto_lot_sequence(self, base_name, company, used_names=None):
        self.ensure_one()

        used_names = used_names or set()
        pattern = re.compile(r'^%s-(\d+)$' % re.escape(base_name))

        lot_names = self.env['stock.lot'].search([
            ('product_id', '=', self.id),
            ('company_id', 'in', [company.id, False]),
            ('name', '=like', base_name + '-%'),
        ]).mapped('name')

        draft_line_names = self.env['stock.move.line'].search([
            ('product_id', '=', self.id),
            ('company_id', '=', company.id),
            ('lot_name', '=like', base_name + '-%'),
        ]).mapped('lot_name')

        max_number = 0
        for name in set(lot_names + draft_line_names + list(used_names)):
            match = pattern.match(name or '')
            if match:
                max_number = max(max_number, int(match.group(1)))

        next_number = max_number + 1

        while '%s-%03d' % (base_name, next_number) in used_names:
            next_number += 1

        return next_number

    def _get_or_create_auto_stock_lot(self, lot_name, company):
        self.ensure_one()

        lot = self.env['stock.lot'].search([
            ('name', '=', lot_name),
            ('product_id', '=', self.id),
            ('company_id', 'in', [company.id, False]),
        ], limit=1)

        if not lot:
            lot = self.env['stock.lot'].create({
                'name': lot_name,
                'product_id': self.id,
                'company_id': company.id,
            })

        return lot