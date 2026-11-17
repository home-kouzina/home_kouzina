# -*- coding: utf-8 -*-
from odoo import fields, models


class SohDownload(models.Model):
    """
    A copy of the Actual SOH values at the moment the count file was
    downloaded. On upload, a row counts as 'changed' only if its Actual SOH
    differs from this copy, so stock movements between download and upload
    are never undone.
    """

    _name = 'soh.download'
    _description = 'SOH Count File Download'
    _order = 'id desc'

    week_id = fields.Many2one('soh.week', string='Week', required=True, ondelete='cascade', index=True)
    user_id = fields.Many2one('res.users', string='Downloaded By', default=lambda self: self.env.user)
    line_ids = fields.One2many('soh.download.line', 'download_id', string='Lines')


class SohDownloadLine(models.Model):
    _name = 'soh.download.line'
    _description = 'SOH Count File Download Line'

    download_id = fields.Many2one('soh.download', required=True, ondelete='cascade', index=True)
    product_id = fields.Many2one('product.product', required=True)
    actual_soh = fields.Float(digits='Product Unit of Measure', help='Value written in the downloaded file (Ideal SOH).')
    kg_factor = fields.Float(default=1.0, help='0.001 if the report shows this product in kg instead of grams.')


class SohUploadLog(models.Model):
    _name = 'soh.upload.log'
    _description = 'SOH Count Upload Log'
    _order = 'create_date desc, id desc'
    _rec_name = 'file_name'

    week_id = fields.Many2one('soh.week', string='Week', ondelete='set null', index=True)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user, readonly=True)
    file_data = fields.Binary(string='File', attachment=True, readonly=True)
    file_name = fields.Char(string='File Name', readonly=True)
    rows_read = fields.Integer(string='Rows Read', readonly=True)
    rows_changed = fields.Integer(string='Rows Changed', readonly=True)
    result = fields.Selection(
        [('applied', 'Applied'), ('rejected', 'Rejected')],
        string='Result', readonly=True)
    note = fields.Text(string='Note', readonly=True)
    line_ids = fields.One2many('soh.upload.log.line', 'log_id', string='Changes', readonly=True)


class SohUploadLogLine(models.Model):
    _name = 'soh.upload.log.line'
    _description = 'SOH Count Upload Change'

    log_id = fields.Many2one('soh.upload.log', required=True, ondelete='cascade', index=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_name = fields.Char(string='Product Name', readonly=True)
    uom_name = fields.Char(string='UoM', readonly=True)
    downloaded_qty = fields.Float(string='Actual SOH When Downloaded', digits='Product Unit of Measure', readonly=True)
    counted_qty = fields.Float(string='Counted', digits='Product Unit of Measure', readonly=True)
    stock_change = fields.Float(string='Stock Change', digits='Product Unit of Measure', readonly=True,
                                help='Counted minus the live stock at the moment the upload was confirmed.')
    location_id = fields.Many2one('stock.location', string='Adjusted In', readonly=True)
