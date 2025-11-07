from odoo import models, fields, api
from odoo.exceptions import ValidationError


class StockLocation(models.Model):
    _inherit = 'stock.location'

    is_source_location = fields.Boolean(
        string="Is Source Location",
        help="Enable this if this location should be used as the default source location."
    )
    is_destination_location = fields.Boolean(
        string="Is Destination Location",
        help="Enable this if this location should be used as the default destination location."
    )

    @api.constrains('is_source_location', 'is_destination_location')
    def _check_source_and_destination_exclusive(self):
        """
        Ensure that a location cannot be both source and destination at the same time.
        """
        for rec in self:
            if rec.is_source_location and rec.is_destination_location:
                raise ValidationError(
                    "A location cannot be marked as both Source and Destination. "
                    "Please select only one option."
                )

    @api.onchange('is_source_location', 'is_destination_location')
    def _onchange_source_destination_flags(self):
        """
        Automatically uncheck the other flag if one is selected (for better UX).
        """
        for rec in self:
            if rec.is_source_location:
                rec.is_destination_location = False
            elif rec.is_destination_location:
                rec.is_source_location = False
