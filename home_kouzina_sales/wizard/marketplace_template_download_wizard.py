from odoo import fields, models


class MarketplaceTemplateDownloadWizard(models.TransientModel):
    _name = 'marketplace.template.download.wizard'
    _description = 'Marketplace Template Download Wizard'

    marketplace_id = fields.Many2one('marketplace.master', string='Marketplace')

    def action_download_template(self):
        """Return the common XLSX template used for every marketplace."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/home_kouzina_sales/static/src/files/Master_Sale_Template.xlsx',
            'target': 'new',
        }
