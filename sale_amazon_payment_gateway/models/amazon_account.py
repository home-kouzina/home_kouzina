# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AmazonAccount(models.Model):
    _inherit = 'amazon.account'

    @staticmethod
    def _get_amazon_payment_gateway(order_data):
        """Return the most precise payment method provided by Amazon."""
        payment_details = order_data.get('PaymentMethodDetails') or []
        if isinstance(payment_details, str):
            payment_details = [payment_details]
        payment_details = [detail for detail in payment_details if detail]
        return ', '.join(payment_details) or order_data.get('PaymentMethod') or False

    def _prepare_order_values(self, order_data):
        order_vals = super()._prepare_order_values(order_data)
        order_vals['amazon_payment_gateway'] = self._get_amazon_payment_gateway(order_data)
        return order_vals

    def _process_order_data(self, order_data):
        order = super()._process_order_data(order_data)
        if order and (
            'PaymentMethodDetails' in order_data or 'PaymentMethod' in order_data
        ):
            payment_gateway = self._get_amazon_payment_gateway(order_data)
            if order.amazon_payment_gateway != payment_gateway:
                order.amazon_payment_gateway = payment_gateway
        return order
