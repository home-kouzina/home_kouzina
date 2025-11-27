# -*- coding: utf-8 -*-
#################################################################################
#
#    Copyright (c) 2019-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#
#################################################################################
from odoo import api, fields, models, _
from odoo import tools, api
from datetime import datetime, timedelta
from odoo.tools.translate import _
from odoo.exceptions import UserError
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

class ExportTemplates(models.TransientModel):
    _inherit = "export.templates"

    flipkart_template_ids = fields.Many2many(
        'product.template',
        'export_product_id',
        'template_id',
        'rel_key',
        string='Products')
    
    flipkart_mapping_ids = fields.Many2many(
        'channel.template.mappings',
        'mapping_id',
        'export_id',
        'rel_key',
        string='Products')

    @api.model
    def create_template_mapping_export(self, template_id, channel_id, values):
        msg= ''
        try:
            exists = self.env['channel.template.mappings'].search([('template_name','=',template_id)])
            if not exists:
                MapValues = {
                        'store_product_id': values.get('listingId'),
                        'odoo_template_id': template_id,
                        'template_name': template_id,
                        'ecom_store': 'flipkart',
                        'channel_id': channel_id,
                        'default_code':values.get('skuId')
                    }
                self.env['channel.template.mappings'].create(MapValues)
        except Exception as e:
            msg = 'Exception in creating Template mapping %s'%(_unescape(e.message))
        return msg
    
    @api.model
    def create_flipkart_lisiting(self, client, template_id):
        message_status = ''
        status = True
        message = ""
        if client and template_id:
            template_obj = self.env['product.template'].browse(template_id)
            if not template_obj.default_code or not template_obj.hs_code or not template_obj.flipkart_fsn:
                message = "Any of the fields SKU(Default Code), HSN(HS Code) or FSN(Flipkart HSN) of the product %s is missing. Odoo ID= %s"%(template_obj.name, template_id)
            else:
                try:
                    skuObj = client.sku(str(template_obj.default_code), fsn=str(template_obj.flipkart_fsn))
                    try:
                        if skuObj.listing.listing_id:
                            flipkart_listing = skuObj.create_listing(
                                mrp=template_obj.standard_price,
                                selling_price=template_obj.list_price,
                                listing_status = str(self.channel_id.flipkart_listing_status),
                                fulfilled_by=str(self.channel_id.flipkart_fulfilled_by),
                                national_shipping_charge=self.channel_id.flipkart_national_shipping_charge,
                                zonal_shipping_charge=self.channel_id.flipkart_zonal_shipping_charge,
                                local_shipping_charge=self.channel_id.flipkart_local_shipping_charge,
                                procurement_sla=self.channel_id.flipkart_procurement_sla,
                                stock_count= int(template_obj.qty_available),
                                hsn = str(template_obj.hs_code),
                                package_length = self.channel_id.flipkart_package_length,
                                package_breadth = self.channel_id.flipkart_package_breadth,
                                package_height = self.channel_id.flipkart_package_height,
                                package_weight = self.channel_id.flipkart_package_weight,
                                procurement_type = str(self.channel_id.flipkart_procurement_type),
                                goods_services_tax = str(self.channel_id.flipkart_goods_services_tax)
                            )
                            response = flipkart_listing.save()
                            if response.get('listingId'):
                                self.create_template_mapping_export(template_id, self.channel_id.id, response)
                                message = "Product %s has been successfully Exported/Updated. </br> Flipkart Listing ID=%s"%(template_obj.name,response.get('listingId'))
                            else:
                                _logger.info('----------fail --------%r',response)
                                message = "Error in Exporting Product"
                    except Exception as e:
                        message = "Error in Exporting Product: </br> %s"%e
                        _logger.info('-----------Exception -------%r',e)
                except Exception as e:
                    message = "There is some kind of exception in exporting the product please try after some time. </br> Error Description: %s "%e
                    _logger.info('---------------exception -------%r',e)
        return {'message': message,
                }

    @api.model
    def export_update_product(self, template_id):
        final_message = ""
        client_res = self.channel_id.flpkart_api_client(self.channel_id.flipkart_access_token)
        if client_res.get('status'):
            res = self.create_flipkart_lisiting(client_res.get('client'),template_id)
            final_message = res.get('message')
            _logger.info('--------resttt--------------%r',res)
        else:
            final_message += client_res.get('msg')
        return final_message

    
    def _export_product_to_flipkart(self, template_id):
        
        final_message = ""
        status = True
        context = dict(self._context or {})
        MapObj = self.env['channel.template.mappings']
        
        result_dict = {}
        syn_status = ''
        ebay_id = ''
	# Added this for particular channel mapping
        channel_id = self.channel_id.id
        tmpl = self.env['product.template'].browse(template_id)
	# update here also for the particular channel mapping
        exists = MapObj.search([('odoo_template_id', '=', template_id),('channel_id','=',channel_id)],limit=1)
        if not exists:
            msg = self.export_update_product(template_id)
            final_message = msg
        else:
            final_message = 'Product <b> %s </b> has been Already Exported to Flipkart. Flipkart Listing id is %s </br>' % (_unescape(tmpl.name), exists.store_product_id)
        return {'final_message': final_message,
                
                }

    
    def export_flipkart_templates(self):
        for record in self:
            final_message = ""
            status = True
            context = dict(self._context or {})
            template_ids = []
            if self.flipkart_template_ids:
                template_ids = self.flipkart_template_ids.ids
            else:
                template_ids = self._context['active_ids']
            for temp_id in template_ids:
                result = self.with_context(
                    context)._export_product_to_flipkart(temp_id)
                final_message += result['final_message']
        wizard_id = self.env['wk.wizard.message'].create({'text': final_message})
        return {'name': _("Summary"),
                'view_mode': 'form',
                'view_id': False,
                'view_type': 'form',
                'res_model': 'wk.wizard.message',
                'res_id': wizard_id.id,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'new',
                'domain': '[]',
                }

    
    def update_flipkart_templates(self):
        for record in self:
            final_message = ""
            status = True
            context = dict(self._context or {})
            template_ids = []
            if self.flipkart_mapping_ids:
                for map_id in self.flipkart_mapping_ids:
                    msg = self.with_context(context).export_update_product(int(map_id.odoo_template_id))
                    final_message += msg
            else:
                for temp_id in self._context['active_ids']:
                    map_id = self.env['channel.template.mappings'].search(
                        [('template_name', '=', temp_id), ('channel_id', '=', self.channel_id.id)], limit=1)
                    if map_id:
                        msg = self.with_context(
                        context).export_update_product(temp_id)
                        final_message += msg
                    else:
                        final_message = "There is no mapping for this product you need to export it."
        wizard_id = self.env['wk.wizard.message'].create({'text': final_message})
        return {'name': _("Summary"),
                'view_mode': 'form',
                'view_id': False,
                'view_type': 'form',
                'res_model': 'wk.wizard.message',
                'res_id': wizard_id.id,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'new',
                'domain': '[]',
                }
