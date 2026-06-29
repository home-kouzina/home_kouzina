# -*- coding: utf-8 -*-
import io
import json
import re

from werkzeug.exceptions import InternalServerError

from odoo import http
from odoo.exceptions import AccessError, UserError
from odoo.http import content_disposition, request
from odoo.tools.misc import xlsxwriter


_NUMERIC_RE = re.compile(r"^[-+]?((\d{1,3}(,\d{3})+)|\d+)(\.\d+)?$")


class VisibleGroupedListExport(http.Controller):

    @http.route('/web/export/visible_grouped_xlsx', type='http', auth='user')
    def visible_grouped_xlsx(self, data, **kwargs):
        try:
            payload = json.loads(data or '{}')
            content = self._make_xlsx(payload)

            filename = self._safe_filename(payload.get('title') or 'Grouped Export')
            if not filename.lower().endswith('.xlsx'):
                filename += '.xlsx'

            return request.make_response(
                content,
                headers=[
                    ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                    ('Content-Disposition', content_disposition(filename)),
                ],
            )
        except Exception as exc:
            payload = json.dumps({
                'code': 200,
                'message': 'Odoo Server Error',
                'data': http.serialize_exception(exc),
            })
            raise InternalServerError(payload) from exc

    def _check_export_access(self, model_name):
        if not request.env.user.has_group('base.group_allow_export'):
            raise AccessError(request.env._('You are not allowed to export data.'))

        if not model_name or model_name not in request.env:
            raise UserError(request.env._('Invalid export model.'))

        request.env[model_name].check_access_rights('read')

    def _safe_filename(self, filename):
        filename = re.sub(r"[\\/:*?\"<>|]+", '-', filename or '')
        filename = re.sub(r"\s+", ' ', filename).strip()
        return filename or 'Grouped Export.xlsx'

    def _coerce_cell_value(self, value, column_type=None):
        if value is None or value is False:
            return ''

        if not isinstance(value, str):
            return value

        value = value.replace('\u00a0', ' ').strip()

        if not value or value in {'—', '-'}:
            return ''

        if column_type in {'integer', 'float', 'monetary'}:
            candidate = value.replace(',', '')
            if _NUMERIC_RE.match(value):
                try:
                    number = float(candidate)
                    if column_type == 'integer' and number.is_integer():
                        return int(number)
                    return number
                except ValueError:
                    return value

        return value

    def _is_blank(self, value):
        return (
            value is None
            or value is False
            or str(value).replace('\u00a0', ' ').strip() in {'', '—', '-'}
        )

    def _simplify_grouped_rows(self, columns, rows):
        if not columns or not rows:
            return columns, rows

        has_group_rows = any((row.get('type') or 'record') == 'group' for row in rows)

        keep_indexes = []

        for index, column in enumerate(columns):
            if index == 0:
                keep_indexes.append(index)
                continue

            has_value = any(
                index < len(row.get('values') or [])
                and not self._is_blank((row.get('values') or [])[index])
                for row in rows
            )

            if has_value:
                keep_indexes.append(index)

        new_columns = [dict(columns[index]) for index in keep_indexes]

        if has_group_rows and new_columns:
            new_columns[0]['label'] = request.env._('Group')
            new_columns[0]['name'] = 'group_label'
            new_columns[0]['type'] = 'char'

        new_rows = []

        for row in rows:
            values = row.get('values') or []
            new_row = dict(row)
            new_row['values'] = [
                values[index] if index < len(values) else ''
                for index in keep_indexes
            ]
            new_rows.append(new_row)

        return new_columns, new_rows

    def _make_xlsx(self, payload):
        if not xlsxwriter:
            raise UserError(request.env._('XlsxWriter is required to export XLSX files.'))

        model_name = payload.get('model')
        self._check_export_access(model_name)

        columns = payload.get('columns') or []
        rows = payload.get('rows') or []

        if not columns:
            raise UserError(request.env._('Nothing to export: no visible columns found.'))

        if not rows:
            raise UserError(request.env._('Nothing to export: no visible rows found.'))

        columns, rows = self._simplify_grouped_rows(columns, rows)

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet(request.env._('Grouped Export'))

        # Keep formats plain.
        # No bg_color.
        # No borders.
        # No table style.
        # This allows normal Excel / LibreOffice / Google Sheets gridlines to remain visible.
        header_format = workbook.add_format({
            'bold': True,
        })

        text_format = workbook.add_format({})

        int_format = workbook.add_format({
            'num_format': '#,##0',
        })

        num_format = workbook.add_format({
            'num_format': '#,##0.00',
        })

        # Write headers.
        for col_index, column in enumerate(columns):
            worksheet.write(
                0,
                col_index,
                column.get('label') or column.get('name') or '',
                header_format,
            )

        # Write visible rows.
        for row_index, row in enumerate(rows, start=1):
            values = row.get('values') or []
            level = min(max(int(row.get('level') or 0), 0), 7)

            for col_index, column in enumerate(columns):
                raw_value = values[col_index] if col_index < len(values) else ''
                column_type = column.get('type') or 'char'
                cell_value = self._coerce_cell_value(raw_value, column_type)

                # Add simple space indentation only in first column.
                # Do not use Excel indent formatting because we want a plain sheet.
                if col_index == 0 and isinstance(cell_value, str) and level:
                    cell_value = ('    ' * level) + cell_value

                if isinstance(cell_value, int):
                    fmt = int_format
                elif isinstance(cell_value, float):
                    fmt = num_format
                else:
                    fmt = text_format

                worksheet.write(row_index, col_index, cell_value, fmt)

        # Simple column widths only. No styling.
        for col_index, column in enumerate(columns):
            header = str(column.get('label') or column.get('name') or '')
            max_len = len(header)

            for row in rows[:500]:
                values = row.get('values') or []
                if col_index < len(values):
                    max_len = max(max_len, len(str(values[col_index] or '')))

            if col_index == 0:
                worksheet.set_column(col_index, col_index, min(max(max_len + 4, 24), 55))
            else:
                worksheet.set_column(col_index, col_index, min(max(max_len + 2, 12), 24))

        workbook.close()
        return output.getvalue()