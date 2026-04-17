import base64
import io
from collections import defaultdict

from openpyxl import Workbook, load_workbook
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class WeeklyInventoryUpload(models.Model):
    _name = 'weekly.inventory.upload'
    _description = 'Weekly Inventory Upload'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'
    _template_max_row = 1048576

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True,
    )
    upload_file = fields.Binary(string='Excel File', attachment=True)
    upload_filename = fields.Char(string='File Name')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('processed', 'Processed'),
        ('undone', 'Undone'),
    ], default='draft', tracking=True)
    upload_date = fields.Datetime(string='Upload Date', readonly=True)
    uploaded_by = fields.Many2one('res.users', string='Uploaded By', readonly=True)
    total_rows = fields.Integer(string='Total Rows', readonly=True)
    success_rows = fields.Integer(string='Success Rows', readonly=True)
    failed_rows = fields.Integer(string='Failed Rows', readonly=True)
    message_summary = fields.Text(string='Summary', readonly=True)
    error_file = fields.Binary(string='Error Report', attachment=True, readonly=True)
    error_filename = fields.Char(string='Error File Name', readonly=True)
    line_ids = fields.One2many('weekly.inventory.upload.line', 'upload_id', string='Upload Logs', readonly=True)
    can_undo = fields.Boolean(compute='_compute_can_undo')

    @api.depends('state')
    def _compute_can_undo(self):
        for rec in self:
            rec.can_undo = rec.state == 'processed'

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env['ir.sequence']
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = seq.next_by_code('weekly.inventory.upload') or _('New')
        return super().create(vals_list)

    def _find_product(self, product_name):
        if product_name.startswith('[') and '] ' in product_name:
            default_code = product_name[1:].split('] ', 1)[0].strip()
            if default_code:
                product = self.env['product.product'].search([
                    ('default_code', '=', default_code),
                ], limit=2)
                if len(product) > 1:
                    raise ValidationError(_(
                        'Multiple products found for internal reference "%s".'
                    ) % default_code)
                if product:
                    return product

        product = self.env['product.product'].search([
            ('name', '=', product_name),
        ], limit=2)
        if len(product) > 1:
            raise ValidationError(_(
                'Multiple products found for "%s". Please use a unique product name or internal reference.'
            ) % product_name)
        if product:
            return product

        product = self.env['product.product'].search([
            ('default_code', '=', product_name),
        ], limit=2)
        if len(product) > 1:
            raise ValidationError(_(
                'Multiple products found for internal reference "%s".'
            ) % product_name)
        if product:
            return product

        raise ValidationError(_('Product not found: %s') % product_name)

    def _find_location(self, location_name):
        location_domain = [('usage', 'in', ('internal', 'transit'))]
        location = self.env['stock.location'].search(
            location_domain + [('complete_name', '=', location_name)],
            limit=2,
        )
        if len(location) > 1:
            raise ValidationError(_(
                'Multiple locations found for "%s". Please use a unique full location name.'
            ) % location_name)
        if location:
            return location

        location = self.env['stock.location'].search(
            location_domain + [('barcode', '=', location_name)],
            limit=2,
        )
        if len(location) > 1:
            raise ValidationError(_(
                'Multiple locations found for barcode "%s".'
            ) % location_name)
        if location:
            return location

        location = self.env['stock.location'].search(
            location_domain + [('name', '=', location_name)],
            limit=2,
        )
        if len(location) > 1:
            raise ValidationError(_(
                'Multiple locations found for "%s". Please use the full location name.'
            ) % location_name)
        if location:
            return location

        raise ValidationError(_('Location not found: %s') % location_name)

    def _get_template_product_values(self):
        products = self.env['product.product'].search(
            [('is_storable', '=', True)],
            order='default_code, name, id',
        )
        values = []
        for product in products:
            if product.default_code:
                values.append('[%s] %s' % (product.default_code, product.name))
            else:
                values.append(product.name)
        return values or ['']

    def _get_template_location_values(self):
        locations = self.env['stock.location'].search(
            [('usage', 'in', ('internal', 'transit'))],
            order='complete_name, id',
        )
        return locations.mapped('complete_name') or ['']

    def _add_template_dropdown(self, sheet, column, range_name, title, message):
        validation = DataValidation(
            type='list',
            formula1='=%s' % range_name,
            allow_blank=True,
        )
        validation.promptTitle = title
        validation.prompt = message
        validation.errorTitle = _('Invalid Value')
        validation.error = message
        sheet.add_data_validation(validation)
        validation.add('%s2:%s%s' % (column, column, self._template_max_row))

    def action_download_sample_template(self):
        self.ensure_one()
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = 'Inventory Upload'
        sheet.append(['Product', 'Location', 'Quantity'])

        product_values = self._get_template_product_values()
        location_values = self._get_template_location_values()

        data_sheet = workbook.create_sheet('TemplateData')
        data_sheet.append(['Products', 'Locations'])
        max_rows = max(len(product_values), len(location_values))
        for index in range(max_rows):
            data_sheet.cell(row=index + 2, column=1, value=product_values[index] if index < len(product_values) else '')
            data_sheet.cell(row=index + 2, column=2, value=location_values[index] if index < len(location_values) else '')
        data_sheet.sheet_state = 'hidden'

        workbook.defined_names.add(DefinedName(
            'WeeklyInventoryProducts',
            attr_text="'TemplateData'!$A$2:$A$%s" % (len(product_values) + 1),
        ))
        workbook.defined_names.add(DefinedName(
            'WeeklyInventoryLocations',
            attr_text="'TemplateData'!$B$2:$B$%s" % (len(location_values) + 1),
        ))

        self._add_template_dropdown(
            sheet,
            'A',
            'WeeklyInventoryProducts',
            _('Product'),
            _('Select a product from the list.'),
        )
        self._add_template_dropdown(
            sheet,
            'B',
            'WeeklyInventoryLocations',
            _('Location'),
            _('Select a stock location from the list.'),
        )
        sheet.freeze_panes = 'A2'
        sheet.column_dimensions['A'].width = 35
        sheet.column_dimensions['B'].width = 45
        sheet.column_dimensions['C'].width = 14

        output = io.BytesIO()
        workbook.save(output)
        file_content = base64.b64encode(output.getvalue())
        self.write({
            'error_file': file_content,
            'error_filename': 'sample_weekly_inventory_template.xlsx',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s/%s/error_file/%s?download=true' % (self._name, self.id, self.error_filename or 'sample_weekly_inventory_template.xlsx'),
            'target': 'self',
        }

    def action_process_upload(self):
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Only draft uploads can be processed.'))
        if not self.upload_file:
            raise UserError(_('Please upload an Excel file first.'))

        self.line_ids.unlink()
        self.write({
            'error_file': False,
            'error_filename': False,
            'message_summary': False,
            'total_rows': 0,
            'success_rows': 0,
            'failed_rows': 0,
        })

        file_data = base64.b64decode(self.upload_file)
        workbook = load_workbook(filename=io.BytesIO(file_data), data_only=True)
        sheet = workbook.active

        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            raise UserError(_('The uploaded file is empty.'))

        headers = [str(h).strip() if h is not None else '' for h in rows[0]]
        valid_headers = [
            ['Product', 'Location', 'Quantity'],
            ['Product', 'Warehouse Location', 'Quantity'],
            ['Product', 'Warehouse', 'Quantity'],
        ]
        if headers[:3] not in valid_headers:
            raise ValidationError(_('Invalid template. Required first three columns are: Product, Location, Quantity.'))

        total_rows = 0
        success_rows = 0
        failed_rows = 0
        error_rows = []
        grouped_rows = defaultdict(list)

        for index, row in enumerate(rows[1:], start=2):
            if not row or all(cell in (None, '') for cell in row[:3]):
                continue

            total_rows += 1
            product_value = (row[0] or '')
            location_value = (row[1] or '')
            quantity_value = row[2]
            grouped_rows[(str(product_value).strip(), str(location_value).strip())].append((index, quantity_value))

        for (product_name, location_name), grouped in grouped_rows.items():
            # if duplicates exist, last quantity wins but all duplicate rows are logged
            last_row_no, final_qty = grouped[-1]
            duplicate_rows = [g[0] for g in grouped]
            duplicate_note = ''
            if len(grouped) > 1:
                duplicate_note = _(' Duplicate rows detected at Excel rows: %s. Last row quantity used.') % ', '.join(map(str, duplicate_rows))

            try:
                if not product_name:
                    raise ValidationError(_('Product is missing.'))
                if not location_name:
                    raise ValidationError(_('Location is missing.'))
                if final_qty in (None, ''):
                    raise ValidationError(_('Quantity is missing.'))

                try:
                    final_qty = float(final_qty)
                except Exception:
                    raise ValidationError(_('Quantity must be numeric.'))

                if final_qty < 0:
                    raise ValidationError(_('Quantity cannot be negative.'))

                product = self._find_product(product_name)
                location = self._find_location(location_name)
                quant = self.env['stock.quant'].search([
                    ('product_id', '=', product.id),
                    ('location_id', '=', location.id),
                ], limit=1)
                old_qty = quant.quantity if quant else 0.0

                if quant:
                    quant.inventory_quantity = final_qty
                    quant._apply_inventory()
                else:
                    new_quant = self.env['stock.quant'].with_context(inventory_mode=True).create({
                        'product_id': product.id,
                        'location_id': location.id,
                        'inventory_quantity': final_qty,
                    })
                    new_quant._apply_inventory()

                self.env['weekly.inventory.upload.line'].create({
                    'upload_id': self.id,
                    'row_number': last_row_no,
                    'product_name': product_name,
                    'warehouse_name': location_name,
                    'product_id': product.id,
                    'warehouse_id': location.warehouse_id.id,
                    'location_id': location.id,
                    'old_qty': old_qty,
                    'new_qty': final_qty,
                    'status': 'success',
                    'message': _('Inventory updated successfully.') + duplicate_note,
                })
                success_rows += 1
            except Exception as exc:
                failed_rows += 1
                message = str(exc)
                error_rows.append([product_name, location_name, final_qty if final_qty not in (None, '') else '', message])
                self.env['weekly.inventory.upload.line'].create({
                    'upload_id': self.id,
                    'row_number': last_row_no,
                    'product_name': product_name,
                    'warehouse_name': location_name,
                    'new_qty': final_qty if isinstance(final_qty, (int, float)) else 0.0,
                    'status': 'failed',
                    'message': message,
                })

        summary = _('Inventory updated successfully for %s products') % success_rows
        if failed_rows:
            summary += _('. Failed rows: %s') % failed_rows
            self._generate_error_report(error_rows)

        self.write({
            'state': 'processed',
            'upload_date': fields.Datetime.now(),
            'uploaded_by': self.env.user.id,
            'total_rows': total_rows,
            'success_rows': success_rows,
            'failed_rows': failed_rows,
            'message_summary': summary,
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Upload Complete'),
                'message': summary,
                'sticky': False,
                'type': 'success' if not failed_rows else 'warning',
                'next': {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                }
            }
        }

    def _generate_error_report(self, error_rows):
        self.ensure_one()
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = 'Error Report'
        sheet.append(['Product', 'Location', 'Quantity', 'Error Message'])
        for row in error_rows:
            sheet.append(row)
        output = io.BytesIO()
        workbook.save(output)
        self.write({
            'error_file': base64.b64encode(output.getvalue()),
            'error_filename': '%s_error_report.xlsx' % self.name,
        })

    def action_download_error_report(self):
        self.ensure_one()
        if not self.error_file:
            raise UserError(_('No error report found for this upload.'))
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s/%s/error_file/%s?download=true' % (self._name, self.id, self.error_filename or 'error_report.xlsx'),
            'target': 'self',
        }

    def action_undo_upload(self):
        self.ensure_one()
        if self.state != 'processed':
            raise UserError(_('Only processed uploads can be undone.'))

        success_lines = self.line_ids.filtered(lambda l: l.status == 'success')
        if not success_lines:
            raise UserError(_('No successful lines found to undo.'))

        for line in success_lines:
            quant = self.env['stock.quant'].search([
                ('product_id', '=', line.product_id.id),
                ('location_id', '=', line.location_id.id),
            ], limit=1)
            if quant:
                quant.inventory_quantity = line.old_qty
                quant._apply_inventory()
            else:
                new_quant = self.env['stock.quant'].with_context(inventory_mode=True).create({
                    'product_id': line.product_id.id,
                    'location_id': line.location_id.id,
                    'inventory_quantity': line.old_qty,
                })
                new_quant._apply_inventory()
            line.undo_done = True

        self.write({
            'state': 'undone',
            'message_summary': _('Inventory restored successfully.'),
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Undo Complete'),
                'message': _('Inventory restored successfully.'),
                'sticky': False,
                'type': 'success',
                 'next': {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                }
            }
        }


class WeeklyInventoryUploadLine(models.Model):
    _name = 'weekly.inventory.upload.line'
    _description = 'Weekly Inventory Upload Line'
    _order = 'id asc'

    upload_id = fields.Many2one('weekly.inventory.upload', string='Upload', required=True, ondelete='cascade')
    row_number = fields.Integer(string='Excel Row')
    product_name = fields.Char(string='Product')
    warehouse_name = fields.Char(string='Location')
    product_id = fields.Many2one('product.product', string='Matched Product')
    warehouse_id = fields.Many2one('stock.warehouse', string='Related Warehouse')
    location_id = fields.Many2one('stock.location', string='Matched Location')
    old_qty = fields.Float(string='Old Quantity', digits='Product Unit of Measure')
    new_qty = fields.Float(string='New Quantity', digits='Product Unit of Measure')
    status = fields.Selection([
        ('success', 'Success'),
        ('failed', 'Failed'),
    ], string='Status', default='success')
    message = fields.Text(string='Message')
    undo_done = fields.Boolean(string='Undo Done', default=False)
