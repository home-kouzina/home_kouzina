from odoo import models, fields, api
from odoo.exceptions import UserError


class MarketplaceTemplateDownloadWizard(models.TransientModel):
    _name = 'marketplace.template.download.wizard'
    _description = 'Marketplace Template Download Wizard'

    marketplace_id = fields.Many2one('marketplace.master', string='Marketplace', required=True)

    def action_download_template(self):
        """Return XLSX download URL based on selected marketplace."""
        self.ensure_one()
        marketplace_name = self.marketplace_id.name.lower()

        # Map marketplace name → static XLSX file path
        template_map = {
            'flipkart': '/home_kouzina_sales/static/src/files/flipkart_order.xlsx',
            'amazon':  '/home_kouzina_sales/static/src/files/amazon_order.xlsx',
            'blinkit': '/home_kouzina_sales/static/src/files/blinkit_order.xlsx',
            'shopify': '/home_kouzina_sales/static/src/files/shopify_order.xlsx',
        }

        file_url = template_map.get(marketplace_name)
        if not file_url:
            raise UserError("No XLSX template configured for this marketplace.")

        # Return file as a direct download
        return {
            'type': 'ir.actions.act_url',
            'url': file_url,
            'target': 'new',
        }
