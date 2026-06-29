# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale_amazon.tests import common


class TestAmazonPaymentGateway(common.TestAmazonCommon):

    def test_prepare_order_values_uses_payment_method_details(self):
        order_data = dict(
            common.ORDER_MOCK,
            PaymentMethod='Other',
            PaymentMethodDetails=['CreditCard', 'GiftCertificate'],
        )

        order_vals = self.account._prepare_order_values(order_data)

        self.assertEqual(
            order_vals['amazon_payment_gateway'],
            'CreditCard, GiftCertificate',
        )

    def test_prepare_order_values_falls_back_to_payment_method(self):
        order_data = dict(common.ORDER_MOCK, PaymentMethod='COD')

        order_vals = self.account._prepare_order_values(order_data)

        self.assertEqual(order_vals['amazon_payment_gateway'], 'COD')

    def test_process_order_data_updates_existing_order(self):
        order = self.env['sale.order'].create({
            'partner_id': self.env.user.partner_id.id,
            'amazon_order_ref': common.ORDER_MOCK['AmazonOrderId'],
        })
        order_data = dict(
            common.ORDER_MOCK,
            PaymentMethod='Other',
            PaymentMethodDetails=['CreditCard'],
        )

        result = self.account._process_order_data(order_data)

        self.assertEqual(result, order)
        self.assertEqual(order.amazon_payment_gateway, 'CreditCard')

    def test_process_order_data_keeps_gateway_when_amazon_omits_payment_data(self):
        order = self.env['sale.order'].create({
            'partner_id': self.env.user.partner_id.id,
            'amazon_order_ref': common.ORDER_MOCK['AmazonOrderId'],
            'amazon_payment_gateway': 'COD',
        })

        result = self.account._process_order_data(common.ORDER_MOCK)

        self.assertEqual(result, order)
        self.assertEqual(order.amazon_payment_gateway, 'COD')
