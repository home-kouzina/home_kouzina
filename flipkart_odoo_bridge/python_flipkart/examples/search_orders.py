# -*- coding: utf-8 -*-
"""
An example just to give you a good idea about how this API works.
Use them for testing your API key, but do not ever use it in production.
"""
import os
import random
from flipkart import FlipkartAPI, Authentication

# Set authentication credentials
app_id = os.environ['FLIPKART_APP_ID']
app_secret = os.environ['FLIPKART_APP_SECRET']
auth = Authentication(app_id, app_secret, sandbox=True)

# Get an access token
token = auth.get_token_from_client_credentials()

# Get a flipkart client
flipkart = FlipkartAPI(token['access_token'], sandbox=True, debug=True)


def get_listings_of(sku):
    sku = flipkart.sku(sku)
    for listing in sku.listings:
        print listing.attributes['mrp']


def create_listing(sku, fsn):
    """
    create a listing
    """
    sku = flipkart.sku(sku, fsn)
    listing = sku.create_listing(
        mrp=2400,
        selling_price=2300,
        listing_status="INACTIVE",
        fulfilled_by="seller",
        national_shipping_charge=20,
        zonal_shipping_charge=20,
        local_shipping_charge=20,
        procurement_sla=3,
        stock_count=23,
    )
    listing.save()


def create_test_orders():
    skus = [
        flipkart.sku('my-special-sku'),
        flipkart.sku('my-special-sku-2'),
        flipkart.sku('my-special-sku-3'),
    ]
    listings = [sku.listing for sku in skus]
    order_items = flipkart.create_test_orders(
        *[(listing, random.choice(range(1, 5))) for listing in listings]
    )
    return order_items


if __name__ == '__main__':
    get_listings_of('my-special-sku')
    create_listing('my-special-sku-3', 'TSHDBN332XDYBZ5M')
    get_listings_of('my-special-sku-3')
    create_test_orders()
    response = list(flipkart.search_orders())

    print "Number of orders: %d" % len(response)
