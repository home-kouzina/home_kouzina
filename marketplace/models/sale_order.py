from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    marketplace_type = fields.Selection([
        ('flipkart', 'Flipkart'),
        ('amazon', 'Amazon'),
        ('blinkit', 'Blinkit'),
        ('shopify', 'Shopify')
    ], string="Marketplace")

    
    # Master field to control which marketplace fields are visible
    # --- Flipkart Fields ---
    flipkart_order_id = fields.Char(string="Flipkart Order ID")
    flipkart_order_date = fields.Date(string="Flipkart Order Date")
    flipkart_payment_status = fields.Selection([
        ('paid', 'Paid'), ('cod', 'COD'), ('pending', 'Pending')
    ], string="Flipkart Payment Status")
    flipkart_order_status = fields.Selection([
        ('delivered', 'Delivered'), ('shipped', 'Shipped'), ('pending', 'Pending')
    ], string="Flipkart Order Status")
    flipkart_total_amount = fields.Float(string="Flipkart Total Amount")

    # --- Amazon Fields ---
    amazon_order_id = fields.Char(string="Amazon Order ID")
    amazon_order_date = fields.Date(string="Amazon Order Date")
    amazon_payment_status = fields.Selection([
        ('paid', 'Paid'), ('cod', 'COD')
    ], string="Amazon Payment Status")
    amazon_order_status = fields.Selection([
        ('pending', 'Pending'), ('shipped', 'Shipped'), ('delivered', 'Delivered')
    ], string="Amazon Order Status")
    amazon_total_amount = fields.Float(string="Amazon_Total_Amount")

    # --- Blinkit Fields ---
    blinkit_order_id = fields.Char(string="Blinkit Order ID")
    blinkit_delivery_slot = fields.Char(string="Blinkit Delivery Slot")
    blinkit_payment_status = fields.Selection([
        ('paid', 'Paid'), ('unpaid', 'Unpaid')
    ], string="Blinkit Payment Status")
    blinkit_order_status = fields.Selection([
        ('placed', 'Placed'), ('packed', 'Packed'), ('delivered', 'Delivered')
    ], string="Blinkit Order Status")
    blinkit_total_amount = fields.Float(string="Blinkit_Total_Amount")

    # --- Shopify Fields ---
    shopify_order_id = fields.Char(string="Shopify Order ID")
    shopify_order_date = fields.Date(string="Shopify Order Date")
    shopify_payment_status = fields.Selection([
        ('paid', 'Paid'), ('pending', 'Pending'), ('refunded', 'Refunded')
    ], string="Shopify Payment Status")
    shopify_order_status = fields.Selection([
        ('fulfilled', 'Fulfilled'), ('unfulfilled', 'Unfulfilled'), ('partial', 'Partially Fulfilled')
    ], string="Shopify Order Status")
    shopify_total_amount = fields.Float(string="Shopify Total Amount")
    marketplace_invoice_number = fields.Char(string="Marketplace Invoice Number")
    marketplace_invoice_type = fields.Char(string="Invoice Type")
    marketplace_sale_state = fields.Char(string="Sale State")
