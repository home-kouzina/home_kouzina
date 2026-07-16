import base64
import csv
import io
import datetime

from odoo import fields, models, api
from odoo.exceptions import UserError


class SaleMarginCogsBulkWizard(models.TransientModel):
    _name = 'sale.margin.cogs.bulk.wizard'
    _description = 'Bulk Backfill COGS from CSV (SKU, COS)'

    state = fields.Selection([('draft', 'Draft'), ('done', 'Done')], default='draft')

    date_from = fields.Date(
        string='From Date',
        help="Optional. Leave both dates empty to apply across all orders, "
             "regardless of date."
    )
    date_to = fields.Date(string='To Date')

    csv_file = fields.Binary(string='CSV File', required=True)
    csv_filename = fields.Char(string='Filename')

    only_missing = fields.Boolean(
        string='Only fix lines with missing/zero COGS',
        default=True,
        help="Recommended: only updates lines where COGS is currently 0 or "
             "not set. Turn off to force-overwrite lines that already have "
             "a COGS value."
    )

    result_summary = fields.Text(string='Result', readonly=True)

    # ------------------------------------------------------------------
    # CSV parsing
    # ------------------------------------------------------------------
    def _parse_csv(self):
        """Returns a list of (sku, cos_value) tuples from the uploaded file.
        Accepts a header row with columns named (case-insensitively):
        SKU / Default Code / Product Code   and   COS / COGS / Cost.
        Any other columns in the file (Name, EAN, Pack, Total, ...) are
        ignored.
        """
        self.ensure_one()
        if not self.csv_file:
            raise UserError("Please upload a CSV file.")

        raw = base64.b64decode(self.csv_file)
        text = raw.decode('utf-8-sig', errors='ignore')
        reader = csv.DictReader(io.StringIO(text))

        if not reader.fieldnames:
            raise UserError("The CSV file appears to be empty.")

        norm_map = {}
        for original in reader.fieldnames:
            key = (original or '').strip().lower()
            norm_map[key] = original

        sku_col = next((norm_map[k] for k in norm_map if k in ('sku', 'default code', 'default_code', 'product code', 'product_code')), None)
        cos_col = next((norm_map[k] for k in norm_map if k in ('cos', 'cogs', 'cost', 'cos value', 'cos_value')), None)

        if not sku_col or not cos_col:
            raise UserError(
                "Couldn't find the required columns. The CSV must have a "
                "column named 'SKU' and a column named 'COS' (headers are "
                "case-insensitive). Found columns: %s" % ', '.join(reader.fieldnames)
            )

        rows = []
        for row in reader:
            sku = (row.get(sku_col) or '').strip()
            cos_raw = (row.get(cos_col) or '').strip()
            if not sku or not cos_raw:
                continue
            try:
                cos_value = float(cos_raw.replace(',', ''))
            except ValueError:
                continue
            rows.append((sku, cos_value))
        return rows

    def _date_domain(self):
        """Returns the order-date leg of the domain, or [] if no range set."""
        self.ensure_one()
        if not self.date_from and not self.date_to:
            return []
        if bool(self.date_from) != bool(self.date_to):
            raise UserError("Please set both 'From Date' and 'To Date', or leave both empty.")
        if self.date_from > self.date_to:
            raise UserError("'From Date' must be before or equal to 'To Date'.")

        date_to_upper = fields.Datetime.to_string(
            fields.Datetime.from_string(str(self.date_to)) + datetime.timedelta(days=1)
        )
        return [
            ('order_id.date_order', '>=', str(self.date_from)),
            ('order_id.date_order', '<', date_to_upper),
        ]

    # ------------------------------------------------------------------
    # Main action
    # ------------------------------------------------------------------
    def action_apply_bulk_cogs(self):
        self.ensure_one()
        rows = self._parse_csv()
        if not rows:
            raise UserError("No valid (SKU, COS) rows found in the file.")

        date_domain = self._date_domain()

        not_found_skus = []
        zero_match_skus = []
        updated_lines_total = 0
        updated_skus = 0

        # If the same SKU appears more than once in the file, the last row wins.
        cos_by_sku = dict(rows)

        for sku, cos_value in cos_by_sku.items():
            product = self.env['product.product'].search([('default_code', '=', sku)], limit=1)
            if not product:
                not_found_skus.append(sku)
                continue

            domain = [
                ('product_id', '=', product.id),
                ('display_type', '=', False),
            ] + date_domain
            if self.only_missing:
                domain += ['|', ('cogs_unit_price', '=', 0), ('cogs_unit_price', '=', False)]

            lines = self.env['sale.order.line'].sudo().search(domain)
            if not lines:
                zero_match_skus.append(sku)
                continue

            lines.write({'cogs_unit_price': cos_value})
            updated_lines_total += len(lines)
            updated_skus += 1

        summary_parts = [
            f"SKUs processed: {len(cos_by_sku)}",
            f"SKUs updated: {updated_skus}",
            f"Order lines updated: {updated_lines_total}",
        ]
        if zero_match_skus:
            summary_parts.append(
                f"\nSKUs with no matching order lines ({len(zero_match_skus)}):\n" + ', '.join(zero_match_skus)
            )
        if not_found_skus:
            summary_parts.append(
                f"\nSKUs not found in Products ({len(not_found_skus)}):\n" + ', '.join(not_found_skus)
            )

        self.result_summary = '\n'.join(summary_parts)
        self.state = 'done'

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.margin.cogs.bulk.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_back_to_draft(self):
        self.ensure_one()
        self.state = 'draft'
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.margin.cogs.bulk.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
