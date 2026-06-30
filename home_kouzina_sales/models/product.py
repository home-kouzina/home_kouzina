from odoo import api, fields, models
from odoo.tools import float_compare


class ProductProduct(models.Model):
    _inherit = "product.product"

    labelled_product = fields.Many2one(
        'product.template',
        string="Labelled Product",
        domain="[('is_labelling', '=', True)]",
        help="Select the products that are labelled with this packaging product."
    )
    packaging_product = fields.Many2one(
        'product.template',
        string="Packaging Product",
        domain="[('is_packaging', '=', True)]",
        help="Select the products that are used for packaging."
    )

    cog_before_sale = fields.Float(
        string="COG Before Sale",
        compute="_compute_cog_before_sale",
        store=True,
        help="Cost of goods before the product is sold."
    )

    default_code = fields.Char(string='SKU')
    barcode = fields.Char(string='EAN')

    def _log_cost_history(self, previous_costs=None):
        """Store the cost that is effective for the active company."""
        history_model = self.env['product.cost.history'].sudo()
        company = self.env.company
        history_vals = []
        precision_digits = 6

        for product in self:
            current_cost = product.with_company(company).standard_price or 0.0
            previous_cost = None if previous_costs is None else previous_costs.get(product.id)

            if previous_cost is not None and float_compare(
                current_cost,
                previous_cost,
                precision_digits=precision_digits,
            ) == 0:
                continue

            if previous_cost is None and not current_cost:
                continue

            history_vals.append({
                'product_tmpl_id': product.product_tmpl_id.id,
                'company_id': company.id,
                'cost_price': current_cost,
                'effective_date': fields.Datetime.now(),
            })

        if history_vals:
            history_model.create(history_vals)

    @api.depends(
        'standard_price',
        'labelled_product.standard_price',
        'packaging_product.standard_price',
    )
    def _compute_cog_before_sale(self):
        for record in self:
            record.cog_before_sale = (
                (record.standard_price or 0.0) +
                (record.labelled_product.standard_price or 0.0) +
                (record.packaging_product.standard_price or 0.0)
            )

    @api.model_create_multi
    def create(self, vals_list):
        products = super().create(vals_list)
        for product, vals in zip(products, vals_list):
            if 'standard_price' in vals:
                product._log_cost_history()
        return products

    def write(self, vals):
        previous_costs = {}
        if 'standard_price' in vals:
            previous_costs = {
                product.id: product.with_company(self.env.company).standard_price or 0.0
                for product in self
            }

        res = super().write(vals)

        if previous_costs:
            self._log_cost_history(previous_costs=previous_costs)

        return res

    is_finished_good = fields.Boolean(related="product_tmpl_id.is_finished_good", store=True)
    regional_language_name = fields.Char(related="product_tmpl_id.regional_language_name", store=True)
