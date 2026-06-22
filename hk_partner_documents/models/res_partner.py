from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    cin_attachment_ids = fields.Many2many(
        'ir.attachment',
        'res_partner_cin_attachment_rel',
        'partner_id',
        'attachment_id',
        string="CIN"
    )

    other_attachment_ids = fields.Many2many(
        'ir.attachment',
        'res_partner_other_attachment_rel',
        'partner_id',
        'attachment_id',
        string="Attachments"
    )
    gst_number = fields.Char(string="GST Number")
