from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductPackages(models.Model):
    _name = "product.packages"

    name = fields.Char('Product Packaging', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True,
                                 ondelete="cascade")
    qty = fields.Float('Contained Quantity', default=1, digits='Product Unit of Measure',
                       help="Quantity of products contained in the packaging.")


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    package_ids = fields.Many2many('product.packages', string='Product Packaging')
    regional_language_name = fields.Char("Regional Language Name",related="product_template_id.regional_language_name")
