# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import xlsxwriter
import base64
import io


class InventoryVariation(models.Model):
    _name = "inventory.variation"
    _description = "Inventory Variation Session"
    _order = "date desc, id desc"

    name = fields.Char(string="Reference", required=True, copy=False, default="IVR")
    date = fields.Date(string="Count Date", required=True, default=fields.Date.context_today)
    # warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=False)
    #Added the ability to select multiple warehouses for inventory variation session
    warehouse_ids = fields.Many2many('stock.warehouse', string='Warehouse', required=False)

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('reported', 'Reported')
    ], string='State', default='draft')
    line_ids = fields.One2many('inventory.variation.line', 'variation_id', string='Lines', copy=True)
    total_variation = fields.Float(string='Total Variation', compute='_compute_total_variation')

    @api.model
    def create(self, vals):
        """
        Assign a unique sequence to the 'name' field if not provided.

        When a new inventory variation record is created, this method ensures
        it gets a unique sequence number from 'inventory.variation' if 'name'
        is missing or set to '/'.
        """
        # Auto-generate sequence if 'name' is empty or placeholder
        if vals.get('name', 'IVR') == 'IVR' or not vals.get('name'):
            vals['name'] = self.env['ir.sequence'].next_by_code('inventory.variation') or 'IVR'
        return super().create(vals)

    @api.depends('line_ids.variation_qty')
    def _compute_total_variation(self):
        """
        Compute the total variation quantity.

        Sums up the 'variation_qty' from all related lines and stores
        the result in the 'total_variation' field.
        """
        # Calculate total variation from all line_ids
        for rec in self:
            rec.total_variation = sum(rec.line_ids.mapped('variation_qty'))
            
    #Do the changes In this Function
    def action_load_products(self):
        """
        Load products and their theoretical quantities from stock quants.
        Creates or updates variation lines based on current warehouse stock.
        """
        self.ensure_one()
        if not self.warehouse_ids:
            raise UserError(_("Please select at least one warehouse before loading products."))

        # CHANGED: handle multiple warehouses
        root_locations = self.warehouse_ids.mapped('lot_stock_id')
        domain = [('id', 'child_of', root_locations.ids), ('usage', '=', 'internal')]
        locations = self.env['stock.location'].search(domain)

        if not locations:
            raise UserError(_("No internal locations found for the selected warehouses."))

        # Fetch quants and aggregate quantities by product and location
        quants = self.env['stock.quant'].search([('location_id', 'in', locations.ids), ('product_id.active', '=', True)])
        product_quant_map = {}
        for q in quants:
            key = (q.product_id.id, q.location_id.id)
            product_quant_map[key] = product_quant_map.get(key, 0.0) + q.quantity

        # Check for existing lines and update or create new ones
        existing = {(l.product_id.id, l.location_id.id): l for l in self.line_ids}
        new_lines = []

        for (pid, lid), qty in product_quant_map.items():
            product = self.env['product.product'].browse(pid)

            # ADDED: product type value from finished_good
            product_type = 'Finished' if product.is_finished_good else 'Raw Material'

            if (pid, lid) in existing:
                # CHANGED: also update product type and sale price on existing lines
                existing_line = existing[(pid, lid)]
                existing_line.theoretical_qty = qty
                existing_line.product_type = product_type
                existing_line.sale_price = product.lst_price
            else:
                # CHANGED: add product type and sale price while creating new lines
                new_lines.append((0, 0, {
                    'product_id': pid,
                    'location_id': lid,
                    'theoretical_qty': qty,
                    'physical_qty': 0.0,
                    'uom_id': product.uom_id.id,
                    'product_type': product_type,
                    'sale_price': product.lst_price,
                }))

        if new_lines:
            self.write({'line_ids': new_lines})

        self.line_ids._compute_variation_qty()

    # def action_load_products(self):
    #     """
    #     Load products and their theoretical quantities from stock quants.
    #     Creates or updates variation lines based on current warehouse stock.
    #     """
    #     self.ensure_one()
    #     if not self.warehouse_ids:
    #         raise UserError(_("Please select a warehouse before loading products."))

    #     # Find all internal locations under the selected warehouse
    #     root_loc = self.warehouse_ids.lot_stock_id
    #     domain = [('id', 'child_of', root_loc.id), ('usage', '=', 'internal')]
    #     locations = self.env['stock.location'].search(domain)
    #     if not locations:
    #         raise UserError(_("No internal locations found for the selected warehouse."))

    #     # Fetch quants and aggregate quantities by product and location
    #     quants = self.env['stock.quant'].search([('location_id', 'in', locations.ids)])
    #     product_quant_map = {}
    #     for q in quants:
    #         key = (q.product_id.id, q.location_id.id)
    #         product_quant_map[key] = product_quant_map.get(key, 0.0) + q.quantity

    #     # Check for existing lines and update or create new ones
    #     existing = {(l.product_id.id, l.location_id.id): l for l in self.line_ids}
    #     new_lines = []
    #     for (pid, lid), qty in product_quant_map.items():
    #         if (pid, lid) in existing:
    #             existing[(pid, lid)].theoretical_qty = qty
    #         else:
    #             new_lines.append((0, 0, {
    #                 'product_id': pid,
    #                 'location_id': lid,
    #                 'theoretical_qty': qty,
    #                 'physical_qty': 0.0,
    #                 'uom_id': self.env['product.product'].browse(pid).uom_id.id,
    #             }))

    #     # Write new lines if any and recompute variation
    #     if new_lines:
    #         self.write({'line_ids': new_lines})
    #     self.line_ids._compute_variation_qty()

    def action_compute_variance(self):
        """
        Recompute variation quantities for all lines.
        Ensures the variation field is updated based on current data.
        """
        self.ensure_one()
        # Trigger computation of variation quantity for each line
        self.line_ids._compute_variation_qty()

    def action_confirm(self):
        """
        Confirm the inventory variation session.
        Changes state from 'draft' to 'confirmed' if validation passes.
        """
        self.ensure_one()
        # Ensure record is still in draft state before confirming
        if self.state != 'draft':
            raise UserError(_("Only draft sessions can be confirmed."))
        # Update state to confirmed
        self.state = 'confirmed'
        
        
    def action_create_excel_report(self):
        """
        Generate and download an Excel report for mismatched inventory lines.
        Only lines with non-zero variation will be included in the report.
        """
        self.ensure_one()

        # Filter only lines where variation exists
        mismatched = self.line_ids.filtered(lambda l: float(l.variation_qty) != 0.0)
        if not mismatched:
            raise UserError(_("No mismatched lines to report."))

        # Prepare Excel output buffer
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet("Inventory Variation Report")

        # Define cell formatting styles
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 18,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#1F4E78',
            'font_color': 'white',
            'border': 1
        })
        info_format_label = workbook.add_format({'bold': True, 'bg_color': '#BDD7EE', 'border': 1})
        info_format_value = workbook.add_format({'bg_color': '#DDEBF7', 'border': 1})
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1, 'align': 'center'})
        row_format = workbook.add_format({'border': 1})

        # ADDED: format for warehouse names outside the info box
        warehouse_text_format = workbook.add_format({
            'bold': True,
            'font_size': 11,
            'align': 'left',
            'valign': 'vcenter'
        })

        # Shift report content two columns to the right for better layout
        shift_col = 2

        # CHANGED: increased merge range because more columns are added
        sheet.merge_range(
            0, shift_col, 0, shift_col + 7,
            f"{self.company_id.name if self.company_id else 'Company'} - Inventory Variation Report",
            title_format
        )

        # ADDED: show selected warehouse names outside the info box
        warehouse_names = ', '.join(self.warehouse_ids.mapped('name')) if self.warehouse_ids else ''
        sheet.write(1, shift_col, f"Warehouses: {warehouse_names}", warehouse_text_format)

        # Add basic info fields (company, date, reference)
        # CHANGED: removed warehouse from info box
        info_start_row = 2
        info_pairs = [
            ('Company:', self.company_id.name if self.company_id else ''),
            ('Date:', str(self.date) if self.date else ''),
            ('Reference:', self.name),
        ]

        # Write info in layout
        for i in range(0, len(info_pairs), 2):
            row = info_start_row + i // 2
            col = shift_col + 1
            for j in range(2):
                if i + j < len(info_pairs):
                    label, value = info_pairs[i + j]
                    sheet.write(row, col, label, info_format_label)
                    sheet.write(row, col + 1, value, info_format_value)
                    col += 2

        # Add table headers for product data
        table_start_row = info_start_row + (len(info_pairs) + 1) // 2 + 2

        # CHANGED: added Product Type and Sale Price columns
        table_headers = [
            'Product Code',
            'Product Name',
            'Product Type',
            'Sale Price',
            'Location',
            'Theoretical Qty',
            'Physical Qty',
            'Variation'
        ]
        for col_offset, header in enumerate(table_headers):
            sheet.write(table_start_row, shift_col + col_offset, header, header_format)

        # Populate report rows with mismatched data
        for row_idx, line in enumerate(mismatched, start=table_start_row + 1):
            # ADDED: set product type based on finished_good field
            product_type = 'Finished' if line.product_id.is_finished_good else 'Raw Material'

            # CHANGED: added product type and sale price values
            sheet.write(row_idx, shift_col + 0, line.product_id.default_code or '', row_format)
            sheet.write(row_idx, shift_col + 1, line.product_id.name or '', row_format)
            sheet.write(row_idx, shift_col + 2, product_type, row_format)
            sheet.write(row_idx, shift_col + 3, line.product_id.lst_price or 0.0, row_format)
            sheet.write(row_idx, shift_col + 4, line.location_id.complete_name or '', row_format)
            sheet.write(row_idx, shift_col + 5, line.theoretical_qty, row_format)
            sheet.write(row_idx, shift_col + 6, line.physical_qty, row_format)
            sheet.write(row_idx, shift_col + 7, line.variation_qty, row_format)

        # CHANGED: adjusted column widths for new columns
        sheet.set_column(shift_col + 0, shift_col + 0, 18)  # Product Code
        sheet.set_column(shift_col + 1, shift_col + 1, 35)  # Product Name
        sheet.set_column(shift_col + 2, shift_col + 2, 18)  # Product Type
        sheet.set_column(shift_col + 3, shift_col + 3, 15)  # Sale Price
        sheet.set_column(shift_col + 4, shift_col + 4, 25)  # Location
        sheet.set_column(shift_col + 5, shift_col + 7, 18)  # Qty columns

        # Finalize workbook and reset buffer
        workbook.close()
        output.seek(0)

        # Save Excel file as an attachment
        file_name = f'Inventory_Variation_Report_{self.name}.xlsx'
        attachment = self.env['ir.attachment'].create({
            'name': file_name,
            'type': 'binary',
            'datas': base64.b64encode(output.read()),
            'store_fname': file_name,
            'res_model': self._name,
            'res_id': self.id,
        })

        # Update session state to reported
        self.state = 'reported'

        # Return action to download the generated file
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }

    # def action_create_excel_report(self):
    #     """
    #     Generate and download an Excel report for mismatched inventory lines.
    #     Only lines with non-zero variation will be included in the report.
    #     """
    #     self.ensure_one()

    #     # Filter only lines where variation exists
    #     mismatched = self.line_ids.filtered(lambda l: float(l.variation_qty) != 0.0)
    #     if not mismatched:
    #         raise UserError(_("No mismatched lines to report."))

    #     # Prepare Excel output buffer
    #     output = io.BytesIO()
    #     workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    #     sheet = workbook.add_worksheet("Inventory Variation Report")

    #     # Define cell formatting styles
    #     title_format = workbook.add_format({
    #         'bold': True,
    #         'font_size': 18,
    #         'align': 'center',
    #         'valign': 'vcenter',
    #         'bg_color': '#1F4E78',
    #         'font_color': 'white',
    #         'border': 1
    #     })
    #     info_format_label = workbook.add_format({'bold': True, 'bg_color': '#BDD7EE', 'border': 1})
    #     info_format_value = workbook.add_format({'bg_color': '#DDEBF7', 'border': 1})
    #     header_format = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1, 'align': 'center'})
    #     row_format = workbook.add_format({'border': 1})

    #     # Shift report content two columns to the right for better layout
    #     shift_col = 2

    #     # Add merged report title with company name
    #     sheet.merge_range(
    #         0, shift_col, 0, shift_col + 5,
    #         f"{self.company_id.name if self.company_id else 'Company'} - Inventory Variation Report",
    #         title_format
    #     )

    #     # Add basic info fields (company, warehouse, date, reference)
    #     info_start_row = 2
    #     info_pairs = [
    #         ('Company:', self.company_id.name if self.company_id else ''),
    #         # Changes are Here For Ware House Field To Show Multiple Warehouses
    #         ('Warehouse:', ', '.join(self.warehouse_ids.mapped('name')) if self.warehouse_ids else ''),
    #         ('Date:', str(self.date) if self.date else ''),
    #         ('Reference:', self.name),
    #     ]

    #     # Write info in a 2x2 table layout
    #     for i in range(0, len(info_pairs), 2):
    #         row = info_start_row + i // 2
    #         col = shift_col + 1
    #         for j in range(2):
    #             if i + j < len(info_pairs):
    #                 label, value = info_pairs[i + j]
    #                 sheet.write(row, col, label, info_format_label)
    #                 sheet.write(row, col + 1, value, info_format_value)
    #                 col += 2

    #     # Add table headers for product data
    #     table_start_row = info_start_row + (len(info_pairs) + 1) // 2 + 1
    #     table_headers = ['Product Code', 'Product Name', 'Location', 'Theoretical Qty', 'Physical Qty', 'Variation']
    #     for col_offset, header in enumerate(table_headers):
    #         sheet.write(table_start_row, shift_col + col_offset, header, header_format)

    #     # Populate report rows with mismatched data
    #     for row_idx, line in enumerate(mismatched, start=table_start_row + 1):
    #         sheet.write(row_idx, shift_col + 0, line.product_id.default_code or '', row_format)
    #         sheet.write(row_idx, shift_col + 1, line.product_id.name or '', row_format)
    #         sheet.write(row_idx, shift_col + 2, line.location_id.name or '', row_format)
    #         sheet.write(row_idx, shift_col + 3, line.theoretical_qty, row_format)
    #         sheet.write(row_idx, shift_col + 4, line.physical_qty, row_format)
    #         sheet.write(row_idx, shift_col + 5, line.variation_qty, row_format)

    #     # Adjust column widths for better readability
    #     for i in range(6):
    #         if i == 0:
    #             sheet.set_column(shift_col + i, shift_col + i, 18)
    #         elif i == 1:
    #             sheet.set_column(shift_col + i, shift_col + i, 35)
    #         elif i == 2:
    #             sheet.set_column(shift_col + i, shift_col + i, 25)
    #         else:
    #             sheet.set_column(shift_col + i, shift_col + i, 18)

    #     # Finalize workbook and reset buffer
    #     workbook.close()
    #     output.seek(0)

    #     # Save Excel file as an attachment
    #     file_name = f'Inventory_Variation_Report_{self.name}.xlsx'
    #     attachment = self.env['ir.attachment'].create({
    #         'name': file_name,
    #         'type': 'binary',
    #         'datas': base64.b64encode(output.read()),
    #         'store_fname': file_name,
    #         'res_model': self._name,
    #         'res_id': self.id,
    #     })

    #     # Update session state to reported
    #     self.state = 'reported'

    #     # Return action to download the generated file
    #     return {
    #         'type': 'ir.actions.act_url',
    #         'url': f'/web/content/{attachment.id}?download=true',
    #         'target': 'new',
    #     }

    def action_download_pdf_report(self):
        """
        Return action to download PDF report for inventory variation.
        Only includes lines with non-zero variation.
        """
        self.ensure_one()
        if not self.line_ids.filtered(lambda l: l.variation_qty != 0):
            raise UserError(_("No mismatched lines to report."))

        return self.env.ref('hk_inventory_variation.action_report_inventory_variation').report_action(self)


