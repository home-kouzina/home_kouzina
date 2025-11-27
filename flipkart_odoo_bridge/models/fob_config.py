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
try:
    from odoo.addons.flipkart_odoo_bridge.python_flipkart.flipkart import FlipkartAPI, Authentication
    import flipkart
    from flipkart import FlipkartAPI, Authentication
except Exception as e:
    pass

CRON_INTERVAL_TYPE = [
    ('minutes', 'Minutes'),
    ('hours', 'Hours'),
    ('days', 'Days'),
    ('weeks', 'Weeks'),
    ('months', 'Months')
]
CRON_STATE = [
    ('stop', 'Stop'),
    ('start', 'Start')
]


def _unescape(text):
        ##
        # Replaces all encoded characters by urlib with plain utf8 string.

        # @param text source text.
        # @return The plain text.
    from urllib import unquote_plus
    return unquote_plus(text.encode('utf8'))


class MultiChannelSale(models.Model):
    _inherit = "multi.channel.sale"

    @api.model
    def get_channel(self):
        res = super(MultiChannelSale, self).get_channel()
        res.append(("flipkart", "Flipkart"))
        return res
   
    @api.model
    def flpkart_api_authentication(self):
        status = True
        sandbox = True
        msg = ''
        auth = ''
        debug = False
        if self.environment == 'production':
            sandbox = False
        if self.debug == 'enable':
            debug = True
        appi_id = self.flipkart_app_id
        cert_id =  self.flipkart_secret_id
        try:
            auth = Authentication(str(appi_id), str(cert_id), sandbox=sandbox)
            if debug:
                _logger.info('----------Flipkart auth response--%r',auth)
        except Exception as e:
            _logger.info('---------Exception in Authentication--------%r',e)
            status = False
            msg = "There is an error in the Authentication of flipkart API </br> <b>Error :- </b>%s" % e
        return {'status':status,'auth':auth,'msg':msg}

    @api.model
    def flpkart_api_client(self, token):
        sandbox = True
        debug = False
        client = False
        status = True
        msg = ''
        if self.environment == 'production':
            sandbox = False
        if self.debug == 'enable':
            debug = True
        try:
            client = FlipkartAPI(token, sandbox=sandbox, debug=debug)
            if debug:
                _logger.info('----------Flipkart client response--%r',client)
        except Exception as e:
            _logger.info('-----------Exception in creating client--%r',e)
            msg = "There is some error in creating the client. </br> <b>Error:- </b>%s" % e
            status = False
        return {'status':status,'msg':msg,'client':client}

    
    def test_flipkart_connection(self):
        for obj in self:
            if obj.channel == 'flipkart':
                final_message = ""
                debug = False
                auth_res = self.flpkart_api_authentication()
                if auth_res.get('status'):
                    response = auth_res.get('auth').get_token_from_client_credentials()
                    if response.get('access_token'):
                        final_message = "All tests passed successfully. You can start synchronizing from your flipkart store now."
                        obj.state = 'validate'
                        obj.flipkart_access_token =  response.get('access_token')
                        if self.debug == 'enable':
                            _logger.info('-------Response ----%r--',response)
                    else:
                        final_message = "There is some error in creating the connection. Please verify your credentails and try again. </br> <b>API Response :- </b>%s" % response.get('error_description')
                        if self.debug == 'enable':
                            _logger.info('-------Response ----%r--',response)
                else:
                    final_message = auth_res.get('msg')

                wizard_id = self.env['wk.wizard.message'].create(
                    {'text': final_message})
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
    
    def generate_flipkart_access_token(self):
        auth_res = self.flpkart_api_authentication()
        final_message = ""
        if auth_res.get('status'):
            response = auth_res.get('auth').get_token_from_client_credentials()
            if response.get('access_token'):
                self.flipkart_access_token = response.get('access_token')
                final_message = "Access Token Updated successfully!!"
            else:
                final_message = "There is some error generating the token. Please verify your credentails and try again. </br> <b>API Response :- </b>%s" % response.get('error_description')
        else:
            final_message = auth_res.get('msg')
        wizard_id = self.env['wk.wizard.message'].create(
        {'text': final_message})
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

    
    def import_flipkart_orders_cron_start(self):
        ir_model_data = self.env['ir.model.data']
        interval_number = self.flipkart_order_cron_interval_number
        interval_type = self.flipkart_order_cron_interval_type
        nextcall = self.flipkart_order_cron_nxtcall
        if int(interval_number) < 1:
            raise UserError('Value of Interval Number can`t be negative or 0.')
        if not interval_type:
            raise UserError('You must select Interval Type.')
        try:
            cron_id = ir_model_data._xmlid_lookup('flipkart_odoo_bridge.ir_cron_import_flipkart_orders')[1]
            cron_obj = self.env["ir.cron"].browse(cron_id)
            cron_obj.write({'active': True, 'interval_number': interval_number,
                            'interval_type': interval_type, 'nextcall': nextcall})
            self.write({'flipkart_order_cron_state': 'start'})
            return True
        except Exception as e:
            raise UserError("Error: %s" % e)

    
    def import_flipkart_orders_cron_stop(self):
        ir_model_data = self.env['ir.model.data']
        try:
            cron_id = ir_model_data._xmlid_lookup('flipkart_odoo_bridge.ir_cron_import_flipkart_orders')[1]
            cron_obj = self.env["ir.cron"].browse(cron_id)
            cron_obj.write({'active': False})
            self.write({'flipkart_order_cron_state': 'stop'})
            return True
        except Exception as e:
            raise UserError("Error: %s" % e)
    
    flipkart_app_id = fields.Char(
        string='Flipkart App ID',
        help="APP ID of your flipkart account.")

    flipkart_secret_id = fields.Char(
        string='Flipkart Secret ID',
        help="Secret ID of your flipkart account.")
    flipkart_access_token = fields.Char(
        string="Access Token",
        readonly=True,
        help="Token will be expired some time and you need to create a token by clicking in the button.")
    

    flipkart_order_cron_template = fields.Many2one(
        comodel_name='ir.cron',
        string='Set Cron For Orders')
    flipkart_order_cron_interval_number = fields.Integer(
        string='Interval Number',
        default=1,
        help="Repeat every x.")
    flipkart_order_cron_interval_type = fields.Selection(
        CRON_INTERVAL_TYPE,
        string='Interval Unit',
        help='Type of the interval',
        default="hours")
    flipkart_order_cron_state = fields.Selection(
        CRON_STATE,
        string='Cron State',
        help="State of the cron(stop, start)")
    flipkart_order_cron_nxtcall = fields.Datetime(
        string='Next Execution Date',
        default=datetime.now(),
        help="This fields is taken as the CreateDateTo for fetching the orders from flipkart. And the CreateDatefrom is taken as value of Interval Number before CreateDateTo.")
    flipkart_configure_order_cron = fields.Selection(
        [('yes', 'Yes'), ('no', 'NO')],
        default="no",
        string='Do you want to Configure Cron to Import Orders',
        help="Configure the cron for importing Orders from flipkart")
    flipkart_order_status = fields.Selection(
        [('APPROVED', 'APPROVED'),
		('PACKED', 'PACKED'),
		('READY_TO_DISPATCH', 'READY_TO_DISPATCH'),
		('CANCELLED', 'CANCELLED')],
		string='Flipkart Order Status',
        default = "APPROVED",
		help="The field is used to retrieve orders that are in a specific state.")
    flipkart_listing_status = fields.Selection([
        ('ACTIVE','ACTIVE'),
        ('INACTIVE','INACTIVE')],
        string="Listing Status",
        default="ACTIVE",
        help="Allows sellers to control their listing status")
    flipkart_national_shipping_charge = fields.Integer(
        string="National Shipping Charge",
        default=1,
        help="The cost the seller charges the buyer to ship an order within the country"
    )
    flipkart_zonal_shipping_charge = fields.Integer(
        string="Zonal Shipping Charge",
        default = 1,
        help="The cost the seller charges the buyer to ship an order in the same zone"
    )
    flipkart_local_shipping_charge = fields.Integer(
        string="Local Shipping Charge",
        default=1,
        help="The cost the seller charges the buyer to ship an order locally"
    )
    flipkart_procurement_sla = fields.Integer(
        string="Procurement SLA",
        default=1,
        help="The time required by the seller to keep the product ready for pick-up"
    )
    flipkart_fulfilled_by = fields.Selection(
        [('seller', 'Seller')],
        string="Fulfilled By",
        default = "seller"
    )
    flipkart_package_length = fields.Float(
        string="Package Length",
        default=1.0,
    )
    flipkart_package_breadth = fields.Float(
        string="Package Breadth",
        default = 1.0,
    )
    flipkart_package_height = fields.Float(
        string='Package Height',
        default=1.0)
    flipkart_package_weight = fields.Float(
        string="Package Weight",
        default=1.0
    )
    flipkart_procurement_type = fields.Char(
        string="Procurement Type",
        default="REGULAR"
    )
    flipkart_goods_services_tax = fields.Integer(
        string="Goods & Services Tax (GST)",
        default=18,
        help="The values should be the correct gst values"
    )
   
