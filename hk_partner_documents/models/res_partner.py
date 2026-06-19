from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    cin_image = fields.Image(string="CIN")
    doc_image = fields.Image(string="Document")
    gst_number = fields.Char(string="GST Number")
