from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    cin_image = fields.Image(string="CIN")
    other_image = fields.Image(string="Other")
    gst_number = fields.Char(string="GST Number")
