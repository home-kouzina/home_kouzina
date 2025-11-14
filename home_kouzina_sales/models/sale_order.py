from odoo import models, fields, _
import xlsxwriter
from odoo import models, api, _
from odoo.exceptions import UserError, ValidationError
import base64
import io
import openpyxl
import pandas as pd


class SaleOrder(models.Model):
    _inherit = "sale.order"

    template_file = fields.Binary("Template File")
    template_filename = fields.Char("Template Filename")

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            # Get the delivery picking created for this sale order
            picking = self.env['stock.picking'].search([
                ('origin', '=', order.name),
                ('state', '!=', 'cancel'),
                ('picking_type_id.code', '=', 'outgoing')
            ], limit=1)

            # ✅ Dictionary to accumulate total qty per package product
            package_totals = {}

            for line in order.order_line:
                product_qty = line.product_uom_qty  # Quantity of main product

                for package in line.package_ids:
                    package_product = package.product_id

                    # Skip consumables
                    if package_product.type != 'consu':
                        continue

                    # Accumulate total quantity for this package product
                    package_totals[package_product] = package_totals.get(package_product, 0) + product_qty

            # ✅ Now process each package product just once
            for package_product, total_qty in package_totals.items():
                # Check stock availability
                stock_location = self.env.ref('stock.stock_location_stock')
                quants = self.env['stock.quant'].sudo().search([
                    ('product_id', '=', package_product.id),
                    ('location_id', '=', stock_location.id)
                ])

                total_qty_available = sum(quants.mapped('inventory_quantity_auto_apply'))
                if total_qty_available < total_qty:
                    raise ValidationError(
                        f"Not enough stock for package product '{package_product.display_name}'"
                    )

                # ✅ Create ONE stock move for the total quantity
                if picking:
                    self.env['stock.move'].create({
                        'name': package_product.display_name,
                        'product_id': package_product.id,
                        'product_uom_qty': total_qty,
                        'product_uom': package_product.uom_id.id,
                        'picking_id': picking.id,
                        'location_id': picking.location_id.id,
                        'location_dest_id': picking.location_dest_id.id,
                    })

        return res

    def open_marketplace_import_wizard(self):
        """ Opens the marketplace order import wizard. """
        return {
            'name': 'Import Marketplace Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'marketplace.order.import.wizard',
            'view_mode': 'form',
            'target': 'new',
        }

    def action_download_template(self):
        """
        Generate Excel template for sale orders and return it as a downloadable file.
        """
        # Create an in-memory bytes buffer to hold the Excel file
        output = io.BytesIO()

        # Create a new Excel workbook in memory
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        # Add a new worksheet named "Sale Order Template"
        sheet = workbook.add_worksheet("Sale Order Template")

        # Define headers for the Excel template
        headers = ["Customer", "Product", "Quantity", "Price"]

        # Write headers in the first row of the worksheet
        for col, header in enumerate(headers):
            sheet.write(0, col, header)

        # Close the workbook to save the data into the buffer
        workbook.close()

        # Move the pointer back to the start of the buffer
        output.seek(0)

        # Encode the in-memory Excel file as base64 to store in a binary field
        file_data = base64.b64encode(output.read())

        # Assign the encoded file to the template_file field on the record
        self.template_file = file_data

        # Return a dictionary instructing Odoo to open a download link for the generated file
        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/{self.id}/template_file/{self.template_filename}?download=true",
            'target': 'self',
        }

    @api.model
    def action_import_from_xlsx(self, base64_file):
        """
        Import Sale Orders using Product Default Code.
        Multiple products for one customer go into one order.
        Blank Customer cells use the last non-empty customer.
        """
        if not base64_file:
            raise UserError(_("No file uploaded!"))

        try:
            # Decode Base64 → BytesIO
            file_bytes = base64.b64decode(base64_file)
            buffer = io.BytesIO(file_bytes)

            # Load Excel
            df = pd.read_excel(buffer)

            required_cols = ["Customer", "Product Code", "Quantity"]
            for col in required_cols:
                if col not in df.columns:
                    raise UserError(_("Missing required column: %s") % col)

            created_orders = 0
            last_customer_name = None

            # Dictionary to keep track of orders per customer
            orders_dict = {}

            for idx, row in df.iterrows():
                customer_name = str(row["Customer"]).strip() if pd.notna(row["Customer"]) else last_customer_name
                if not customer_name:
                    raise UserError(_("Customer must be provided at least once for each group of products."))

                last_customer_name = customer_name

                # Find or create customer
                partner = self.env["res.partner"].search([("name", "=", customer_name)], limit=1)
                if not partner:
                    partner = self.env["res.partner"].create({"name": customer_name})

                # Create Sale Order only once per customer
                if partner.id not in orders_dict:
                    order = self.create({"partner_id": partner.id})
                    orders_dict[partner.id] = order
                    created_orders += 1
                else:
                    order = orders_dict[partner.id]

                # Find product by default_code
                product_code = str(row["Product Code"]).strip()
                product = self.env["product.product"].search([("default_code", "=", product_code)], limit=1)
                if not product:
                    raise UserError(_("Product not found with default code: %s") % product_code)

                qty = float(row["Quantity"])

                # Add order line
                self.env["sale.order.line"].create({
                    "order_id": order.id,
                    "product_id": product.id,
                    "product_uom_qty": qty,
                    "price_unit": product.list_price,
                })

            return {"success": True, "message": _("%s Sale Orders created.") % created_orders}

        except Exception as e:
            return {"success": False, "message": str(e)}
