# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    show_auto_assign_finished_lot = fields.Boolean(
        string='Show Auto Assign Finished Lot',
        compute='_compute_show_auto_assign_finished_lot',
    )
    approval_status = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('pending', 'Pending'),
            ('approved', 'Approved'),
        ],
        string='Approval Status',
        default='draft',
        tracking=True,
        copy=False,
    )
    mo_status_bar = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('confirmed', 'Confirmed'),
            ('done', 'Done'),
        ],
        string='Status',
        compute='_compute_mo_status_bar',
    )

    @api.depends('state', 'approval_status')
    def _compute_mo_status_bar(self):
        for production in self:
            if production.state == 'done':
                production.mo_status_bar = 'done'
            elif production.state in ('confirmed', 'progress', 'to_close'):
                production.mo_status_bar = 'confirmed'
            elif production.approval_status in ('pending', 'approved'):
                production.mo_status_bar = production.approval_status
            else:
                production.mo_status_bar = 'draft'

    @api.depends(
        'state',
        'product_id.tracking',
        'lot_producing_id',
    )
    def _compute_show_auto_assign_finished_lot(self):
        for production in self:
            production.show_auto_assign_finished_lot = bool(
                production.state in ('confirmed', 'progress', 'to_close')
                and production.product_id.tracking == 'lot'
                and not production.lot_producing_id
            )

    def action_auto_assign_finished_lot(self):
        generated_count = 0
        used_names = set()

        for production in self:
            if production.state not in ('confirmed', 'progress', 'to_close'):
                raise UserError(_(
                    "You can assign a finished product lot only on confirmed, "
                    "in progress, or to close Manufacturing Orders."
                ))

            if production.product_id.tracking != 'lot':
                raise UserError(_(
                    "The finished product is not tracked by lots."
                ))

            if production.lot_producing_id:
                raise UserError(_(
                    "A finished product lot is already assigned on this Manufacturing Order."
                ))

            lot_name = production.product_id._get_next_auto_lot_name(
                company=production.company_id,
                used_names=used_names,
            )
            used_names.add(lot_name)

            lot = production.product_id._get_or_create_auto_stock_lot(
                lot_name=lot_name,
                company=production.company_id,
            )

            production.lot_producing_id = lot.id
            generated_count += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Finished lot assigned'),
                'message': _('%s finished product lot(s) generated.') % generated_count,
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                },
            },
        }
    
    ## Approval Functionality In the Manufacturing Order Is Below 
    
    def action_approved(self):
        for production in self:
            if not self.env.user.manufacture_approver:
                raise UserError(_("Only a manufacturing approver can approve this Manufacturing Order."))
            if production.approval_status != 'pending':
                raise UserError(_("Only Manufacturing Orders pending approval can be approved."))

            production.approval_status = 'approved'
            production.message_post(
                body=_("Manufacturing Order approved by %s.") % self.env.user.display_name,
            )

    def action_approved_submit(self):
        for production in self:
            if production.approval_status == 'approved':
                raise UserError(_("This Manufacturing Order is already approved."))

            production.approval_status = 'pending'
            production.message_post(
                body=_("Manufacturing Order submitted for approval by %s.") % self.env.user.display_name,
            )


    is_manufacture_approver = fields.Boolean(
        string='Is Manufacturing Approver',
        compute='_compute_is_manufacture_approver',
    )

    @api.depends_context('uid')
    def _compute_is_manufacture_approver(self):
        is_approver = self.env.user.manufacture_approver
        for rec in self:
            rec.is_manufacture_approver = is_approver    
