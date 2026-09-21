# -*- coding: utf-8 -*-
from odoo import models, fields, tools


class MoRawMaterialConsumption(models.Model):
    """
    MO-wise Raw Material Consumption.

    Standalone report — does not read from, write to, or otherwise touch
    inventory.soh.report (Inventory SOH Report) or mo.cost.report
    (MO Cost Report) in any way.

    One row per (raw material, Manufacturing Order): how much of that raw
    material was consumed as a component in that specific done MO, plus
    the MO's own number and Production Date. Because the grain is one row
    per MO (not one row per product), Production Date can be grouped by
    month like any normal Odoo report — that's not possible on Inventory
    SOH Report, which is one row per product with no date anywhere on it.

    Deliberately does NOT include On Hand, Purchased, Return, Wastage,
    Ideal SOH, Actual SOH, Variance or Value. Those are lifetime totals
    for the product as a whole, not something that happened "at" a
    specific MO — there is no accurate way to show them on a per-MO row:
    repeating the same product-level number on every one of that
    product's MO rows would silently overcount if anyone summed the
    column (e.g. a product with 56 MOs would have its On Hand added up
    56 times instead of once). Leaving this report to just Qty Consumed
    — the one column that genuinely has a real, distinct value per MO —
    was a deliberate accuracy decision, not an oversight.

    Reuses the exact same "raw material consumption" definition already
    used by inventory_soh_report's own `consumption` CTE (done stock
    moves, from an internal location to a non-internal one, linked to a
    Manufacturing Order's component consumption, on a product that isn't
    a finished good) — just grouped by (product, MO) instead of summed to
    one lifetime total. Also applies the same gram→kg display conversion
    inventory_soh_report uses, for consistency between reports.
    """

    _name = 'mo.raw.material.consumption'
    _description = 'MO-wise Raw Material Consumption'
    _auto = False
    _rec_name = 'mo_name'
    _order = 'production_date desc, mo_name'

    mo_id = fields.Many2one(
        'mrp.production', string='Manufacturing Order', readonly=True)

    mo_name = fields.Char(
        string='MO Number', readonly=True)

    production_date = fields.Datetime(
        string='Production Date', readonly=True,
        help='The Manufacturing Order\'s own Production Date '
             '(mrp.production.date_start) — same field/label MO Cost '
             'Report uses, for consistency between reports.')

    product_id = fields.Many2one(
        'product.product', string='Raw Material', readonly=True)

    product_tmpl_id = fields.Many2one(
        'product.template', string='Product Template', readonly=True)

    categ_id = fields.Many2one(
        'product.category', string='Product Category', readonly=True)

    uom_id = fields.Many2one(
        'uom.uom', string='Unit of Measure', readonly=True)

    sku = fields.Char(
        string='SKU', readonly=True,
        help='Internal Reference (SKU) of the product.')

    qty_consumed = fields.Float(
        string='Qty Consumed',
        digits='Product Unit of Measure', readonly=True,
        help='Quantity of this raw material consumed as a component in '
             'this specific Manufacturing Order. Shown in kg instead of '
             'grams for any product whose Unit of Measure is grams, '
             'matching Inventory SOH Report\'s convention.')

    def init(self):
        """Drop and recreate the SQL view."""
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (

            WITH

            -- ─── Raw materials: components consumed in manufacturing orders,
            --     grouped by (product, MO) instead of summed to one lifetime
            --     total — one row per MO instead of one row per product ────
            consumption AS (
                SELECT
                    sm.raw_material_production_id  AS mo_id,
                    sm.product_id,
                    SUM(sm.quantity)                AS qty_consumed
                FROM stock_move sm
                JOIN stock_location loc_src  ON loc_src.id  = sm.location_id
                JOIN stock_location loc_dest ON loc_dest.id = sm.location_dest_id
                JOIN product_product pp2     ON pp2.id      = sm.product_id
                WHERE sm.state        = 'done'
                  AND loc_src.usage   = 'internal'
                  AND loc_dest.usage != 'internal'
                  AND sm.raw_material_production_id IS NOT NULL
                  AND pp2.is_finished_good = FALSE
                GROUP BY sm.raw_material_production_id, sm.product_id
            )

            -- ─── Final SELECT: attach MO + product info, apply kg factor ───
            SELECT
                row_number() OVER (ORDER BY c.mo_id, c.product_id)  AS id,
                c.mo_id                                     AS mo_id,
                mp.name                                     AS mo_name,
                mp.date_start                               AS production_date,
                pp.id                                       AS product_id,
                pt.id                                       AS product_tmpl_id,
                pt.categ_id,
                pt.uom_id,
                COALESCE(pp.default_code, pt.default_code)  AS sku,

                -- Same gram→kg report-display conversion used by
                -- Inventory SOH Report: 1 unless the product's UoM is
                -- grams, in which case 0.001 (so 45g reads as 0.045).
                c.qty_consumed
                    * CASE WHEN uu.name->>'en_US' = 'g' THEN 0.001 ELSE 1 END
                                                             AS qty_consumed

            FROM consumption c
            JOIN mrp_production    mp ON mp.id = c.mo_id
            JOIN product_product   pp ON pp.id = c.product_id
            JOIN product_template  pt ON pt.id = pp.product_tmpl_id
            LEFT JOIN uom_uom      uu ON uu.id = pt.uom_id

            )
        """ % self._table)
