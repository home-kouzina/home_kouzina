# -*- coding: utf-8 -*-

import logging

from odoo import models, _

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    DELETED_VARIANT_FALLBACK_KEY = "_ept_deleted_variant_service_fallback"

    def _shopify_mark_deleted_variant_service_fallback(self, line):
        """Mark the runtime Shopify order line to be imported with Custom Service Product.

        The Shopify queue JSON is not changed. This flag lives only in memory during queue processing.
        """
        line[self.DELETED_VARIANT_FALLBACK_KEY] = True
        line["_ept_original_shopify_product_id"] = line.get("product_id")
        line["_ept_original_shopify_variant_id"] = line.get("variant_id")
        return line

    def _shopify_log_deleted_variant_service_fallback(self, instance, line, order_number, order_data_queue_line):
        """Create an audit log when a deleted/missing Shopify variant is imported as a service line."""
        product = instance.custom_service_product_id
        message = _(
            "Shopify order %(order)s contains line [%(sku)s][%(name)s] with Shopify product ID %(product_id)s "
            "and variant ID %(variant_id)s, but this variant was not found in Odoo and could not be imported "
            "from Shopify. The line will be imported using Custom Service Product [%(custom_product)s]."
        ) % {
            "order": order_number,
            "sku": line.get("sku") or "",
            "name": line.get("name") or line.get("title") or "",
            "product_id": line.get("product_id") or "",
            "variant_id": line.get("variant_id") or "",
            "custom_product": product.display_name if product else "",
        }
        _logger.warning(message)
        self.env["common.log.lines.ept"].create_common_log_line_ept(
            shopify_instance_id=instance.id,
            module="shopify_ept",
            message=message,
            model_name="sale.order",
            order_ref=order_number,
            shopify_order_data_queue_line_id=order_data_queue_line.id if order_data_queue_line else False,
        )

    def check_mismatch_details(self, lines, instance, order_number, order_data_queue_line):
        """Allow historical Shopify orders to import when a line points to a deleted variant.

        Base connector behavior:
        - Search Shopify variant mapping by variant_id / SKU.
        - If not found, try importing the Shopify product by product_id.
        - If the exact old variant is still not found, fail the order.

        Custom behavior added here:
        - After the normal search + sync attempt fails, use the instance Custom Service Product.
        - This avoids stock impact and keeps the sale line price/tax/qty/name from the Shopify order data.
        """
        shopify_product_template_obj = self.env["shopify.product.template.ept"]
        common_log_line_obj = self.env["common.log.lines.ept"]
        mismatch = False

        for line in lines:
            shopify_variant = self.search_shopify_variant(line, instance)
            if shopify_variant:
                continue

            # Keep Emipro's original gift-card protection unchanged.
            if line.get("gift_card", False):
                product = instance.gift_card_product_id or False
                if product:
                    continue
                message = _(
                    "System tried to import the order: %s but in the order there are Gift card details but "
                    "Gift card products has been deleted\n"
                    "Action items:\n"
                    "- Upgrade the Shopify connector in odoo. so it will create Gift Card product in odoo\n"
                    "- Try to reprocess the order data queue "
                ) % order_number
                common_log_line_obj.create_common_log_line_ept(
                    shopify_instance_id=instance.id,
                    module="shopify_ept",
                    message=message,
                    model_name="sale.order",
                    order_ref=order_number,
                    shopify_order_data_queue_line_id=order_data_queue_line.id if order_data_queue_line else False,
                )
                mismatch = True
                break

            line_variant_id = line.get("variant_id", False)
            line_product_id = line.get("product_id", False)

            # Same normal connector attempt: if both Shopify product and variant IDs exist,
            # try to import/sync the Shopify product first.
            if line_product_id and line_variant_id:
                shopify_product_template_obj.shopify_sync_products(
                    False, line_product_id, instance, order_data_queue_line
                )
                shopify_variant = self.search_shopify_variant(line, instance)
                if shopify_variant:
                    continue

                # New fallback: deleted/missing old Shopify variant. Use configured service product.
                if instance.custom_service_product_id:
                    self._shopify_mark_deleted_variant_service_fallback(line)
                    self._shopify_log_deleted_variant_service_fallback(
                        instance, line, order_number, order_data_queue_line
                    )
                    continue

                message = _(
                    "Product [%(sku)s][%(name)s] not found for Order %(order)s. The Shopify variant may be "
                    "deleted and no Custom Service Product is configured on the Shopify instance.\n"
                    "Action item: Set Shopify Instance > Default Products > Custom Service Product and reprocess "
                    "the order queue."
                ) % {
                    "sku": line.get("sku") or "",
                    "name": line.get("name") or line.get("title") or "",
                    "order": order_number,
                }
                common_log_line_obj.create_common_log_line_ept(
                    shopify_instance_id=instance.id,
                    module="shopify_ept",
                    message=message,
                    model_name="sale.order",
                    order_ref=order_number,
                    shopify_order_data_queue_line_id=order_data_queue_line.id if order_data_queue_line else False,
                )
                mismatch = True
                break

        return mismatch

    def search_custom_tip_gift_card_product(self, line, instance):
        """Use the Custom Service Product for runtime lines marked as deleted Shopify variants."""
        if line.get(self.DELETED_VARIANT_FALLBACK_KEY):
            return True, False, instance.custom_service_product_id
        return super().search_custom_tip_gift_card_product(line, instance)
