import base64
import io
import openpyxl
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class InventoryCustomWizard(models.TransientModel):
    _name = 'inventory.custom.wizard'
    _description = 'Inventory Custom Wizard'

    upload_file = fields.Binary(string="Upload File", required=True)
    file_name = fields.Char(string="File Name")

    def action_confirm(self):
        self.ensure_one()

        if not self.upload_file:
            raise UserError(_("Please upload an Excel file."))

        # ───── READ EXCEL ─────
        try:
            file_data = base64.b64decode(self.upload_file)
            data_io = io.BytesIO(file_data)
            workbook = openpyxl.load_workbook(data_io, data_only=True)
            sheet = workbook.active
        except Exception as e:
            raise UserError(_("Error reading file: %s") % e)

        # ───── HEADERS ─────
        headers = [cell.value for cell in sheet[1]]
        col_index = {name: idx for idx, name in enumerate(headers)}

        if 'SKU' not in col_index:
            raise UserError(_("Excel format invalid! 'SKU' column missing."))

        warehouse_columns = headers[4:-1]  # Skips Product Name, SKU, Variant, Regional Language Name

        # ───── PROCESS ROWS ─────
        for row_no, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):

            product_code = str(row[col_index.get('SKU')] or '').strip()
            product_name = str(row[col_index.get('Product Name')] or '').strip()

            if not product_code:
                continue  # Skip blank rows

            # ─────────────────────────
            # 1️⃣ CHECK IF SKU EXISTS → UPDATE
            # ─────────────────────────
            product = self.env['product.product'].search([
                ('default_code', '=', product_code)
            ], limit=1)

            # ─────────────────────────
            # 2️⃣ IF SKU NOT FOUND → CREATE A NEW PRODUCT (NO VARIANTS)
            # ─────────────────────────
            if not product:
                product = self.env['product.product'].create({
                    'name': product_name,
                    'default_code': product_code,
                    'is_storable':True
                })

            # ─────────────────────────
            # 3️⃣ UPDATE QUANTITIES FOR EACH WAREHOUSE
            # ─────────────────────────
            for wh_name in warehouse_columns:
                qty = row[col_index.get(wh_name)]

                if not qty or qty == 0:
                    continue

                try:
                    qty = float(qty)
                except Exception:
                    raise UserError(_(
                        "Invalid quantity at row %s for warehouse '%s'. Value: %s"
                        % (row_no, wh_name, qty)
                    ))

                warehouse = self.env['stock.warehouse'].search([
                    '|', ('name', '=', wh_name),
                    ('code', '=', wh_name)
                ], limit=1)

                if not warehouse:
                    raise UserError(_(
                        "Warehouse not found at row %s → '%s'"
                        % (row_no, wh_name)
                    ))

                self._update_quantity(product, warehouse.lot_stock_id, qty)

        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def _update_quantity(self, product, location, quantity):
        if quantity <= 0:
            return

        StockQuant = self.env['stock.quant']
        StockQuant._update_available_quantity(product, location, quantity)
