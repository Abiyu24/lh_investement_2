from odoo import models, fields, api

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    margin_order_ids = fields.One2many('purchase.lc.margin', 'purchase_order_id', string="Margins")


class PurchaseLCMargin(models.Model):
    _name = 'purchase.lc.margin'
    _description = 'Purchase Order LC Margin'

    purchase_order_id = fields.Many2one('purchase.order', string="Purchase Order", ondelete="cascade")
    # margin_order = fields.Char(string="Margin Order")
    margin_percentage = fields.Float(string="Margin %")
    calculation = fields.Float(string="Calculation")
    usd_amount = fields.Float(string="USD")
    exchange_rate = fields.Float(string="Exchange Rate")
    etb_amount = fields.Float(string="ETB")
    account = fields.Many2one('account.budget.post',string="Account")
    move_reference = fields.Char(string="Move Reference")
    lc_reference = fields.Many2one('purchase.order.lc', string="LC Reference")
    
    MARGIN_TYPE_SELECTION = [
        ('firstmargin', 'First Margin'),
        ('lastmargin', 'Last Margin'),
        ('partialmargin', 'Partial Margin '),
    ]
    
    margin_order_create = fields.Selection(
        selection=MARGIN_TYPE_SELECTION,
        string="Margin Order",
        required=True,
          # Set a default value if needed
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super(PurchaseLCMargin, self).create(vals_list)

        # If you need to do any post-processing on the records:
        for record in records:
            # Your custom logic here
            pass

        return records
