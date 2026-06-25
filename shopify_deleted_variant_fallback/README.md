# Shopify Deleted Variant Order Fallback

This Odoo 18 module extends Emipro's `shopify_ept` connector.

## Purpose

It allows Shopify order import to continue when an old order line points to a Shopify variant that no longer exists / cannot be imported from Shopify.

## Logic

1. The connector first follows the normal Emipro logic: search variant mapping, then try Shopify product sync by product ID.
2. If the exact variant is still missing, this module marks only that runtime order line as a deleted-variant fallback.
3. During sale order line creation, that line uses the Shopify instance's **Custom Service Product**.
4. The line name, price, quantity, taxes and discount allocation still come from the Shopify order line JSON.
5. Because the fallback product is a service product, it does not create stock moves for that deleted item.

## Manual setup

Create one service product, for example `Legacy Deleted Shopify Product`, then set it on:

Shopify Instance → Default Products → Custom Service Product

Then reprocess failed order queues.

## Notes

This module does not edit Shopify order data and does not create Shopify EPT variant mappings.
