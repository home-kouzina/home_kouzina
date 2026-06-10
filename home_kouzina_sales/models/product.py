from odoo import fields, models, api


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

    is_finished_good = fields.Boolean(related="product_tmpl_id.is_finished_good", store=True)
    regional_language_name = fields.Char(related="product_tmpl_id.regional_language_name", store=True)