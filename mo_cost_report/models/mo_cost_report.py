from odoo import api, fields, models, tools


class MoCostReport(models.Model):
    _name = 'mo.cost.report'
    _description = 'Manufacturing Order Cost Report'
    _auto = False
    _rec_name = 'mo_name'
    _order = 'mo_name desc'

    mo_id = fields.Many2one('mrp.production', string='Manufacturing Order', readonly=True)
    mo_name = fields.Char(string='MO Number', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_name = fields.Char(string='Product Name', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', string='Product Template', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('progress', 'In Progress'),
        ('to_close', 'To Close'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True)
    date_start = fields.Datetime(string='Scheduled Date', readonly=True)
    product_qty = fields.Float(string='Quantity', readonly=True)
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure', readonly=True)
    mo_cost = fields.Float(string='Cost', digits='Product Price', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    # Requested By = user who created the MO (create_uid)
    requested_by_id = fields.Many2one('res.users', string='Requested By', readonly=True)
    # Approved By = user who marked the MO as done (write_uid when state = done)
    approved_by_id = fields.Many2one('res.users', string='Approved By', readonly=True)
    # SKU = product.product default_code
    sku_code = fields.Char(string='SKU', readonly=True)
    # Lot/Serial Number = lot_producing_id on mrp.production
    lot_producing_id = fields.Many2one('stock.lot', string='Lot/Serial Number', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    mp.id                               AS id,
                    mp.id                               AS mo_id,
                    mp.name                             AS mo_name,
                    mp.product_id                       AS product_id,
                    pt.name                             AS product_name,
                    pp.product_tmpl_id                  AS product_tmpl_id,
                    mp.state                            AS state,
                    mp.date_start                       AS date_start,
                    mp.product_qty                      AS product_qty,
                    mp.product_uom_id                   AS product_uom_id,
                    COALESCE(pp.default_code, '')       AS sku_code,
                    mp.lot_producing_id                 AS lot_producing_id,
                    COALESCE(
                        (
                            SELECT SUM(svl.value)
                            FROM stock_valuation_layer svl
                            JOIN stock_move sm ON sm.id = svl.stock_move_id
                            WHERE sm.production_id = mp.id
                              AND sm.state = 'done'
                        ), 0.0
                    )                                   AS mo_cost,
                    rc.currency_id                      AS currency_id,
                    mp.company_id                       AS company_id,
                    mp.create_uid                       AS requested_by_id,
                    CASE
                        WHEN mp.state = 'done' THEN mp.write_uid
                        ELSE NULL
                    END                                 AS approved_by_id
                FROM mrp_production mp
                JOIN product_product pp      ON pp.id = mp.product_id
                JOIN product_template pt     ON pt.id = pp.product_tmpl_id
                JOIN res_company rc          ON rc.id = mp.company_id
            )
        """ % self._table)
