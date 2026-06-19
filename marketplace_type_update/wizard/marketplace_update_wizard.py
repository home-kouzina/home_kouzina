from odoo import fields, models
from odoo.exceptions import UserError


class MarketplaceUpdateWizard(models.TransientModel):
    _name = 'marketplace.update.wizard'
    _description = 'Bulk Update Marketplace Type on Sale Orders'

    def _get_marketplace_type_selection(self):
        # Reuse the exact same selection logic as sale.order.marketplace_type
        # so the stored values (codes) always match.
        marketplaces = self.env['marketplace.master'].sudo().search([], order='name')
        selection = []
        seen_codes = set()
        for marketplace in marketplaces:
            code = marketplace.code or marketplace._normalize_marketplace_code(marketplace.name)
            if not code or code in seen_codes:
                continue
            selection.append((code, marketplace.name))
            seen_codes.add(code)
        return selection or self.env['marketplace.master']._get_default_marketplace_selection()

    marketplace_type = fields.Selection(
        selection='_get_marketplace_type_selection',
        string='Marketplace Type',
        required=True,
    )

    def action_apply(self):
        self.ensure_one()
        active_ids = self.env.context.get('active_ids')
        if not active_ids:
            raise UserError("No Sale Orders selected.")

        orders = self.env['sale.order'].browse(active_ids)
        orders.write({'marketplace_type': self.marketplace_type})

        return {'type': 'ir.actions.act_window_close'}
