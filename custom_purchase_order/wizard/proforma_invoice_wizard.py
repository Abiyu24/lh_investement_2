from odoo import fields, models

class ProformaInvoiceWizard(models.TransientModel):
    _name = 'proforma.invoice.wizard'
    _description = 'Proforma Invoice Wizard'

   # market_analysis_id = fields.Many2one('custom.market.analysis', string='Market Analysis')
    rfq_id = fields.Many2one('foreign.create.rfq', string='RFQ')
    #foreign_rfq_id= fields.many2one('foreign.create.rfq', string='')
    proforma_invoice_ids = fields.One2many('proforma.invoice.wizard.line', 'wizard_id', string='Proforma Invoices')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    validity_period = fields.Date(string='Validity Period', required=True)
    vendor_id = fields.Many2one('res.partner', string='Supplier', required=True)
    buyer_id = fields.Many2one('res.partner', string='Buyer', required=True)
    authorized_by = fields.Char(string='Signature')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True)
    exchange_rate = fields.Float(string='Exchange Rate', default=1.0)
    proforma_invoice_date = fields.Date(string='Proforma Invoice Date', default=fields.Date.today, required=True)
    def action_create_invoices(self):
        self.ensure_one()
        for line in self.proforma_invoice_ids:
            invoice_vals = {
                'proforma_invoice_no': self.env['ir.sequence'].next_by_code('market.analysis'),
                'proforma_invoice_date': line.proforma_invoice_date,
                'validity_period': line.validity_period,
                'vendor_id': line.vendor_id.id,
                'buyer_id': line.buyer_id.id,
                'authorized_by': line.authorized_by,
                'currency_id': line.currency_id.id,
                'exchange_rate': line.exchange_rate,
                'incoterm': line.incoterm,
                'terms_conditions': line.terms_conditions,
                'payment_term': line.payment_term.id,
                'country_of_origin': line.country_of_origin.id,
                'shipping_method': line.shipping_method,
                'port_of_loading': line.port_of_loading,
                'port_of_discharge': line.port_of_discharge,
                'port_of_final_destination': line.port_of_final_destination,
                'state': 'draft',
                'line_ids': [(0, 0, {
                    'product_id': line_item.product_id.id,
                    'description': line_item.description,
                    'quantity': line_item.quantity,
                    'uom_id': line_item.uom_id.id,
                    'price_unit': line_item.price_unit,
                    'hs_code': line_item.hs_code,
                    'country_id': line_item.country_id.id,
                }) for line_item in line.line_ids],
            }
            self.env['custom.market.analysis'].create(invoice_vals)
        return {'type': 'ir.actions.act_window_close'}

class ProformaInvoiceWizardLine(models.TransientModel):
    _name = 'proforma.invoice.wizard.line'
    _description = 'Proforma Invoice Wizard Line'

    wizard_id = fields.Many2one('proforma.invoice.wizard', string='Wizard', required=True)
    proforma_invoice_date = fields.Date(string='Proforma Invoice Date', default=fields.Date.today, required=True)
    validity_period = fields.Date(string='Validity Period', required=True)
    vendor_id = fields.Many2one('res.partner', string='Supplier', required=True)
    buyer_id = fields.Many2one('res.partner', string='Buyer', required=True)
    authorized_by = fields.Char(string='Signature')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True)
    exchange_rate = fields.Float(string='Exchange Rate', default=1.0)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    incoterm = fields.Selection([
        ('EXW', 'Ex Works'),
        ('FOB', 'Free on Board'),
        ('CIF', 'Cost, Insurance, Freight'),
        ('DAP', 'Delivered at Place'),
    ], string='Incoterms', required=True)
    terms_conditions = fields.Text(string='Terms and Conditions')
    payment_term = fields.Many2one('account.payment.term', string='Payment Term', required=True)
    country_of_origin = fields.Many2one('res.country', string='Country of Origin', required=True)
    description = fields.Text(string='Description')
    quantity = fields.Float(string='Quantity', required=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True)
    price_unit = fields.Float(string='Rate', required=True)
    hs_code = fields.Char(string='HS Code', required=True)
    country_id = fields.Many2one('res.country', string='Country')

    shipping_method = fields.Selection([
        ('sea', 'Sea Freight'),
        ('air', 'Air Freight'),
        ('land', 'Land Transport'),
    ], string='Shipping Method', required=True)
    port_of_loading = fields.Char(string='Port of Loading', required=True)
    port_of_discharge = fields.Char(string='Port of Discharge', required=True)
    port_of_final_destination = fields.Char(string='Port of Final Destination', required=True)
    line_ids = fields.One2many('proforma.invoice.wizard.line.item', 'wizard_line_id', string='Description of Goods')
    proforma_invoice_date = fields.Date(string='Proforma Invoice Date', default=fields.Date.today, required=True)

class ProformaInvoiceWizardLineItem(models.TransientModel):
    _name = 'proforma.invoice.wizard.line.item'
    _description = 'Proforma Invoice Wizard Line Item'

    wizard_line_id = fields.Many2one('proforma.invoice.wizard.line', string='Wizard Line', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    description = fields.Text(string='Description')
    quantity = fields.Float(string='Quantity', required=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True)
    price_unit = fields.Float(string='Rate', required=True)
    hs_code = fields.Char(string='HS Code', required=True)
    country_id = fields.Many2one('res.country', string='Country')
