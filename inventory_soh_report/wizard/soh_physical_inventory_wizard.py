# -*- coding: utf-8 -*-
import base64
import io
from collections import OrderedDict
from datetime import datetime

import xlsxwriter

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_is_zero

try:
    import openpyxl
except ImportError:  # pragma: no cover
    openpyxl = None


# Columns of the downloaded count file: only what the store needs to count.
# "ID" is hidden and is how rows are matched back to products on upload;
# only "Physical Inventory" is read back. It downloads pre-filled with each
# product's Ideal SOH: the store changes only the rows where the count is
# different. On upload every filled row is taken as the count (unchanged
# rows = counted equal to Ideal, so Variance 0). A cleared cell is skipped.
# Products that do not track stock (not storable) download blank.
COUNT_COLUMN = 'Physical Inventory'
COLUMNS = [
    ('ID', 8),
    ('SKU', 18),
    ('Product', 55),
    (COUNT_COLUMN, 18),
]
# Files downloaded before this change named the count column "Actual SOH".
COUNT_COLUMN_OLD = 'Actual SOH'
SHEET_DATA = 'SOH'
SHEET_META = '_meta'
MAX_ERRORS_SHOWN = 20


class SohPhysicalInventoryWizard(models.TransientModel):
    """
    Upload Physical Inventory.

    1. Download Inventory: an Excel count sheet (SKU, Product, UoM and a
       Physical Inventory column pre-filled with Ideal SOH). A soh.download
       record ties the file to the open week and keeps the values written.
    2. Upload Inventory: the same file after the count. Every filled cell
       is a count (unchanged = equal to Ideal); blank cells are skipped.
    3. Confirm: for each counted product the count is saved on the week
       (shown as Actual SOH in the report) and Odoo stock is set to the
       counted quantity through standard inventory adjustments.
    """

    _name = 'soh.physical.inventory.wizard'
    _description = 'Upload Physical Inventory'

    week_id = fields.Many2one(
        'soh.week', string='Week', readonly=True,
        default=lambda self: self.env['soh.week']._ensure_open_week())
    week_name = fields.Char(related='week_id.name', string='Week Name')
    week_start = fields.Datetime(related='week_id.date_start', string='Week Started On')
    state = fields.Selection(
        [('start', 'Start'), ('preview', 'Preview')], default='start', required=True)
    upload_file = fields.Binary(string='Count File')
    upload_filename = fields.Char(string='File Name')
    download_id = fields.Many2one('soh.download', string='Downloaded File', readonly=True)
    rows_read = fields.Integer(string='Rows Read', readonly=True)
    rows_changed = fields.Integer(string='Products Counted', readonly=True)
    rows_unchanged = fields.Integer(string='Left Blank (skipped)', readonly=True)
    error_text = fields.Text(string='Problems Found', readonly=True)
    line_ids = fields.One2many('soh.physical.inventory.wizard.line', 'wizard_id', string='Counted Rows')
    # Only the rows whose value was changed in the file, for the preview list.
    edited_line_ids = fields.One2many('soh.physical.inventory.wizard.line', 'wizard_id',
                                      string='Changed Rows', domain=[('is_edited', '=', True)])
    rows_edited = fields.Integer(string='Changed in File', readonly=True)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _reopen(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Upload Physical Inventory'),
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
        }

    def _reject(self, message, rows_read=0):
        """Log a rejected upload, show the problem in the wizard, save nothing."""
        self.ensure_one()
        self.env['soh.upload.log'].create({
            'week_id': self.week_id.id,
            'file_data': self.upload_file,
            'file_name': self.upload_filename,
            'rows_read': rows_read,
            'rows_changed': 0,
            'result': 'rejected',
            'note': message,
        })
        self.line_ids.unlink()
        self.write({
            'state': 'preview',
            'error_text': message,
            'rows_read': rows_read,
            'rows_changed': 0,
            'rows_unchanged': 0,
        })
        return self._reopen()

    @api.model
    def _report_rows(self, product_ids=None):
        # The report is a SQL view over stock data: flush pending writes and
        # drop cached rows so it is read fresh from the database.
        self.env.flush_all()
        self.env['inventory.soh.report'].invalidate_model()
        domain = [('product_id', 'in', product_ids)] if product_ids is not None else []
        # The report covers every company's products (as the SOH report
        # always has). Read product names/categories as superuser so a user
        # with only some companies selected doesn't hit an access error on
        # the few products that belong to another company.
        return self.env['inventory.soh.report'].search(domain).sudo()

    # ── 1. Download ───────────────────────────────────────────────────────────

    def action_download(self):
        self.ensure_one()
        week = self.env['soh.week']._ensure_open_week()
        rows = self._report_rows()

        download = self.env['soh.download'].create({
            'week_id': week.id,
            'line_ids': [(0, 0, {
                'product_id': row.product_id.id,
                'actual_soh': round(row.ideal_soh, 3),
                'kg_factor': row.kg_factor or 1.0,
            }) for row in rows],
        })

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet(SHEET_DATA)
        fmt_head = workbook.add_format({
            'bold': True, 'bg_color': '#E9ECEF', 'border': 1,
            'text_wrap': True, 'valign': 'vcenter'})
        fmt_head_count = workbook.add_format({
            'bold': True, 'bg_color': '#FFD966', 'border': 1,
            'text_wrap': True, 'valign': 'vcenter'})
        fmt_count = workbook.add_format({'num_format': '0.000', 'bg_color': '#FFF2CC'})

        for col, (title, width) in enumerate(COLUMNS):
            sheet.write(0, col, title, fmt_head_count if title == COUNT_COLUMN else fmt_head)
            sheet.set_column(col, col, width, None, {'hidden': title == 'ID'})
        sheet.set_row(0, 30)

        for r, row in enumerate(rows, start=1):
            sheet.write_number(r, 0, row.product_id.id)
            sheet.write_string(r, 1, row.sku or '')
            sheet.write_string(r, 2, row.product_id.display_name or '')
            if row.product_id.is_storable:
                sheet.write_number(r, 3, round(row.ideal_soh, 3), fmt_count)
            else:
                sheet.write_blank(r, 3, None, fmt_count)  # stock not tracked

        sheet.freeze_panes(1, 3)
        sheet.autofilter(0, 0, max(len(rows), 1), len(COLUMNS) - 1)

        meta = workbook.add_worksheet(SHEET_META)
        meta.write(0, 0, 'download_id')
        meta.write_number(0, 1, download.id)
        meta.write(1, 0, 'week_id')
        meta.write_number(1, 1, week.id)
        meta.write(2, 0, 'week')
        meta.write(2, 1, week.name)
        meta.hide()
        workbook.close()

        file_name = 'Inventory_SOH_%s.xlsx' % week.name.replace(' ', '_')
        attachment = self.env['ir.attachment'].create({
            'name': file_name,
            'datas': base64.b64encode(output.getvalue()),
            'res_model': 'soh.download',
            'res_id': download.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        self.download_id = download
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'download',
        }

    # ── 2. Upload and check ───────────────────────────────────────────────────

    def action_preview(self):
        self.ensure_one()
        if not self.upload_file:
            raise UserError(_('Choose the count file first.'))
        if openpyxl is None:
            raise UserError(_('The Python library openpyxl is not installed on the server.'))

        week = self.env['soh.week']._ensure_open_week()
        self.week_id = week

        try:
            workbook = openpyxl.load_workbook(
                io.BytesIO(base64.b64decode(self.upload_file)), read_only=True, data_only=True)
        except Exception:
            return self._reject(_('The file could not be read. Upload the .xlsx file that '
                                  'Download Inventory gave you.'))

        if SHEET_META not in workbook.sheetnames or SHEET_DATA not in workbook.sheetnames:
            return self._reject(_('This file was not downloaded from Upload Physical Inventory. '
                                  'Press Download Inventory, fill in Physical Inventory and upload that file.'))

        meta = {row[0]: row[1] for row in workbook[SHEET_META].iter_rows(values_only=True)
                if row and row[0]}
        try:
            download = self.env['soh.download'].browse(int(meta.get('download_id') or 0)).exists()
        except (TypeError, ValueError):
            download = self.env['soh.download']
        if not download:
            return self._reject(_('The download this file came from could not be found. '
                                  'Download the file again.'))
        if download.week_id != week:
            return self._reject(_(
                'This file was downloaded for %(file_week)s, which is already closed. '
                'Download the file again for %(week)s.',
                file_week=download.week_id.name, week=week.name))

        rows_iter = workbook[SHEET_DATA].iter_rows(values_only=True)
        header = next(rows_iter, None) or ()
        index = {str(h).strip(): i for i, h in enumerate(header) if h is not None}
        count_col = COUNT_COLUMN if COUNT_COLUMN in index else COUNT_COLUMN_OLD
        if 'ID' not in index or count_col not in index:
            return self._reject(_('The ID or Physical Inventory column is missing. '
                                  'Do not rename or delete columns in the file.'))
        i_id, i_qty = index['ID'], index[count_col]

        downloaded = {line.product_id.id: line for line in download.line_ids}
        counted = OrderedDict()
        errors = []
        rows_read = 0
        for row_no, row in enumerate(rows_iter, start=2):
            if not row or all(v in (None, '') for v in row):
                continue
            rows_read += 1
            raw_id = row[i_id] if len(row) > i_id else None
            raw_qty = row[i_qty] if len(row) > i_qty else None
            try:
                product_id = int(raw_id)
            except (TypeError, ValueError):
                errors.append(_('Row %(row)s: the hidden ID cell is empty or was changed.', row=row_no))
                continue
            if product_id not in downloaded:
                errors.append(_('Row %(row)s: product ID %(id)s is not in the downloaded report.',
                                row=row_no, id=product_id))
                continue
            if product_id in counted:
                errors.append(_('Row %(row)s: this product appears more than once.', row=row_no))
                continue
            if raw_qty is None or (isinstance(raw_qty, str) and not raw_qty.strip()):
                continue  # blank = not counted this time
            try:
                qty = float(raw_qty)
            except (TypeError, ValueError):
                errors.append(_('Row %(row)s: Physical Inventory "%(value)s" is not a number.',
                                row=row_no, value=raw_qty))
                continue
            # A negative count is only accepted when it is the Ideal SOH that
            # was downloaded and left unchanged (stock already negative).
            if qty < 0 and round(qty, 3) != round(downloaded[product_id].actual_soh, 3):
                errors.append(_('Row %(row)s: Physical Inventory cannot be negative.', row=row_no))
                continue
            product = downloaded[product_id].product_id.sudo()
            if not product.is_storable:
                errors.append(_(
                    'Row %(row)s: %(product)s does not track stock in Odoo (not a storable '
                    'product), so it cannot be counted. Leave its Physical Inventory blank.',
                    row=row_no, product=product.display_name))
                continue
            counted[product_id] = qty

        if errors:
            shown = errors[:MAX_ERRORS_SHOWN]
            if len(errors) > MAX_ERRORS_SHOWN:
                shown.append(_('…and %(n)s more problems.', n=len(errors) - MAX_ERRORS_SHOWN))
            return self._reject(
                _('Nothing was saved. Fix these rows and upload again:') + '\n' + '\n'.join(shown),
                rows_read=rows_read)

        changed = list(counted)
        live = {row.product_id.id: row for row in self._report_rows(changed)} if changed else {}
        # A row left as downloaded means "counted equal to Ideal SOH". The file
        # only shows 3 decimals, so use the exact Ideal SOH for it; otherwise
        # rounding would leave a tiny false variance.
        edited = set()
        for pid in changed:
            if pid in live and round(counted[pid], 3) == round(downloaded[pid].actual_soh, 3):
                counted[pid] = live[pid].ideal_soh
            else:
                edited.add(pid)

        self.line_ids.unlink()
        self.write({
            'state': 'preview',
            'error_text': False,
            'download_id': download.id,
            'rows_read': rows_read,
            'rows_changed': len(changed),
            'rows_unchanged': rows_read - len(changed),
            'rows_edited': len(edited),
            'line_ids': [(0, 0, {
                'product_id': pid,
                'product_name': live[pid].product_id.display_name if pid in live else str(pid),
                'uom_name': live[pid].uom_display if pid in live else '',
                'kg_factor': downloaded[pid].kg_factor or 1.0,
                'downloaded_qty': live[pid].qty_on_hand if pid in live else 0.0,
                'counted_qty': counted[pid],
                'live_qty': live[pid].qty_on_hand if pid in live else 0.0,
                'is_edited': pid in edited,
            }) for pid in changed],
        })
        return self._reopen()

    # ── 3. Confirm: correct the stock ─────────────────────────────────────────

    @api.model
    def _main_stock_location(self):
        warehouse = self.env['stock.warehouse'].sudo().search(
            [('company_id', '=', self.env.company.id)], order='sequence, id', limit=1)
        if not warehouse:
            warehouse = self.env['stock.warehouse'].sudo().search([], order='sequence, id', limit=1)
        if not warehouse:
            raise UserError(_('No warehouse found to book the count difference in.'))
        return warehouse.lot_stock_id

    @api.model
    def _adjust_location(self, quants):
        """Where the difference is booked: the product's only location if its
        stock sits in exactly one place, otherwise the main stock location."""
        locations = quants.filtered(lambda q: q.quantity).location_id
        if len(locations) == 1:
            return locations
        return self._main_stock_location()

    @api.model
    def _plan_adjustments(self, product, location, loc_quants, diff):
        """Return {quant: new_quantity} for one product in one location.

        Increase: added to the newest lot (or the quant without lot).
        Decrease: taken from the oldest lots first (FIFO); anything left
        is taken from the quant without lot.
        """
        Quant = self.env['stock.quant'].sudo()
        rounding = product.uom_id.rounding
        oldest = datetime(1970, 1, 1)
        plan = {}

        def plain_quant():
            quant = loc_quants.filtered(lambda q: not q.lot_id and not q.package_id and not q.owner_id)[:1]
            if not quant:
                quant = Quant.create({'product_id': product.id, 'location_id': location.id})
            return quant

        if diff > 0:
            lot_quants = loc_quants.filtered(
                lambda q: q.lot_id and not q.package_id and not q.owner_id
            ).sorted(lambda q: q.in_date or oldest, reverse=True)
            quant = lot_quants[:1] or plain_quant()
            plan[quant] = quant.quantity + diff
            return plan

        remaining = -diff
        for quant in loc_quants.filtered(lambda q: q.quantity > 0).sorted(lambda q: q.in_date or oldest):
            take = min(quant.quantity, remaining)
            plan[quant] = quant.quantity - take
            remaining -= take
            if float_is_zero(remaining, precision_rounding=rounding):
                break
        if not float_is_zero(remaining, precision_rounding=rounding):
            quant = plain_quant()
            plan[quant] = plan.get(quant, quant.quantity) - remaining
        return plan

    def action_confirm(self):
        self.ensure_one()
        week = self.env['soh.week']._get_open_week()
        if self.state != 'preview' or self.error_text or not self.line_ids:
            raise UserError(_('Upload the file and check it before confirming.'))
        if not week or self.download_id.week_id != week:
            raise UserError(_('The week has changed since this file was downloaded. '
                              'Download the file again.'))

        Quant = self.env['stock.quant'].sudo()
        WeekLine = self.env['soh.week.line']
        week_lines = {l.product_id.id: l for l in week.line_ids}
        inventory_name = _('SOH Count %(week)s (%(user)s)', week=week.name, user=self.env.user.name)
        to_apply = Quant
        log_lines = []
        for line in self.line_ids:
            product = line.product_id.sudo()
            factor = line.kg_factor or 1.0
            target = line.counted_qty / factor
            # Save the count on the week: the report shows it as Actual SOH.
            count_vals = {'is_counted': True, 'counted_raw': target}
            if product.id in week_lines:
                week_lines[product.id].write(count_vals)
            else:
                week_lines[product.id] = WeekLine.create(dict(
                    count_vals, week_id=week.id, product_id=product.id, opening_raw=0.0))
            quants = Quant.search([
                ('product_id', '=', product.id),
                ('location_id.usage', '=', 'internal'),
                ('company_id', '!=', False),
            ])
            live = sum(quants.mapped('quantity'))
            diff = target - live
            location = self._adjust_location(quants)
            # Ignore differences too small to show in the report (3 decimals in
            # the displayed unit), so unchanged rows never create stock moves.
            if abs(diff * factor) < 0.0005:
                diff = 0.0
            if not float_is_zero(diff, precision_rounding=product.uom_id.rounding):
                plan = self._plan_adjustments(
                    product, location, quants.filtered(lambda q: q.location_id == location), diff)
                for quant, new_qty in plan.items():
                    quant.inventory_quantity = new_qty
                    to_apply |= quant
            if not line.is_edited:
                continue  # the Upload Log lists only rows changed in the file
            log_lines.append((0, 0, {
                'product_id': product.id,
                'product_name': line.product_name,
                'uom_name': line.uom_name,
                'downloaded_qty': line.downloaded_qty,
                'counted_qty': line.counted_qty,
                'stock_change': diff * factor,
                'location_id': location.id,
            }))

        for company in to_apply.company_id:
            to_apply.filtered(lambda q: q.company_id == company).with_company(company).with_context(
                inventory_name=inventory_name)._apply_inventory()

        self.env['soh.upload.log'].create({
            'week_id': week.id,
            'file_data': self.upload_file,
            'file_name': self.upload_filename,
            'rows_read': self.rows_read,
            'rows_changed': len(log_lines),
            'result': 'applied',
            'line_ids': log_lines,
        })
        message = _('Count applied to %(n)s products in %(week)s.', n=len(self.line_ids), week=week.name)
        return {'type': 'ir.actions.act_window_close', 'infos': {'soh_message': message}}


class SohPhysicalInventoryWizardLine(models.TransientModel):
    _name = 'soh.physical.inventory.wizard.line'
    _description = 'Upload Physical Inventory Changed Row'

    wizard_id = fields.Many2one('soh.physical.inventory.wizard', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_name = fields.Char(string='Product Name', readonly=True)
    uom_name = fields.Char(string='UoM', readonly=True)
    kg_factor = fields.Float(default=1.0)
    downloaded_qty = fields.Float(string='Stock Before Count', digits='Product Unit of Measure', readonly=True)
    counted_qty = fields.Float(string='Counted', digits='Product Unit of Measure', readonly=True)
    live_qty = fields.Float(string='Stock Now', digits='Product Unit of Measure', readonly=True)
    is_edited = fields.Boolean(string='Changed in File',
                               help='The value in the file differs from what was downloaded.')
    stock_change = fields.Float(string='Stock Change', digits='Product Unit of Measure',
                                compute='_compute_stock_change')

    @api.depends('counted_qty', 'live_qty')
    def _compute_stock_change(self):
        for line in self:
            line.stock_change = line.counted_qty - line.live_qty
