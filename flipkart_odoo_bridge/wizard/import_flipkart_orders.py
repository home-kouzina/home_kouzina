# -*- coding: utf-8 -*-
#################################################################################
#
#    Copyright (c) 2019-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#
#################################################################################
from odoo import api, fields, models, _
from odoo import tools, api
import json
import requests
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
from pytz import timezone

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)
# try:
from odoo.addons.flipkart_odoo_bridge.python_flipkart.flipkart import FlipkartAPI, Authentication

#     import flipkart
#     from flipkart import FlipkartAPI, Authentication
# except Exception as e:
#     _logger.info('------Install Python Library------------')
#     pass
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

flipkart_urls = {
	'sandbox_url':'https://sandbox-api.flipkart.net:443/sellers/v2/orders/shipments?orderItemIds=',
	'product_url':'https://api.flipkart.net/sellers/v2/orders/shipments?orderItemIds='
}

class ImportFlipkartOrders(models.TransientModel):
	_name = "import.flipkart.orders"
	_description = "Import Flipkart Orders"

	

	@api.model
	def get_order_shipping_details(self, OrderItemID):
		result = {}
		msg = ''
		status = False
		channel_id = self.channel_id
		if not channel_id:
			channel_id = self._context.get('channel_id')
		if channel_id.flipkart_access_token:
			try:
				authorizaion = "Bearer %s"%str(channel_id.flipkart_access_token)
				headers = {'Authorization' : authorizaion, 'Content-Type' : 'application/json'}
				url = '%s%s'%(flipkart_urls['sandbox_url'],OrderItemID)
				if channel_id.environment == 'production':
					url = '%s%s'%(flipkart_urls['product_url'],OrderItemID)
				response = requests.get(url, headers=headers,  verify=False)
				
				if response.ok:
					status = True
					result = response.text
					result = json.loads(result)
				if channel_id.debug == 'enable':
					_logger.info('-----------Shippment details-----%r-----------%r',OrderItemID, response.text)
				else:
					msg = "There is an error in fetching the detail of This Order item.  </br> Error Description:%s"%response.text
			except Exception as e:
				msg = "Error in getting the details of this order </br> Error Description: %s"%e
		else:
			msg = "No access token present!! Please generate an acces token."
		return {'result':result,'msg':msg,'status':status}
	
	@api.model
	def _fill_odoo_partner_details(self, ship_values):
		""" Creates a partner with all the necessary fields and return a partner object"""
		vals = {}
		status = True
		status_message = 'Partner feed created successfully!!!'
		context = dict(self._context or {})
		if context.get('channel_id'):
			ChannelID = context['channel_id']
		else:
			ChannelID = self.channel_id
		vals['store_id'] = self.get_store_partner_id(ship_values.get('buyerDetails'), ship_values.get('billingAddress'))
		vals['channel_id'] = ChannelID.id
		vals['channel'] = 'flipkart'
		name = '%s %s'%(_unescape(ship_values.get('buyerDetails').get('firstName')),_unescape(ship_values.get('buyerDetails').get('lastName'))) or 'No Name'
		vals['name'] = _unescape(ship_values.get('buyerDetails').get('firstName'))
		if ship_values.get('buyerDetails').get('lastName'):
			vals['last_name'] = ship_values.get('buyerDetails').get('lastName')
		if ship_values.get('buyerDetails').get('primaryEmail'):
			vals['email'] = _unescape(ship_values.get('buyerDetails').get('primaryEmail'))
		if ship_values.get('buyerDetails').get('contactNumber'):
			vals['phone'] = ship_values.get('buyerDetails').get('contactNumber')
		return vals

	@api.model
	def get_store_partner_id(self, buyerDetails, billingAddress=False):
		store_partner_id = _unescape(buyerDetails.get('firstName'))
		if buyerDetails.get('lastName'):
			store_partner_id += '_%s'%_unescape(buyerDetails.get('lastName'))
		if not store_partner_id and billingAddress:
			store_partner_id = _unescape(billingAddress.get('firstName'))
			if billingAddress.get('lastName'):
				store_partner_id += '_%s'%_unescape(billingAddress.get('lastName'))
		return store_partner_id
	
	@api.model
	def create_invoice_address(self, shipping_details):
		""" Creates shipping address and invoice address and returns dictionary of these address values"""
		vals = {}
		invoice_partner_id = self.get_store_partner_id(shipping_details.get('buyerDetails'), shipping_details.get('billingAddress'))
		vals['invoice_partner_id'] = invoice_partner_id
		invoice_details = shipping_details.get('billingAddress')
		name = '%s %s'%(invoice_details.get('firstName'), invoice_details.get('lastName')) or 'No Name'
		vals['customer_name'] = name
		vals['invoice_name'] = name
		vals['customer_email'] = 'No Email'
		vals['invoice_email'] = 'No Email'
		vals['invoice_street'] = invoice_details.get('addressLine1')
		vals['invoice_street2'] = invoice_details.get('addressLine2')
		vals['invoice_phone'] = invoice_details.get('contactNumber')
		vals['invoice_city'] = invoice_details.get('city')
		vals['invoice_zip'] = invoice_details.get('pincode')
		vals['invoice_state_id'] = invoice_details.get('stateCode')
		vals['invoice_state_name'] = invoice_details.get('state')
		return vals


	@api.model
	def create_odoo_partner_feed(self, OrderItemId):
		msg = ""
		status = True
		FeedPartnerEnv = self.env['partner.feed']
		partner_feed_id = False
		vals = {}
		billing_address = {}
		shiping_res = self.get_order_shipping_details(OrderItemId)
		if shiping_res.get('status'):
			shipping_details = shiping_res.get('result').get('shipments')
			if isinstance(shipping_details, (list)):
				shipping_details = shipping_details[0]
			store_partner_id = self.get_store_partner_id(shipping_details.get('buyerDetails'), shipping_details.get('billingAddress'))
			FeedExists = FeedPartnerEnv.search([('store_id', '=', store_partner_id)], limit=1)
			vals = self._fill_odoo_partner_details(shipping_details)
			try:
				if FeedExists:
					FeedExists.write(vals)
					FeedObj = FeedExists
					FeedExists.state = 'update'
					partner_feed_id = FeedExists.store_id
				else:
					FeedObj = FeedPartnerEnv.create(vals)
					partner_feed_id = FeedObj.store_id
			except Exception as e:
				msg = "Exception in creating/updating a partner"
			billing_address = self.create_invoice_address(shipping_details)
			# delivery_address = self.create_delivery_address(shipping_details)
		else:
			msg = shiping_res.get('shiping_res')
			status = False
		return {'partner_feed_id':partner_feed_id,'status':status,'msg':msg,'billing_address':billing_address}

	def next_page_orders(self, next_url, client):
		orders = []
		response = client.request(next_url)
		if response and response.get('orderItems'):
			orders_data = response.get('orderItems')
			if isinstance(orders_data, list):
				orders.extend(orders_data)
			elif isinstance(orders_data, dict):
				orders.append(orders_data)
			if response.get('nextPageUrl'):
				next_url = response.get('nextPageUrl')
				orders.extend(self.next_page_orders(next_url, client))
		return orders

	@api.model
	def get_flipkart_orders(self, client,  date_to=False, date_from=False,order_status=False):
		msg = ''
		status = True
		result = []
		filters = {}
		next_url = False
		from_date = date_from or self.modified_from_date
		to_date = date_to or self.modified_to_date
		order_state = order_status or self.flipkart_order_state
		if from_date and to_date:
			modified_from_date = datetime.strptime(str(from_date), '%Y-%m-%d %H:%M:%S').isoformat()
			modified_to_date = datetime.strptime(str(to_date), '%Y-%m-%d %H:%M:%S').isoformat()
			filters['orderDate'] = {
				"fromDate":modified_from_date,
				"toDate": modified_to_date
			}
			if self.flipkart_order_state:
				filters["states"] = [str(order_state)]
			if self.flipkart_sku:
				filters["sku"] = [str(self.flipkart_sku)]
		sort = ["orderDate","asc"]
		try:
			response = client.search_orders(filters, page_size=20, sort=sort)
			if response.count > 0:
				if response._nextPageUrl:
					next_url = response._nextPageUrl
				result = response.items
			else:
				msg = "Nothing to import in this interval."
				status = False
		except Exception as e:
			_logger.info('---------Exception in fetching flipkart orders--------%r',e)
			status = False
			msg = "There is an error in the fetching the flipkart orders </br> <b>Error :- </b>%s" % e
		return {'status':status,'msg':msg,'result':result, 'next_url': next_url}
	
	
	@api.model
	def get_order_product_feed(self, flipkartOrder, channel_id):
		status_message = 'Order Lines Successfully Created'
		status = True
		product_obj = 0
		msg = ''
		res = {}
		product_map_id = False
		ProductFeedExists = False
		try:
			map_exists = self.env['channel.product.mappings'].search([('store_product_id', '=', flipkartOrder.get('listingId'))])
			if not map_exists:
				res = self.env['import.flipkart.products'].get_product_using_product_id(
					flipkartOrder, channel_id)
				product_feed_exists = self.env['product.feed'].search(
					[('store_id', '=', flipkartOrder.get('listingId'))])
				if product_feed_exists:
					ProductFeedExists = True
			else:
				product_map_id = map_exists
			res['product_map_id'] = product_map_id
			res['ProductFeedExists'] = ProductFeedExists
		except Exception as e:
			_logger.info('--------------Exception--%r',e)
			res['StausMsg'] += '%s' % str(e.message)
			status = False
		finally:
			return res

	@api.model
	def get_feed_order_product_values(self, flipkart_order=False, ChannelID=False):
		feed_vals = {}
		feed_vals.update({
				'line_price_unit': flipkart_order.get('priceComponents').get('sellingPrice'),
				'line_product_uom_qty': flipkart_order.get('quantity'),
				'line_product_id': flipkart_order.get('listingId'),
			})
		res = self.get_order_product_feed(flipkart_order, ChannelID)
		if res.get('mapping_id'):
			feed_vals.update({'line_name':  res.get('mapping_id').name})
		if res.get('product_feed_id'):
			feed_vals.update({'line_name':  res.get('product_feed_id').name})
		if res.get('product_map_id'):
			feed_vals.update({
				'line_name': res['product_map_id'].product_name.name,
				'line_variant_ids': res['product_map_id'].store_variant_id
			})
		return {'feed_vals': feed_vals, 'product_res':res}

	@api.model
	def create_order_feed_lines(self, flipkartOrder=False, ChannelID=False, OrderFeed=False):
		feed_vals = {}
		ProductFeedExisted = False
		ProductFeedCreated = False
		if flipkartOrder.get('title'):
			res = self.get_feed_order_product_values(flipkartOrder, ChannelID)
			feed_vals.update(res.get('feed_vals'))
		# else:
		# 	feed_vals.update({'line_type': 'multi'})
			# line_vals_list = []
			# for ebay_item in ebay_items:
			# 	line_vals = {}
			# 	res = self.GetFeedOrderProductValues(ebay_item, ChannelID)
			# 	line_vals.update(res.get('feed_vals'))
			# 	if not OrderFeed:
			# 		line_vals_list.append((0, 0, line_vals))
			# 	else:
			# 		variant_id = self.GetVariantID(ebay_item)
			# 		order_line_exists = OrderFeed.line_ids.search([('line_product_id','=',ebay_item['Item']['ItemID']),('line_variant_ids','=',variant_id)], limit=1)
			# 		if order_line_exists:
			# 			line_vals_list.append((1, order_line_exists.id, line_vals))
			# 		else:
			# 			line_vals_list.append((0, 0, line_vals))
			# feed_vals.update({'line_ids': line_vals_list})
		if res.get('product_res').get('product_feed_id'):
			ProductFeedCreated = True
		if res.get('product_res').get('ProductFeedExists'):
			ProductFeedExisted = True
		return {'feed_vals': feed_vals, 'ProductFeedExisted': ProductFeedExisted, 'ProductFeedCreated': ProductFeedCreated}
	
	@api.model
	def create_order_feed(self, flipkart_order, partner_vals):
		status = True
		message = ''
		CreatedFeed = False
		ProductFeedCreated = False
		OrderFeedCreated = False
		ProductFeedExisted = False
		OrderFeedUpdated = False
		order_feed_id = False
		context = dict(self._context or {})
		feed_obj = self.env['order.feed']
		res = {}
		partner_feed_id = partner_vals.get('partner_feed_id')
		feed_exists = feed_obj.search([('store_id', '=', flipkart_order.get('orderId'))], limit=1)
		if context.get('channel_id'):
			ChannelID = context['channel_id']
		else:
			ChannelID = self.channel_id
		feed_vals = {
			'partner_id': partner_feed_id,
			'channel_id': ChannelID.id,
			# 'payment_method': ebay_order['CheckoutStatus']['PaymentMethod'],
			'name': flipkart_order.get('orderId'),
			'store_id': flipkart_order.get('orderId'),
			'order_state': flipkart_order.get('status'),
			'line_source':'product',
		}
		feed_vals.update(partner_vals.get('billing_address'))
		res = self.create_order_feed_lines(flipkart_order, ChannelID, feed_exists)
		feed_vals.update(res.get('feed_vals'))
		ProductFeedCreated = res.get('ProductFeedCreated')
		ProductFeedExisted = res.get('ProductFeedExisted')
		if not feed_exists:
			order_feed_id = ChannelID._create_feed(feed_obj, feed_vals)
			OrderFeedCreated = True
		else:
			order_feed_id = feed_exists
			feed_exists.write(feed_vals)
			feed_exists.state = 'update'
			OrderFeedUpdated = True
		return {
			'status': status,
			'message': message,
			'ProductFeedCreated': ProductFeedCreated,
			'OrderFeedCreated': OrderFeedCreated,
			'ProductFeedExisted': ProductFeedExisted,
			'OrderFeedUpdated': OrderFeedUpdated,
			'order_feed_id': order_feed_id
		}

	@api.model
	def create_odoo_order_feeds(self, FlipkartOrders):
		context = dict(self._context or {})
		message = ""
		status = True
		ProductFeedsCreated = CreatedOrderFeeds = ProductFeedExisted = OrderFeedUpdated = 0
		create_ids = []
		update_ids = []
		result = {}
		if context.get('channel_id'):
			ChannelID = context['channel_id']
		else:
			ChannelID = self.channel_id
		try:
			for FlipkartOrder in FlipkartOrders:
				if FlipkartOrder.get('orderItemId'):
					partner_res = self.create_odoo_partner_feed(FlipkartOrder.get('orderItemId'))
					if partner_res.get('status') and partner_res.get('partner_feed_id'):
						result = self.with_context(context).create_order_feed(FlipkartOrder, partner_res)
						if result['ProductFeedCreated']:
							ProductFeedsCreated += 1
						if result['OrderFeedCreated']:
							create_ids.append(result.get('order_feed_id'))
							CreatedOrderFeeds += 1
						if result['ProductFeedExisted']:
							ProductFeedExisted += 1
						if result['OrderFeedUpdated']:
							update_ids.append(result.get('order_feed_id'))
							OrderFeedUpdated += 1
						message += result['message']
					else:
						message += partner_res.get('msg') or ''
				else:
					message += "NO order ItemID present in Order %s"%FlipkartOrder

			if not ChannelID.auto_evaluate_feed:
				if CreatedOrderFeeds > 0:
					message += '%s Orders have been successfully imported to odoo.<br/>' % CreatedOrderFeeds
				if ProductFeedsCreated > 0:
					message += '%s new product feeds have been created please update the product feed.<br/>' % ProductFeedsCreated
				if ProductFeedExisted > 0:
					message += '%s product feeds have not been evaluated yet, please evaluate the feeds before importing the orders<br/>' % ProductFeedExisted
				if OrderFeedUpdated > 0:
					message += '%s product feeds have been updated<br/>' % OrderFeedUpdated
			if CreatedOrderFeeds == 0 and ProductFeedsCreated == 0 and ProductFeedExisted == 0 and OrderFeedUpdated == 0:
					message += 'Nothing to import, All orders have been imported already!!!<br/>'
		
		except Exception as e:
			_logger.info(
				'-------Exception in CreateOdooOrders--------------%r', e)
		finally:
			return {'message': message,
				'create_ids': create_ids,
				'update_ids': update_ids}

	
	def import_now(self):
		final_message = ''
		create_ids, update_ids, map_create_ids, map_update_ids = [], [], [], []
		for record in self:
			if record.modified_from_date > record.modified_to_date:
				raise ValidationError("'Order From Date' can not be smaller than 'Order To Date'. Please specify the date interval correctly!!")
			context = dict(self._context or {})
			if self.channel_id.flipkart_access_token:
				client_res = record.channel_id.flpkart_api_client(self.channel_id.flipkart_access_token)
				if client_res.get('status'):
					order_resp = record.get_flipkart_orders(client_res.get('client'))
					if order_resp.get('status'):
						all_order = order_resp.get('result')
						if order_resp.get('next_url'):
							next_order = self.next_page_orders(order_resp.get('next_url'), client_res.get('client'))
							if next_order:
								all_order.extend(next_order)
						res = record.with_context(context).create_odoo_order_feeds(all_order)
						post_res = record.env['channel.operation'].post_feed_import_process(
							self.channel_id, {'create_ids': res.get(
							"create_ids"), 'update_ids': res.get('update_ids')})
						create_ids += post_res.get('create_ids')
						update_ids += post_res.get('update_ids')
						map_create_ids += post_res.get('map_create_ids')
						map_update_ids += post_res.get('map_update_ids')
						final_message = res['message']
					else:
						final_message = order_resp.get('msg')
				else:
					final_message = client_res.get('msg')
		final_message += self.env['multi.channel.sale'].get_feed_import_message(
			'order', create_ids, update_ids, map_create_ids, map_update_ids
		)
		return self.env['multi.channel.sale'].display_message(final_message)

	@api.model
	def get_start_and_end_time(self, channelID):
		interval_number = channelID.flipkart_order_cron_interval_number
		interavl_type = str(channelID.flipkart_order_cron_interval_type)
		nextcall = str(datetime.now().replace(microsecond=0))
		if interavl_type == 'minutes':
			create_date_from = datetime.strptime(
				nextcall, "%Y-%m-%d %H:%M:%S") + relativedelta(minutes=- interval_number)
			create_date_from = create_date_from.strftime(
				"%Y-%m-%d %H:%M:%S")
		elif interavl_type == 'hours':
			create_date_from = datetime.strptime(
				nextcall, "%Y-%m-%d %H:%M:%S") + relativedelta(hours=- interval_number)
			create_date_from = create_date_from.strftime(
				"%Y-%m-%d %H:%M:%S")
		elif interavl_type == 'days':
			create_date_from = datetime.strptime(
				nextcall, "%Y-%m-%d %H:%M:%S") + relativedelta(days=- interval_number)
			create_date_from = create_date_from.strftime(
				"%Y-%m-%d %H:%M:%S")
		elif interavl_type == 'months':
			create_date_from = datetime.strptime(
				nextcall, "%Y-%m-%d %H:%M:%S") + relativedelta(months=- interval_number)
			create_date_from = create_date_from.strftime(
				"%Y-%m-%d %H:%M:%S")
		elif interavl_type == 'weeks':
			create_date_from = datetime.strptime(
				nextcall, "%Y-%m-%d %H:%M:%S") + relativedelta(weeks=- interval_number)
			create_date_from = create_date_from.strftime(
				"%Y-%m-%d %H:%M:%S")
		if channelID.debug == 'enable':
				_logger.info('-------Date From =====  %r Date To =======  %r---',create_date_from, nextcall)
		return [nextcall, create_date_from]

	@api.model
	def import_flipkart_orders_by_cron(self):
		"""
		Imports the orders through cron. Takes startTimeTo from view
		and calculates the startTimeTo .. Stores the parameters to fetch from ebay in context.
		"""
		create_date_from = ''
		final_message = ""
		status = True
		context = dict(self._context or {})
		channelIDs = self.env['multi.channel.sale'].search(
			[('channel', '=', 'flipkart'), ('active', '=', True),('state','=','validate')])
		for channelID in channelIDs:
			context['channel_id'] = channelID
			if channelID.debug == 'enable':
				_logger.info('Order Cron started for the Instance ID==== %r Time === %r',str(channelID.name), str(datetime.now()))
			res = self.get_start_and_end_time(channelID)
			client_res = channelID.flpkart_api_client(channelID.flipkart_access_token)
			if client_res.get('status'):
				order_resp = self.with_context(context).get_flipkart_orders(client_res.get('client'),res[0], res[1],channelID.flipkart_order_status)
				if order_resp.get('status'):
					all_orders = order_resp.get('result')
					if order_resp.get('next_url'):
						next_order = self.next_page_orders(order_resp.get('next_url'), client_res.get('client'))
						if next_order:
							all_orders.extend(next_order)
					res = self.with_context(context).create_odoo_order_feeds(all_orders)
					post_res = self.env['channel.operation'].post_feed_import_process(
					channelID, {'create_ids': res.get("create_ids"), 'update_ids': res.get('update_ids')})
					final_message = res['message']
				else:
					final_message = order_resp.get('msg')
			else:
				final_message = client_res.get('msg')
			if channelID.debug == 'enable':
				_logger.info('------------Cron Final Message----------%r',final_message)

	@api.model
	def _default_channel_id(self):
		return self._context.get('active_id')

	channel_id = fields.Many2one(
		comodel_name='multi.channel.sale',
		string='Channel ID',
		required=True,
		default=_default_channel_id
		)
	modified_from_date = fields.Datetime(
		string='Order From Date',
		help="The Date from which orders will be imported")
	modified_to_date = fields.Datetime(
		string='Order To Date',
		help="The Date up to which orders will be imported")

	flipkart_order_state = fields.Selection(
		[('APPROVED', 'APPROVED'),
		('PACKED', 'PACKED'),
		('READY_TO_DISPATCH', 'READY_TO_DISPATCH'),
		('CANCELLED', 'CANCELLED')],
		string='Flipkart Order Status',
		help="The field is used to retrieve orders that are in a specific state.")
	flipkart_sku = fields.Char(
		string="SKU",
		help="Find the orders by using sku"
	)
