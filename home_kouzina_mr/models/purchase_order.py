import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    requisition_id = fields.Many2one(
        'material.requisition',
        string="Material Requisition",
        ondelete="cascade"
    )

    def button_confirm(self):
        try:
            for order in self:
                # 1️⃣ Validate total amount
                if order.amount_total <= 20000:
                    raise ValidationError(_(
                        "You cannot confirm this Purchase Order because the total amount (%.2f) "
                        "must be greater than or equal to 20,000."
                    ) % order.amount_total)

                # 2️⃣ Validate user is Administrator
                if not self.env.user.has_group('base.group_system'):
                    raise ValidationError(_(
                        "Only an Administrator can confirm this Purchase Order."
                    ))

            # ✅ If all validations pass → confirm the order
            return super().button_confirm()
        except Exception as e:
            # 🪵 Log unexpected errors, but do NOT raise them
            _logger.error("Unexpected error while confirming PO (ID: %s): %s", self.ids, str(e))
            return super().button_confirm()
