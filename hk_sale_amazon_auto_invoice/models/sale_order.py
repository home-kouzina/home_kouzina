from markupsafe import Markup

from odoo import _, api, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def _cron_amazon_auto_create_invoices(self, limit=100):
        """Create invoices for already imported Amazon orders that are ready to invoice."""
        orders = self.search([
            ('amazon_order_ref', '!=', False),
            ('state', 'in', ['sale', 'done']),
            ('invoice_status', 'in', ['to invoice', 'upselling']),
        ], limit=limit)
        return orders._amazon_auto_create_invoice()

    def _amazon_auto_create_invoice(self):
        """Create and post invoices for Amazon orders when Odoo has invoiceable lines."""
        invoices = self.env['account.move']
        for order in self:
            if not order.amazon_order_ref or order.state not in ('sale', 'done'):
                continue

            existing_invoices = order.invoice_ids.filtered(lambda move: move.state != 'cancel')
            if existing_invoices:
                continue

            invoiceable_lines = order._get_invoiceable_lines(final=False)
            if not invoiceable_lines:
                order.message_post(body=_(
                    "Amazon invoice was not created automatically because the order has no "
                    "invoiceable lines yet. It will be checked again after delivery."
                ))
                continue

            try:
                new_invoices = order._create_invoices()
            except Exception as error:
                order.message_post(body=_(
                    "Amazon invoice automatic creation failed: %s", error
                ))
                continue

            if new_invoices:
                draft_invoices = new_invoices.filtered(lambda invoice: invoice.state == 'draft')
                if draft_invoices:
                    draft_invoices.action_post()
                invoices |= new_invoices
                invoice_links = Markup(', ').join(Markup(
                    "<a href='#' data-oe-model='account.move' data-oe-id='%s'>%s</a>"
                ) % (invoice.id, invoice.display_name) for invoice in new_invoices)
                order.message_post(body=Markup("%s %s") % (
                    _("Amazon invoice created and posted automatically:"),
                    invoice_links,
                ))
        return invoices
