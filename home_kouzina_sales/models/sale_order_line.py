from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    sale_date = fields.Datetime(
        string='Sale Date',
        related='order_id.date_order',
        store=True,
        readonly=True,
        help='Sale Order date',
    )
    cogs_unit_price = fields.Float(
        string='COGS Unit Price',
        compute='_compute_cogs_unit_price',
        store=True,
        readonly=True,
        copy=False,
        digits='Product Price',
        help='Frozen COGS per unit at the time of sale.',
    )

    @api.depends(
        'product_id',
        'order_id.date_order',
        'order_id.company_id',
        'product_id.labelled_product',
        'product_id.packaging_product',
    )
    def _compute_cogs_unit_price(self):
        for line in self:
            line.cogs_unit_price = line._get_frozen_cogs_unit_price()

    def _get_frozen_cogs_unit_price(self):
        self.ensure_one()
        if not self.product_id:
            return 0.0

        company = self.order_id.company_id or self.env.company
        sale_date = self.order_id.date_order or fields.Datetime.now()

        def _template_cost(product_template):
            if not product_template:
                return 0.0

            history = self.env['product.cost.history'].search([
                ('product_tmpl_id', '=', product_template.id),
                ('company_id', '=', company.id),
                ('effective_date', '<=', sale_date),
            ], order='effective_date desc, id desc', limit=1)
            if history:
                return history.cost_price or 0.0

            product_variant = product_template.product_variant_id
            if product_variant:
                return product_variant.with_company(company).standard_price or 0.0
            return 0.0

        total_cost = _template_cost(self.product_id.product_tmpl_id)
        total_cost += _template_cost(self.product_id.labelled_product)
        total_cost += _template_cost(self.product_id.packaging_product)
        return total_cost
