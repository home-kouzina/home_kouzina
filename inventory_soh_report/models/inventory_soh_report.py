# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools


class InventorySohReport(models.Model):
    """
    Inventory SOH (Stock on Hand) Report.

    Changes:
        - Added sku (product default_code)
        - Renamed qty_inward label to 'Purchased Qty'
        - Added variance_value = variance * cog_before_sale
        - actual_soh moved before variance in view
        - variance_value now uses the product variant's own Cost price
          instead of cog_before_sale (which also included labelling/
          packaging costs, overstating the value of a stock variance)
        - qty_on_hand/qty_inward/qty_consumption/qty_return/qty_wastage/
          ideal_soh/actual_soh/variance are shown in kg (not grams) for
          any product whose Unit of Measure is grams
    """

    _name = 'inventory.soh.report'
    _description = 'Inventory SOH Report'
    _auto = False
    _rec_name = 'product_id'
    _order = 'product_id'

    # ── Fields ────────────────────────────────────────────────────────────────

    product_id = fields.Many2one(
        'product.product', string='Product', readonly=True)

    product_tmpl_id = fields.Many2one(
        'product.template', string='Product Template', readonly=True)

    categ_id = fields.Many2one(
        'product.category', string='Product Category', readonly=True)

    product_type = fields.Selection(
        [
            ('consu',    'Consumable'),
            ('service',  'Service'),
            ('product',  'Storable Product'),
            ('storable', 'Storable Product'),
        ],
        string='Product Type', readonly=True)

    uom_id = fields.Many2one(
        'uom.uom', string='Unit of Measure', readonly=True)

    sku = fields.Char(
        string='SKU', readonly=True,
        help='Internal Reference (SKU) of the product.')

    # All eight quantity fields below (qty_on_hand ... variance) are shown
    # in kg, not grams, for any product whose Unit of Measure is grams
    # (e.g. 45g shows as 0.045). This is a display-only conversion applied
    # in the SQL view (see kg_factor in init() below) — it doesn't touch
    # the underlying stock/move data, and doesn't affect products in any
    # other Unit of Measure. "Value" is a currency amount, not a quantity,
    # and is deliberately left unconverted.

    qty_on_hand = fields.Float(
        string='Current On Hand Qty',
        digits='Product Unit of Measure', readonly=True,
        help='Current quantity physically available in internal locations.')

    qty_inward = fields.Float(
        string='Purchased Qty',
        digits='Product Unit of Measure', readonly=True,
        help='Total quantity successfully received into inventory (Receipts).')

    qty_consumption = fields.Float(
        string='Consumption (Used Qty)',
        digits='Product Unit of Measure', readonly=True,
        help='Finished goods: qty delivered via Sale Orders. '
             'Raw materials: qty consumed in Manufacturing Orders.')

    qty_return = fields.Float(
        string='Return Qty',
        digits='Product Unit of Measure', readonly=True,
        help='Quantity returned FROM inventory back to vendor / source location.')

    qty_wastage = fields.Float(
        string='Wastage (Scrap)',
        digits='Product Unit of Measure', readonly=True,
        help='Total quantity scrapped / written off.')

    ideal_soh = fields.Float(
        string='Ideal SOH',
        digits='Product Unit of Measure', readonly=True,
        help='Ideal SOH = On Hand + Purchased - Consumption - Return - Wastage')

    actual_soh = fields.Float(
        string='Actual SOH',
        digits='Product Unit of Measure', readonly=True,
        help='Actual SOH = Ideal SOH - Variance')

    variance = fields.Float(
        string='Variance',
        digits='Product Unit of Measure', readonly=True,
        help='Sum of variation_qty from the latest confirmed Inventory Variation '
             'report (IVR) for this product.')

    # Renamed from "Value = Variance x COG Before Sale": COG Before Sale also
    # adds on labelling/packaging costs, which isn't what "Value" is meant to
    # represent here — this is the value of missing/extra stock, so it should
    # only use the product variant's own raw Cost price.
    variance_value = fields.Float(
        string='Value',
        digits='Account', readonly=True,
        help='Value = Variance x the product variant\'s own Cost price.')

    product_category_type = fields.Char(
        string='Product Category Type', readonly=True,
        help='Retail if is_retail flag is set; otherwise Finished Good or '
             'Raw Material based on is_finished_good flag.')

    # ── SQL View ──────────────────────────────────────────────────────────────

    def init(self):
        """Drop and recreate the SQL view."""
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (

            WITH

            -- ─── On-hand quantities from stock.quant ─────────────────────────
            onhand AS (
                SELECT
                    sq.product_id,
                    SUM(sq.quantity)              AS qty_on_hand
                FROM stock_quant sq
                JOIN stock_location sl ON sl.id = sq.location_id
                WHERE sl.usage = 'internal'
                  AND sq.company_id IS NOT NULL
                GROUP BY sq.product_id
            ),

            -- ─── Inward: done incoming pickings, non-return ───────────────────
            inward AS (
                SELECT
                    sm.product_id,
                    SUM(sm.quantity)              AS qty_inward
                FROM stock_move sm
                JOIN stock_location loc_src  ON loc_src.id  = sm.location_id
                JOIN stock_location loc_dest ON loc_dest.id = sm.location_dest_id
                JOIN stock_picking     sp    ON sp.id       = sm.picking_id
                JOIN stock_picking_type spt  ON spt.id      = sp.picking_type_id
                WHERE sm.state         = 'done'
                  AND loc_src.usage   != 'internal'
                  AND loc_dest.usage   = 'internal'
                  AND spt.code         = 'incoming'
                  AND (sm.origin IS NULL OR sm.origin NOT ILIKE '%%Return%%')
                GROUP BY sm.product_id
            ),

            -- ─── Returns: outgoing done pickings that are vendor returns ──────
            returns AS (
                SELECT
                    sm.product_id,
                    SUM(sm.quantity)              AS qty_return
                FROM stock_move sm
                JOIN stock_location loc_src  ON loc_src.id  = sm.location_id
                JOIN stock_location loc_dest ON loc_dest.id = sm.location_dest_id
                JOIN stock_picking     sp    ON sp.id       = sm.picking_id
                JOIN stock_picking_type spt  ON spt.id      = sp.picking_type_id
                WHERE sm.state         = 'done'
                  AND loc_src.usage    = 'internal'
                  AND loc_dest.usage  != 'internal'
                  AND (
                       sm.origin ILIKE '%%Return%%'
                       OR sp.return_id IS NOT NULL
                  )
                GROUP BY sm.product_id
            ),

            -- ─── Consumption: split by is_finished_good ──────────────────────
            --   Finished Good (is_finished_good=True)  → Sale Order deliveries
            --   Raw Material  (is_finished_good=False) → MRP component moves
            consumption AS (
                SELECT product_id, SUM(qty_consumption) AS qty_consumption
                FROM (
                    -- Finished goods: outgoing deliveries from sale orders
                    SELECT
                        sm.product_id,
                        sm.quantity               AS qty_consumption
                    FROM stock_move sm
                    JOIN stock_location loc_src  ON loc_src.id  = sm.location_id
                    JOIN stock_location loc_dest ON loc_dest.id = sm.location_dest_id
                    JOIN stock_picking     sp    ON sp.id       = sm.picking_id
                    JOIN stock_picking_type spt  ON spt.id      = sp.picking_type_id
                    JOIN product_product   pp2   ON pp2.id      = sm.product_id
                    WHERE sm.state        = 'done'
                      AND loc_src.usage   = 'internal'
                      AND loc_dest.usage != 'internal'
                      AND spt.code        = 'outgoing'
                      AND sp.return_id   IS NULL
                      AND (sm.origin IS NULL OR sm.origin NOT ILIKE '%%Return%%')
                      AND pp2.is_finished_good = TRUE
                      AND sm.sale_line_id IS NOT NULL

                    UNION ALL

                    -- Raw materials: components consumed in manufacturing orders
                    SELECT
                        sm.product_id,
                        sm.quantity               AS qty_consumption
                    FROM stock_move sm
                    JOIN stock_location loc_src  ON loc_src.id  = sm.location_id
                    JOIN stock_location loc_dest ON loc_dest.id = sm.location_dest_id
                    JOIN product_product pp2     ON pp2.id      = sm.product_id
                    WHERE sm.state        = 'done'
                      AND loc_src.usage   = 'internal'
                      AND loc_dest.usage != 'internal'
                      AND sm.raw_material_production_id IS NOT NULL
                      AND pp2.is_finished_good = FALSE
                ) sub
                GROUP BY product_id
            ),

            -- ─── Wastage from stock.scrap ─────────────────────────────────────
            wastage AS (
                SELECT
                    ss.product_id,
                    SUM(ss.scrap_qty)             AS qty_wastage
                FROM stock_scrap ss
                WHERE ss.state = 'done'
                GROUP BY ss.product_id
            ),

            -- ─── Latest confirmed/reported IVR ────────────────────────────────
            latest_ivr_id AS (
                SELECT id
                FROM inventory_variation
                WHERE state IN ('confirmed', 'reported')
                ORDER BY date DESC, id DESC
                LIMIT 1
            ),
            ivr_variance AS (
                SELECT
                    ivl.product_id,
                    SUM(ivl.variation_qty)        AS variance
                FROM inventory_variation_line ivl
                WHERE ivl.variation_id = (SELECT id FROM latest_ivr_id)
                GROUP BY ivl.product_id
            ),

            -- ─── Raw SELECT (everything in the product's own stored UoM) ──────
            raw AS (
                SELECT
                    pp.id                                       AS id,
                    pp.id                                       AS product_id,
                    pt.id                                       AS product_tmpl_id,
                    pt.categ_id,
                    pt.type                                     AS product_type,
                    CASE
                        WHEN pt.is_retail = TRUE
                        THEN 'Retail'
                        WHEN pp.is_finished_good = TRUE
                        THEN 'Finished Good'
                        ELSE 'Raw Material'
                    END                                         AS product_category_type,
                    pt.uom_id,
                    COALESCE(pp.default_code, pt.default_code)  AS sku,

                    -- Report-display kg conversion for gram-UoM products:
                    -- 1 if the product's UoM isn't grams, 0.001 if it is —
                    -- multiplied onto every quantity column below so a
                    -- product tracked in grams reads in kg on this report
                    -- (e.g. 45g shows as 0.045). Purely a display factor;
                    -- doesn't touch the stored stock/move data anywhere.
                    CASE WHEN uu.name->>'en_US' = 'g' THEN 0.001 ELSE 1 END
                                                                AS kg_factor,

                    COALESCE(oh.qty_on_hand,     0)             AS qty_on_hand,
                    COALESCE(iw.qty_inward,      0)             AS qty_inward,
                    COALESCE(co.qty_consumption, 0)             AS qty_consumption,
                    COALESCE(rt.qty_return,      0)             AS qty_return,
                    COALESCE(wa.qty_wastage,     0)             AS qty_wastage,

                    -- Ideal SOH = On Hand + Purchased - Consumption - Return - Wastage
                    (
                        COALESCE(oh.qty_on_hand,     0)
                      + COALESCE(iw.qty_inward,      0)
                      - COALESCE(co.qty_consumption, 0)
                      - COALESCE(rt.qty_return,      0)
                      - COALESCE(wa.qty_wastage,     0)
                    )                                           AS ideal_soh,

                    -- Actual SOH = Ideal SOH - Variance
                    (
                        COALESCE(oh.qty_on_hand,     0)
                      + COALESCE(iw.qty_inward,      0)
                      - COALESCE(co.qty_consumption, 0)
                      - COALESCE(rt.qty_return,      0)
                      - COALESCE(wa.qty_wastage,     0)
                      - COALESCE(iv.variance,        0)
                    )                                           AS actual_soh,

                    -- Variance from latest confirmed IVR
                    COALESCE(iv.variance, 0)                    AS variance,

                    -- Value = Variance x the product variant's own Cost price.
                    -- Was previously Variance x COG Before Sale (cog_before_sale),
                    -- but that field also adds on labelling/packaging costs on
                    -- top of Cost, which overstates the value of a stock
                    -- shortfall/excess — this is meant to price just the raw
                    -- stock itself, so it should read Cost price directly.
                    -- Deliberately NOT scaled by kg_factor below: this is a
                    -- currency amount (Variance x Cost-per-UoM-unit), already
                    -- correct as computed from the raw, unconverted variance.
                    --
                    -- standard_price (Cost price) is a company-dependent field:
                    -- Postgres stores it as a JSON object keyed by company id
                    -- (e.g. {"1": 2.61}), not a plain column, so it can't be read
                    -- with a simple pp.standard_price. jsonb_each_text unpacks
                    -- that JSON and this pulls out whichever value is set,
                    -- regardless of which company id it happens to be keyed
                    -- under. This report has no per-row company column to look
                    -- up one specific company's cost by (unlike mo_cost_report,
                    -- which keys off the order's own company_id) — if a product
                    -- genuinely had a different Cost price set for more than one
                    -- company, this would arbitrarily use one of them.
                    COALESCE(iv.variance, 0)
                        * COALESCE(
                            (SELECT value::numeric
                             FROM jsonb_each_text(pp.standard_price)
                             LIMIT 1),
                            0
                        )                                       AS variance_value

                FROM product_product pp
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                LEFT JOIN uom_uom     uu ON uu.id = pt.uom_id

                LEFT JOIN onhand      oh ON oh.product_id = pp.id
                LEFT JOIN inward      iw ON iw.product_id = pp.id
                LEFT JOIN consumption co ON co.product_id = pp.id
                LEFT JOIN returns     rt ON rt.product_id = pp.id
                LEFT JOIN wastage     wa ON wa.product_id = pp.id
                LEFT JOIN ivr_variance iv ON iv.product_id = pp.id

                WHERE pp.active = TRUE
            )

            -- ─── Final SELECT: apply the kg display factor ─────────────────────
            SELECT
                id, product_id, product_tmpl_id, categ_id, product_type,
                product_category_type, uom_id, sku,
                qty_on_hand     * kg_factor AS qty_on_hand,
                qty_inward      * kg_factor AS qty_inward,
                qty_consumption * kg_factor AS qty_consumption,
                qty_return      * kg_factor AS qty_return,
                qty_wastage     * kg_factor AS qty_wastage,
                ideal_soh       * kg_factor AS ideal_soh,
                actual_soh      * kg_factor AS actual_soh,
                variance        * kg_factor AS variance,
                variance_value               AS variance_value
            FROM raw

            )
        """ % self._table)
