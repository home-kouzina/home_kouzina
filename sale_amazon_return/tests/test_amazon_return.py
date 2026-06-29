# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from unittest.mock import patch

from odoo import Command
from odoo.tests.common import tagged

from odoo.addons.sale_amazon.tests import common


@tagged('post_install', '-at_install')
class TestAmazonReturn(common.TestAmazonCommon):

    def setUp(self):
        super().setUp()
        partner = self.env['res.partner'].create({'name': "Amazon return customer"})
        self.order = self.env['sale.order'].create({
            'partner_id': partner.id,
            'amazon_order_ref': '123-1234567-1234567',
            'order_line': [Command.create({
                'product_id': self.product.id,
                'product_uom_qty': 2,
                'amazon_offer_id': self.offer.id,
                'amazon_item_ref': 'RETURN-ITEM-1',
            })],
        })
        self.report = (
            "Order ID\tReturn request date\tReturn request status\tAmazon RMA ID\t"
            "Merchant SKU\tASIN\tItem Name\tReturn quantity\tReturn Reason\tIn policy\t"
            "Resolution\tCurrency code\tRefunded Amount\n"
            "123-1234567-1234567\t2026-06-20T10:00:00Z\tApproved\tRMA-123\t"
            "TESTING_SKU\tASIN-1\tTest item\t1\tNo longer needed\ttrue\tRefund\tUSD\t12.50\n"
        )
        self.fba_report = (
            "return-date\torder-id\tsku\tasin\tfnsku\tproduct-name\tquantity\t"
            "fulfillment-center-id\tdetailed-disposition\treason\tstatus\t"
            "license-plate-number\tcustomer-comments\n"
            "2026-06-28T05:45:35+00:00\t123-1234567-1234567\tTESTING_SKU\t"
            "ASIN-1\tFNSKU-1\tTest item\t1\tBLR7\tSELLABLE\tUNDELIVERABLE\t"
            "Unit returned to inventory\tLPN-1\tPackage was undeliverable\n"
        )

    def test_import_return_report_and_update_existing_record(self):
        self.account.write({
            'return_report_id': 'REPORT-1',
            'return_report_status': 'IN_QUEUE',
            'return_report_start': datetime(2026, 6, 1),
            'return_report_end': datetime(2026, 6, 21),
        })
        with patch(
            'odoo.addons.sale_amazon.utils.make_sp_api_request',
            return_value={'processingStatus': 'DONE', 'reportDocumentId': 'DOCUMENT-1'},
        ), patch(
            'odoo.addons.sale_amazon_return.utils.download_restricted_report_document',
            return_value=self.report,
        ):
            self.account._process_return_report()

        amazon_return = self.env['amazon.return'].search([('amazon_rma_id', '=', 'RMA-123')])
        self.assertEqual(len(amazon_return), 1)
        self.assertEqual(amazon_return.sale_order_id, self.order)
        self.assertEqual(amazon_return.sale_order_line_id, self.order.order_line)
        self.assertEqual(amazon_return.product_id, self.product)
        self.assertEqual(amazon_return.return_quantity, 1)
        self.assertEqual(amazon_return.refunded_amount, 12.50)
        self.assertFalse(self.account.return_report_id)

        updated_report = self.report.replace('\tApproved\t', '\tReceived\t')
        self.account.write({
            'return_report_id': 'REPORT-2',
            'return_report_status': 'IN_QUEUE',
            'return_report_end': datetime(2026, 6, 22),
        })
        with patch(
            'odoo.addons.sale_amazon.utils.make_sp_api_request',
            return_value={'processingStatus': 'DONE', 'reportDocumentId': 'DOCUMENT-2'},
        ), patch(
            'odoo.addons.sale_amazon_return.utils.download_restricted_report_document',
            return_value=updated_report,
        ):
            self.account._process_return_report()

        self.assertEqual(
            self.env['amazon.return'].search_count([('amazon_rma_id', '=', 'RMA-123')]), 1
        )
        self.assertEqual(amazon_return.return_status, 'Received')

    def test_request_flat_file_return_report(self):
        with patch(
            'odoo.addons.sale_amazon.utils.make_sp_api_request',
            return_value={'reportId': 'REPORT-1'},
        ) as request_mock:
            self.account._request_return_report(days=1)

        request_payload = request_mock.call_args.kwargs['payload']
        self.assertEqual(
            request_payload['reportType'], 'GET_FLAT_FILE_RETURNS_DATA_BY_RETURN_DATE'
        )
        self.assertEqual(request_payload['marketplaceIds'], [self.marketplace.api_ref])
        self.assertEqual(self.account.return_report_id, 'REPORT-1')

    def test_request_fba_return_report(self):
        with patch(
            'odoo.addons.sale_amazon.utils.make_sp_api_request',
            return_value={'reportId': 'FBA-REPORT-1'},
        ) as request_mock:
            self.account._request_fba_return_report(days=60)

        request_payload = request_mock.call_args.kwargs['payload']
        self.assertEqual(
            request_payload['reportType'], 'GET_FBA_FULFILLMENT_CUSTOMER_RETURNS_DATA'
        )
        self.assertEqual(request_payload['marketplaceIds'], [self.marketplace.api_ref])
        self.assertEqual(self.account.fba_return_report_id, 'FBA-REPORT-1')

    def test_import_fba_return_report_and_prevent_duplicates(self):
        self.order.amazon_channel = 'fba'
        self.account.write({
            'fba_return_report_id': 'FBA-REPORT-1',
            'fba_return_report_status': 'IN_QUEUE',
            'fba_return_report_start': datetime(2026, 4, 30),
            'fba_return_report_end': datetime(2026, 6, 29),
        })
        with patch(
            'odoo.addons.sale_amazon.utils.make_sp_api_request',
            return_value={'processingStatus': 'DONE', 'reportDocumentId': 'FBA-DOCUMENT-1'},
        ), patch(
            'odoo.addons.sale_amazon_return.utils.download_restricted_report_document',
            return_value=self.fba_report,
        ):
            self.account._process_fba_return_report()

        amazon_return = self.env['amazon.return'].search([
            ('amazon_order_ref', '=', '123-1234567-1234567'),
            ('fulfillment_type', '=', 'fba'),
        ])
        self.assertEqual(len(amazon_return), 1)
        self.assertEqual(amazon_return.sale_order_id, self.order)
        self.assertEqual(amazon_return.sale_order_line_id, self.order.order_line)
        self.assertEqual(amazon_return.product_id, self.product)
        self.assertEqual(amazon_return.fnsku, 'FNSKU-1')
        self.assertEqual(amazon_return.fulfillment_center_id, 'BLR7')
        self.assertEqual(amazon_return.detailed_disposition, 'SELLABLE')
        self.assertEqual(amazon_return.return_reason, 'UNDELIVERABLE')
        self.assertEqual(amazon_return.return_quantity, 1)
        self.assertEqual(self.account.last_fba_return_report_rows, 1)
        self.assertFalse(self.account.fba_return_report_id)

        self.account.write({
            'fba_return_report_id': 'FBA-REPORT-2',
            'fba_return_report_status': 'IN_QUEUE',
            'fba_return_report_end': datetime(2026, 6, 29),
        })
        with patch(
            'odoo.addons.sale_amazon.utils.make_sp_api_request',
            return_value={'processingStatus': 'DONE', 'reportDocumentId': 'FBA-DOCUMENT-2'},
        ), patch(
            'odoo.addons.sale_amazon_return.utils.download_restricted_report_document',
            return_value=self.fba_report,
        ):
            self.account._process_fba_return_report()

        self.assertEqual(
            self.env['amazon.return'].search_count([
                ('amazon_order_ref', '=', '123-1234567-1234567'),
                ('fulfillment_type', '=', 'fba'),
            ]),
            1,
        )
