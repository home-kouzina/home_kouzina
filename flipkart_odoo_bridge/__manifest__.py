# -*- coding: utf-8 -*-
#################################################################################
# Author      : Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# Copyright(c): 2015-Present Webkul Software Pvt. Ltd.
# All Rights Reserved.
#
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://store.webkul.com/license.html/>
#################################################################################
{
  "name"                 :  "Flipkart Odoo Connector | Odoo Multichannel",
  "summary"              :  """Integrate Fliplkart with Odoo. The module allows you to manage Flipkart store operation in odoo. Import products, customers, etc with Flipkart Odoo connector.
multi channel multi-channel flipkart multichannel flipkart bridge flipkart connector flipkart odoo bridge odoo flipkart extensions for multichannel
  """,
  'category': 'Home Kouzina',
  "version"              :  "1.0.4",
  "sequence"             :  1,
  "author"               :  "Webkul Software Pvt. Ltd.",
  "license"              :  "Other proprietary",
  "website"              :  "https://store.webkul.com/odoo-multichannel-flipkart-connector.html",
  "description"          :  """
https://webkul.com/blog/odoo-multichannel-flipkart-connector/
Flipkart Odoo bridge
Flipkart Odoo connector
Odoo Flipkart Bridge
Odoo multi-channel bridge
Multi channel connector
Multi platform connector
Multiple platforms bridge
Connect Amazon with odoo
Amazon bridge
Flipkart Bridge
Magento Odoo Bridge
Odoo magento bridge
Woocommerce odoo bridge
Odoo woocommerce bridge
Ebay odoo bridge
Odoo ebay bridge
Multi channel bridge
Prestashop odoo bridge
Odoo prestahop
Akeneo bridge
Etsy bridge
Marketplace bridge
Multi marketplace connector
Multiple marketplace platform""",
  "live_test_url"        :  "https://odoodemo.webkul.com/demo_feedback?module=flipkart_odoo_bridge",
  "depends"              :  ['base','odoo_multi_channel_sale'],
    "qweb": [
        "views/inherit_multi_channel_template.xml",
    ],
  "data"                 :  [
                            'security/ir.model.access.csv',
                             'views/multi_channel_inherit_view.xml',
                             'data/flipkart_import_cron.xml',
                             'wizard/export_products_view.xml',
                             'wizard/import_flipkart_orders_view.xml',
                             'views/fob_config.xml',
                             'views/dashboard_view_inherited.xml',
                             'views/inherits.xml',
                            ],
  "demo"                 :  ['data/demo.xml'],
  "images"               :  ['static/description/banner.gif'],
  "application"          :  True,
  "installable"          :  True,
  "auto_install"         :  False,
  "price"                :  170,
  "currency"             :  "USD",
  "pre_init_hook"        :  "pre_init_check",
}
