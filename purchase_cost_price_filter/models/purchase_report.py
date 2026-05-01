from odoo import fields, models
from odoo.tools import SQL


class PurchaseReport(models.Model):
    _inherit = "purchase.report"

    product_standard_price = fields.Monetary(
        string="Cost Price",
        readonly=True,
        aggregator="avg",
    )

    def _select(self) -> SQL:
        return SQL(
            """
                %s,
                (
                    COALESCE(
                        NULLIF(p.standard_price->>(po.company_id::text), ''),
                        '0.0'
                    )::decimal(16, 2) * account_currency_table.rate
                ) AS product_standard_price
            """,
            super()._select(),
        )

    def _group_by(self) -> SQL:
        return SQL(
            """
                %s,
                p.standard_price
            """,
            super()._group_by(),
        )
