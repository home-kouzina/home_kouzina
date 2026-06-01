from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _get_marketplace_type_selection(self):
        marketplaces = self.env['marketplace.master'].sudo().search([], order='name')
        selection = []
        seen_codes = set()
        for marketplace in marketplaces:
            code = marketplace.code or marketplace._normalize_marketplace_code(marketplace.name)
            if not code or code in seen_codes:
                continue
            selection.append((code, marketplace.name))
            seen_codes.add(code)
        return selection or self.env['marketplace.master']._get_default_marketplace_selection()

    marketplace_type = fields.Selection(
        selection='_get_marketplace_type_selection',
        string="Marketplace",
    )
    marketplace_order_ref = fields.Char(string="Order ID")
    marketplace_order_date = fields.Date(string="Order Date")
    marketplace_payment_status = fields.Char(string="Payment Status")
    marketplace_order_status = fields.Char(string="Order Status")
    marketplace_delivery_slot = fields.Char(string="Delivery Slot")
    marketplace_total_amount = fields.Float(string="Total Amount")

    partner_shipping_id = fields.Many2one('res.partner', string="Shipping Address")
    partner_invoice_id = fields.Many2one('res.partner', string="Invoice Address")

    marketplace_invoice_number = fields.Char(string="Marketplace Invoice Number")
    marketplace_invoice_type = fields.Char(string="Invoice Type")
    marketplace_sale_state = fields.Char(string="Sale State")
    # marketplace_supply_city = fields.Char(string="Supply City")
    # marketplace_supply_country = fields.Many2one(
    #     'res.country',
    #     string="Supply Country",
    #     help="Country from where the goods are supplied / dispatched"
    # )
    # marketplace_supply_state = fields.Many2one(
    #     'res.country.state',
    #     string="Supply State",
    #     domain="[('country_id', '=', marketplace_supply_country)]",  # Contextual filtering
    #     help="State from where the goods are supplied / dispatched"
    # )
    # marketplace_supply_state_gst = fields.Char(string="Supply State GST")
    marketplace_hsn_code = fields.Char(string="HSN Code")
    marketplace_item_id = fields.Char(string="Item ID")


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('marketplace_order_ref'):
                vals['marketplace_order_ref'] = str(vals['marketplace_order_ref']).strip()
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('marketplace_order_ref'):
            vals = dict(vals, marketplace_order_ref=str(vals['marketplace_order_ref']).strip())
        return super().write(vals)

    def init(self):
        super().init()
        cr = self.env.cr
        cr.execute("""
            SELECT column_name
              FROM information_schema.columns
             WHERE table_name = 'sale_order'
               AND column_name IN (
                   'marketplace_order_ref', 'marketplace_order_date',
                   'marketplace_payment_status', 'marketplace_order_status',
                   'marketplace_delivery_slot', 'marketplace_total_amount',
                   'flipkart_order_id', 'flipkart_order_date', 'flipkart_payment_status',
                   'flipkart_order_status', 'flipkart_total_amount',
                   'amazon_order_id', 'amazon_order_date', 'amazon_payment_status',
                   'amazon_order_status', 'amazon_total_amount',
                   'blinkit_order_id', 'blinkit_delivery_slot', 'blinkit_payment_status',
                   'blinkit_order_status', 'blinkit_total_amount',
                   'shopify_order_id', 'shopify_order_date', 'shopify_payment_status',
                   'shopify_order_status', 'shopify_total_amount'
               )
        """)
        columns = {row[0] for row in cr.fetchall()}
        required_columns = {
            'marketplace_order_ref', 'marketplace_order_date', 'marketplace_payment_status',
            'marketplace_order_status', 'marketplace_delivery_slot', 'marketplace_total_amount',
        }
        if not required_columns.issubset(columns):
            return

        def existing(*names):
            return [name for name in names if name in columns]

        field_map = {
            'marketplace_order_ref': existing(
                'amazon_order_id', 'flipkart_order_id', 'blinkit_order_id', 'shopify_order_id'
            ),
            'marketplace_order_date': existing(
                'amazon_order_date', 'flipkart_order_date', 'shopify_order_date'
            ),
            'marketplace_payment_status': existing(
                'amazon_payment_status', 'flipkart_payment_status', 'blinkit_payment_status', 'shopify_payment_status'
            ),
            'marketplace_order_status': existing(
                'amazon_order_status', 'flipkart_order_status', 'blinkit_order_status', 'shopify_order_status'
            ),
            'marketplace_delivery_slot': existing('blinkit_delivery_slot'),
            'marketplace_total_amount': existing(
                'amazon_total_amount', 'flipkart_total_amount', 'blinkit_total_amount', 'shopify_total_amount'
            ),
        }

        updates = []
        for field_name, legacy_fields in field_map.items():
            if legacy_fields:
                updates.append(
                    f"{field_name} = COALESCE({field_name}, {', '.join(legacy_fields)})"
                )
        if updates:
            cr.execute(f"UPDATE sale_order SET {', '.join(updates)}")
