from odoo import fields, models


class ProductCostHistory(models.Model):
    _name = "product.cost.history"
    _description = "Product Cost History"
    _order = "effective_date desc, id desc"

    product_tmpl_id = fields.Many2one(
        "product.template",
        string="Product",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company.id,
        index=True,
    )
    cost_price = fields.Float(
        string="Cost Price",
        digits="Product Price",
        required=True,
    )
    effective_date = fields.Datetime(
        string="Effective Date",
        required=True,
        default=fields.Datetime.now,
        index=True,
    )
