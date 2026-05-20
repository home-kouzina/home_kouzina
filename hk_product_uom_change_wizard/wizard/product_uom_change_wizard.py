from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProductUomChangeWizard(models.TransientModel):
    _name = "product.uom.change.wizard"
    _description = "Change Product Unit of Measure"

    product_tmpl_ids = fields.Many2many(
        "product.template",
        "product_uom_change_wizard_product_rel",
        "wizard_id",
        "product_tmpl_id",
        string="Product",
        required=True,
        domain=[("type", "in", ["consu", "product"])],
    )
    selected_product_count = fields.Integer(
        string="Selected Products",
        compute="_compute_selected_product_count",
    )
    current_uom_id = fields.Many2one(
        "uom.uom",
        string="First Product Current UoM",
        readonly=True,
    )
    new_uom_id = fields.Many2one(
        "uom.uom",
        string="New Unit of Measure",
        required=True,
    )
    change_purchase_uom = fields.Boolean(
        string="Also Update Purchase UoM",
        default=True,
        help="Update the purchase unit of measure to the same selected UoM.",
    )

    @api.depends("product_tmpl_ids")
    def _compute_selected_product_count(self):
        for wizard in self:
            wizard.selected_product_count = len(wizard.product_tmpl_ids)

    @api.onchange("product_tmpl_ids")
    def _onchange_product_tmpl_ids(self):
        for wizard in self:
            product = wizard.product_tmpl_ids[:1]
            wizard.current_uom_id = product.uom_id
            wizard.new_uom_id = product.uom_id

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        products = self.env["product.template"]

        default_product_commands = values.get("product_tmpl_ids")
        if default_product_commands:
            products = self.env["product.template"].browse(default_product_commands[0][2])
        active_ids = self.env.context.get("active_ids") or [self.env.context.get("active_id")]
        active_ids = [active_id for active_id in active_ids if active_id]
        if not products and self.env.context.get("active_model") == "product.template":
            products = self.env["product.template"].browse(active_ids)
            values["product_tmpl_ids"] = [(6, 0, products.ids)]
        elif not products and self.env.context.get("active_model") == "product.product":
            variants = self.env["product.product"].browse(active_ids)
            products = variants.mapped("product_tmpl_id")
            values["product_tmpl_ids"] = [(6, 0, products.ids)]

        product = products[:1]
        if product:
            values.setdefault("current_uom_id", product.uom_id.id)
            values.setdefault("new_uom_id", product.uom_id.id)
        return values

    def action_apply_uom(self):
        self.ensure_one()
        products = self.product_tmpl_ids
        if not products:
            raise UserError(_("Please select at least one product."))

        updated_fields = ["uom_id"]
        if self.change_purchase_uom:
            updated_fields.append("uom_po_id")

        if self.change_purchase_uom:
            self.env.cr.execute(
                """
                UPDATE product_template
                   SET uom_id = %s,
                       uom_po_id = %s,
                       write_uid = %s,
                       write_date = NOW()
                 WHERE id IN %s
                """,
                (self.new_uom_id.id, self.new_uom_id.id, self.env.uid, tuple(products.ids)),
            )
        else:
            self.env.cr.execute(
                """
                UPDATE product_template
                   SET uom_id = %s,
                       write_uid = %s,
                       write_date = NOW()
                 WHERE id IN %s
                """,
                (self.new_uom_id.id, self.env.uid, tuple(products.ids)),
            )

        products.invalidate_recordset(updated_fields)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Unit of Measure Updated"),
                "message": _("%(count)s product(s) updated to %(uom)s.") % {
                    "count": len(products),
                    "uom": self.new_uom_id.display_name,
                },
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
