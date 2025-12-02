from odoo import fields, models


class ProductCategory(models.Model):
    _inherit = "product.category"

    allow_negative_stock = fields.Boolean(
        help="Allow negative stock levels for the stockable products "
        "linked to this category. This option does not apply to products "
        "assigned to sub-categories of this category.",
    )


class ProductTemplate(models.Model):
    _inherit = "product.template"

    allow_negative_stock = fields.Boolean(
        help="Allow negative stock levels for this stockable product. "
             "If this option is disabled here and on the product's category, "
             "validation of related stock moves will be blocked if the stock "
             "level would become negative."
    )
