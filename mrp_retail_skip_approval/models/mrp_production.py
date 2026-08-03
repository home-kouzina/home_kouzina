# -*- coding: utf-8 -*-

from odoo import _, fields, models
from odoo.exceptions import UserError


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    is_retail_product = fields.Boolean(
        related='product_id.product_tmpl_id.is_retail',
        string='Is Retail Product',
    )

    def action_confirm(self):
        for production in self:
            if not production.is_retail_product and production.approval_status != 'approved':
                raise UserError(_(
                    "'%s' must be approved before it can be confirmed. "
                    "Please submit it for approval first."
                ) % production.display_name)

        return super().action_confirm()
