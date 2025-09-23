# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import io
import xlsxwriter
import base64
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class PurchaseRequisitionExcelReportWizard(models.TransientModel):
    _name = 'purchase.requisition.excel.report.wizard'
    _description = 'Purchase Requisition Excel Report Wizard'

    start_date = fields.Date(string='Start Date', required=True,
                             default=lambda self: (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = fields.Date(string='End Date', required=True,
                           default=lambda self: datetime.now().strftime('%Y-%m-%d'))
    request_raised_by = fields.Many2one('hr.employee', string='Request Raised By')
    request_raised_for = fields.Many2one('hr.employee', string='Request Raised For')
    report_file = fields.Binary(string="Report File", readonly=True)
    report_file_name = fields.Char(string="Report File Name")

    def action_generate_excel_report(self):
        """Generate an Excel report of material requisitions based on selected filters.
           Saves the file to the record and returns a download URL for the generated report."""

        domain = []
        if self.start_date:
            domain.append(('indented_date', '>=', self.start_date.strftime('%Y-%m-%d 00:00:00')))
        if self.end_date:
            domain.append(('indented_date', '<=', self.end_date.strftime('%Y-%m-%d 23:59:59')))
        if self.request_raised_by:
            domain.append(('request_raised_by', '=', self.request_raised_by.id))
        if self.request_raised_for:
            domain.append(('request_raised_for', '=', self.request_raised_for.id))

        requisitions = self.env['material.requisition'].search(domain)

        if not requisitions:
            raise UserError(_("No Material Requisitions found for the selected criteria."))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Material Requisition Report')

        # --- Define Formats ---
        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#D3D3D3',
            'border': 1,
            'text_wrap': True
        })
        cell_format = workbook.add_format({
            'align': 'left',
            'valign': 'vcenter',
            'border': 1,
            'text_wrap': True
        })
        date_format = workbook.add_format({
            'align': 'left',
            'valign': 'vcenter',
            'border': 1,
            'num_format': 'dd/mm/yyyy hh:mm',
            'text_wrap': True
        })
        bold_cell_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'bg_color': '#F2F2F2'
        })
        filter_value_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'bg_color': '#F2F2F2'
        })
        company_title_format = workbook.add_format({
            'bold': True,
            'font_size': 20,
            'align': 'center',
            'valign': 'vcenter',
            'font_color': '#0A2B45',
        })
        report_title_format = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'align': 'center',
            'valign': 'vcenter',
            'font_color': '#333333',
        })
        # --- End Define Formats ---

        # Define headers (updated to exclude specified columns)
        headers = [
            'S.No.', 'Requisition Reference', 'State', 'Request Raised By', 'Department', 'Job Position',
            'Request Raised For', 'Requested For Department', 'Requested For Job Position',
            'Purpose', 'Indent Date',
            'Product', 'Requested Quantity', 'Unit of Measure'
        ]
        num_columns = len(headers)

        # --- Report Header Section ---
        current_row = 0

        # Company Name
        company_name = self.env.company.name if self.env.company else 'Your Company Name'
        sheet.merge_range(current_row, 0, current_row, num_columns - 1, company_name, company_title_format)
        current_row += 2

        # Report Title
        sheet.merge_range(current_row, 0, current_row, num_columns - 1, 'Material Requisition Report',
                          report_title_format)
        current_row += 3

        # --- Filters Information Section ---
        filter_block_start_col = max(0, (num_columns // 2) - 2)

        # Row for Start/End Date
        sheet.merge_range(current_row, filter_block_start_col, current_row, filter_block_start_col + 1,
                          'Start Date:', bold_cell_format)
        sheet.merge_range(current_row, filter_block_start_col + 2, current_row, filter_block_start_col + 3,
                          self.start_date.strftime('%Y-%m-%d') if self.start_date else '', filter_value_format)
        current_row += 1

        sheet.merge_range(current_row, filter_block_start_col, current_row, filter_block_start_col + 1,
                          'End Date:', bold_cell_format)
        sheet.merge_range(current_row, filter_block_start_col + 2, current_row, filter_block_start_col + 3,
                          self.end_date.strftime('%Y-%m-%d') if self.end_date else '', filter_value_format)
        current_row += 1

        # Row for Request Raised By/For
        sheet.merge_range(current_row, filter_block_start_col, current_row, filter_block_start_col + 1,
                          'Request Raised By:', bold_cell_format)
        sheet.merge_range(current_row, filter_block_start_col + 2, current_row, filter_block_start_col + 3,
                          self.request_raised_by.name if self.request_raised_by else 'All', filter_value_format)
        current_row += 1

        sheet.merge_range(current_row, filter_block_start_col, current_row, filter_block_start_col + 1,
                          'Request Raised For:', bold_cell_format)
        sheet.merge_range(current_row, filter_block_start_col + 2, current_row, filter_block_start_col + 3,
                          self.request_raised_for.name if self.request_raised_for else 'All', filter_value_format)
        current_row += 2

        # --- Set Column Widths (Adjusted for remaining columns) ---
        sheet.set_column('A:A', 6)  # S.No.
        sheet.set_column('B:B', 22) # Requisition Reference
        sheet.set_column('C:C', 15) # State
        sheet.set_column('D:D', 28) # Request Raised By
        sheet.set_column('E:E', 28) # Department
        sheet.set_column('F:F', 28) # Job Position
        sheet.set_column('G:G', 28) # Request Raised For
        sheet.set_column('H:H', 28) # Requested For Department
        sheet.set_column('I:I', 28) # Requested For Job Position
        sheet.set_column('J:J', 40) # Purpose
        sheet.set_column('K:K', 20) # Indent Date
        sheet.set_column('M:M', 35) # Product (was 'O:O')
        sheet.set_column('N:N', 18) # Requested Quantity (was 'P:P')
        sheet.set_column('O:O', 15) # Unit of Measure (was 'Q:Q')

        # Write main headers to the Excel sheet
        col = 0
        for header in headers:
            sheet.write(current_row, col, header, header_format)
            col += 1

        current_row += 1
        s_no = 1
        for req in requisitions:
            if req.material_requisition_line_ids:
                for line in req.material_requisition_line_ids:
                    col = 0
                    sheet.write(current_row, col, s_no, cell_format)
                    col += 1
                    sheet.write(current_row, col, req.name or '', cell_format)
                    col += 1
                    sheet.write(current_row, col, dict(req._fields['state'].selection).get(req.state) or '',
                                cell_format)
                    col += 1
                    sheet.write(current_row, col, req.request_raised_by.name or '', cell_format)
                    col += 1
                    sheet.write(current_row, col, req.department_id.name or '', cell_format)
                    col += 1
                    sheet.write(current_row, col, req.job_position_id.name or '', cell_format)
                    col += 1
                    sheet.write(current_row, col, req.request_raised_for.name or '', cell_format)
                    col += 1
                    sheet.write(current_row, col, req.requested_for_department_id.name or '', cell_format)
                    col += 1
                    sheet.write(current_row, col, req.requested_for_job_position_id.name or '', cell_format)
                    col += 1
                    sheet.write(current_row, col, req.purpose or '', cell_format)
                    col += 1
                    sheet.write(current_row, col,
                                req.indented_date.strftime('%d/%m/%Y %H:%M') if req.indented_date else '', date_format)
                    col += 1
                    sheet.write(current_row, col, line.product_id.name or '', cell_format)
                    col += 1
                    sheet.write(current_row, col, line.product_uom_qty, cell_format)
                    col += 1
                    sheet.write(current_row, col, line.product_uom.name or '', cell_format)
                    col += 1
                    # Removed 'On Hand Quantity' and 'Stock Available'
                    current_row += 1
                s_no += 1
            else:
                col = 0
                sheet.write(current_row, col, s_no, cell_format)
                col += 1
                sheet.write(current_row, col, req.name or '', cell_format)
                col += 1
                sheet.write(current_row, col, dict(req._fields['state'].selection).get(req.state) or '', cell_format)
                col += 1
                sheet.write(current_row, col, req.request_raised_by.name or '', cell_format)
                col += 1
                sheet.write(current_row, col, req.department_id.name or '', cell_format)
                col += 1
                sheet.write(current_row, col, req.job_position_id.name or '', cell_format)
                col += 1
                sheet.write(current_row, col, req.request_raised_for.name or '', cell_format)
                col += 1
                sheet.write(current_row, col, req.requested_for_department_id.name or '', cell_format)
                col += 1
                sheet.write(current_row, col, req.requested_for_job_position_id.name or '', cell_format)
                col += 1
                sheet.write(current_row, col, req.purpose or '', cell_format)
                col += 1
                sheet.write(current_row, col, req.indented_date.strftime('%d/%m/%Y %H:%M') if req.indented_date else '',
                            date_format)
                col += 1
                sheet.write(current_row, col, 'N/A', cell_format)
                col += 1
                sheet.write(current_row, col, 'N/A', cell_format)
                col += 1
                sheet.write(current_row, col, 'N/A', cell_format)
                col += 1
                current_row += 1
                s_no += 1

        workbook.close()
        output.seek(0)
        xlsx_data = output.read()

        self.write({
            'report_file': base64.encodebytes(xlsx_data),
            'report_file_name': 'Purchase_Requisition_Report.xlsx',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s/%s/report_file/%s?download=true' % (self._name, self.id, self.report_file_name),
            'target': 'self',
        }
