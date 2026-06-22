from odoo import models, fields, api
from odoo.tools import SQL


class HKPurchaseReport(models.Model):
    _name = 'hk.purchase.report'
    _description = 'HK Purchase Report'
    _auto = False
    _rec_name = 'order_name'
    _order = 'date_order desc, id desc'

    # ── Core identifiers ──────────────────────────────────────────
    order_id = fields.Many2one('purchase.order', string='Purchase Order', readonly=True)
    order_name = fields.Char(string='Order Reference', readonly=True)

    # ── Product ───────────────────────────────────────────────────
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', string='Product Template', readonly=True)
    sku = fields.Char(string='SKU / Internal Ref', readonly=True)
    categ_id = fields.Many2one('product.category', string='Product Category', readonly=True)
    lot_numbers = fields.Char(string='Lot/Serial Number', readonly=True)

    # ── Vendor / Order Info ───────────────────────────────────────
    partner_id = fields.Many2one('res.partner', string='Vendor', readonly=True)
    user_id = fields.Many2one('res.users', string='Purchase Representative', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)

    # ── Quantities ────────────────────────────────────────────────
    product_qty = fields.Float(string='Ordered Qty', digits='Product Unit of Measure', readonly=True)
    qty_received = fields.Float(string='Received Qty', digits='Product Unit of Measure', readonly=True)
    qty_returned = fields.Float(string='Returned Qty', digits='Product Unit of Measure', readonly=True)
    qty_invoiced = fields.Float(string='Billed Qty', digits='Product Unit of Measure', readonly=True)
    qty_to_invoice = fields.Float(string='Qty to Bill', digits='Product Unit of Measure', readonly=True)
    qty_to_receive = fields.Float(string='Qty to Receive', digits='Product Unit of Measure', readonly=True)
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure', readonly=True)

    # ── Prices ────────────────────────────────────────────────────
    price_unit = fields.Float(string='Unit Price', digits='Product Price', readonly=True)
    price_subtotal = fields.Monetary(string='Subtotal', currency_field='currency_id', readonly=True)
    price_tax = fields.Monetary(string='Taxes', currency_field='currency_id', readonly=True)
    price_total = fields.Monetary(string='Total', currency_field='currency_id', readonly=True)

    # ── Dates ─────────────────────────────────────────────────────
    date_order = fields.Char(string='Order Date', readonly=True)
    date_approve = fields.Char(string='Confirmation Date', readonly=True)
    date_planned = fields.Char(string='Scheduled Date', readonly=True)

    date_order_raw   = fields.Datetime(string='Order Date (raw)',   readonly=True)
    date_approve_raw = fields.Datetime(string='Confirm Date (raw)', readonly=True)
    date_planned_raw = fields.Datetime(string='Scheduled Date (raw)', readonly=True)

    # ── Status ────────────────────────────────────────────────────
    state = fields.Selection([
        ('draft', 'RFQ'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'To Approve'),
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True)

    # ── Receipt Status ────────────────────────────────────────────
    receipt_status = fields.Selection([
        ('nothing', 'Nothing to Receive'),
        ('to receive', 'Waiting Receipts'),
        ('received', 'Fully Received'),
    ], string='Receipt Status', readonly=True)

    # ── Billing Status ────────────────────────────────────────────
    invoice_status = fields.Selection([
        ('nothing', 'Nothing to Bill'),
        ('to invoice', 'Waiting Bills'),
        ('invoiced', 'Fully Billed'),
    ], string='Billing Status', readonly=True)

    # new field for the product type
    product_category_type = fields.Char(
        string='Product Category Type', readonly=True,
        help='Finished Good or Raw Material based on is_finished_good flag.')

    # ────────────────────────────────────────────────────────────────
    # SQL VIEW
    # ────────────────────────────────────────────────────────────────
    def init(self):
        self.env.cr.execute("DROP VIEW IF EXISTS hk_purchase_report")
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW hk_purchase_report AS (
                SELECT
                    pol.id                                          AS id,
                    po.id                                           AS order_id,
                    po.name                                         AS order_name,

                    pol.product_id                                  AS product_id,
                    pp.product_tmpl_id                              AS product_tmpl_id,
                    COALESCE(pp.default_code, pt.default_code, '')  AS sku,
                    pt.categ_id                                     AS categ_id,
                    lots.lot_numbers                                AS lot_numbers,
                    CASE
                        WHEN pp.is_finished_good = TRUE
                        THEN 'Finished Good'
                        ELSE 'Raw Material'
                    END                                         AS product_category_type,

                    po.partner_id                                   AS partner_id,
                    po.user_id                                      AS user_id,
                    po.company_id                                   AS company_id,
                    po.currency_id                                  AS currency_id,

                    pol.product_qty                                 AS product_qty,
                    pol.qty_received                                AS qty_received,
                    COALESCE(returns.qty_returned, 0)               AS qty_returned,
                    pol.qty_invoiced                                AS qty_invoiced,
                    GREATEST(pol.product_qty - pol.qty_invoiced, 0) AS qty_to_invoice,
                    GREATEST(pol.product_qty - pol.qty_received, 0) AS qty_to_receive,
                    pol.product_uom                                 AS product_uom,

                    pol.price_unit                                  AS price_unit,
                    pol.price_subtotal                              AS price_subtotal,
                    pol.price_tax                                   AS price_tax,
                    pol.price_total                                 AS price_total,

                    
                    TO_CHAR(po.date_order,   'DD/MM/YYYY')          AS date_order,
                    TO_CHAR(po.date_approve, 'DD/MM/YYYY')          AS date_approve,
                    TO_CHAR(pol.date_planned,'DD/MM/YYYY')          AS date_planned,
                    
                    po.date_order                                   AS date_order_raw,
                    po.date_approve                                 AS date_approve_raw,
                    pol.date_planned                                AS date_planned_raw,

                    po.state                                        AS state,

                    CASE
                        WHEN po.state IN ('draft','sent','to approve','cancel') THEN 'nothing'
                        WHEN pol.qty_received >= pol.product_qty               THEN 'received'
                        ELSE 'to receive'
                    END                                             AS receipt_status,

                    CASE
                        WHEN po.state IN ('draft','sent','to approve','cancel') THEN 'nothing'
                        WHEN pol.qty_invoiced >= pol.product_qty               THEN 'invoiced'
                        ELSE 'to invoice'
                    END                                             AS invoice_status

                FROM purchase_order_line pol
                JOIN purchase_order    po  ON po.id  = pol.order_id
                JOIN product_product   pp  ON pp.id  = pol.product_id
                JOIN product_template  pt  ON pt.id  = pp.product_tmpl_id
                LEFT JOIN (
                    SELECT
                        sm.purchase_line_id                         AS purchase_line_id,
                        STRING_AGG(DISTINCT sl.name, ', ')          AS lot_numbers
                    FROM stock_move sm
                    JOIN stock_move_line sml ON sml.move_id = sm.id
                    JOIN stock_lot sl         ON sl.id = sml.lot_id
                    WHERE sm.purchase_line_id IS NOT NULL
                    GROUP BY sm.purchase_line_id
                ) lots ON lots.purchase_line_id = pol.id
                LEFT JOIN (
                    SELECT
                        sm.purchase_line_id                         AS purchase_line_id,
                        SUM(sm.quantity)                            AS qty_returned
                    FROM stock_move sm
                    JOIN stock_location sl ON sl.id = sm.location_dest_id
                    WHERE sm.purchase_line_id IS NOT NULL
                      AND sm.state = 'done'
                      AND sl.usage = 'supplier'
                    GROUP BY sm.purchase_line_id
                ) returns ON returns.purchase_line_id = pol.id
            )
        """)
