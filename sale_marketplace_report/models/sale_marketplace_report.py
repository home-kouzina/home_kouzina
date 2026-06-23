from odoo import fields, models, tools, api
from odoo.http import request

class SaleMarketplaceReport(models.Model):
    _name = 'sale.marketplace.report'
    _description = 'Sale Marketplace Report'
    _auto = False
    _rec_name = 'so_name'
    _order = 'order_date desc'

    # Sale Order
    so_id = fields.Many2one('sale.order', string='Sale Order Ref', readonly=True)
    so_name = fields.Char(string='SO Number', readonly=True)
    state = fields.Selection([
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True)
    order_date = fields.Datetime(string='Order Date', readonly=True)
    order_date_only = fields.Char(string='Order Date', readonly=True)

    # Customer & Salesperson
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    user_id = fields.Many2one('res.users', string='Salesperson', readonly=True)
    city = fields.Char(string='City', readonly=True)

    # Marketplace
    marketplace_type = fields.Char(string='Marketplace', readonly=True)
    #sku 
    sku = fields.Char(
        string='SKU', readonly=True,
        help='Internal Reference (SKU) of the product.')

    # Product line fields
    sol_id = fields.Integer(string='Line ID', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', string='Product Template', readonly=True)
    price_unit = fields.Float(string='Unit Price', digits='Product Price', readonly=True)
    product_uom_qty = fields.Float(string='Quantity', readonly=True)
    discount = fields.Float(string='Discount (%)', digits='Discount', readonly=True)
    price_subtotal = fields.Float(string='Total Amount', digits='Product Price', readonly=True)

    # Currency
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    sol.id                          AS id,
                    sol.id                          AS sol_id,
                    so.id                           AS so_id,
                    so.name                         AS so_name,
                    so.state                        AS state,
                    so.date_order                   AS order_date,
                    TO_CHAR(so.date_order, 'DD/MM/YYYY')  AS order_date_only,
                    so.partner_id                   AS partner_id,
                    so.user_id                      AS user_id,
                    rp.city                         AS city,
                    COALESCE(
                        so.marketplace_type::TEXT,
                        ''
                    )                               AS marketplace_type,
                    sol.product_id                  AS product_id,
                    pt.id                           AS product_tmpl_id,
                    COALESCE(pp.default_code, pt.default_code, '')  AS sku,
                    sol.price_unit                  AS price_unit,
                    sol.product_uom_qty             AS product_uom_qty,
                    sol.discount/100.0              AS discount,
                    sol.price_subtotal              AS price_subtotal,
                    so.currency_id                  AS currency_id,
                    so.company_id                   AS company_id
                FROM sale_order_line sol
                JOIN sale_order so           ON so.id = sol.order_id
                JOIN product_product pp      ON pp.id = sol.product_id
                JOIN product_template pt     ON pt.id = pp.product_tmpl_id
                LEFT JOIN res_partner rp     ON rp.id = so.partner_id
                WHERE sol.display_type IS NULL
            )
        """ % self._table)




class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        if request and 'marketplace_type' in fields_list:
            defaults['marketplace_type'] = 'b2b'  # manual UI creation default
        return defaults

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('amazon_channel') or vals.get('amazon_order_ref'):
                vals.setdefault('marketplace_type', 'amazon')
            elif vals.get('shopify_order_id') or vals.get('shopify_instance_id'):
                vals.setdefault('marketplace_type', 'shopify')
        return super().create(vals_list)