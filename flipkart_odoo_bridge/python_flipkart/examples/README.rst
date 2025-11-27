Examples
========

This folder includes a few examples of python code that uses the flipkart
API. Most examples are written with client credentials based
authentication workflow.

How to run
----------

1. Get a Sandbox account
````````````````````````

See `Flipkart Documentation on how to 
<https://seller.flipkart.com/api-docs/FMSAPI.html#seller-registration>`_

2. Register an application
``````````````````````````

See `Flipkart Documentation on how to register new application
<https://seller.flipkart.com/api-docs/FMSAPI.html#authentication-process>`_


3. Set FLIPKART_APP_ID and FLIPKART_APP_SECRET in environment
`````````````````````````````````````````````````````````````

.. code-block:: shell

   export FLIPKART_APP_ID=123456hgjahgs65868
   export FLIPKART_APP_SECRET=123456hgjahgs65868

4. Run the python file
``````````````````````

.. code-block:: shell

    $ python examples/search_orders.py
