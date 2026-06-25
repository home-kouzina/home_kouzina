# Part of Odoo. See LICENSE file for full copyright and licensing details.

import gzip
import logging
from datetime import datetime

import requests
from werkzeug.urls import url_join, url_parse

from odoo import _
from odoo.exceptions import ValidationError

from odoo.addons.sale_amazon import const, utils as amazon_utils


_logger = logging.getLogger(__name__)


def download_restricted_report_document(account, document_id):
    """Download a restricted Amazon report document using a document-specific RDT."""
    document_path = f'/reports/2021-06-30/documents/{document_id}'
    token_response = amazon_utils.make_sp_api_request(
        account,
        'createRestrictedDataToken',
        payload={'restrictedResources': [{
            'method': 'GET',
            'path': document_path,
        }]},
        method='POST',
    )
    restricted_token = token_response['restrictedDataToken']
    domain = const.API_DOMAINS_MAPPING[account.base_marketplace_id.region]
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json; charset=utf-8',
        'host': url_parse(domain).netloc,
        'x-amz-access-token': restricted_token,
        'x-amz-date': datetime.utcnow().strftime('%Y%m%dT%H%M%SZ'),
    }
    try:
        response = requests.get(url_join(domain, document_path), headers=headers, timeout=60)
        response.raise_for_status()
        document_info = response.json()
        document_response = requests.get(document_info['url'], timeout=60)
        document_response.raise_for_status()
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        _logger.exception("Could not download Amazon return report document %s.", document_id)
        raise ValidationError(_("Could not establish the connection to the Amazon Reports API."))
    except requests.exceptions.HTTPError as error:
        _logger.exception("Amazon rejected return report document %s.", document_id)
        if error.response.status_code == 403:
            raise ValidationError(_(
                "Amazon denied access to the return report document. Verify that the SP-API "
                "application has Inventory and Order Tracking and Direct to Consumer Shipping "
                "(Restricted) roles, then re-authorize the seller account."
            ))
        raise ValidationError(_("Amazon rejected the return report document request."))

    content = document_response.content
    if document_info.get('compressionAlgorithm') == 'GZIP':
        content = gzip.decompress(content)
    return content.decode('utf-8-sig')

