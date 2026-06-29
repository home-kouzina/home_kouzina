# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import logging
from datetime import timezone

import dateutil.parser

from odoo import api, fields, models


_logger = logging.getLogger(__name__)


class AmazonReturn(models.Model):
    _name = 'amazon.return'
    _description = "Amazon Return"
    _rec_name = 'amazon_rma_id'
    _order = 'return_request_date desc, id desc'
    _check_company_auto = True

    account_id = fields.Many2one(
        string="Amazon Account",
        comodel_name='amazon.account',
        required=True,
        readonly=True,
        ondelete='cascade',
        check_company=True,
    )
    company_id = fields.Many2one(related='account_id.company_id', store=True, readonly=True)
    fulfillment_type = fields.Selection(
        selection=[('fbm', "Fulfillment by Merchant"), ('fba', "Fulfillment by Amazon")],
        required=True,
        default='fbm',
        readonly=True,
    )
    amazon_rma_id = fields.Char(string="Amazon RMA", required=True, readonly=True)
    merchant_rma_id = fields.Char(string="Merchant RMA", readonly=True)
    amazon_order_ref = fields.Char(string="Amazon Order", required=True, readonly=True)
    sale_order_id = fields.Many2one(
        string="Sales Order",
        comodel_name='sale.order',
        readonly=True,
        check_company=True,
    )
    sale_order_line_id = fields.Many2one(
        string="Sales Order Line",
        comodel_name='sale.order.line',
        readonly=True,
        check_company=True,
    )
    product_id = fields.Many2one(
        string="Product",
        comodel_name='product.product',
        readonly=True,
        check_company=True,
    )
    merchant_sku = fields.Char(string="Merchant SKU", required=True, readonly=True)
    asin = fields.Char(string="ASIN", readonly=True)
    item_name = fields.Char(readonly=True)
    return_quantity = fields.Float(readonly=True)
    order_quantity = fields.Float(readonly=True)
    return_reason = fields.Char(readonly=True)
    return_status = fields.Char(readonly=True)
    return_type = fields.Char(readonly=True)
    resolution = fields.Char(readonly=True)
    in_policy = fields.Boolean(readonly=True)
    is_prime = fields.Boolean(readonly=True)
    a_to_z_claim = fields.Char(string="A-to-Z Claim", readonly=True)
    order_date = fields.Datetime(readonly=True)
    return_request_date = fields.Datetime(readonly=True)
    return_delivery_date = fields.Datetime(readonly=True)
    return_carrier = fields.Char(readonly=True)
    tracking_id = fields.Char(readonly=True)
    label_type = fields.Char(readonly=True)
    label_to_be_paid_by = fields.Char(readonly=True)
    currency_id = fields.Many2one(comodel_name='res.currency', readonly=True)
    label_cost = fields.Monetary(readonly=True)
    order_amount = fields.Monetary(readonly=True)
    refunded_amount = fields.Monetary(readonly=True)
    invoice_number = fields.Char(readonly=True)
    safe_t_action_reason = fields.Char(string="Safe-T Action Reason", readonly=True)
    safe_t_claim_id = fields.Char(string="Safe-T Claim ID", readonly=True)
    safe_t_claim_state = fields.Char(string="Safe-T Claim State", readonly=True)
    safe_t_claim_creation_time = fields.Datetime(string="Safe-T Claim Creation Time", readonly=True)
    safe_t_reimbursement_amount = fields.Monetary(
        string="Safe-T Reimbursement Amount", readonly=True
    )
    fnsku = fields.Char(string="FNSKU", readonly=True)
    fulfillment_center_id = fields.Char(string="Fulfillment Center", readonly=True)
    detailed_disposition = fields.Char(string="Disposition", readonly=True)
    license_plate_number = fields.Char(string="LPN", readonly=True)
    customer_comments = fields.Text(readonly=True)

    _sql_constraints = [(
        'unique_amazon_return_line',
        'UNIQUE(account_id, amazon_rma_id, amazon_order_ref, merchant_sku)',
        "An Amazon return line can only be imported once.",
    )]

    @api.model
    def _parse_report_datetime(self, value):
        if not value:
            return False
        try:
            parsed = dateutil.parser.parse(value)
        except (TypeError, ValueError, OverflowError):
            _logger.warning("Could not parse Amazon return report date %r.", value)
            return False
        if parsed.tzinfo:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed

    @api.model
    def _parse_report_float(self, value):
        if not value:
            return 0.0
        try:
            return float(value.replace(',', ''))
        except (AttributeError, TypeError, ValueError):
            _logger.warning("Could not parse Amazon return report number %r.", value)
            return 0.0

    @api.model
    def _parse_report_boolean(self, value):
        return str(value).strip().lower() in ('1', 'true', 'yes', 'y')

    @api.model
    def _prepare_values_from_report_row(self, account, row):
        amazon_order_ref = row.get('order_id')
        merchant_sku = row.get('merchant_sku')
        sale_order = self.env['sale.order'].search(
            [('amazon_order_ref', '=', amazon_order_ref)], limit=1
        )
        offer = self.env['amazon.offer'].search([
            ('account_id', '=', account.id),
            ('sku', '=', merchant_sku),
        ], limit=1)
        sale_order_line = sale_order.order_line.filtered(
            lambda line: line.amazon_offer_id == offer
        )[:1]
        currency = self.env['res.currency'].with_context(active_test=False).search(
            [('name', '=', row.get('currency_code'))], limit=1
        )
        return {
            'account_id': account.id,
            'fulfillment_type': 'fbm',
            'amazon_rma_id': row.get('amazon_rma_id'),
            'merchant_rma_id': row.get('merchant_rma_id'),
            'amazon_order_ref': amazon_order_ref,
            'sale_order_id': sale_order.id,
            'sale_order_line_id': sale_order_line.id,
            'product_id': (sale_order_line.product_id or offer.product_id).id,
            'merchant_sku': merchant_sku,
            'asin': row.get('asin'),
            'item_name': row.get('item_name'),
            'return_quantity': self._parse_report_float(row.get('return_quantity')),
            'order_quantity': self._parse_report_float(row.get('order_quantity')),
            'return_reason': row.get('return_reason'),
            'return_status': row.get('return_request_status'),
            'return_type': row.get('return_type'),
            'resolution': row.get('resolution'),
            'in_policy': self._parse_report_boolean(row.get('in_policy')),
            'is_prime': self._parse_report_boolean(row.get('is_prime')),
            'a_to_z_claim': row.get('a_to_z_claim'),
            'order_date': self._parse_report_datetime(row.get('order_date')),
            'return_request_date': self._parse_report_datetime(row.get('return_request_date')),
            'return_delivery_date': self._parse_report_datetime(row.get('return_delivery_date')),
            'return_carrier': row.get('return_carrier'),
            'tracking_id': row.get('tracking_id'),
            'label_type': row.get('label_type'),
            'label_to_be_paid_by': row.get('label_to_be_paid_by'),
            'currency_id': currency.id,
            'label_cost': self._parse_report_float(row.get('label_cost')),
            'order_amount': self._parse_report_float(row.get('order_amount')),
            'refunded_amount': self._parse_report_float(row.get('refunded_amount')),
            'invoice_number': row.get('invoice_number'),
            'safe_t_action_reason': row.get('safe_t_action_reason'),
            'safe_t_claim_id': row.get('safe_t_claim_id'),
            'safe_t_claim_state': row.get('safe_t_claim_state'),
            'safe_t_claim_creation_time': self._parse_report_datetime(
                row.get('safe_t_claim_creation_time')
            ),
            'safe_t_reimbursement_amount': self._parse_report_float(
                row.get('safe_t_claim_reimbursement_amount')
            ),
        }

    @api.model
    def _import_report_rows(self, account, rows):
        imported_returns = self.env['amazon.return']
        for row in rows:
            required_values = (
                row.get('amazon_rma_id'), row.get('order_id'), row.get('merchant_sku')
            )
            if not all(required_values):
                _logger.warning(
                    "Skipped an incomplete Amazon return report row for account %s: %s",
                    account.id, row,
                )
                continue
            domain = [
                ('account_id', '=', account.id),
                ('amazon_rma_id', '=', row['amazon_rma_id']),
                ('amazon_order_ref', '=', row['order_id']),
                ('merchant_sku', '=', row['merchant_sku']),
            ]
            amazon_return = self.search(domain, limit=1)
            values = self._prepare_values_from_report_row(account, row)
            if amazon_return:
                amazon_return.write(values)
            else:
                amazon_return = self.create(values)
            imported_returns |= amazon_return
        return imported_returns

    @api.model
    def _get_fba_reference(self, row):
        """Build a stable technical reference for an FBA return report row."""
        reference_values = (
            row.get('return_date', ''),
            row.get('order_id', ''),
            row.get('sku', ''),
            row.get('fnsku', ''),
            row.get('fulfillment_center_id', ''),
            row.get('license_plate_number', ''),
            row.get('detailed_disposition', ''),
            row.get('reason', ''),
        )
        digest = hashlib.sha1(  # noqa: S324 - used as a stable identifier, not for security.
            '\N{UNIT SEPARATOR}'.join(reference_values).encode(),
            usedforsecurity=False,
        ).hexdigest()[:20]
        return f"FBA-{digest}"

    @api.model
    def _prepare_values_from_fba_report_row(self, account, row, fba_reference):
        amazon_order_ref = row.get('order_id')
        merchant_sku = row.get('sku')
        sale_order = self.env['sale.order'].search(
            [('amazon_order_ref', '=', amazon_order_ref)], limit=1
        )
        offer = self.env['amazon.offer'].search([
            ('account_id', '=', account.id),
            ('sku', '=', merchant_sku),
        ], limit=1)
        sale_order_line = sale_order.order_line.filtered(
            lambda line: line.amazon_offer_id == offer
        )[:1]
        return {
            'account_id': account.id,
            'fulfillment_type': 'fba',
            'amazon_rma_id': fba_reference,
            'amazon_order_ref': amazon_order_ref,
            'sale_order_id': sale_order.id,
            'sale_order_line_id': sale_order_line.id,
            'product_id': (sale_order_line.product_id or offer.product_id).id,
            'merchant_sku': merchant_sku,
            'asin': row.get('asin'),
            'fnsku': row.get('fnsku'),
            'item_name': row.get('product_name'),
            'return_quantity': self._parse_report_float(row.get('quantity')),
            'return_reason': row.get('reason'),
            'return_status': row.get('status'),
            'return_type': 'FBA',
            'return_request_date': self._parse_report_datetime(row.get('return_date')),
            'fulfillment_center_id': row.get('fulfillment_center_id'),
            'detailed_disposition': row.get('detailed_disposition'),
            'license_plate_number': row.get('license_plate_number'),
            'customer_comments': row.get('customer_comments'),
        }

    @api.model
    def _import_fba_report_rows(self, account, rows):
        imported_returns = self.env['amazon.return']
        for row in rows:
            required_values = (row.get('return_date'), row.get('order_id'), row.get('sku'))
            if not all(required_values):
                _logger.warning(
                    "Skipped an incomplete Amazon FBA return report row for account %s: %s",
                    account.id, row,
                )
                continue
            fba_reference = self._get_fba_reference(row)
            amazon_return = self.search([
                ('account_id', '=', account.id),
                ('amazon_rma_id', '=', fba_reference),
                ('amazon_order_ref', '=', row['order_id']),
                ('merchant_sku', '=', row['sku']),
            ], limit=1)
            values = self._prepare_values_from_fba_report_row(
                account, row, fba_reference
            )
            if amazon_return:
                amazon_return.write(values)
            else:
                amazon_return = self.create(values)
            imported_returns |= amazon_return
        return imported_returns
