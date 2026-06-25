# -*- coding: utf-8 -*-

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    manufacture_approver = fields.Boolean(
        string='Manufacturing Approver',
        default=False,
    )