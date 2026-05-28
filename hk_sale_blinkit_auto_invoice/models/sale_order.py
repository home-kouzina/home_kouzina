from markupsafe import Markup

from odoo import _, api, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def _cron_blinkit_b2c_auto_create_invoices(self, limit=100):
        """Confirm and invoice imported B2C orders."""
        orders = self.search([
            ('marketplace_invoice_type', '=ilike', 'b2c'),
            ('state', '=', 'sale'),
        ], limit=limit)
        return orders._blinkit_b2c_auto_create_invoice()

    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()
        move_fields = self.env['account.move']._fields
        marketplace_vals = {
            'marketplace_invoice_number': self.marketplace_invoice_number,
            'marketplace_invoice_type': self.marketplace_invoice_type,
            'marketplace_sale_state': self.marketplace_sale_state,
        }
        invoice_vals.update({
            field: value
            for field, value in marketplace_vals.items()
            if field in move_fields and value
        })
        return invoice_vals

    def _is_blinkit_b2c_order(self):
        self.ensure_one()
        invoice_type = (self.marketplace_invoice_type or '').strip().lower()
        return invoice_type == 'b2c'

    def _blinkit_b2c_confirm_order(self):
        self.ensure_one()
        if self.state in ('draft', 'sent'):
            self.action_confirm()
        return self.state in ('sale', 'done')

    def _blinkit_b2c_validate_deliveries(self):
        self.ensure_one()
        pickings = self.sudo().picking_ids.filtered(
            lambda picking: picking.picking_type_code == 'outgoing'
            and picking.state not in ('done', 'cancel')
        )
        if not pickings:
            return True

        for picking in pickings:
            picking = picking.sudo()
            if picking.state == 'draft':
                picking.action_confirm()
            if picking.state != 'assigned':
                picking.action_assign()

            moves = picking.move_ids_without_package.filtered(lambda move: move.state not in ('done', 'cancel'))
            for move in moves:
                if move.product_uom_qty:
                    move._set_quantity_done(move.product_uom_qty)
                move.picked = True

            picking.with_context(skip_backorder=True, skip_sms=True).button_validate()
            if picking.state != 'done':
                order_message = _(
                    "B2C invoice was not created because delivery %s needs manual validation.",
                    picking.display_name,
                )
                self.message_post(body=order_message)
                return False
        return True

    def _blinkit_b2c_auto_create_invoice(self):
        """Create and post invoices for Blinkit B2C orders, even if delivery is not validated."""
        invoices = self.env['account.move']
        for order in self:
            if not order._is_blinkit_b2c_order():
                continue

            existing_invoices = order.invoice_ids.filtered(lambda move: move.state != 'cancel')
            if existing_invoices:
                continue

            try:
                if not order._blinkit_b2c_confirm_order():
                    order.message_post(body=_(
                        "B2C invoice was not created because the quotation could not be confirmed."
                    ))
                    continue
                try:
                    order._blinkit_b2c_validate_deliveries()
                except Exception as error:
                    order.message_post(body=_(
                        "B2C delivery automatic validation failed, but invoice creation will continue: %s",
                        error,
                    ))
                new_invoices = order._create_invoices()
            except Exception as error:
                order.message_post(body=_(
                    "B2C invoice automatic process failed: %s", error
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
                    _("B2C invoice created and posted automatically:"),
                    invoice_links,
                ))
        return invoices
