from odoo import fields, models, tools


# MR-change 9: the 'percentage' widget's x100 + '%' is a display-only trick done by the web
# client - Export (XLSX/CSV) reads the raw stored value and ignores the widget entirely, so
# without this override cogs_percent/gross_margin/discount_percent would export as 0.37 instead
# of the 37 the UI shows. This subclass makes Export match what's on screen (still a plain
# number, e.g. 37 - Excel/CSV cells can't carry a '%' glyph on a usable numeric value).
class PercentageFloat(fields.Float):
    def convert_to_export(self, value, record):
        if not value and value != 0.0:
            return ''
        digits = self.get_digits(record.env)
        return round(value * 100, digits[1] if digits else 2)


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
    # MR-change 1: discount = (MRP x Qty) - Nett(Untaxed)
    discount = fields.Float(string='Discount', readonly=True, digits='Product Price')
    # MR-change 1: discount percentage = Discount / Nett(Untaxed)
    # MR-change 6: same fix as cogs_percent/gross_margin - aggregator=False (recomputed in
    # read_group() below) and stored as a fraction so the 'percentage' widget can display the '%'
    # sign. The negative-value question (why some lines go negative) is still deferred - unchanged here.
    # MR-change 8: rounded to a whole number (0 decimals) instead of 2, same as cogs_percent/gross_margin
    # MR-change 9: PercentageFloat so Export shows the same number as the UI (37, not 0.37)
    # MR-change 10: aggregator must be truthy (not False) or the web client's grouped list view
    # never even asks the server for this field when a group is collapsed, leaving it blank.
    # 'avg' here is a placeholder the client needs to see - the actual value is overwritten by
    # read_group() below with the correct (total Discount / total Nett) computation regardless
    # of what aggregator ORM would have used.
    discount_percent = PercentageFloat(string='Discount %', readonly=True, digits=(16, 0), aggregator='avg')
    # MR-change 2: disable default 'sum' aggregation on this ratio field - grouped values are
    # recomputed in read_group() below as (total COGS / total Nett) * 100, not summed per-line percentages
    # MR-change 4: stored as a fraction (0-1, not 0-100) so the 'percentage' widget can display the
    # '%' sign; the widget multiplies by 100 and rounds using 'digits' for display
    # MR-change 9: PercentageFloat so Export shows the same number as the UI (37, not 0.37)
    # MR-change 10: aggregator must be truthy or collapsed group headers stay blank - see discount_percent
    cogs_percent = PercentageFloat(string='COGS %', readonly=True, digits=(16, 0), aggregator='avg')
    # MR-change 5: same fix as cogs_percent - aggregator=False (recomputed in read_group() below)
    # and stored as a fraction so the 'percentage' widget can display the '%' sign
    # MR-change 7: rounded to a whole number (0 decimals) instead of 2, same as cogs_percent
    # MR-change 9: PercentageFloat so Export shows the same number as the UI (63, not 0.63)
    # MR-change 10: aggregator must be truthy or collapsed group headers stay blank - see discount_percent
    gross_margin = PercentageFloat(string='Gross Margin %', readonly=True, digits=(16, 0), aggregator='avg')
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
                    -- MRP fetched from the sale order line's own Unit Price (sol.price_unit),
                    -- multiplied by qty so it's a line amount like cogs/nett
                    sol.price_unit * sol.product_uom_qty AS mrp,
                    -- MR-change 11: discount = MRP - Nett(Untaxed), using the same MRP basis as the
                    -- 'mrp' column above (sol.price_unit x qty) instead of the old pt.list_price x qty -
                    -- keeps Discount consistent with what's actually shown in the MRP column
                    ((sol.price_unit * sol.product_uom_qty) - sol.price_subtotal) AS discount,
                    -- MR-change 1: discount percentage = Discount / Nett(Untaxed)
                    -- MR-change 6: stored as a fraction (no x100) - the view's 'percentage' widget
                    -- multiplies by 100 and appends '%' for display
                    -- MR-change 11: same MRP-basis fix as discount above
                    CASE
                        WHEN sol.price_subtotal <> 0.0
                        THEN ((sol.price_unit * sol.product_uom_qty) - sol.price_subtotal)
                            / sol.price_subtotal
                        ELSE 0.0
                    END AS discount_percent,
                    -- MR-change 4: stored as a fraction (no x100) - the view's 'percentage' widget
                    -- multiplies by 100 and appends '%' for display
                    CASE
                        WHEN sol.price_subtotal <> 0.0
                        THEN (COALESCE(sol.cogs_unit_price, 0.0) * sol.product_uom_qty)
                            / sol.price_subtotal
                        ELSE 0.0
                    END AS cogs_percent,
                    -- MR-change 5: stored as a fraction (no x100) - the view's 'percentage' widget
                    -- multiplies by 100 and appends '%' for display
                    CASE
                        WHEN sol.price_subtotal <> 0.0
                        THEN (sol.price_subtotal - (
                                COALESCE(sol.cogs_unit_price, 0.0) * sol.product_uom_qty))
                            / sol.price_subtotal
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

    # MR-change 2: recompute COGS % as (total COGS / total Nett) on each group, instead of
    # letting the ORM sum the per-line cogs_percent values (which produced meaningless totals like
    # 1,445.16% when grouped by month).
    # MR-change 5: same fix applied to gross_margin = (total Nett - total COGS) / total Nett.
    # MR-change 6: same fix applied to discount_percent = total Discount / total Nett.
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        requested_names = {f.split(':')[0] for f in fields}
        needs_cogs_percent = 'cogs_percent' in requested_names
        needs_gross_margin = 'gross_margin' in requested_names
        needs_discount_percent = 'discount_percent' in requested_names
        fields = list(fields)
        extra_fields = []
        if needs_cogs_percent or needs_gross_margin or needs_discount_percent:
            for needed in ('cogs', 'nett', 'discount'):
                if needed not in requested_names:
                    fields.append(needed)
                    extra_fields.append(needed)

        result = super().read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

        if needs_cogs_percent or needs_gross_margin or needs_discount_percent:
            for group in result:
                cogs = group.get('cogs') or 0.0
                nett = group.get('nett') or 0.0
                discount = group.get('discount') or 0.0
                # MR-change 4 / MR-change 5 / MR-change 6: stored as a fraction (no x100), matches
                # the 'percentage' widget's expectation
                if needs_cogs_percent:
                    group['cogs_percent'] = cogs / nett if nett else 0.0
                if needs_gross_margin:
                    group['gross_margin'] = (nett - cogs) / nett if nett else 0.0
                if needs_discount_percent:
                    group['discount_percent'] = discount / nett if nett else 0.0
                for extra in extra_fields:
                    group.pop(extra, None)

        return result
