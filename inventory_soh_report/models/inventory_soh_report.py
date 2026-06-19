# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools


class InventorySohReport(models.Model):
    """
    Inventory SOH (Stock on Hand) Report.

    SQL-view-backed read-only model.  Variance is sourced from the LATEST
    confirmed (or reported) inventory.variation session (hk_inventory_variation
    module) for each product, summed across all its lines.

    Columns:
        product_id          : The storable product
        product_tmpl_id     : Product template
        categ_id            : Internal category
        product_type        : pt.type  ('product' / 'consu' / 'storable')
        qty_on_hand         : Current on-hand qty  (stock.quant, internal locs)
        qty_inward          : Total received qty    (incoming pickings, done)
        qty_consumption     : Total delivered/used  (outgoing pickings, done, non-return)
        qty_return          : Qty returned to vendor (outgoing returns, done)
        qty_wastage         : Qty scrapped          (stock.scrap, done)
        ideal_soh           : qty_on_hand + qty_inward - qty_consumption
                              - qty_return - qty_wastage
        variance            : SUM of variation_qty from the LATEST confirmed IVR
                              (physical_qty - theoretical_qty per line)
        actual_soh          : ideal_soh - variance
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

    qty_on_hand = fields.Float(
        string='Current On Hand Qty',
        digits='Product Unit of Measure', readonly=True,
        help='Current quantity physically available in internal locations.')

    qty_inward = fields.Float(
        string='Inward Qty',
        digits='Product Unit of Measure', readonly=True,
        help='Total quantity successfully received into inventory (Receipts).')

    qty_consumption = fields.Float(
        string='Consumption (Used Qty)',
        digits='Product Unit of Measure', readonly=True,
        help='Total quantity consumed / delivered out of inventory.')

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
        help='Ideal SOH = On Hand + Inward - Consumption - Return - Wastage')

    variance = fields.Float(
        string='Variance',
        digits='Product Unit of Measure', readonly=True,
        help='Sum of variation_qty from the latest confirmed Inventory Variation '
             'report (IVR) for this product.  '
             'variation_qty = physical_qty - theoretical_qty per IVR line.')

    actual_soh = fields.Float(
        string='Actual SOH',
        digits='Product Unit of Measure', readonly=True,
        help='Actual SOH = Ideal SOH - Variance')

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

            -- ─── Latest confirmed/reported IVR per product ────────────────────
            --
            --  We pick the single most-recent inventory.variation session
            --  (by date DESC, then id DESC) that is in state confirmed or reported,
            --  and sum the variation_qty lines for each product inside that session.
            --
            --  variation_qty = physical_qty - theoretical_qty  (stored on the line)
            --
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
            )

            -- ─── Final SELECT ─────────────────────────────────────────────────
            SELECT
                pp.id                                   AS id,
                pp.id                                   AS product_id,
                pt.id                                   AS product_tmpl_id,
                pt.categ_id,
                pt.type                                 AS product_type,
                pt.uom_id,

                COALESCE(oh.qty_on_hand,     0)         AS qty_on_hand,
                COALESCE(iw.qty_inward,      0)         AS qty_inward,
                COALESCE(co.qty_consumption, 0)         AS qty_consumption,
                COALESCE(rt.qty_return,      0)         AS qty_return,
                COALESCE(wa.qty_wastage,     0)         AS qty_wastage,

                -- Ideal SOH = On Hand + Inward - Consumption - Return - Wastage
                (
                    COALESCE(oh.qty_on_hand,     0)
                  + COALESCE(iw.qty_inward,      0)
                  - COALESCE(co.qty_consumption, 0)
                  - COALESCE(rt.qty_return,      0)
                  - COALESCE(wa.qty_wastage,     0)
                )                                       AS ideal_soh,

                -- Variance from latest confirmed IVR
                -- (positive = physical was MORE than system; negative = less)
                COALESCE(iv.variance, 0)                AS variance,

                -- Actual SOH = Ideal SOH - Variance
                (
                    COALESCE(oh.qty_on_hand,     0)
                  + COALESCE(iw.qty_inward,      0)
                  - COALESCE(co.qty_consumption, 0)
                  - COALESCE(rt.qty_return,      0)
                  - COALESCE(wa.qty_wastage,     0)
                  - COALESCE(iv.variance,        0)
                )                                       AS actual_soh

            FROM product_product pp
            JOIN product_template pt ON pt.id = pp.product_tmpl_id

            LEFT JOIN onhand      oh ON oh.product_id = pp.id
            LEFT JOIN inward      iw ON iw.product_id = pp.id
            LEFT JOIN consumption co ON co.product_id = pp.id
            LEFT JOIN returns     rt ON rt.product_id = pp.id
            LEFT JOIN wastage     wa ON wa.product_id = pp.id
            LEFT JOIN ivr_variance iv ON iv.product_id = pp.id

            WHERE pt.type IN ('product', 'consu', 'storable')
              AND pp.active = TRUE

            )
        """ % self._table)
