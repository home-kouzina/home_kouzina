# -*- coding: utf-8 -*-
#################################################################################
#
#    Copyright (c) 2019-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#
#################################################################################

from odoo import api, fields, models, _
import logging
_logger = logging.getLogger(__name__)
def _unescape(text):
    ##
    # Replaces all encoded characters by urlib with plain utf8 string.
    #
    # @param text source text.
    # @return The plain text.

    try:
        return unquote_plus(text.encode('utf8'))
    except Exception as e:
        return text
class ImportFlipkartProducts(models.TransientModel):
    _name = "import.flipkart.products"
    _description = "Import Flipkart Products"

    @api.model
    def GetOdooTemplateData(self, productDetails, ChannelID):
        template_data = {
            'name': _unescape(productDetails.get('title')),
            'list_price': productDetails.get('price'),
            'store_id': productDetails.get('listingId'),
            'channel_id': ChannelID.id,
            'channel': 'flipkart',
            # 'qty_available': qty_available,
            'default_code':productDetails.get('sku'),
            'hs_code':productDetails.get('hsn'),
            # 'wk_product_id_type':'wk_isbn',
            'flipkart_fsn':productDetails.get('fsn'),
        }
        return template_data


    @api.model
    def _CreateOdooFeed(self, ProductData):
        context = dict(self._context or {})
        FeedObj = self.env['product.feed']
        mapping_id = FeedObj.search( [('store_id', '=', ProductData.get('listingId'))])
        status = False
        FeedsCreated = False
        FeedsUpdated = False
        StausMsg = ''
        feed_id = False
        try:
            if context.get('channel_id'):
                ChannelID = context['channel_id']
            else:
                ChannelID = self.channel_id
            template_data = self.GetOdooTemplateData(ProductData, ChannelID)
            if not mapping_id:
                feed_id = FeedObj.create(template_data)
                if ChannelID.debug == 'enable':
                    _logger.info('------------Template %s created-----',feed_id.name)
                status = True
                FeedsCreated = True
            else:
                res = mapping_id.write(template_data)
                if ChannelID.debug == 'enable':
                    _logger.info('------------Template %s Updated-----',mapping_id.name)
                if res:
                    FeedsUpdated = True
                    mapping_id.state = 'update'
                status = True
                FeedsCreated = False
        except Exception as e:
          _logger.info('------------Exception-CreateOdooTemplate------%r',e)
          StausMsg = "Error in Fetching Product: %s" % e
        finally:
            return {
                'status': status,
                'StausMsg': StausMsg,
                'FeedsCreated': FeedsCreated,
                'product_feed_id': feed_id,
                'FeedsUpdated': FeedsUpdated,
                'mapping_id': mapping_id,
            }

    @api.model
    def get_product_using_product_id(self, ProductDetals, ChannelID):
        create_ids = []
        update_ids = []
        context = dict(self._context or {})
        context.update({'channel_id': ChannelID})
        try:
            res = self.with_context(context)._CreateOdooFeed(ProductDetals)
        except Exception as e:
            res['StausMsg'] = 'Error in Creating Product Feed %s'%str(e.message)
        if res.get('mapping_id'):
            update_ids.append(res.get('mapping_id'))
            res['StausMsg'] += 'Product %s have been updated' % res.get('mapping_id').name
        if res.get('product_feed_id'):
            create_ids.append(res.get('product_feed_id'))
        post_res = self.env['channel.operation'].post_feed_import_process(
            ChannelID, {'create_ids': create_ids, 'update_ids': update_ids})
        if res.get('FeedsCreated') and res.get('product_feed_id'):
            res['StausMsg'] += 'Product %s have been imported to odoo' % res.get('product_feed_id').name
        return res