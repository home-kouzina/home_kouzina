from odoo import models


class AmazonAccount(models.Model):
    _inherit = 'amazon.account'

    def _process_order_data(self, order_data):
        order = super()._process_order_data(order_data)
        if order and order.amazon_order_ref:
            order._amazon_auto_create_invoice()
        return order
