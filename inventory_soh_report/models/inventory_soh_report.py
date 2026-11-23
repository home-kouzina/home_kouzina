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
          products whose Unit of Measure is grams
        - (2026-11-23) every move/scrap quantity is converted to the
          product's own UoM first (e.g. a 300 g MO line on a product in
          Units/kg counts as 0.3). Replaces the old rule that treated any
          product with a gram move as a gram product and divided all its
          columns, including kg stock, by 1000.
        - Weekly count (soh.week):
            * new Opening column = Actual SOH of the last closed week (the
              first week starts from on-hand stock when it was opened)
            * Purchased / Consumption / Return / Wastage now cover only the
              open week (since soh.week.date_start), not all time
            * Ideal SOH = Opening + Purchased - Consumption - Return - Wastage
            * Actual SOH = live on-hand stock (corrected by count uploads)
            * Variance = Actual SOH - Ideal SOH (no longer read from IVR)
            * Manager's weekly flow (2026-11-16): new Produced column (MO
              output); Ideal SOH = Opening + Purchased + Produced -
              Consumption - Return - Wastage; Actual SOH = this week's
              uploaded physical count (0 until counted); Variance only for
              counted products
            * Only Finished Goods and Raw Materials are shown (Retail
              products and Services are left out)
            * Consumption is decided by the move, not the product flag:
              customer deliveries (minus customer returns) + manufacturing
              order component moves. Before, Retail products' sales and MO
              components with an empty is_finished_good flag were never
              counted.
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

    qty_opening = fields.Float(
        string='Opening',
        digits='Product Unit of Measure', readonly=True,
        help='Actual SOH of the last closed week. The first week starts from '
             'the on-hand stock at the moment it was opened.')

    qty_on_hand = fields.Float(
        string='Current On Hand Qty',
        digits='Product Unit of Measure', readonly=True,
        help='Current quantity physically available in internal locations.')

    qty_inward = fields.Float(
        string='Purchased Qty',
        digits='Product Unit of Measure', readonly=True,
        help='Quantity received from vendors (Receipts) during the open week.')

    qty_produced = fields.Float(
        string='Produced',
        digits='Product Unit of Measure', readonly=True,
        help='Quantity made by Manufacturing Orders marked Done during the open week.')

    qty_consumption = fields.Float(
        string='Consumption (Used Qty)',
        digits='Product Unit of Measure', readonly=True,
        help='During the open week: quantity delivered to customers (minus '
             'customer returns) plus quantity consumed as a component in '
             'Manufacturing Orders.')

    qty_return = fields.Float(
        string='Return Qty',
        digits='Product Unit of Measure', readonly=True,
        help='Quantity returned to vendors during the open week.')

    qty_wastage = fields.Float(
        string='Wastage (Scrap)',
        digits='Product Unit of Measure', readonly=True,
        help='Quantity scrapped during the open week.')

    ideal_soh = fields.Float(
        string='Ideal SOH',
        digits='Product Unit of Measure', readonly=True,
        help='Ideal SOH = Opening + Purchased + Produced - Consumption - Return - Wastage')

    actual_soh = fields.Float(
        string='Actual SOH',
        digits='Product Unit of Measure', readonly=True,
        help='Physical count uploaded for this week. 0 until the product is '
             'counted; resets to 0 when the week is closed.')

    variance = fields.Float(
        string='Variance',
        digits='Product Unit of Measure', readonly=True,
        help='Variance = Actual SOH - Ideal SOH, for products counted this '
             'week (0 otherwise). A shortage is negative.')

    is_counted = fields.Boolean(
        string='Counted This Week', readonly=True,
        help='A physical count was uploaded for this product in the open week.')

    # Technical fields used by the weekly count wizard / week closing.
    qty_on_hand_raw = fields.Float(
        string='On Hand (product UoM)', digits='Product Unit of Measure', readonly=True,
        help='On-hand stock in the product\'s own UoM, without kg conversion.')

    kg_factor = fields.Float(
        string='Display Factor', readonly=True,
        help='0.001 when this product\'s quantities are shown in kg instead of grams, else 1.')

    uom_display = fields.Char(
        string='Shown In', readonly=True,
        help='Unit the report quantities are shown in for this product.')

    # Renamed from "Value = Variance x COG Before Sale": COG Before Sale also
    # adds on labelling/packaging costs, which isn't what "Value" is meant to
    # represent here — this is the value of missing/extra stock, so it should
    # only use the product variant's own raw Cost price.
    variance_value = fields.Float(
        string='Value',
        digits='Account', readonly=True,
        help='Value = Variance x the product variant\'s own Cost price. '
             'A shortage is negative.')

    consumption_value = fields.Float(
        string='Consumption$',
        digits='Account', readonly=True,
        help='Consumption$ = Consumption x Cost Price: the cost of what was '
             'used or sold during the open week.')

    product_category_type = fields.Char(
        string='Product Category Type', readonly=True,
        help='Retail if is_retail flag is set; otherwise Finished Good or '
             'Raw Material based on is_finished_good flag.')

    # ── SQL View ──────────────────────────────────────────────────────────────

    def init(self):
        """Drop and recreate the SQL view.

        The view reads the open week from soh_week / soh_week_line, so those
        models must be initialised first (see models/__init__.py order).
        """
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (

            WITH

            -- ─── Open counting week ──────────────────────────────────────────
            --   All movement columns below only count moves done since the
            --   open week started. If no week exists yet (should not happen:
            --   one is created on install), everything since 1970 counts.
            open_week AS (
                SELECT id, date_start
                FROM soh_week
                WHERE state = 'open'
                ORDER BY id DESC
                LIMIT 1
            ),
            week_start AS (
                SELECT COALESCE(
                    (SELECT date_start FROM open_week),
                    TIMESTAMP '1970-01-01'
                ) AS ts
            ),

            -- ─── Opening: stored on the open week's lines (product UoM) ──────
            opening AS (
                SELECT swl.product_id, SUM(swl.opening_raw) AS qty_opening
                FROM soh_week_line swl
                WHERE swl.week_id = (SELECT id FROM open_week)
                GROUP BY swl.product_id
            ),

            -- ─── On-hand quantities from stock.quant (live) ──────────────────
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

            -- ─── Purchased: done vendor receipts this week, non-return ───────
            inward AS (
                SELECT
                    sm.product_id,
                    SUM(sm.quantity / mu.factor * pu.factor) AS qty_inward
                FROM stock_move sm
                JOIN stock_location loc_src  ON loc_src.id  = sm.location_id
                JOIN stock_location loc_dest ON loc_dest.id = sm.location_dest_id
                -- move quantity converted to the product's own UoM (e.g. 300 g -> 0.3 Units/kg)
                JOIN uom_uom mu ON mu.id = sm.product_uom
                JOIN product_product mpp ON mpp.id = sm.product_id
                JOIN product_template mpt ON mpt.id = mpp.product_tmpl_id
                JOIN uom_uom pu ON pu.id = mpt.uom_id
                JOIN stock_picking     sp    ON sp.id       = sm.picking_id
                JOIN stock_picking_type spt  ON spt.id      = sp.picking_type_id
                WHERE sm.state         = 'done'
                  AND sm.date         >= (SELECT ts FROM week_start)
                  AND loc_src.usage   != 'internal'
                  AND loc_dest.usage   = 'internal'
                  AND spt.code         = 'incoming'
                  AND sp.return_id    IS NULL
                  AND (sm.origin IS NULL OR sm.origin NOT ILIKE '%%Return%%')
                  AND loc_src.usage   != 'customer'
                GROUP BY sm.product_id
            ),

            -- ─── Return: done returns to vendor this week ────────────────────
            returns AS (
                SELECT
                    sm.product_id,
                    SUM(sm.quantity / mu.factor * pu.factor) AS qty_return
                FROM stock_move sm
                JOIN stock_location loc_src  ON loc_src.id  = sm.location_id
                JOIN stock_location loc_dest ON loc_dest.id = sm.location_dest_id
                -- move quantity converted to the product's own UoM (e.g. 300 g -> 0.3 Units/kg)
                JOIN uom_uom mu ON mu.id = sm.product_uom
                JOIN product_product mpp ON mpp.id = sm.product_id
                JOIN product_template mpt ON mpt.id = mpp.product_tmpl_id
                JOIN uom_uom pu ON pu.id = mpt.uom_id
                JOIN stock_picking     sp    ON sp.id       = sm.picking_id
                WHERE sm.state         = 'done'
                  AND sm.date         >= (SELECT ts FROM week_start)
                  AND loc_src.usage    = 'internal'
                  AND loc_dest.usage  NOT IN ('internal', 'customer')
                  AND (
                       sm.origin ILIKE '%%Return%%'
                       OR sp.return_id IS NOT NULL
                  )
                GROUP BY sm.product_id
            ),

            -- ─── Consumption: decided by the move, not the product flag ──────
            --   + deliveries to customers (any product type)
            --   - customer returns back into stock
            --   + components consumed in manufacturing orders (any type)
            consumption AS (
                SELECT product_id, SUM(qty) AS qty_consumption
                FROM (
                    -- Deliveries to customers
                    SELECT sm.product_id, sm.quantity / mu.factor * pu.factor AS qty
                    FROM stock_move sm
                    JOIN stock_location loc_src  ON loc_src.id  = sm.location_id
                    JOIN stock_location loc_dest ON loc_dest.id = sm.location_dest_id
                -- move quantity converted to the product's own UoM (e.g. 300 g -> 0.3 Units/kg)
                JOIN uom_uom mu ON mu.id = sm.product_uom
                JOIN product_product mpp ON mpp.id = sm.product_id
                JOIN product_template mpt ON mpt.id = mpp.product_tmpl_id
                JOIN uom_uom pu ON pu.id = mpt.uom_id
                    WHERE sm.state        = 'done'
                      AND sm.date        >= (SELECT ts FROM week_start)
                      AND loc_src.usage   = 'internal'
                      AND loc_dest.usage  = 'customer'

                    UNION ALL

                    -- Customer returns (subtracted)
                    SELECT sm.product_id, -(sm.quantity / mu.factor * pu.factor) AS qty
                    FROM stock_move sm
                    JOIN stock_location loc_src  ON loc_src.id  = sm.location_id
                    JOIN stock_location loc_dest ON loc_dest.id = sm.location_dest_id
                -- move quantity converted to the product's own UoM (e.g. 300 g -> 0.3 Units/kg)
                JOIN uom_uom mu ON mu.id = sm.product_uom
                JOIN product_product mpp ON mpp.id = sm.product_id
                JOIN product_template mpt ON mpt.id = mpp.product_tmpl_id
                JOIN uom_uom pu ON pu.id = mpt.uom_id
                    WHERE sm.state        = 'done'
                      AND sm.date        >= (SELECT ts FROM week_start)
                      AND loc_src.usage   = 'customer'
                      AND loc_dest.usage  = 'internal'

                    UNION ALL

                    -- Components consumed in manufacturing orders
                    SELECT sm.product_id, sm.quantity / mu.factor * pu.factor AS qty
                    FROM stock_move sm
                    JOIN stock_location loc_src  ON loc_src.id  = sm.location_id
                    JOIN stock_location loc_dest ON loc_dest.id = sm.location_dest_id
                -- move quantity converted to the product's own UoM (e.g. 300 g -> 0.3 Units/kg)
                JOIN uom_uom mu ON mu.id = sm.product_uom
                JOIN product_product mpp ON mpp.id = sm.product_id
                JOIN product_template mpt ON mpt.id = mpp.product_tmpl_id
                JOIN uom_uom pu ON pu.id = mpt.uom_id
                    WHERE sm.state        = 'done'
                      AND sm.date        >= (SELECT ts FROM week_start)
                      AND loc_src.usage   = 'internal'
                      AND loc_dest.usage  = 'production'
                      AND sm.raw_material_production_id IS NOT NULL
                ) sub
                GROUP BY product_id
            ),

            -- ─── Produced: finished products of MOs done this week ───────────
            produced AS (
                SELECT
                    sm.product_id,
                    SUM(sm.quantity / mu.factor * pu.factor) AS qty_produced
                FROM stock_move sm
                JOIN stock_location loc_src  ON loc_src.id  = sm.location_id
                JOIN stock_location loc_dest ON loc_dest.id = sm.location_dest_id
                -- move quantity converted to the product's own UoM (e.g. 300 g -> 0.3 Units/kg)
                JOIN uom_uom mu ON mu.id = sm.product_uom
                JOIN product_product mpp ON mpp.id = sm.product_id
                JOIN product_template mpt ON mpt.id = mpp.product_tmpl_id
                JOIN uom_uom pu ON pu.id = mpt.uom_id
                WHERE sm.state         = 'done'
                  AND sm.date         >= (SELECT ts FROM week_start)
                  AND sm.production_id IS NOT NULL
                  AND loc_src.usage    = 'production'
                  AND loc_dest.usage   = 'internal'
                GROUP BY sm.product_id
            ),

            -- ─── Physical count uploaded this week (product UoM) ─────────────
            counted AS (
                SELECT swl.product_id, SUM(swl.counted_raw) AS counted_raw
                FROM soh_week_line swl
                WHERE swl.week_id = (SELECT id FROM open_week)
                  AND swl.is_counted = TRUE
                GROUP BY swl.product_id
            ),

            -- ─── Wastage: done scraps this week ──────────────────────────────
            wastage AS (
                SELECT
                    ss.product_id,
                    SUM(ss.scrap_qty / su.factor * pu.factor) AS qty_wastage
                FROM stock_scrap ss
                -- scrap quantity converted to the product's own UoM
                JOIN uom_uom su ON su.id = ss.product_uom_id
                JOIN product_product spp ON spp.id = ss.product_id
                JOIN product_template spt ON spt.id = spp.product_tmpl_id
                JOIN uom_uom pu ON pu.id = spt.uom_id
                WHERE ss.state = 'done'
                  AND ss.date_done >= (SELECT ts FROM week_start)
                GROUP BY ss.product_id
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

                    -- Report-display kg conversion: every quantity above is
                    -- already in the product's own UoM, so only products whose
                    -- UoM is "g" are shown in kg (x 0.001). Display only.
                    CASE
                        WHEN uu.name->>'en_US' = 'g' THEN 0.001
                        ELSE 1
                    END                                         AS kg_factor,
                    CASE
                        WHEN uu.name->>'en_US' = 'g' THEN 'kg'
                        ELSE uu.name->>'en_US'
                    END                                         AS uom_display,

                    -- Cost price is per product UoM and every quantity is now
                    -- in the product UoM, so no extra factor is needed.
                    1                                           AS cost_qty_factor,

                    COALESCE(op.qty_opening,     0)             AS qty_opening,
                    COALESCE(oh.qty_on_hand,     0)             AS qty_on_hand,
                    COALESCE(iw.qty_inward,      0)             AS qty_inward,
                    COALESCE(pr.qty_produced,    0)             AS qty_produced,
                    COALESCE(co.qty_consumption, 0)             AS qty_consumption,
                    COALESCE(rt.qty_return,      0)             AS qty_return,
                    COALESCE(wa.qty_wastage,     0)             AS qty_wastage,

                    -- Ideal SOH = Opening + Purchased + Produced
                    --             - Consumption - Return - Wastage
                    (
                        COALESCE(op.qty_opening,     0)
                      + COALESCE(iw.qty_inward,      0)
                      + COALESCE(pr.qty_produced,    0)
                      - COALESCE(co.qty_consumption, 0)
                      - COALESCE(rt.qty_return,      0)
                      - COALESCE(wa.qty_wastage,     0)
                    )                                           AS ideal_soh,

                    -- Actual SOH = this week's physical count (0 if not counted)
                    (ct.product_id IS NOT NULL)                 AS is_counted,
                    COALESCE(ct.counted_raw, 0)                 AS actual_soh,

                    -- standard_price (Cost price) is company-dependent and
                    -- stored as JSON keyed by company id; take whichever value
                    -- is set (see CHANGES.md for the multi-company caveat).
                    COALESCE(
                        (SELECT value::numeric
                         FROM jsonb_each_text(pp.standard_price)
                         LIMIT 1),
                        0
                    )                                           AS cost_price

                FROM product_product pp
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                LEFT JOIN uom_uom     uu ON uu.id = pt.uom_id

                LEFT JOIN opening     op ON op.product_id = pp.id
                LEFT JOIN onhand      oh ON oh.product_id = pp.id
                LEFT JOIN inward      iw ON iw.product_id = pp.id
                LEFT JOIN produced    pr ON pr.product_id = pp.id
                LEFT JOIN counted     ct ON ct.product_id = pp.id
                LEFT JOIN consumption co ON co.product_id = pp.id
                LEFT JOIN returns     rt ON rt.product_id = pp.id
                LEFT JOIN wastage     wa ON wa.product_id = pp.id

                WHERE pp.active = TRUE
                  -- Only Finished Goods and Raw Materials: Retail products
                  -- ("Is Retail" ticked) and Services are left out.
                  AND pt.is_retail IS NOT TRUE
                  AND pt.type <> 'service'
            )

            -- ─── Final SELECT: variance, value and the kg display factor ──────
            SELECT
                id, product_id, product_tmpl_id, categ_id, product_type,
                product_category_type, uom_id, sku, kg_factor, uom_display,
                is_counted,
                qty_on_hand                       AS qty_on_hand_raw,
                qty_opening     * kg_factor       AS qty_opening,
                qty_on_hand     * kg_factor       AS qty_on_hand,
                qty_inward      * kg_factor       AS qty_inward,
                qty_produced    * kg_factor       AS qty_produced,
                qty_consumption * kg_factor       AS qty_consumption,
                qty_return      * kg_factor       AS qty_return,
                qty_wastage     * kg_factor       AS qty_wastage,
                ideal_soh       * kg_factor       AS ideal_soh,
                actual_soh      * kg_factor       AS actual_soh,
                -- Variance only for products counted this week, rounded to the
                -- 3 decimals the report and the count file show.
                CASE WHEN is_counted
                     THEN ROUND(((actual_soh - ideal_soh) * kg_factor)::numeric, 3)
                     ELSE 0 END                   AS variance,
                -- Value = Variance x Cost, on the unconverted quantity
                -- (Cost is per product UoM). Not scaled by kg_factor.
                CASE WHEN is_counted
                     THEN ROUND(((actual_soh - ideal_soh) * kg_factor)::numeric, 3)
                          / kg_factor * cost_qty_factor * cost_price
                     ELSE 0 END                   AS variance_value,
                -- Consumption$ = Consumption x Cost
                qty_consumption * cost_qty_factor * cost_price AS consumption_value
            FROM raw

            )
        """ % self._table)
