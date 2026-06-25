# Part of Odoo. See LICENSE file for full copyright and licensing details.

import csv
import io
import logging
import re
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.sale_amazon import const, utils as amazon_utils

from .. import utils as return_utils


_logger = logging.getLogger(__name__)


def _normalize_report_header(header):
    normalized_header = re.sub(r'[^a-z0-9]+', '_', header.strip().lower()).strip('_')
    return normalized_header.replace('safet_', 'safe_t_')


const.API_OPERATIONS_MAPPING.update({
    'createReturnReport': {
        'url_path': '/reports/2021-06-30/reports',
        'restricted_resource_path': None,
    },
    'getReturnReport': {
        'url_path': '/reports/2021-06-30/reports/{param}',
        'restricted_resource_path': None,
    },
})


class AmazonAccount(models.Model):
    _inherit = 'amazon.account'

    last_returns_sync = fields.Datetime(
        string="Last Returns Sync",
        help="The last time an Amazon return report was successfully imported.",
        default=lambda self: fields.Datetime.now() - timedelta(days=1),
        readonly=True,
    )
    return_report_id = fields.Char(readonly=True)
    return_report_status = fields.Selection(
        selection=[
            ('IN_QUEUE', "In Queue"),
            ('IN_PROGRESS', "In Progress"),
            ('DONE', "Done"),
            ('CANCELLED', "Cancelled / No Data"),
            ('FATAL', "Failed"),
        ],
        readonly=True,
    )
    return_report_start = fields.Datetime(readonly=True)
    return_report_end = fields.Datetime(readonly=True)
    return_sync_error = fields.Text(readonly=True)
    return_count = fields.Integer(compute='_compute_return_count')

    @api.depends('company_id')
    def _compute_return_count(self):
        grouped_data = self.env['amazon.return']._read_group(
            [('account_id', 'in', self.ids)], ['account_id'], ['__count']
        )
        counts = {account.id: count for account, count in grouped_data}
        for account in self:
            account.return_count = counts.get(account.id, 0)

    def action_view_returns(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Amazon Returns"),
            'res_model': 'amazon.return',
            'view_mode': 'list,form',
            'domain': [('account_id', '=', self.id)],
            'context': {'create': False, 'delete': False},
        }

    def action_check_return_authorization(self):
        self.ensure_one()
        if self.return_report_id:
            raise UserError(_(
                "A return report is already being processed. Its current status is %s.",
                self.return_report_status or _("waiting"),
            ))
        self._request_return_report(days=60)
        return {
            'effect': {
                'type': 'rainbow_man',
                'message': _(
                    "Amazon accepted the return report request. This confirms report-request "
                    "access; restricted document access will be checked when the report is ready."
                ),
            }
        }

    def action_sync_returns(self):
        self._sync_returns(force=True)
        return {
            'effect': {
                'type': 'rainbow_man',
                'message': _(
                    "Amazon return synchronization was started. Reports are imported "
                    "asynchronously by the scheduled action."
                ),
            }
        }

    def _request_return_report(self, days=60):
        self.ensure_one()
        amazon_utils.ensure_account_is_set_up(self)
        end_time = fields.Datetime.now()
        start_time = end_time - timedelta(days=days)
        payload = {
            'reportType': 'GET_FLAT_FILE_RETURNS_DATA_BY_RETURN_DATE',
            'marketplaceIds': self.active_marketplace_ids.mapped('api_ref'),
            'dataStartTime': start_time.isoformat() + 'Z',
            'dataEndTime': end_time.isoformat() + 'Z',
        }
        response = amazon_utils.make_sp_api_request(
            self, 'createReturnReport', payload=payload, method='POST'
        )
        self.write({
            'return_report_id': response['reportId'],
            'return_report_status': 'IN_QUEUE',
            'return_report_start': start_time,
            'return_report_end': end_time,
            'return_sync_error': False,
        })

    def _process_return_report(self):
        self.ensure_one()
        response = amazon_utils.make_sp_api_request(
            self, 'getReturnReport', path_parameter=self.return_report_id
        )
        status = response['processingStatus']
        self.return_report_status = status
        if status in ('IN_QUEUE', 'IN_PROGRESS'):
            return
        if status == 'DONE':
            document_id = response.get('reportDocumentId')
            if not document_id:
                raise UserError(_("Amazon completed the return report without a document."))
            report_content = return_utils.download_restricted_report_document(self, document_id)
            rows = csv.DictReader(io.StringIO(report_content), delimiter='\t')
            normalized_rows = ({
                _normalize_report_header(key): value.strip() if value else ''
                for key, value in row.items() if key
            } for row in rows)
            self.env['amazon.return']._import_report_rows(self, normalized_rows)
        elif status == 'FATAL':
            raise UserError(_("Amazon failed to generate the return report."))

        self.write({
            'last_returns_sync': self.return_report_end or fields.Datetime.now(),
            'return_report_id': False,
            'return_report_start': False,
            'return_report_end': False,
            'return_sync_error': False,
        })

    def _sync_returns(self, force=False):
        accounts = self or self.search([])
        for account in accounts:
            try:
                with self.env.cr.savepoint():
                    if account.return_report_id:
                        account._process_return_report()
                    elif force or not account.last_returns_sync or (
                        account.last_returns_sync <= fields.Datetime.now() - timedelta(days=1)
                    ):
                        account._request_return_report()
            except Exception as error:
                if force:
                    raise
                _logger.exception(
                    "Could not synchronize Amazon returns for account with id %s.", account.id
                )
                account.return_sync_error = str(error)
