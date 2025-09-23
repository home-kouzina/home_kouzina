# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class MaterialRequisition(models.Model):
    _name = 'material.requisition'
    _description = 'Material Requisition'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Requisition Reference', required=True, copy=False, readonly=True,
                       default=lambda self: _('New'))
    state = fields.Selection([
        ('draft', 'Draft'),
        ('request', 'Request'),
        ('request_accepted', 'Request Accepted'),
        ('internal_transit', 'In Transit'),
        ('received', 'Received'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    source_location_id = fields.Many2one('stock.location', string="Source Location")
    source_location_company_id = fields.Many2one('res.company', string="Source Location Company", related='source_location_id.company_id')
    destination_location_id = fields.Many2one('stock.location', string='Destination Location', required=True,
                                              domain="[('usage','=','internal')]")
    destination_location_company_id = fields.Many2one('res.company', string="Destination Location Company", related='destination_location_id.company_id')
    indented_date = fields.Datetime(string='Indent Date', default=fields.Datetime.now(), readonly=True)
    request_raised_by = fields.Many2one('hr.employee', string='Request Raised By', required=True,
                                        default=lambda self: self.env['hr.employee'].search(
                                            [('user_id', '=', self.env.user.id)], limit=1))
    department_id = fields.Many2one('hr.department', string='Department', related='request_raised_by.department_id',
                                    store=True, readonly=True)
    job_position_id = fields.Many2one('hr.job', string='Job Position', related='request_raised_by.job_id', store=True,
                                      readonly=True)
    request_raised_for = fields.Many2one('hr.employee', string='Request Raised For', required=True)
    required_date = fields.Datetime(string='Required Date', required=True)
    reporting_manager_id = fields.Many2one('hr.employee', string='Reporting Manager',
                                           related='request_raised_by.parent_id', store=True, readonly=True)
    requested_for_department_id = fields.Many2one('hr.department', string='Department',
                                                  related='request_raised_for.department_id', store=True, readonly=True)
    requested_for_reporting_manager_id = fields.Many2one('hr.employee', string='Reporting Manager',
                                                         related='request_raised_for.parent_id', store=True,
                                                         readonly=True)
    signature = fields.Binary(string='Signature', help="Signature of the requestor")
    requested_for_job_position_id = fields.Many2one('hr.job', string='Job Position',
                                                    related='request_raised_for.job_id', store=True, readonly=True)
    purpose = fields.Char(string='Purpose', required=True)
    picking_id = fields.Many2one('stock.picking', string='Internal Transfer', copy=False, readonly=True)
    purchase_order_ids = fields.One2many('purchase.order', 'requisition_id', string="Purchase Orders")
    sale_order_ids = fields.One2many('sale.order', 'requisition_id', string="Sale Orders")

    material_requisition_line_ids = fields.One2many('material.requisition.line', 'requisition_id',
                                                    string='Requisition Lines')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    purchase_order_count = fields.Integer(string="PO Count", compute="_compute_counts")
    sale_order_count = fields.Integer(string="SO Count", compute="_compute_counts")
    transfer_count = fields.Integer(string="Transfer Count", compute="_compute_counts")

    @api.depends('purchase_order_ids', 'sale_order_ids', 'picking_id')
    def _compute_counts(self):
        """Compute counts of related purchase orders, sale orders, and stock transfers."""
        for rec in self:
            # Count the number of linked purchase orders
            rec.purchase_order_count = len(rec.purchase_order_ids)
            # Count the number of linked sale orders
            rec.sale_order_count = len(rec.sale_order_ids)
            # Check if a related stock picking exists; set 1 if exists, else 0
            rec.transfer_count = 1 if rec.picking_id else 0

    def action_request(self):
        """Validate lines and move the requisition from Draft to Request state."""
        for rec in self:
            # Ensure at least one product line exists before requesting
            if not rec.material_requisition_line_ids:
                raise ValidationError(_("Please add products before requesting."))
            # Create the corresponding internal transfer for this requisition
            # rec._create_internal_transfer()
            # Update the state to 'request'
            rec.state = 'request'

    @api.model
    def create(self, vals):
        """Assign a sequence name if not provided and create the requisition."""

        # Check if name is default 'New' and assign a sequence number
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('material.requisition.sequence') or _('New')
        # Call the super method to actually create the record
        result = super(MaterialRequisition, self).create(vals)
        return result

    def action_accept_request(self):
        """Accept the requisition: create SO & PO and move to In Transit."""

        for rec in self:
            # Create the linked sale order
            rec._create_sale_order()
            # Create the linked purchase order
            rec._create_purchase_order()
            # Update the state to 'internal_transit'
            rec.state = 'internal_transit'

    def action_receive(self):
        """Receives: confirm POs, validate receipts & mark as Received """
        for rec in self:
            # Ensure all related Sale Orders are confirmed
            if any(so.state != 'sale' for so in rec.sale_order_ids):
                raise ValidationError(_("You cannot receive until all related Sale Orders are confirmed."))

            # Ensure all Delivery Orders for these Sale Orders are validated (done)
            for so in rec.sale_order_ids:
                delivery_orders = self.env['stock.picking'].search([
                    ('origin', '=', so.name),
                    ('picking_type_code', '=', 'outgoing')
                ])
                if not delivery_orders:
                    raise ValidationError(_("No Delivery Orders found for Sale Order %s." % so.name))

                for picking in delivery_orders:
                    if picking.state != 'done':
                        raise ValidationError(
                            _("Delivery Order %s for Sale Order %s is not done yet." % (picking.name, so.name)))

            # Confirm all related Purchase Orders if still draft
            for po in rec.purchase_order_ids:
                if po.state in ('draft', 'sent'):
                    po.button_confirm()

                # Validate all related receipts
                for picking in po.picking_ids:
                    if picking.state not in ('done', 'cancel'):
                        picking.button_validate()
            # Finally, mark MR as received
            rec.state = 'received'

    def action_cancel(self):
        """Cancel the MR"""
        self.write({'state': 'cancel'})

    # ---------------------------------------------
    # Helpers for SO/PO
    # ---------------------------------------------
    def _create_purchase_order(self):
        """Create a purchase order for the requisition and link it to the record."""

        PurchaseOrder = self.env['purchase.order']
        for rec in self:
            # Create a vendor based on the source location
            vendor = self.env['res.partner'].create({
                'name': rec.source_location_company_id.name,
                'supplier_rank': 1,
            })

            # Prepare purchase order values
            po_vals = {
                'partner_id': vendor.id,
                'origin': rec.name,
                'requisition_id': rec.id,
                'order_line': [],
            }

            # Add lines from the material requisition
            for line in rec.material_requisition_line_ids:
                po_vals['order_line'].append((0, 0, {
                    'product_id': line.product_id.id,
                    'name': line.product_id.display_name,
                    'product_qty': line.product_uom_qty,
                    'product_uom': line.product_uom.id,
                    'price_unit': line.product_id.standard_price,
                }))

            # Create the purchase order and link it to the requisition
            po = PurchaseOrder.create(po_vals)
            rec.purchase_order_ids = [(4, po.id)]

    def _create_sale_order(self):
        """Create a sale order for the requisition and link it to the record."""

        SaleOrder = self.env['sale.order']
        for rec in self:
            # Create a customer based on the destination location
            customer = self.env['res.partner'].create({
                'name': rec.destination_location_company_id.name,
                'customer_rank': 1,
            })

            # Prepare sale order values
            so_vals = {
                'partner_id': customer.id,
                'origin': rec.name,
                'requisition_id': rec.id,
                'order_line': [],
            }

            # Add lines from the material requisition
            for line in rec.material_requisition_line_ids:
                so_vals['order_line'].append((0, 0, {
                    'product_id': line.product_id.id,
                    'name': line.product_id.display_name,
                    'product_uom_qty': line.product_uom_qty,
                    'product_uom': line.product_uom.id,
                    'price_unit': line.product_id.lst_price,
                }))

            # Create the sale order and link it to the requisition
            so = SaleOrder.create(so_vals)
            rec.sale_order_ids = [(4, so.id)]

    def _create_internal_transfer(self):
        """Create an internal stock transfer for the requisition's products."""
        # Ensure this method is called on a single record
        self.ensure_one()

        # Get the main stock location
        source_location = self.env.ref('stock.stock_location_stock', raise_if_not_found=False)
        if not source_location:
            raise UserError(
                _("Main Stock location 'WH/Stock' not found. Please ensure it exists in your inventory locations or configure the correct source location."))

        # Ensure the requisition has product lines
        if not self.material_requisition_line_ids:
            raise UserError(_("Cannot create transfer for a requisition with no products."))

        # Prepare the picking (stock transfer) values
        picking_vals = {
            'picking_type_id': self.env.ref('stock.picking_type_internal').id,
            'location_id': source_location.id,
            'location_dest_id': self.destination_location_id.id,
            'origin': self.name,
            'partner_id': self.request_raised_by.user_id.partner_id.id if self.request_raised_by and self.request_raised_by.user_id else False,
            'note': _("Internal Transfer for Material Requisition: %s - Purpose: %s") % (self.name, self.purpose),
            'company_id': self.company_id.id,
        }

        # Create the picking
        picking = self.env['stock.picking'].create(picking_vals)

        # Prepare move lines for all products in the requisition
        move_lines_vals = []
        for line in self.material_requisition_line_ids:
            move_lines_vals.append((0, 0, {
                'name': line.product_id.display_name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.product_uom_qty,
                'product_uom': line.product_uom.id,
                'location_id': source_location.id,
                'location_dest_id': self.destination_location_id.id,
                'picking_id': picking.id,
                'company_id': self.company_id.id,
            }))

        # Write the move lines to the picking and confirm the transfer
        picking.write({'move_ids_without_package': move_lines_vals})
        picking.action_confirm()

        # Link the created picking to the requisition
        self.write({
            'picking_id': picking.id,
        })

    # ---------------------------------------------
    # Smart Button Actions
    # ---------------------------------------------
    def action_view_purchase_orders(self):
        """Open a window showing purchase orders linked to this requisition."""
        # Ensure method is called on a single record
        self.ensure_one()
        return {
            'name': _('Purchase Orders'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.purchase_order_ids.ids)],  # Filter for linked POs
            'context': dict(self._context),
        }

    def action_view_sale_orders(self):
        """Open a window showing sale orders linked to this requisition."""
        # Ensure method is called on a single record
        self.ensure_one()
        return {
            'name': _('Sale Orders'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.sale_order_ids.ids)],  # Filter for linked SOs
            'context': dict(self._context),
        }

    def action_view_transfers(self):
        """Open a window showing the internal transfer linked to this requisition."""
        # Ensure method is called on a single record
        self.ensure_one()
        return {
            'name': _('Transfers'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'list,form',
            'domain': [('id', '=', self.picking_id.id)],  # Filter for the linked picking
            'context': dict(self._context),
        }

    def action_print_requisition_report(self):
        """
        Prints the material requisition report.
        """
        return self.env.ref('home_kouzina_mr.action_pdf_report_material_requisition').report_action(self)

    def action_open_purchase_requisition_excel_wizard(self):
        """
        Opens the wizard for generating the Purchase Requisition Excel Report.
        """
        return {
            'name': _('Purchase Requisition Excel Report'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.requisition.excel.report.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_start_date': (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
                'default_end_date': datetime.now().strftime('%Y-%m-%d'),
            }
        }


class MaterialRequisitionLine(models.Model):
    _name = 'material.requisition.line'
    _description = 'Material Requisition Line'

    requisition_id = fields.Many2one('material.requisition', string='Material Requisition', required=True,
                                     ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True,domain=[('is_finished_good', '=', False)])
    product_uom_qty = fields.Float(string='Requested Quantity', digits='Product Unit of Measure', required=True,
                                   default=1.0)
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure', related='product_id.uom_id', store=True,
                                  readonly=True)
    onhand_quantity = fields.Float(
        string='On Hand Quantity (at Dest. Loc.)',
        compute='_compute_onhand_quantity',
        store=True,
        readonly=True
    )

    @api.depends('product_id', 'requisition_id.destination_location_id')
    def _compute_onhand_quantity(self):
        """Compute the available quantity of the product at the requisition's destination."""
        for line in self:
            if line.product_id and line.requisition_id.destination_location_id:
                # Get the available quantity in the destination location
                product_qty_in_location = line.product_id.with_context(
                    location=line.requisition_id.destination_location_id.id
                ).qty_available
                line.onhand_quantity = product_qty_in_location
            else:
                # No product or destination, so on-hand is 0
                line.onhand_quantity = 0.0

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Update the unit of measure when the product changes."""
        if self.product_id:
            # Set the product UOM to the default UOM of the selected product
            self.product_uom = self.product_id.uom_id.id

    @api.constrains('product_uom_qty')
    def _check_product_uom_qty(self):
        """Ensure the requested quantity is greater than zero."""
        for record in self:
            if record.product_uom_qty <= 0:
                # Raise an error if the quantity is invalid
                raise ValidationError(_("Requested Quantity must be greater than zero."))
