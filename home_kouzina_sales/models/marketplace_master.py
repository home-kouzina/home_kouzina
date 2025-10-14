from odoo import fields, models

class MarketplaceMaster(models.Model):
    _name = 'marketplace.master'
    _description = 'Marketplace Master'

    name = fields.Char(string='Marketplace Name', required=True)
    warehouse_map = fields.Many2one('stock.warehouse', string='Warehouse')
    so_tag = fields.Many2one('crm.tag', string='Default Sales Order Tag')
