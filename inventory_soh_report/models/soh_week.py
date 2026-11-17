# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SohWeek(models.Model):
    """
    One counting week of the Inventory SOH Report.

    Exactly one week is 'open' at a time. The live Inventory SOH Report reads
    the open week's start time (to limit Purchased / Consumption / Return /
    Wastage to this week) and its Opening quantities (stored on the lines).

    When the week is closed, the full report is frozen into the lines, and a
    new open week starts immediately, with the closed week's Actual SOH as
    its Opening.
    """

    _name = 'soh.week'
    _description = 'SOH Weekly Count'
    _order = 'date_start desc, id desc'

    name = fields.Char(string='Week', required=True, readonly=True)
    date_start = fields.Datetime(string='Started On', required=True, readonly=True)
    date_end = fields.Datetime(string='Closed On', readonly=True)
    state = fields.Selection(
        [('open', 'Open'), ('closed', 'Closed')],
        string='Status', default='open', required=True, readonly=True)
    closed_by_id = fields.Many2one('res.users', string='Closed By', readonly=True)
    line_ids = fields.One2many('soh.week.line', 'week_id', string='Report Lines', readonly=True)
    upload_log_ids = fields.One2many('soh.upload.log', 'week_id', string='Uploads', readonly=True)
    changed_count = fields.Integer(
        string='Products Changed by Count', readonly=True,
        help='Number of products whose stock was corrected by a physical count upload in this week.')
    total_value = fields.Float(string='Total Value', digits='Account', readonly=True,
                               help='Sum of Value (Variance x Cost) for the week, frozen when the week was closed.')

    # ── Helpers ───────────────────────────────────────────────────────────────

    @api.model
    def _get_open_week(self):
        return self.search([('state', '=', 'open')], order='id desc', limit=1)

    @api.model
    def _week_name(self, dt):
        local = fields.Datetime.context_timestamp(self, dt)
        iso_year, iso_week, _weekday = local.isocalendar()
        base = _('Week %(week)s - %(year)s', week=iso_week, year=iso_year)
        name, n = base, 2
        while self.search_count([('name', '=', name)]):
            name = '%s (%s)' % (base, n)
            n += 1
        return name

    @api.model
    def _current_on_hand_raw(self):
        """Current on-hand per product in the product's own UoM, summed over
        all internal locations — the same figure the report uses."""
        self.env.flush_all()
        self.env.cr.execute("""
            SELECT sq.product_id, SUM(sq.quantity)
            FROM stock_quant sq
            JOIN stock_location sl ON sl.id = sq.location_id
            WHERE sl.usage = 'internal' AND sq.company_id IS NOT NULL
            GROUP BY sq.product_id
        """)
        return dict(self.env.cr.fetchall())

    @api.model
    def _create_open_week(self, opening_by_product, date_start=None):
        date_start = date_start or fields.Datetime.now()
        week = self.create({
            'name': self._week_name(date_start),
            'date_start': date_start,
            'state': 'open',
        })
        # Only the products the Inventory SOH Report shows: active Finished
        # Goods and Raw Materials (no Retail, no Services).
        products = self.env['product.product'].browse(
            [pid for pid, qty in opening_by_product.items() if qty]).exists().filtered(
            lambda p: p.active and not p.product_tmpl_id.is_retail and p.type != 'service')
        self.env['soh.week.line'].create([{
            'week_id': week.id,
            'product_id': product.id,
            'opening_raw': opening_by_product[product.id],
        } for product in products])
        self.env.flush_all()
        return week

    @api.model
    def _ensure_open_week(self):
        """Called on module install/upgrade: make sure an open week exists.
        The first week starts now, with today's on-hand stock as its Opening."""
        week = self._get_open_week()
        if not week:
            week = self._create_open_week(self._current_on_hand_raw())
        return week

    def action_view_lines(self):
        """Open the week's report lines as a full list (search, group, export)."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.name,
            'res_model': 'soh.week.line',
            'view_mode': 'list',
            'views': [(self.env.ref('inventory_soh_report.view_soh_week_line_list').id, 'list')],
            'search_view_id': [self.env.ref('inventory_soh_report.view_soh_week_line_search').id, 'search'],
            'domain': [('week_id', '=', self.id)],
            'context': {'create': False},
        }

    # ── Called from the report's buttons ─────────────────────────────────────

    @api.model
    def get_open_week_info(self):
        week = self._ensure_open_week()
        start = fields.Datetime.context_timestamp(self, week.date_start)
        return {
            'id': week.id,
            'name': week.name,
            'start': start.strftime('%d %b %Y, %H:%M'),
            # Close Week is offered only once a count has been applied this week.
            'has_upload': bool(week.upload_log_ids.filtered(lambda l: l.result == 'applied')),
        }

    @api.model
    def action_close_current_week(self):
        """Freeze the live report into the open week, close it, and start the
        next week with this week's Actual SOH as Opening."""
        week = self._get_open_week()
        if not week:
            raise UserError(_('There is no open week to close.'))
        if not week.upload_log_ids.filtered(lambda l: l.result == 'applied'):
            raise UserError(_('Upload the physical inventory for %s before closing the week.', week.name))

        # The report is a SQL view: flush and drop cached rows so the frozen
        # copy and the next Opening use the current stock.
        self.env.flush_all()
        self.env['inventory.soh.report'].invalidate_model()
        rows = self.env['inventory.soh.report'].search([])

        existing = {line.product_id.id: line for line in week.line_ids}
        next_opening = {}
        create_vals = []
        for row in rows:
            vals = {
                'sku': row.sku,
                'categ_id': row.categ_id.id,
                'product_category_type': row.product_category_type,
                'uom_name': row.uom_display,
                'qty_opening': row.qty_opening,
                'qty_inward': row.qty_inward,
                'qty_produced': row.qty_produced,
                'qty_consumption': row.qty_consumption,
                'qty_return': row.qty_return,
                'qty_wastage': row.qty_wastage,
                'ideal_soh': row.ideal_soh,
                'actual_soh': row.actual_soh,
                'variance': row.variance,
                'variance_value': row.variance_value,
                'consumption_value': row.consumption_value,
            }
            line = existing.get(row.product_id.id)
            if line:
                line.write(vals)
            else:
                vals.update({'week_id': week.id, 'product_id': row.product_id.id, 'opening_raw': 0.0})
                create_vals.append(vals)
            if row.qty_on_hand_raw:
                next_opening[row.product_id.id] = row.qty_on_hand_raw
        if create_vals:
            self.env['soh.week.line'].create(create_vals)
        # History must match the report row for row: drop lines of products
        # that are no longer in the report (e.g. archived during the week).
        week.line_ids.filtered(lambda l: l.product_id not in rows.product_id).unlink()

        applied_logs = week.upload_log_ids.filtered(lambda l: l.result == 'applied')
        now = fields.Datetime.now()
        week.write({
            'state': 'closed',
            'date_end': now,
            'closed_by_id': self.env.user.id,
            'changed_count': len(applied_logs.line_ids.product_id),
            'total_value': sum(rows.mapped('variance_value')),
        })
        new_week = self._create_open_week(next_opening, date_start=now)
        return {'closed': week.name, 'opened': new_week.name}


