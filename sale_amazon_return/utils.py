# Part of Odoo. See LICENSE file for full copyright and licensing details.

import gzip
import logging

import requests

from odoo import _
from odoo.exceptions import ValidationError

from odoo.addons.sale_amazon import utils as amazon_utils


_logger = logging.getLogger(__name__)


def download_restricted_report_document(account, document_id):
    """Download an Amazon return report document.

    The report metadata endpoint expects the ``reportDocumentId`` returned by
    ``getReport``. Requesting an RDT before this metadata call can make Amazon
    reject otherwise valid report documents with "Invalid or unsupported document
    ID found" for some restricted report types/marketplaces. Therefore, use the
    standard Odoo SP-API request helper for the metadata call, then download the
    pre-signed document URL returned by Amazon.
    """
    try:
        document_info = amazon_utils.make_sp_api_request(
            account, 'getReturnReportDocument', path_parameter=document_id
        )
        document_response = requests.get(document_info['url'], timeout=60)
        document_response.raise_for_status()
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        _logger.exception("Could not download Amazon return report document %s.", document_id)
        raise ValidationError(_("Could not establish the connection to the Amazon Reports API."))
    except requests.exceptions.HTTPError as error:
        _logger.exception("Amazon rejected return report document URL %s.", document_id)
        if error.response.status_code in (401, 403):
            raise ValidationError(_(
                "Amazon denied access to the return report document. Verify that the SP-API "
                "application has Inventory and Order Tracking and Direct to Consumer Shipping "
                "(Restricted) roles, then re-authorize the seller account."
            ))
        raise ValidationError(_("Amazon rejected the return report document download."))

    content = document_response.content
    if document_info.get('compressionAlgorithm') == 'GZIP':
        content = gzip.decompress(content)
    return content.decode('utf-8-sig')
