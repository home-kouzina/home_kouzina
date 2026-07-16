import datetime

from odoo import fields, models, api
from odoo.exceptions import UserError


class SaleMarginCogsWizard(models.TransientModel):
    _name = 'sale.margin.cogs.wizard'
    _description = 'Backfill COGS on Sale Order Lines'

    date_from = fields.Date(string='From Date', required=True)
    date_to = fields.Date(string='To Date', required=True)
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        help="Leave empty to apply the COS value to ALL products in the "
             "selected date range. Set this to only fix one specific product."
    )
    cogs_unit_price = fields.Float(
        string='COS Value (per unit)',
        required=True,
        digits='Product Price',
        help="This value will be written to the COGS unit price of the "
             "matching order lines."
    )
    only_missing = fields.Boolean(
        string='Only fix lines with missing/zero COGS',
        default=True,
        help="Recommended: only updates lines where COGS is currently 0 or "
             "not set, so lines that already have a correct value are left "
             "untouched. Turn this off to force-overwrite every matching "
             "line, including ones that already have a COGS value."
    )
    line_count = fields.Integer(string='Matching Lines', compute='_compute_line_count')

    @api.depends('date_from', 'date_to', 'product_id', 'only_missing')
    def _compute_line_count(self):
        for wiz in self:
            wiz.line_count = len(wiz._get_matching_lines()) if wiz.date_from and wiz.date_to else 0

    def _get_matching_lines(self):
        self.ensure_one()
        if not (self.date_from and self.date_to):
            return self.env['sale.order.line']
        if self.date_from > self.date_to:
            raise UserError("'From Date' must be before or equal to 'To Date'.")

        # date_order is a Datetime field, so make the upper bound exclusive
        # and one day past date_to, to include the entire "To Date" day.
        date_to_upper = fields.Datetime.to_string(
            fields.Datetime.from_string(str(self.date_to)) + datetime.timedelta(days=1)
        )
        domain = [
            ('order_id.date_order', '>=', str(self.date_from)),
            ('order_id.date_order', '<', date_to_upper),
            ('display_type', '=', False),
        ]
        if self.product_id:
            domain.append(('product_id', '=', self.product_id.id))
        if self.only_missing:
            domain += ['|', ('cogs_unit_price', '=', 0), ('cogs_unit_price', '=', False)]

        return self.env['sale.order.line'].sudo().search(domain)

    def action_apply_cogs(self):
        self.ensure_one()
        lines = self._get_matching_lines()
        if not lines:
            raise UserError("No sale order lines matched this date range / product / filter.")

        lines.write({'cogs_unit_price': self.cogs_unit_price})

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'COGS Updated',
                'message': f'Updated COGS on {len(lines)} sale order line(s). '
                           f'Refresh the Margin Report to see the new values.',
                'type': 'success',
                'sticky': False,
            },
        }
