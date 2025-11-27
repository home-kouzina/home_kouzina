======================================
Python Flipkart Marketplace API Client
======================================

.. image:: https://img.shields.io/travis/fulfilio/python-flipkart.svg
        :target: https://travis-ci.org/fulfilio/python-flipkart

.. image:: https://img.shields.io/pypi/v/python-flipkart.svg
        :target: https://pypi.python.org/pypi/python-flipkart


Python Flipkart Marketplace API Client

* Free software: BSD license
* Documentation: https://python-flipkart.readthedocs.org.
* Authors: `Fulfil.IO - order fulfillment and inventory management system
  <https://www.fulfil.io/>`_

Installing
----------

From PYPI:

.. code-block:: shell

   $ pip install python-flipkart

From source code (advanced users and for development):

.. code-block:: shell

   $ git clone https://github.com/fulfilio/python-flipkart.git
   $ cd python-flipkart
   $ python setup.py install


Example Usage
-------------

.. code-block:: python

    from flipkart import FlipkartAPI, Authentication

    auth = Authentication('app id', 'app secret', sandbox=True)
    token = auth.get_token_from_client_credentials()

    flipkart = FlipkartAPI(token['access_token'], sandbox=True, debug=True)
    orders = flipkart.search_orders()


Get listings of a SKU
`````````````````````

.. code-block:: python

    sku = flipkart.sku('my-special-sku', fsn='TSHDBN3326TEZHQZ')
    for listing in sku.listings:
        print listing.attributes['mrp']


Create a listing
````````````````

.. code-block:: python

    sku = flipkart.sku('my-special-sku', fsn='TSHDBN3326TEZHQZ')
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
    print listing.mrp

Update a listing
````````````````

.. code-block:: python

    listing = flipkart.listing('LSTTSHDBN332XDYBZ5MHX30XI')
    listing.attributes['mrp'] = 2600
    listing.save()


Searching for orders
````````````````````

.. code-block:: python

    orders = flipkart.search_orders()

Find only orders of selected SKUs:

.. code-block:: python

    orders = flipkart.search_orders(
        filters={'sku': ['my-sku-1', 'my-sku-2']}
    )

Filter by state:

.. code-block:: python

    orders = flipkart.search_orders(
        filters={'states': ['Approved']}
    )

.. tip::

   For a list of valid state see `API documentation 
   <https://seller.flipkart.com/api-docs/order-api-docs/OMAPIOverview.html>`_

Fetching a specific order item
``````````````````````````````

.. code-block:: python

    order_item = flipkart.order_item('1731')
    order_item.attributes['quantity']

Or to get several order items at once

.. code-block:: python

    order_items = flipkart.order_items('1731', '1732')

Once the order is ready to pack, generate a label

.. code-block:: python

    label_request = order_item.generate_label(
        date.today(),   # Invoice date
        'INV12345',     # Invoice number
    )

When there are items that need serial numbers

.. code-block:: python

    label_request = order_item.generate_label(
        date.today(),   # Invoice date
        'INV12345',     # Invoice number
        [['IMEI1']],
    )

If the item was dual sim

.. code-block:: python

    label_request = order_item.generate_label(
        date.today(),   # Invoice date
        'INV12345',     # Invoice number
        [['IMEI1', 'IMEI2']],
    )

If 2 units of dual sim mobiles

.. code-block:: python

    label_request = order_item.generate_label(
        date.today(),   # Invoice date
        'INV12345',     # Invoice number
        [['IMEI1', 'IMEI2'], ['IMEI3', 'IMEI4']],
    )

The response of ``generate_label`` is a Label Request. The label request
is a lazy API. The status can be refreshed by calling

.. code-block:: python

    label_request.refresh_status()

Once the status is cleared, the item can be shipped out. To get the label
to ship call the ``get_label`` method to get a PDF of the label and
possibly the invoice.

.. code-block:: python

    pdf = order_item.get_label()

Once your shipment is ready to be picked by Flipkart logistics partner,
call the ready to ``dispatch`` API.


.. code-block:: python

    order_item.dispatch()


Getting shipment details
````````````````````````

The Shipments API gives the shipping details for orderitems

.. code-block:: python

    order_item.get_shipment_details()

the response items can be seen on `Flipkart API documentation 
<https://seller.flipkart.com/api-docs/order-api-docs/OMAPIRef.html#get-orders-shipments-orderitemsids-id-list>`_


Getting Access Token
````````````````````

If you have registered an application with your seller credentials and
would like to access resources in your account, you could use the
application id and secret alone to do so. The authentication helper in the
API gives you a convenient way to get tokens

.. code-block:: python

    from auth import Authentication

    auth = Authentication(
        '<application id>',
        '<application secret>',
        sandbox=True,           # If you are using sandbox
    )
    auth.get_token_from_client_credentials()

About Fulfil.IO
---------------

.. image:: https://www.fulfil.io/static/images/logo.png
        :target: https://www.fulfil.io/



`Fulfil.IO <https://www.fulfil.io/>`_ manages orders across Mobile, Social,
Online and Offline Channels. Flipkart is India's leading marketplace and
the first integration of Fulfil.IO in India.

This python module supports the Flipkart - Fulfil.IO order fulfilment and
inventory management system integration.
