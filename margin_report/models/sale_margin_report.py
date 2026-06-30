from odoo import fields, models, tools


class SaleMarginReport(models.Model):
    _name = 'sale.margin.report'
    _description = 'Sales Margin Report'
    _auto = False
    _rec_name = 'so_name'
    _order = 'order_date desc'

    so_id = fields.Many2one('sale.order', string='Sales Order', readonly=True)
    so_name = fields.Char(string='Sales Order Number', readonly=True)
    customer_name = fields.Char(string='Customer Name', readonly=True)
    marketplace_type = fields.Char(string='Marketplace', readonly=True)
    city = fields.Char(string='City', readonly=True)
    invoice_number = fields.Char(string='Invoice Number', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_name = fields.Char(string='Product Name', readonly=True)
    ean_number = fields.Char(string='EAN Number', readonly=True)
    sku = fields.Char(string='SKU', readonly=True)
    is_finished_good = fields.Boolean(string='Is Finished Good', readonly=True)
    is_retail = fields.Boolean(string='Is Retail', readonly=True)
    product_uom_qty = fields.Float(string='Qty', readonly=True)
    cogs = fields.Float(string='COGS', readonly=True, digits='Product Price')
    nett = fields.Float(string='Nett(Untaxed)', readonly=True, digits='Product Price')
    mrp = fields.Float(string='MRP', readonly=True, digits='Product Price')
    cogs_percent = fields.Float(string='COGS %', readonly=True, digits=(16, 2))
    gross_margin = fields.Float(string='Gross Margin %', readonly=True, digits=(16, 2))
    total_amount_taxed = fields.Float(string='Total Amount (Taxed)', readonly=True, digits='Product Price')
    order_date = fields.Datetime(string='Order Date', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    sol.id AS id,
                    so.id AS so_id,
                    so.name AS so_name,
                    rp.name AS customer_name,
                    COALESCE(
                        so.marketplace_type::TEXT,
                        ''
                    ) AS marketplace_type,
                    COALESCE(rp.city, '') AS city,
                    COALESCE(
                        (
                            SELECT STRING_AGG(am2.name, ', ' ORDER BY am2.name)
                            FROM account_move am2
                            WHERE am2.invoice_origin = so.name
                              AND am2.move_type = 'out_invoice'
                              AND am2.state != 'cancel'
                        ), ''
                    ) AS invoice_number,
                    pp.id AS product_id,
                    COALESCE(pt.name->>'en_US', pt.name::text) AS product_name,
                    COALESCE(pp.barcode, '') AS ean_number,
                    COALESCE(pp.default_code, '') AS sku,
                    pp.is_finished_good AS is_finished_good,
                    pt.is_retail AS is_retail,
                    sol.product_uom_qty AS product_uom_qty,
                    COALESCE(sol.cogs_unit_price, 0.0) * sol.product_uom_qty AS cogs,
                    sol.price_subtotal AS nett,
                    pt.list_price AS mrp,
                    CASE
                        WHEN sol.price_subtotal <> 0.0
                        THEN ROUND(
                            ((COALESCE(sol.cogs_unit_price, 0.0) * sol.product_uom_qty)
                            / sol.price_subtotal * 100.0)::numeric, 2)
                        ELSE 0.0
                    END AS cogs_percent,
                    CASE
                        WHEN sol.price_subtotal <> 0.0
                        THEN ROUND(
                            ((sol.price_subtotal - (
                                COALESCE(sol.cogs_unit_price, 0.0) * sol.product_uom_qty))
                            / sol.price_subtotal * 100.0)::numeric, 2)
                        ELSE 0.0
                    END AS gross_margin,
                    sol.price_total AS total_amount_taxed,
                    so.date_order AS order_date
                FROM sale_order_line sol
                JOIN sale_order so ON so.id = sol.order_id
                JOIN product_product pp ON pp.id = sol.product_id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                LEFT JOIN res_partner rp ON rp.id = so.partner_id
                WHERE sol.display_type IS NULL
            )
        """)