class SohWeekLine(models.Model):
    """
    One product row of a week.

    While the week is open, `opening_raw` and the uploaded count
    (`is_counted` / `counted_raw`) are read by the live report's SQL view. When the week is closed, the full report row is
    copied in, so history shows the report exactly as it was.
    """

    _name = 'soh.week.line'
    _description = 'SOH Weekly Count Line'
    _order = 'week_id desc, product_id'

    week_id = fields.Many2one('soh.week', string='Week', required=True, ondelete='cascade', index=True)
    week_state = fields.Selection(related='week_id.state', string='Week Status')
    # Used by "SOH History by Product" to group rows by the month the week closed.
    week_closed_on = fields.Datetime(related='week_id.date_end', string='Week Closed On', store=True)
    product_id = fields.Many2one('product.product', string='Product', required=True, index=True)
    sku = fields.Char(string='SKU')
    categ_id = fields.Many2one('product.category', string='Category')
    product_category_type = fields.Char(string='Type of Product')
    uom_name = fields.Char(string='UoM')

    # Opening in the product's own stored UoM (not converted to kg). Used by
    # the live report while this week is open.
    opening_raw = fields.Float(string='Opening (product UoM)', digits='Product Unit of Measure')

    # Physical count uploaded this week (written by the count upload). The
    # live report shows it as Actual SOH; products not counted show 0.
    is_counted = fields.Boolean(string='Counted', default=False)
    counted_raw = fields.Float(string='Counted (product UoM)', digits='Product Unit of Measure')

    # Frozen report values (as displayed in the report, kg for gram products)
    qty_opening = fields.Float(string='Opening', digits='Product Unit of Measure')
    qty_inward = fields.Float(string='Purchased', digits='Product Unit of Measure')
    qty_produced = fields.Float(string='Produced', digits='Product Unit of Measure')
    qty_consumption = fields.Float(string='Consumption', digits='Product Unit of Measure')
    qty_return = fields.Float(string='Return', digits='Product Unit of Measure')
    qty_wastage = fields.Float(string='Wastage', digits='Product Unit of Measure')
    ideal_soh = fields.Float(string='Ideal SOH', digits='Product Unit of Measure')
    actual_soh = fields.Float(string='Actual SOH', digits='Product Unit of Measure')
    variance = fields.Float(string='Variance', digits='Product Unit of Measure')
    variance_value = fields.Float(string='Value', digits='Account')
    consumption_value = fields.Float(string='Consumption$', digits='Account')
