import base64
import io
from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import UserError
import xlsxwriter
from openpyxl import load_workbook


class MarketplaceImportLog(models.TransientModel):
    _name = "marketplace.import.log"
    _description = "Marketplace Import Log"
    _rec_name = 'wizard_id'

    wizard_id = fields.Many2one('marketplace.order.import.wizard', string='Wizard')
    row_index = fields.Integer(string='Row #')
    status = fields.Selection([('success', 'Success'), ('failed', 'Failed'), ('warning', 'Warning')], string='Status')
    message = fields.Text(string='Message')


class MarketplaceOrderImportWizard(models.TransientModel):
    _name = 'marketplace.order.import.wizard'
    _description = 'Import Marketplace Orders from XLSX'
    _rec_name = 'marketplace_id'

    marketplace_id = fields.Many2one('marketplace.master', string='Marketplace', required=True)
    xlsx_file = fields.Binary(string='Upload XLSX File', required=True)
    xlsx_filename = fields.Char(string='Filename')
    confirm_orders = fields.Boolean(string='Confirm Created Orders', default=False)
    create_customer_if_missing = fields.Boolean(string='Create Customers if Missing', default=True)
    log_ids = fields.One2many('marketplace.import.log', 'wizard_id', string='Import Log')
    report_file = fields.Binary(string='Failed Orders Report')
    report_filename = fields.Char(string='Report Filename')

    # Expected default headers
    DEFAULT_EXPECTED_HEADERS = [
        'marketplace_order_id', 'customer_email', 'customer_name',
        'billing_street', 'billing_city', 'billing_zip',
        'order_date', 'product_sku', 'quantity', 'unit_price',
        'order_line_note','marketplace_invoice_number',
        'marketplace_invoice_type','marketplace_sale_state'
    ]

    # Map user-friendly Excel headers to internal field names
    HEADER_MAP = {
        'Marketplace Order ID': 'marketplace_order_id',
        'Customer Email': 'customer_email',
        'Customer Name': 'customer_name',
        'Billing Street': 'billing_street',
        'Billing City': 'billing_city',
        'Billing State': 'billing_state',
        'Billing Zip': 'billing_zip',
        'Order Date': 'order_date',
        'Product SKU': 'product_sku',
        'Product Name': 'product_name',
        'Quantity': 'quantity',
        'Unit Price': 'unit_price',
        'Order Line Note': 'order_line_note',
        'Tax Percent': 'tax_percent',
        'Shipping Amount': 'shipping_amount',
        'Currency': 'currency',
        'Order Tag': 'order_tag',
        'Order ID': 'marketplace_order_ref',
        'Marketplace Order Date': 'marketplace_order_date',
        'Payment Status': 'marketplace_payment_status',
        'Order Status': 'marketplace_order_status',
        'Delivery Slot': 'marketplace_delivery_slot',
        'Total Amount': 'marketplace_total_amount',
        # Marketplace-specific template headers now map to common sale order fields.
        'Flipkart Order ID': 'marketplace_order_ref',
        'Flipkart Order Date': 'marketplace_order_date',
        'Flipkart Payment Status': 'marketplace_payment_status',
        'Flipkart Order Status': 'marketplace_order_status',
        'Flipkart Total Amount': 'marketplace_total_amount',
        'Amazon Order ID': 'marketplace_order_ref',
        'Amazon Order Date': 'marketplace_order_date',
        'Amazon Payment Status': 'marketplace_payment_status',
        'Amazon Order Status': 'marketplace_order_status',
        'Amazon Total Amount': 'marketplace_total_amount',
        'Blinkit Order ID': 'marketplace_order_ref',
        'Blinkit Order Date': 'marketplace_order_date',
        'Blinkit Delivery Slot': 'marketplace_delivery_slot',
        'Blinkit Payment Status': 'marketplace_payment_status',
        'Blinkit Order Status': 'marketplace_order_status',
        'Blinkit Total Amount': 'marketplace_total_amount',
        'Shopify Order ID': 'marketplace_order_ref',
        'Shopify Order Date': 'marketplace_order_date',
        'Shopify Payment Status': 'marketplace_payment_status',
        'Shopify Order Status': 'marketplace_order_status',
        'Shopify Total Amount': 'marketplace_total_amount',
        #...............INVOICE,,,,,,,,,,
        'Invoice Number': 'marketplace_invoice_number',
        'Invoice Type': 'marketplace_invoice_type',
        'State of Sale': 'marketplace_sale_state',
    }

    @api.onchange('xlsx_file')
    def _onchange_xlsx_file(self):
        if not self.xlsx_file:
            self.report_file = False
            self.report_filename = False

    # -------------------------------------------------------------
    # MAIN VALIDATOR ENTRY
    # -------------------------------------------------------------
    def _validate_row(self, row, index):
        """
        Validate a single order line (row) from import data.
        Returns a comma-separated string of errors.
        """
        errors = []
        try:
            errors += self._validate_basic_fields(row)
            errors += self._validate_customer_fields(row)
            errors += self._validate_address_fields(row)
            errors += self._validate_product_fields(row)
            errors += self._validate_pricing_fields(row)
            errors += self._validate_misc_fields(row)
            errors += self._validate_csv_injection(row)
        except Exception as e:
            errors.append(f"Unexpected error in row {index}: {str(e)}")

        return ', '.join(errors)

    # -------------------------------------------------------------
    # SUB-VALIDATION BLOCKS
    # -------------------------------------------------------------
    def _validate_basic_fields(self, row):
        """Validate core order identifiers and date."""
        errors = []
        try:
            marketplace_order_id = row.get('marketplace_order_id')
            if not marketplace_order_id:
                errors.append('Missing marketplace_order_id')
            elif not isinstance(marketplace_order_id, str):
                errors.append('marketplace_order_id must be a string')

            order_date = row.get('order_date')
            if not order_date:
                errors.append('Missing order_date')
            else:
                if not isinstance(order_date, str):
                    errors.append('order_date must be a string in YYYY-MM-DD format')
                else:
                    try:
                        datetime.strptime(order_date, '%Y-%m-%d')
                    except ValueError:
                        errors.append('order_date must be in YYYY-MM-DD format')
        except Exception as e:
            errors.append(f"Error validating basic fields: {str(e)}")
        return errors

    def _validate_customer_fields(self, row):
        """Validate customer information."""
        errors = []
        try:
            customer_name = row.get('customer_name')
            if not customer_name:
                errors.append('Missing customer_name')
            elif not isinstance(customer_name, str):
                errors.append('customer_name must be a string')

            customer_email = row.get('customer_email')
            if not customer_email:
                errors.append('Missing customer_email')
            elif not isinstance(customer_email, str):
                errors.append('customer_email must be a string')
            elif '@' not in customer_email:
                errors.append('Invalid email format')
        except Exception as e:
            errors.append(f"Error validating customer fields: {str(e)}")
        return errors

    def _validate_address_fields(self, row):
        """Validate billing address fields."""
        errors = []
        try:
            for field in ['billing_street', 'billing_city', 'billing_state']:
                value = row.get(field)
                if not value:
                    errors.append(f"Missing {field}")
                elif not isinstance(value, str):
                    errors.append(f"{field} must be a string")

            billing_zip = row.get('billing_zip')
            if not billing_zip:
                errors.append('Missing billing_zip')
            elif not str(billing_zip).isdigit():
                errors.append('billing_zip must be numeric')
        except Exception as e:
            errors.append(f"Error validating address fields: {str(e)}")
        return errors

    def _validate_product_fields(self, row):
        """Validate product details and SKU mapping."""
        errors = []
        try:
            product_sku = row.get('product_sku')
            if not product_sku:
                errors.append('Missing product_sku')
            elif not isinstance(product_sku, str):
                errors.append('product_sku must be a string')
            else:
                # Optional: check if SKU exists in product.product
                product = self.env['product.product'].search([('default_code', '=', product_sku)], limit=1)
                if not product:
                    errors.append(f"Product with SKU '{product_sku}' not found")

            product_name = row.get('product_name')
            if not product_name:
                errors.append('Missing product_name')
            elif not isinstance(product_name, str):
                errors.append('product_name must be a string')

            quantity = row.get('quantity')
            if quantity is None or str(quantity).strip() == '':
                errors.append('Missing quantity')
            else:
                try:
                    qty = float(quantity)
                    if qty <= 0:
                        errors.append('quantity must be greater than 0')
                except ValueError:
                    errors.append('quantity must be a number')
        except Exception as e:
            errors.append(f"Error validating product fields: {str(e)}")
        return errors

    def _validate_pricing_fields(self, row):
        """Validate pricing-related fields."""
        errors = []
        try:
            unit_price = row.get('unit_price')
            if unit_price is None or str(unit_price).strip() == '':
                errors.append('Missing unit_price')
            else:
                try:
                    price = float(unit_price)
                    if price < 0:
                        errors.append('unit_price cannot be negative')
                except ValueError:
                    errors.append('unit_price must be a number')

            tax_percent = row.get('tax_percent')
            if tax_percent is None or str(tax_percent).strip() == '':
                errors.append('Missing tax_percent')
            else:
                try:
                    tax = float(tax_percent)
                    if tax < 0:
                        errors.append('tax_percent cannot be negative')
                except ValueError:
                    errors.append('tax_percent must be a number')

            shipping_amount = row.get('shipping_amount')
            if shipping_amount is None or str(shipping_amount).strip() == '':
                errors.append('Missing shipping_amount')
            else:
                try:
                    shipping = float(shipping_amount)
                    if shipping < 0:
                        errors.append('shipping_amount cannot be negative')
                except ValueError:
                    errors.append('shipping_amount must be a number')
        except Exception as e:
            errors.append(f"Error validating pricing fields: {str(e)}")
        return errors

    def _validate_misc_fields(self, row):
        """Validate tags and optional fields."""
        errors = []
        try:
            currency = row.get('currency')
            if not currency:
                errors.append('Missing currency')
            elif not isinstance(currency, str):
                errors.append('currency must be a string')

            order_line_note = row.get('order_line_note')
            if order_line_note and not isinstance(order_line_note, str):
                errors.append('order_line_note must be a string')

            order_tag = row.get('order_tag')
            if not order_tag:
                errors.append('Missing order_tag')
            elif not isinstance(order_tag, str):
                errors.append('order_tag must be a string')
        except Exception as e:
            errors.append(f"Error validating misc fields: {str(e)}")
        return errors

    def _validate_csv_injection(self, row):
        """
        Protect against CSV/Excel injection.
        Escape fields that start with '=', '+', '-', '@'.
        """
        errors = []
        try:
            dangerous_prefixes = ('=', '+', '-', '@')
            for key, value in row.items():
                if isinstance(value, str) and value.startswith(dangerous_prefixes):
                    errors.append(f"Incorrect injection in field '{key}'")
        except Exception as e:
            errors.append(f"Error checking CSV injection: {str(e)}")
        return errors

    # -------------------------------------------------------------
    # PER-ORDER CHECKS (optional, to be run after grouping rows)
    # -------------------------------------------------------------
    def _validate_order_consistency(self, order_lines):
        """
        Validate consistency across multiple lines of the same order.
        Example: addresses match, same warehouse, etc.
        """
        errors = []
        try:
            order_ids = set(line.get('marketplace_order_id') for line in order_lines)
            if len(order_ids) > 1:
                errors.append("Multiple order IDs in one batch block")

            first_addr = order_lines[0].get('billing_city')
            for line in order_lines:
                if line.get('billing_city') != first_addr:
                    errors.append("Inconsistent billing_city across order lines")

            # Example: warehouse mapping
            for line in order_lines:
                marketplace = line.get('marketplace_name')
                if marketplace:
                    master = self.env['marketplace.master'].search([('name', '=', marketplace)], limit=1)
                    if not master or not master.warehouse_map:
                        errors.append(f"Missing warehouse_map for marketplace {marketplace}")
        except Exception as e:
            errors.append(f"Error validating order consistency: {str(e)}")
        return errors

        # ----------------- High level orchestrator -----------------

    def action_import_orders(self):
        self.ensure_one()

        # 1) Read & parse file
        try:
            headers, data_rows = self._read_xlsx()
        except Exception as e:
            raise UserError(("Failed to read XLSX file: %s") % str(e))

        # 2) Validate headers (case-insensitive)
        missing = self._validate_headers(headers, self.DEFAULT_EXPECTED_HEADERS)
        if missing:
            raise UserError(("The following required columns are missing or incorrect: %s") % ', '.join(missing))

        # 3) Prepare for import
        # clear previous logs
        if self.log_ids:
            self.log_ids.unlink()

        # ensure Error column exists in headers list for report writing

        if 'Status' not in headers:
            headers = list(headers) + ['Status']

        if 'Error' not in headers:
            headers = list(headers) + ['Error']

        # 4) Pre-validate rows (row-level validation)
        parsed_rows = []
        has_error = False
        for idx, raw in enumerate(data_rows, start=1):
            # convert keys to normalized header names (original header case preserved in headers)
            row = {k: (v if v is not None else '') for k, v in raw.items()}
            row_error = self._validate_row_basic(row, idx)
            row['Error'] = row_error
            parsed_rows.append(row)

            if row_error:
                row['Status'] = 'Failed'
                has_error = True
                self._log_failure(idx, row_error)
            else:
                row['Status'] = 'Success'

        # 5) If any row-level errors -> generate report and return download
        self._generate_report_file(headers, parsed_rows)
        if has_error:
            return {
                'type': 'ir.actions.act_url',
                'url': '/web/content/?model=marketplace.order.import.wizard&field=report_file&id=%s&filename=%s&download=true' % (
                    self.id, self.report_filename),
                'target': 'new',
            }

        # 6) Group rows by marketplace_order_id and process each group transactionally
        grouped = self._group_rows_by_order(parsed_rows)
        created_orders = []
        failed_rows = []
        for marketplace_order_id, group in grouped.items():
            # per-order savepoint so one order failing doesn't roll back others
            try:
                with self.env.cr.savepoint():
                    order_result = self._process_order_group(marketplace_order_id, group)
                    if order_result.get('success'):
                        created_orders.append(order_result.get('order'))
                    else:
                        failed_rows.extend(order_result.get('failed_rows', []))
            except Exception as e:
                # unexpected exception for this order; log all rows as failed
                err_msg = ("Unexpected error: %s") % str(e)
                for idx, _ in group:
                    self._log_failure(idx, err_msg)
                    failed_rows.append((idx, err_msg))

        # 7) Regenerate final report with per-row Error messages and summary
        # refresh rows with latest logs (we kept parsed_rows with Error='' — update with logs)
        final_rows = self._attach_log_messages_to_rows(parsed_rows)
        self._generate_report_file(headers, final_rows, created_orders=created_orders)

        # If there were failures, provide the report for download
        if failed_rows:
            return {
                'type': 'ir.actions.act_url',
                'url': '/web/content/?model=marketplace.order.import.wizard&field=report_file&id=%s&filename=%s&download=true' % (
                    self.id, self.report_filename),
                'target': 'new',
            }

        # All good -> reload and show message
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'params': {
                'message': ("Marketplace orders imported successfully! Created %d orders.") % len(created_orders)}
        }

        # ----------------- File parsing -----------------

    def _read_xlsx(self):
        """Read uploaded xlsx, return (internal_headers, list_of_dict_rows)"""
        if not self.xlsx_file:
            raise UserError(("Please upload an XLSX file."))
        if not (self.xlsx_filename or "").lower().endswith('.xlsx'):
            raise UserError(("Only XLSX files are allowed."))

        file_content = base64.b64decode(self.xlsx_file)
        workbook = load_workbook(filename=io.BytesIO(file_content))
        sheet = workbook.active
        rows = list(sheet.iter_rows(values_only=True))
        if not rows or len(rows) < 2:
            raise UserError(("XLSX file is empty or invalid."))

        # Original headers from Excel
        raw_headers = [str(h).strip() for h in rows[0]]

        # Detect marketplace based on headers
        marketplace = None
        if any(h.startswith('Flipkart') for h in raw_headers):
            marketplace = 'Flipkart'
        elif any(h.startswith('Amazon') for h in raw_headers):
            marketplace = 'Amazon'
        elif any(h.startswith('Blinkit') for h in raw_headers):
            marketplace = 'Blinkit'
        elif any(h.startswith('Shopify') for h in raw_headers):
            marketplace = 'Shopify'

        if not marketplace:
            marketplace = self.marketplace_id.name

        marketplace_id = self.env['marketplace.master'].search([('name', '=', marketplace)], limit=1)
        if not marketplace_id:
            raise UserError(f"Marketplace '{marketplace}' not found in system.")

        if self.marketplace_id.name.strip().lower() != marketplace.strip().lower():
            raise UserError(
                f"Uploaded file belongs to '{marketplace}' marketplace, "
                f"but you selected '{self.marketplace_id.name}'. Please upload the correct file."
            )

        # Map headers to internal field names
        headers = []
        for h in raw_headers:
            mapped = self.HEADER_MAP.get(h, h.strip())
            headers.append(mapped)

        # Read data rows
        data_rows = []
        for r in rows[1:]:
            row_dict = dict(zip(headers, r))
            # Optional: strip strings in row values
            row_dict = {k: (v.strip() if isinstance(v, str) else v) for k, v in row_dict.items()}
            # Include marketplace name for downstream use
            row_dict['marketplace_name'] = marketplace
            data_rows.append(row_dict)

        return headers, data_rows

        # ----------------- Header validation -----------------

    def _validate_headers(self, headers, expected):
        """Case-insensitive check; returns list of missing expected headers (in expected's case)"""
        lower_headers = [h.lower() for h in headers]
        missing = [h for h in expected if h.lower() not in lower_headers]
        return missing

        # ----------------- Row basic validation -----------------

    def _validate_row_basic(self, row, index):
        """
        Validate required fields present and basic parsing.
        Returns '' if OK, else error message string.
        Required per-line: product_sku, quantity. unit_price can be empty and later replaced by product lst_price.
        Also validate numeric fields and date parsing.
        """
        errors = []
        # marketplace_order_id
        if not row.get('marketplace_order_id'):
            errors.append('Missing marketplace_order_id')

        # product_sku
        if not row.get('product_sku'):
            errors.append('Missing product_sku')

        # quantity
        q = row.get('quantity')
        if q in (None, ''):
            errors.append('Missing quantity')
        else:
            try:
                float(str(q))
            except Exception:
                errors.append('Invalid quantity')

        # unit_price optional but if present must be numeric
        up = row.get('unit_price')
        if up not in (None, ''):
            try:
                float(str(up))
            except Exception:
                errors.append('Invalid unit_price')

        # order_date - try parse with datetime if present
        od = row.get('order_date')
        if od not in (None, ''):
            try:
                # openpyxl may give datetime already; otherwise try parsing common formats
                if not isinstance(od, (datetime,)):
                    # try iso
                    od = datetime.fromisoformat(str(od))
            except Exception:
                errors.append('Invalid order_date')

        return '; '.join(errors)

        # ----------------- Grouping -----------------

    def _group_rows_by_order(self, parsed_rows):
        """Return dict: marketplace_order_id -> list of (original_index, rowdict)"""
        groups = {}
        for idx, row in enumerate(parsed_rows, start=1):
            mid = str(row.get('marketplace_order_id') or '').strip()
            row['marketplace_order_id'] = mid
            if mid not in groups:
                groups[mid] = []
            groups[mid].append((idx, row))
        return groups

    def _find_existing_marketplace_order(self, marketplace_order_id, marketplace_type):
        marketplace_order_id = str(marketplace_order_id or '').strip()
        if not marketplace_order_id:
            return self.env['sale.order']

        origin = f"marketplace:{(self.marketplace_id.name or 'unknown')}|{marketplace_order_id}"
        return self.env['sale.order'].search([
            '|',
            ('origin', '=', origin),
            ('marketplace_order_ref', '=', marketplace_order_id),
        ], limit=1)

        # ----------------- Per-order processing -----------------

    def _process_order_group(self, marketplace_order_id, rows):
        """
        Process a single order group within a savepoint.
        Steps:
          - validate all lines in group (we already did basic; do any additional checks)
          - resolve customer
          - create sale.order header
          - create sale.order.lines (log per-row failures)
          - confirm order if configured
        Returns dict {'success': bool, 'order': sale.order record or None, 'failed_rows': [(idx,msg), ...]}
        """
        failed_rows = []

        # a) Extra validation for the group (e.g., check that numeric conversion works)
        for idx, row in rows:
            # re-check quantity & unit_price convertibility
            try:
                row_qty = float(row.get('quantity') or 0)
            except Exception:
                failed_rows.append((idx, 'Quantity is not numeric'))
            try:
                if row.get('unit_price') not in (None, ''):
                    float(row.get('unit_price'))
            except Exception:
                failed_rows.append((idx, 'Unit price is not numeric'))

        if failed_rows:
            for idx, msg in failed_rows:
                self._log_failure(idx, msg)
            return {'success': False, 'failed_rows': failed_rows}

        # b) Resolve or create customer
        first_row = rows[0][1]
        customer = self._resolve_customer(first_row)
        if not customer:
            # mark all rows for this order failed
            msg = 'Customer not found and creation disabled.'
            for idx, _ in rows:
                self._log_failure(idx, msg)
            return {'success': False, 'failed_rows': [(idx, msg) for idx, _ in rows]}

        # c) Check if sale.order already exists
        marketplace_order_id = str(marketplace_order_id or '').strip()
        origin = f"marketplace:{(self.marketplace_id.name or 'unknown')}|{marketplace_order_id}"
        marketplace_type = self.marketplace_id.code or self.marketplace_id._normalize_marketplace_code(
            self.marketplace_id.name
        )
        existing_order = self._find_existing_marketplace_order(marketplace_order_id, marketplace_type)
        if existing_order:
            msg = ("Sale order %s already exists") % existing_order.name
            # mark all rows as failed
            for idx, _ in rows:
                self._log_failure(idx, msg)
            return {'success': False, 'failed_rows': [(idx, msg) for idx, _ in rows]}

        # d) Create order header
        order_vals = {
            'partner_id': customer.id,
            'date_order': first_row.get('order_date') or fields.Datetime.now(),
            'origin': origin,
            # warehouse mapping
            'warehouse_id': (self.marketplace_id.warehouse_map.id if getattr(self.marketplace_id, 'warehouse_map',
                                                                             False) else self.env.ref(
                'stock.warehouse0').id),
            # sales team - keep your previous default
            'team_id': self.env.ref('sales_team.salesteam_website_sales').id,
            'marketplace_type': marketplace_type,
            'marketplace_order_ref': marketplace_order_id,
            'marketplace_order_date': first_row.get('order_date'),
            # 'marketplace_invoice_number': first_row.get('marketplace_invoice_number'),
            # 'marketplace_invoice_type': first_row.get('marketplace_invoice_type'),
            # 'marketplace_invoice_state': first_row.get('marketplace_sale_state'),
        }

        # Tag logic: marketplace specific tag, fallback to marketplace name tag, CSV override 'order_tag' if present
        order_tag_name = None
        csv_tag = first_row.get('order_tag') or ''
        if csv_tag:
            order_tag_name = csv_tag.strip()
        elif getattr(self.marketplace_id, 'so_tag', False):
            # if marketplace has mapping to a tag record
            order_vals['tag_ids'] = [(6, 0, [self.marketplace_id.so_tag.id])]
        else:
            order_tag_name = self.marketplace_id.name or None

        if order_tag_name:
            # find or create tag
            tag = self.env['crm.tag'].search([('name', '=', order_tag_name)], limit=1)
            if not tag:
                tag = self.env['crm.tag'].create({'name': order_tag_name})
            order_vals.setdefault('tag_ids', []).append((4, tag.id))

        # --- Include common marketplace fields if present ---
        marketplace_fields = [
            'marketplace_order_ref', 'marketplace_order_date', 'marketplace_payment_status',
            'marketplace_order_status', 'marketplace_delivery_slot', 'marketplace_total_amount',
            #invoice
            'marketplace_invoice_number','marketplace_invoice_type','marketplace_sale_state'
        ]
        for fld in marketplace_fields:
            if first_row.get(fld):
                order_vals[fld] = first_row.get(fld)
        sale_order = self.env['sale.order'].create(order_vals)

        # e) Create lines
        for idx, row in rows:
            sku = row.get('product_sku')
            product = self.env['product.product'].search([
                '|', ('default_code', '=', sku), ('barcode', '=', sku)
            ], limit=1)

            if not product:
                # Product missing: current behavior = log failure and skip line.
                # TODO: if you want to auto-create a placeholder product, add a wizard option and handle here.
                msg = ("Product %s not found.") % sku
                self._log_failure(idx, msg)
                failed_rows.append((idx, msg))
                continue

            # compute quantity and price (use product list price if unit_price empty)
            try:
                qty = float(row.get('quantity') or 0)
            except Exception:
                qty = 0.0
            try:
                unit_price = float(row.get('unit_price')) if row.get('unit_price') not in (None,
                                                                                           '') else product.lst_price
            except Exception:
                unit_price = product.lst_price

            line_vals = {
                'order_id': sale_order.id,
                'product_id': product.id,
                'product_uom_qty': qty,
                'price_unit': unit_price,
                'name': row.get('order_line_note') or product.name,
            }

            # taxes: if CSV contains tax_percent, try to apply simple tax
            tax_percent = row.get('tax_percent')
            if tax_percent not in (None, ''):
                try:
                    t_pct = float(tax_percent)
                    tax_name = f"{int(t_pct)}% VAT"
                    tax = self.env['account.tax'].search([('amount', '=', t_pct), ('type_tax_use', '=', 'sale')],
                                                         limit=1)
                    if not tax:
                        # create a simple tax (adjust fields as needed for your chart of accounts)
                        tax = self.env['account.tax'].create({
                            'name': tax_name,
                            'amount': t_pct,
                            'type_tax_use': 'sale',
                            'amount_type': 'percent',
                        })
                    if tax:
                        line_vals['tax_id'] = [(6, 0, [tax.id])]
                except Exception:
                    # ignore tax parse errors, not fatal for order creation
                    pass

            self.env['sale.order.line'].create(line_vals)

        # f) Confirm if requested
        if self.confirm_orders:
            try:
                sale_order.action_confirm()
            except Exception as e:
                # confirmation failed -> log but do not rollback entire order unless you want to
                for idx, _ in rows:
                    self._log_failure(idx, ("Failed to confirm order: %s") % str(e))
                return {'success': False, 'order': sale_order, 'failed_rows': [(idx, str(e)) for idx, _ in rows]}

        # g) log success for rows (optional)
        for idx, _ in rows:
            self.env['marketplace.import.log'].create({
                'wizard_id': self.id,
                'row_index': idx,
                'status': 'success',
                'message': ('Order %s created') % sale_order.name,
            })

        return {'success': True, 'order': sale_order, 'failed_rows': failed_rows}

        # ----------------- Customer resolution -----------------

    def _resolve_customer(self, first_row):
        """Search by email, then name. Create if allowed."""
        email = (first_row.get('customer_email') or '').strip()
        name = (first_row.get('customer_name') or '').strip()

        customer = None
        if email:
            customer = self.env['res.partner'].search([('email', '=', email)], limit=1)
        if not customer and name:
            customer = self.env['res.partner'].search([('name', '=', name)], limit=1)

        if not customer and self.create_customer_if_missing:
            partner_vals = {
                'name': name or email or 'Unknown Customer',
                'email': email or False,
                'street': first_row.get('billing_street') or False,
                'city': first_row.get('billing_city') or False,
                'zip': first_row.get('billing_zip') or False,
            }
            customer = self.env['res.partner'].create(partner_vals)

        return customer

        # ----------------- Logging -----------------

    def _log_failure(self, row_index, message):
        """Create or update a log line for a failed row."""
        self.env['marketplace.import.log'].create({
            'wizard_id': self.id,
            'row_index': row_index,
            'status': 'failed',
            'message': str(message),
        })

    # ----------------- Report generation -----------------
    def _generate_report_file(self, headers, rows, created_orders=None):
        """Generate an XLSX report stored on the wizard (report_file/report_filename) with proper Status/Error columns."""
        created_orders = created_orders or []

        output = io.BytesIO()
        workbook_out = xlsxwriter.Workbook(output, {'in_memory': True})

        # Define formats
        header_format = workbook_out.add_format({
            'bold': True,
            'bg_color': '#4F81BD',
            'font_color': 'white',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })

        success_format = workbook_out.add_format({
            'bg_color': '#C6EFCE',  # light green
            'font_color': '#006100',
            'border': 1
        })

        failed_format = workbook_out.add_format({
            'bg_color': '#FFC7CE',  # light red
            'font_color': '#9C0006',
            'border': 1
        })

        default_format = workbook_out.add_format({'border': 1})
        date_format = workbook_out.add_format({'num_format': 'DD-MM-YYYY HH:MM', 'border': 1})

        # Main worksheet
        worksheet = workbook_out.add_worksheet('Import Report')
        worksheet.freeze_panes(1, 0)  # freeze header row

        header_display_map = {
            'marketplace_order_id': 'Marketplace Order ID',
            'order_date': 'Order Date',
            'status': 'Status',
            'error': 'Error'
        }

        # Ensure 'Status' is second-last and 'Error' is last
        headers_lower = [h.lower() for h in headers]
        if 'status' in headers_lower and 'error' in headers_lower:
            headers_sorted = [h for h in headers if h.lower() not in ('status', 'error')]
            headers_sorted += ['Status', 'Error']
        else:
            headers_sorted = headers

        col_widths = [max(len(header_display_map.get(h, h)), 15) for h in headers_sorted]

        # Write headers
        for col_num, header in enumerate(headers_sorted):
            display_name = header_display_map.get(header, header.replace('_', ' ').title())
            worksheet.write(0, col_num, display_name, header_format)

        # Write data rows
        for row_num, row_data in enumerate(rows, start=1):
            # Ensure row_data is a dict
            row_data = dict(row_data)

            # Determine Status and Error values
            if 'error' in row_data and row_data['error']:
                row_data['status'] = 'Failed'
            else:
                row_data['status'] = 'Success'
                row_data['error'] = ''  # clear error if none

            for col_num, column in enumerate(headers_sorted):
                value = row_data.get(column, '')

                # Handle order_date as proper Excel date
                if column.lower() == 'order_date' and value:
                    try:
                        if isinstance(value, str):
                            value_dt = fields.Datetime.from_string(value)
                        else:
                            value_dt = value
                        value = value_dt
                        cell_format = date_format
                    except Exception:
                        value = str(value)
                        cell_format = default_format
                else:
                    cell_format = default_format

                # Apply coloring based on Status/Error
                if column.lower() == 'status':
                    if str(value).lower() == 'success':
                        cell_format = success_format
                    elif str(value).lower() == 'failed':
                        cell_format = failed_format
                elif column.lower() == 'error':
                    cell_format = failed_format if value else success_format

                # Write value
                if column.lower() == 'order_date' and isinstance(value, fields.Datetime):
                    worksheet.write_datetime(row_num, col_num, value, cell_format)
                else:
                    worksheet.write(row_num, col_num, value, cell_format)

                # Adjust column width
                col_widths[col_num] = max(col_widths[col_num], len(str(value)) + 2)

        # Set column widths
        for i, width in enumerate(col_widths):
            worksheet.set_column(i, i, width)

        # Summary sheet
        ws_sum = workbook_out.add_worksheet('Summary')
        summary_header = workbook_out.add_format({
            'bold': True, 'bg_color': '#4BACC6', 'font_color': 'white', 'border': 1
        })
        summary_value = workbook_out.add_format({'border': 1})

        ws_sum.write(0, 0, 'Total Rows', summary_header)
        ws_sum.write(0, 1, len(rows), summary_value)
        ws_sum.write(1, 0, 'Created Orders', summary_header)
        ws_sum.write(1, 1, len(created_orders), summary_value)

        failed_count = self.env['marketplace.import.log'].search_count(
            [('wizard_id', '=', self.id), ('status', '=', 'failed')]
        )
        ws_sum.write(2, 0, 'Failed Rows', summary_header)
        ws_sum.write(2, 1, failed_count, summary_value)

        workbook_out.close()
        output.seek(0)
        self.report_file = base64.b64encode(output.read())

        # Timestamped filename
        current_user_dt = fields.Datetime.context_timestamp(self, fields.Datetime.now())
        self.report_filename = 'Failed_Orders_Report_%s.xlsx' % (
            current_user_dt.strftime('%d-%m-%Y %I.%M %p')
        )

    def _attach_log_messages_to_rows(self, parsed_rows):
        """
        Return a new list of dict rows where each row's 'Error' column is updated
        with messages from marketplace.import.log and Status is marked accordingly.
        """
        # fetch logs for this wizard
        logs = self.env['marketplace.import.log'].search([('wizard_id', '=', self.id)])
        log_map = {}
        for l in logs:
            # assume row_index stored as int
            log_map.setdefault(int(l.row_index), []).append(f"{l.status}: {l.message}")

        final_rows = []
        for idx, row in enumerate(parsed_rows, start=1):
            row_copy = dict(row)
            msgs = log_map.get(idx, [])

            # Merge previous and log-based error messages
            earlier = row_copy.get('Error') or ''
            combined = '; '.join(filter(None, [earlier] + msgs))
            row_copy['Error'] = combined

            if any('fail' in m.lower() or 'error' in m.lower() for m in msgs):
                row_copy['Status'] = 'Failed'
            elif not row_copy.get('Status'):
                row_copy['Status'] = 'Success'

            final_rows.append(row_copy)

        return final_rows
