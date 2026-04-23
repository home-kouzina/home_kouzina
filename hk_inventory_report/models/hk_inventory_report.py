from odoo import models, fields, api
import io
import base64
from datetime import datetime
import xlsxwriter
import re


class HKInventoryReport(models.TransientModel):
    _name = 'hk.inventory.report.wizard'
    _description = 'HK Inventory Report Wizard'

    file_data = fields.Binary('File')
    file_name = fields.Char('File Name')

    def _split_product_details(self,display_name):
        """
        Example: '[HK_MSM_01] Maharashtrian Sabzi (Bhaaji) Masala (100g)'
        Returns: ('HK_MSM_01', 'Maharashtrian Sabzi (Bhaaji) Masala', '100g')
        """
        sku = ''
        variant = ''
        name = display_name

        # Extract SKU -> text inside []
        sku_match = re.search(r'\[(.*?)\]', display_name)
        if sku_match:
            sku = sku_match.group(1)
            name = display_name.replace(sku_match.group(0), '').strip()

        # Extract Variant -> text inside () at end
        variant_match = re.search(r'\((.*?)\)$', name)
        if variant_match:
            variant = variant_match.group(1)
            name = name.replace(variant_match.group(0), '').strip()

        return sku, name, variant

    # -----------------------------------------
    # Excel Report
    # -----------------------------------------
    def action_generate_excel(self):
        # Create in-memory output
        fp = io.BytesIO()
        workbook = xlsxwriter.Workbook(fp)
        worksheet = workbook.add_worksheet('Inventory Report')

        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'font_color': 'white',
            'bg_color': '#4F81BD',  # Blue header
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })

        text_format = workbook.add_format({
            'align': 'left',
            'valign': 'vcenter',
            'border': 1
        })

        qty_format = workbook.add_format({
            'align': 'right',
            'valign': 'vcenter',
            'border': 1,
            'num_format': '#,##0.00'
        })

        alt_row_format = workbook.add_format({
            'bg_color': '#F2F2F2',
            'align': 'left',
            'valign': 'vcenter',
            'border': 1
        })

        alt_qty_format = workbook.add_format({
            'bg_color': '#F2F2F2',
            'align': 'right',
            'valign': 'vcenter',
            'border': 1,
            'num_format': '#,##0.00'
        })

        # Fetch data
        warehouses = self.env['stock.warehouse'].search([])
        products = self.env['product.product'].search([])

        # ----------------------
        # HEADER
        # ----------------------
        header = ['Product Name','Product Type', 'SKU', 'Variant', 'Regional Language Name']  # Added the Header Of Product Type
        for wh in warehouses:
            header.append(wh.name)
        header.append('Total Quantity')

        # Write header
        for col, name in enumerate(header):
            worksheet.write(0, col, name, header_format)

        # ----------------------
        # DATA ROWS
        # ----------------------
        row_num = 1
        for product in products:
            # Alternate row background
            text_fmt = text_format if row_num % 2 != 0 else alt_row_format
            qty_fmt = qty_format if row_num % 2 != 0 else alt_qty_format

            total_qty = 0
            col_num = 0

            # ---- SPLIT PRODUCT DETAILS ----
            sku, base_name, variant = self._split_product_details(product.display_name or '')

            worksheet.write(row_num, col_num, base_name, text_fmt)  # Product Name
            col_num += 1
             # ADDED: Product Type column value based on is_finished field
            product_type = 'Finished Product' if product.is_finished_good else 'Raw Material'
            worksheet.write(row_num, col_num, product_type, text_fmt)  # Product Type
            col_num += 1
            worksheet.write(row_num, col_num, sku, text_fmt)  # SKU
            col_num += 1
            worksheet.write(row_num, col_num, variant, text_fmt)  # Variant
            col_num += 1

            # Regional Name
            worksheet.write(row_num, col_num, product.regional_language_name or '', text_fmt)
            col_num += 1

            # Per warehouse quantities
            for wh in warehouses:
                qty = self.env['stock.quant'].search([
                    ('product_id', '=', product.id),
                    ('location_id', 'child_of', wh.view_location_id.id)
                ]).mapped('quantity')
                qty_sum = sum(qty)
                total_qty += qty_sum
                worksheet.write(row_num, col_num, qty_sum, qty_fmt)
                col_num += 1

            # Total column
            worksheet.write(row_num, col_num, total_qty, qty_fmt)
            row_num += 1

        # ----------------------
        # COLUMN WIDTHS
        # ----------------------
        worksheet.set_column(0, 0, 40)  # Product Name
        worksheet.set_column(1, 1, 20)  # SKU
        worksheet.set_column(2, 2, 15)  # Variant (100g / 1kg)
        worksheet.set_column(3, 3, 30)  # Regional Language Name
        worksheet.set_column(4, len(header) - 1, 20)  # Warehouses+Total

        # Freeze header row
        worksheet.freeze_panes(1, 0)

        # Close and encode file
        workbook.close()
        fp.seek(0)
        excel_data = base64.b64encode(fp.read())
        fp.close()

        filename = f"HK_Inventory_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        self.write({'file_data': excel_data, 'file_name': filename})

        # Return file download action
        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/?model={self._name}&id={self.id}&field=file_data&filename_field=file_name&download=true",
            'target': 'self',
        }

    # -----------------------------------------
    # PDF Report
    # -----------------------------------------
    def action_generate_pdf(self):
        return self.env.ref('hk_inventory_report.action_hk_inventory_pdf').report_action(self)


class HKInventoryPDF(models.AbstractModel):
    _name = 'report.hk_inventory_report.hk_inventory_pdf'
    _description = 'HK Inventory PDF Report'

    def _get_report_values(self, docids, data=None):
        warehouses = self.env['stock.warehouse'].search([])
        products = self.env['product.product'].search([])
        report_data = []

        for product in products:
            sku, name, variant = self.env['hk.inventory.report.wizard']._split_product_details(product.display_name or '')
            wh_qty = []
            total_qty = 0

            for wh in warehouses:
                qty = self.env['stock.quant'].search([
                    ('product_id', '=', product.id),
                    ('location_id', 'child_of', wh.view_location_id.id)
                ]).mapped('quantity')
                qty_sum = sum(qty)
                wh_qty.append({'warehouse': wh.name, 'qty': qty_sum})
                total_qty += qty_sum

            report_data.append({
                'product_name': name,
                'sku': sku,
                'variant': variant,
                'regional_language_name': product.regional_language_name or '',
                'product_type': 'Finished Product' if product.is_finished_good else 'Raw Material',
                'quantities': wh_qty,
                'total': total_qty,
            })

        sorted_data = sorted(report_data, key=lambda d: d['product_name'], reverse=True)

        return {
            'docs': sorted_data,
            'warehouses': warehouses,
            'generated_on': fields.Date.today(),
        }
