from datetime import datetime

from odoo import Command, fields
from odoo.tests.common import TransactionCase


class TestSaleMarginReportHistory(TransactionCase):
    def setUp(self):
        super().setUp()
        self.uom_unit = self.env.ref('uom.product_uom_unit')
        self.partner = self.env['res.partner'].create({
            'name': 'Margin Report Customer',
        })
        self.product = self.env['product.template'].create({
            'name': 'Historical Cost Product',
            'type': 'product',
            'uom_id': self.uom_unit.id,
            'uom_po_id': self.uom_unit.id,
            'list_price': 100.0,
        }).product_variant_id
        self.product.write({'standard_price': 10.0})

    def _history_record(self):
        return self.env['product.cost.history'].search([
            ('product_tmpl_id', '=', self.product.product_tmpl_id.id),
            ('company_id', '=', self.env.company.id),
        ], limit=1)

    def _create_sale_order(self, order_date):
        return self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'date_order': fields.Datetime.to_string(order_date),
            'order_line': [Command.create({
                'product_id': self.product.id,
                'product_uom_qty': 2.0,
                'price_unit': 25.0,
            })],
        })

    def test_margin_report_uses_historical_cost_by_order_date(self):
        first_history = self._history_record()
        first_history.write({
            'effective_date': datetime(2024, 1, 1, 10, 0, 0),
        })

        first_order = self._create_sale_order(datetime(2024, 1, 2, 10, 0, 0))
        first_line = first_order.order_line[:1]
        self.assertAlmostEqual(first_line.cogs_unit_price, 10.0, places=2)
        first_report_line = self.env['sale.margin.report'].search([
            ('so_id', '=', first_order.id),
        ], limit=1)
        self.assertTrue(first_report_line)
        self.assertAlmostEqual(first_report_line.cogs, 20.0, places=2)

        self.product.write({'standard_price': 15.0})
        second_history = self.env['product.cost.history'].search([
            ('product_tmpl_id', '=', self.product.product_tmpl_id.id),
            ('company_id', '=', self.env.company.id),
        ], order='effective_date desc, id desc', limit=1)
        second_history.write({
            'effective_date': datetime(2024, 1, 3, 10, 0, 0),
        })

        second_order = self._create_sale_order(datetime(2024, 1, 4, 10, 0, 0))
        second_line = second_order.order_line[:1]
        self.assertAlmostEqual(second_line.cogs_unit_price, 15.0, places=2)
        second_report_line = self.env['sale.margin.report'].search([
            ('so_id', '=', second_order.id),
        ], limit=1)
        self.assertTrue(second_report_line)
        self.assertAlmostEqual(second_report_line.cogs, 30.0, places=2)
