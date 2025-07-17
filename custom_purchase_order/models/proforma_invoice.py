from odoo import models, fields, api

class PurchaseOrder(models.Model):
    _inherit = 'foreign.create.rfq'

    proforma_invoice_no = fields.Char(string="Proforma Invoice Number")
    proforma_invoice_date = fields.Date(string="Proforma Invoice Date")
    vendor_id = fields.Many2one('res.partner', string='Supplier')  # Maps to Supplier  # Maps to Buyer
    authorized_by = fields.Char(string='Signature')  # Maps to Signature
    incoterm = fields.Many2one('account.incoterms', string="Incoterm")
    validity_period= fields.Date(string='Validity Until', )
    payment_term = fields.Selection([
        ('cad', 'CAD'),
        ('lc', 'LC'),
        ('tt', 'TT'),
        ('franco', 'FRANCO'),
    ], string='Payment Term', tracking=True , default="lc")
    terms_conditions = fields.Text(string='Terms and Conditions')
    shipping_origin = fields.Char(string='Shipping Origin', )
    shipping_destination = fields.Char(string='Shipping Destination', )
    shipping_method = fields.Selection([
        ('sea', 'Sea Freight'),
        ('air', 'Air Freight'),
        ('land', 'Land Transport'),
    ], string='Shipping Method', )
    currency_id = fields.Many2one('res.currency', string='Currency' ,default=lambda self: self.env.company.currency_id)  # Maps to currency
    exchange_rate = fields.Float(string='Exchange Rate', default=1.0, readonly=True,help='Exchange rate applied if supplier currency differs from payment currency')  # Optional
    total_amount = fields.Float(string='Total Price', compute='_compute_total_amount',store=True)  # Maps to total_amount
    estimated_delivery_date = fields.Date(string='Estimated Delivery Date', )
    country_of_origin = fields.Many2one('res.country', string='Country of Origin',)

    
    MOD_OF_SHIPMENT_TYPE_SELECTION = [
        ('air', 'AIR'),
        ('sea', 'SEA'),
    ]
    
    mod_of_shipment = fields.Selection(
        selection=MOD_OF_SHIPMENT_TYPE_SELECTION,
        string="Mod of Shipment ",
        default='air',  # Set a default value if needed
    )
    port_of_loading = fields.Many2one('purchase.port.loading',string="Port Of Loading")
    port_of_discharge = fields.Many2one('purchase.port.loading',string="Port Of Discharge")    
    port_of_final_destination = fields.Many2one('purchase.port.loading',string="Port Of Final Destination") 
    payment_terms = fields.Float(string="Custom Duty Tax")

    @api.depends('line_ids.quantity', 'line_ids.price_unit')
    def _compute_total_amount(self):
        for record in self:
            record.total_amount = sum(line.quantity * line.price_unit for line in record.line_ids)