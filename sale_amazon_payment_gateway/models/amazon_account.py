# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, api, models
from odoo.exceptions import UserError

from odoo.addons.sale_amazon import utils as amazon_utils

_logger = logging.getLogger(__name__)


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

    def _fetch_order_payment_details(self, amazon_order_ref):
        """Fetch payment details for a specific order from Amazon.
        
        :param str amazon_order_ref: The Amazon order reference ID.
        :return: The payment gateway string or False if not available.
        :rtype: str or bool
        """
        self.ensure_one()
        try:
            amazon_utils.ensure_account_is_set_up(self, require_marketplaces=False)
            # Use getOrder to fetch details for a specific order
            response = amazon_utils.make_sp_api_request(
                self, 'getOrder', path_parameter=amazon_order_ref
            )
            order_data = response.get('payload', response)
            
            if order_data:
                return self._get_amazon_payment_gateway(order_data)
        except amazon_utils.AmazonRateLimitError:
            _logger.warning(
                "Amazon rate limit reached while fetching payment details for order %s",
                amazon_order_ref
            )
        except Exception as error:
            _logger.warning(
                "Failed to fetch payment details for order %s: %s",
                amazon_order_ref, str(error)
            )
        return False

    def backfill_payment_methods_for_existing_orders(self):
        """Fetch and update payment methods for all existing Amazon orders that don't have them.
        
        This method is useful when the sale_amazon_payment_gateway module is newly installed
        and previous orders need their payment method information populated.
        
        :return: Number of orders updated.
        :rtype: int
        """
        self.ensure_one()
        
        Sale = self.env['sale.order']
        # Find all Amazon orders for this account that don't have payment gateway info
        orders_without_payment = Sale.search([
            ('amazon_order_ref', '!=', False),
            ('amazon_payment_gateway', '=', False),
        ])
        
        updated_count = 0
        for order in orders_without_payment:
            try:
                payment_gateway = self._fetch_order_payment_details(order.amazon_order_ref)
                if payment_gateway:
                    order.amazon_payment_gateway = payment_gateway
                    updated_count += 1
                    _logger.info(
                        "Updated payment method for order %s to: %s",
                        order.amazon_order_ref, payment_gateway
                    )
            except Exception as error:
                _logger.warning(
                    "Error updating payment method for order %s: %s",
                    order.amazon_order_ref, str(error)
                )
        
        return updated_count

    def action_backfill_payment_methods(self):
        """Action button to manually trigger payment method backfill for previous orders."""
        self.ensure_one()
        try:
            updated_count = self.backfill_payment_methods_for_existing_orders()
            message = _("Successfully updated %d order(s) with their payment method information.") % updated_count
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Payment Methods Updated"),
                    'message': message,
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as error:
            raise UserError(_("Error backfilling payment methods: %s") % str(error))