class InventoryVariationLine(models.Model):
    _name = "inventory.variation.line"
    _description = "Inventory Variation Line"
    _order = "product_id"
    _rec_name = 'variation_id'

    variation_id = fields.Many2one('inventory.variation', string='Variation', ondelete='cascade', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    location_id = fields.Many2one('stock.location', string='Location', domain=[('usage', '=', 'internal')])
    uom_id = fields.Many2one('uom.uom', string='UoM')
    theoretical_qty = fields.Float(string='System Qty', digits='Product Unit of Measure', default=0.0)
    physical_qty = fields.Float(string='Physical Qty', digits='Product Unit of Measure', default=0.0)
    variation_qty = fields.Float(string='Variation', digits='Product Unit of Measure', compute='_compute_variation_qty', store=True)
    #Added these Two Fields To Show In The Report
    product_type = fields.Char(string='Product Type')
    sale_price = fields.Float(string='Sale Price')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """
        Auto-update the UoM when the product changes.
        Sets the unit of measure field based on the selected product.
        """
        for rec in self:
            if rec.product_id:
                # Automatically set UoM to the product's default UoM
                rec.uom_id = rec.product_id.uom_id

    @api.depends('physical_qty', 'theoretical_qty')
    def _compute_variation_qty(self):
        """
        Compute the variation quantity for each line.
        Difference = Physical Quantity - Theoretical Quantity.
        """
        for rec in self:
            # Calculate variation, using 0.0 if any field is empty
            rec.variation_qty = (rec.physical_qty or 0.0) - (rec.theoretical_qty or 0.0)
