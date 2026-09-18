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
    # Renamed from "Scheduled Date" so it reads the same as the matching
    # relabel done on the Manufacturing Order form itself.
    date_start = fields.Datetime(string='Production Date', readonly=True)
    product_qty = fields.Float(string='Quantity', readonly=True)
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure', readonly=True)
    mo_cost = fields.Float(
        string='Cost', digits='Product Price', readonly=True,
        help="The product variant's own Cost price (General Information tab), "
             "not multiplied by the quantity produced.")
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
    # New: when this MO was submitted for approval (mrp_auto_component_lots'
    # requested_date, stamped by action_approved_submit). Requires that
    # module to be installed — see __manifest__.py depends.
    requested_date = fields.Datetime(string='Requested Date', readonly=True)
    # New: Retail / Finished Good / Raw Material, same classification logic
    # as inventory_soh_report, so the two reports agree with each other.
    product_category_type = fields.Char(
        string='Type of Product', readonly=True,
        help="Retail if the product's own 'Is Retail' box is ticked; "
             "otherwise Finished Good or Raw Material based on its "
             "'Is Finished Good' box.")

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
                    -- requested_date lives on mrp.production, added by the
                    -- mrp_auto_component_lots module (this module now depends
                    -- on it, see __manifest__.py, so the column always exists
                    -- whenever this view is created).
                    mp.requested_date                   AS requested_date,
                    -- Same Retail / Finished Good / Raw Material split used by
                    -- inventory_soh_report, so both reports classify products
                    -- the same way.
                    CASE
                        WHEN pt.is_retail = TRUE
                        THEN 'Retail'
                        WHEN pp.is_finished_good = TRUE
                        THEN 'Finished Good'
                        ELSE 'Raw Material'
                    END                                  AS product_category_type,
                    -- Cost = the product variant's own Cost price, shown as-is (not
                    -- multiplied by quantity), replacing the old inventory-valuation-
                    -- ledger sum. standard_price is company-specific (stored as JSON
                    -- keyed by company id), so it's looked up for this order's own
                    -- company_id.
                    COALESCE(
                        (pp.standard_price ->> mp.company_id::text)::numeric, 0.0
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
